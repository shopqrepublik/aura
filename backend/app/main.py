"""
AURA backend — FastAPI skeleton implementing the API contract from spec §12.

Recognition strategy history (see README "Распознавание" section for the
full history with numbers):
  1. Closed-candidate-list prompt ("pick an id from this catalog or null") —
     the spec §8.1 "retrieval on a controlled set" as originally read.
  2. Two-stage (closed): text shortlist of 3 + visual verification against 3
     real reference images — added after finding the model was pattern-
     matching same-artist works from memory instead of comparing pixels.
  3. Open + fuzzy-match only: recognize_open() (no candidate list at all)
     + fuzzy_match_catalog() against DEMO_ARTWORKS, text score as the final
     answer. Fixed the "forced wrong choice" failure mode from (1)/(2), but
     text similarity alone can't be both permissive (to recover legitimate
     translations/paraphrases) and safe (to reject a model that confidently
     misidentifies a photo as a *different real* catalog painting) — see (4).
  4. Hybrid, single candidate: open recognition -> fuzzy_match_catalog()
     (candidate screen, not a final answer) -> visual_verify_single_candidate()
     (ONE reference image, only when a candidate was actually found). Two
     fast paths skip the vision call entirely: nothing recognized, or
     nothing catalog-adjacent by text. Text matching's job is now recall
     (find plausible candidates, tolerate false positives like the model
     saying "Study of Olympia" scoring high against our "Olympia" entry);
     the visual step's job is precision (reject same-title/same-artist
     look-alikes that don't actually match on pixels — this is what catches
     a Cézanne still life confidently misidentified as a different, real
     Cézanne still life, which pure text similarity structurally cannot).
  5. Current — hybrid, runner-up retry: a full 101-image self-recognition
     audit found 23/26 no-matches were the TOP text candidate being
     correctly rejected at the visual stage because it was the WRONG
     catalog entry (fuzzy_match_catalog only ever tried its single best
     text match, and a same-artist decoy can coincidentally out-score the
     true match when the model answers in a different title language —
     rapidfuzz's char-level ratio doesn't know French from noise, and
     "Manet"/"Monet" are one Levenshtein edit apart). Now retries
     visual_verify_single_candidate() against fuzzy_match_catalog()'s
     runner-up when the top candidate fails — one extra vision call, only
     on an already-rejected top candidate, so this can't slow down an
     already-successful match and doesn't touch the confident-wrong
     guarantee (Stage 2 is still the only path to a returned artwork_id).
     A real but partial fix: recovers some of the 23 (confirmed against
     Régates à Argenteuil, Vue de toits, Portrait of the Artist with the
     Yellow Christ) but not all of them (Luncheon on the Grass, Lola de
     Valence still fail — their true match wasn't the runner-up either).
  6. Museum-scoped (Phase 3, multi-museum): fuzzy_match_catalog() now takes
     museum_id and only scores DEMO_ARTWORKS entries belonging to that
     museum. Before this, a second museum's catalog (e.g. Orangerie) would
     have been scored against every Orsay entry too, risking a same-titled
     or similarly-described work from the wrong museum winning the fuzzy
     match. Regression-checked against 5 Orsay reference images post-change
     (4/5 correct, 1 no-match — same partial-effectiveness as item 5 above,
     not a new failure introduced by scoping).

Requires OPENAI_API_KEY in the environment (or a .env file, see
.env.example). The old random mock is available only when
ALLOW_RECOGNITION_MOCK=true, so production cannot silently return random
artworks if the AI provider is misconfigured.

Run:
    pip install -r requirements.txt
    copy the repo-root .env.example to .env and fill in OPENAI_API_KEY
    uvicorn app.main:app --reload --port 8090
"""
import base64
import hashlib
import json
import math
import os
import random
import re
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from threading import Lock
from typing import Optional, List, Dict, Any, Callable

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

load_dotenv()  # reads .env from the repo root if present; no-op otherwise

# Real user accounts (email magic link + Google; Apple deferred until an
# Apple Developer account exists) replace the old anonymous in-memory
# VISITS dict below -- every /v1/visits* endpoint now requires a verified
# Supabase JWT and persists to real Postgres (see app/db.py, app/auth.py).
from .auth import get_current_user, get_optional_current_user  # noqa: E402
from .admin import (  # noqa: E402
    _link_analytics_identity,
    _trusted_internal_request,
    _validate_analytics_session,
    record_product_event_from_server,
    router as admin_router,
)
from .catalog import (  # noqa: E402
    CatalogUnavailableError,
    InstitutionNotReadyError,
    InstitutionRuntimeConfig,
    aggregate_eligible_value,
    count_catalog_artworks,
    get_catalog_artwork,
    get_catalog_artworks_by_ids,
    get_recognition_candidates,
    get_global_recognition_candidates,
    get_institution_runtime_config,
)
from .db import SessionLocal, get_db  # noqa: E402
from .models import Artwork, ArtworkLocalization, InstitutionProfile, Museum, RecognitionAttempt, UncatalogedSighting, User, Visit, VisitArtwork  # noqa: E402
from .visual_retrieval import rank_visual_candidates  # noqa: E402

app = FastAPI(title="AURA API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://elyio.vercel.app",
        "https://elyio.co",
        "https://www.elyio.co",
        "http://localhost:3000",  # local web/ dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_router)


@app.middleware("http")
async def limit_public_event_body(request: Request, call_next):
    if request.url.path == "/v1/events":
        body = await request.body()
        max_bytes = int(os.environ.get("EVENT_BODY_MAX_BYTES", "32768"))
        if len(body) > max_bytes:
            return JSONResponse(status_code=413, content={"detail": "event payload too large"})
    return await call_next(request)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ALLOW_RECOGNITION_MOCK = os.environ.get("ALLOW_RECOGNITION_MOCK", "").lower() in {"1", "true", "yes"}
MAX_RECOGNITION_IMAGE_BASE64_CHARS = int(os.environ.get("MAX_RECOGNITION_IMAGE_BASE64_CHARS", "8000000"))
OPENAI_RECOGNITION_RETRIES = int(os.environ.get("OPENAI_RECOGNITION_RETRIES", "2"))
OPENAI_RECOGNITION_TIMEOUT_SECONDS = float(os.environ.get("OPENAI_RECOGNITION_TIMEOUT_SECONDS", "35"))
RECOGNITION_MODEL = os.environ.get("OPENAI_RECOGNITION_MODEL", "gpt-4o")
INDICATIVE_VALUE_MODEL = os.environ.get("OPENAI_INDICATIVE_VALUE_MODEL", RECOGNITION_MODEL)
# Stage 2 (visual_verify_single_candidate) TRIED gpt-4o-mini to cut slow-path
# latency — rolled back. On the 101-catalog test it dropped 76/101 -> 71/101
# (2 confirmed false negatives on exact-title-match candidates gpt-4o accepted
# correctly), and on the 13 real-photo test it flipped BOTH previously-correct
# in-catalog matches (Cezanne onions, Vetheuil) to wrong rejections, 12/13 ->
# 11/13. Confident-wrong stayed at 0 in both cases — this is a real-accuracy
# regression, not a safety one — but "don't regress accuracy" was the explicit
# bar, so Stage 2 stays on gpt-4o. See README for the full before/after numbers.
VISUAL_VERIFY_MODEL = "gpt-4o"
INDICATIVE_VALUE_CACHE: dict[str, dict] = {}



DEMO_ARTWORKS = [
    {"id": "orsay_rf_1995_10", "artist": "Gustave Courbet", "title": "L'Origine du monde", "year": "1866", "hall": None, "inventory_number": "RF 1995 10", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Origin-of-the-World.jpg", "estimate_low": 14, "estimate_high": 22, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1668", "artist": "Édouard Manet", "title": "Luncheon on the Grass", "year": "1863", "hall": None, "inventory_number": "RF 1668", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Luncheon%20on%20the%20Grass%20-%20Google%20Art%20Project.jpg", "estimate_low": 55, "estimate_high": 85, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2739", "artist": "Pierre-Auguste Renoir", "title": "Bal du moulin de la Galette", "year": "1876", "hall": None, "inventory_number": "RF 2739", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Renoir%2C%20Pierre-Auguste%20-%20Dance%20at%20Le%20Moulin%20de%20la%20Galette%2C%201876.jpg", "estimate_low": 70, "estimate_high": 90, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_644", "artist": "Édouard Manet", "title": "Olympia", "year": "1863", "hall": None, "inventory_number": "RF 644", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Olympia%20-%20Google%20Art%20Project%203.jpg", "estimate_low": 55, "estimate_high": 85, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1975_19", "artist": "Vincent van Gogh", "title": "Starry Night Over the Rhone", "year": "1888", "hall": None, "inventory_number": "RF 1975 19", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20Starry%20Night%20-%20Google%20Art%20Project.jpg", "estimate_low": 95, "estimate_high": 130, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1951_42", "artist": "Vincent van Gogh", "title": "The Church at Auvers", "year": "1890", "hall": None, "inventory_number": "RF 1951 42", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20Church%20in%20Auvers-sur-Oise%2C%20View%20from%20the%20Chevet%20-%20Google%20Art%20Project.jpg", "estimate_low": 45, "estimate_high": 80, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_325", "artist": "Gustave Courbet", "title": "A Burial at Ornans", "year": "1849-1850", "hall": None, "inventory_number": "RF 325", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Courbet%20-%20A%20Burial%20at%20Ornans%20-%20Google%20Art%20Project.jpg", "estimate_low": 14, "estimate_high": 25, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_253", "artist": "William-Adolphe Bouguereau", "title": "The Birth of Venus", "year": "1879", "hall": None, "inventory_number": "RF 253", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20%281825-1905%29%20-%20The%20Birth%20of%20Venus%20%281879%29.jpg", "estimate_low": 3.5, "estimate_high": 8, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_699", "artist": "James McNeill Whistler", "title": "Whistler's Mother", "year": "1871", "hall": None, "inventory_number": "RF 699", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Whistlers%20Mother%20high%20res.jpg", "estimate_low": 2.5, "estimate_high": 6, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2257", "artist": "Gustave Courbet", "title": "The Painter's Studio", "year": "1854-1855", "hall": None, "inventory_number": "RF 2257", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Courbet%20LAtelier%20du%20peintre.jpg", "estimate_low": 14, "estimate_high": 24, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1984", "artist": "Edgar Degas", "title": "L'Absinthe", "year": "1875", "hall": None, "inventory_number": "RF 1984", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20In%20a%20Caf%C3%A9%20-%20Google%20Art%20Project%202.jpg", "estimate_low": 13, "estimate_high": 25, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_219", "artist": "Jean-Auguste-Dominique Ingres", "title": "The Source", "year": "1856", "hall": None, "inventory_number": "RF 219", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean%20Auguste%20Dominique%20Ingres%20-%20The%20Spring%20-%20Google%20Art%20Project%202.jpg", "estimate_low": 3, "estimate_high": 8, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2772", "artist": "Édouard Manet", "title": "The Balcony", "year": "1868", "hall": None, "inventory_number": "RF 2772", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20The%20Balcony%20-%20Google%20Art%20Project.jpg", "estimate_low": 25, "estimate_high": 45, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_592", "artist": "Jean-François Millet", "title": "The Gleaners", "year": "1857", "hall": None, "inventory_number": "RF 592", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-Fran%C3%A7ois%20Millet%20-%20Gleaners%20-%20Google%20Art%20Project.jpg", "estimate_low": 2.5, "estimate_high": 7, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2738", "artist": "Pierre-Auguste Renoir", "title": "La Balançoire", "year": "1876", "hall": None, "inventory_number": "RF 2738", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Swing-Renoir.jpeg", "estimate_low": 15, "estimate_high": 35, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2010_8", "artist": "William-Adolphe Bouguereau", "title": "Dante and Virgil in Hell", "year": "1850", "hall": None, "inventory_number": "RF 2010 8", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William%20Bouguereau%20-%20Dante%20and%20Virgile%20-%20Google%20Art%20Project%202.jpg", "estimate_low": 3.5, "estimate_high": 7, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_755", "artist": "Pierre-Auguste Renoir", "title": "Girls at the Piano", "year": "1892", "hall": None, "inventory_number": "RF 755", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Auguste%20Renoir%20-%20Young%20Girls%20at%20the%20Piano%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2765", "artist": "Paul Gauguin", "title": "Tahitian Women on the Beach", "year": "1890", "hall": None, "inventory_number": "RF 2765", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20056.jpg", "estimate_low": 85, "estimate_high": 120, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2773", "artist": "Claude Monet", "title": "Women in the Garden", "year": "1866", "hall": None, "inventory_number": "RF 2773", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20024.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_273", "artist": "Alexandre Cabanel", "title": "The Birth of Venus", "year": "1863", "hall": None, "inventory_number": "RF 273", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Alexandre%20Cabanel%20-%20The%20Birth%20of%20Venus%20-%20Google%20Art%20Project%202.jpg", "estimate_low": 1, "estimate_high": 3, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1949_17", "artist": "Vincent van Gogh", "title": "Self-portrait", "year": "1889", "hall": None, "inventory_number": "RF 1949 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20Self-Portrait%20-%20Google%20Art%20Project.jpg", "estimate_low": 55, "estimate_high": 80, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1992", "artist": "Édouard Manet", "title": "The Fifer", "year": "1866", "hall": None, "inventory_number": "RF 1992", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Manet%2C%20Edouard%20-%20Young%20Flautist%2C%20or%20The%20Fifer%2C%201866%20%282%29.jpg", "estimate_low": 25, "estimate_high": 45, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_051804048", "artist": "Jean-François Millet", "title": "The Angelus", "year": "1858", "hall": None, "inventory_number": "RF 051804048", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/JEAN-FRAN%C3%87OIS%20MILLET%20-%20El%20%C3%81ngelus%20%28Museo%20de%20Orsay%2C%201857-1859.%20%C3%93leo%20sobre%20lienzo%2C%2055.5%20x%2066%20cm%29.jpg", "estimate_low": 3, "estimate_high": 8, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2210", "artist": "Edgar Degas", "title": "The Bellelli Family", "year": "1858", "hall": None, "inventory_number": "RF 2210", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20The%20Bellelli%20Family%20-%20Google%20Art%20Project.jpg", "estimate_low": 20, "estimate_high": 38, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1984_164", "artist": "Claude Monet", "title": "The Magpie", "year": "1868", "hall": None, "inventory_number": "RF 1984 164", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Magpie%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2718", "artist": "Gustave Caillebotte", "title": "Les raboteurs de parquet", "year": "1875", "hall": None, "inventory_number": "RF 2718", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Caillebotte%20-%20The%20Floor%20Planers%20-%20Google%20Art%20Project.jpg", "estimate_low": 45, "estimate_high": 70, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2511", "artist": "Georges Seurat", "title": "The Circus", "year": "1891", "hall": None, "inventory_number": "RF 2511", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Georges%20Seurat%20-%20The%20Circus%20-%20Google%20Art%20Project.jpg", "estimate_low": 80, "estimate_high": 140, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1978_13", "artist": "Pierre-Auguste Renoir", "title": "Dance in the City", "year": "1883", "hall": None, "inventory_number": "RF 1978 13", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20019.jpg", "estimate_low": 15, "estimate_high": 35, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1979_64", "artist": "Pierre-Auguste Renoir", "title": "Dance in the Country", "year": "1883", "hall": None, "inventory_number": "RF 1979 64", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre%20Auguste%20Renoir%20-%20Country%20Dance%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 35, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1998_30", "artist": "Édouard Manet", "title": "Berthe Morisot with a Bouquet of Violets", "year": "1872", "hall": None, "inventory_number": "RF 1998 30", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Berthe%20Morisot%20With%20a%20Bouquet%20of%20Violets%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1957_7", "artist": "Claude Monet", "title": "Le Déjeuner sur l'herbe", "year": "1865", "hall": None, "inventory_number": "RF 1957 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Le%20dejeurner%20sur%20l%27herbe%20%28left%20panel%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2205", "artist": "Édouard Manet", "title": "Portrait of Emile Zola", "year": "1868", "hall": None, "inventory_number": "RF 2205", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20049.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_338", "artist": "Gustave Courbet", "title": "The Wounded Man", "year": "1844", "hall": None, "inventory_number": "RF 338", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Portrait%20of%20the%20Artist%20called%20The%20Wounded%20Man%20%28L%27homme%20bless%C3%A9%29%20by%20Gustave%20Courbet.jpg", "estimate_low": 5, "estimate_high": 12, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_64", "artist": "Rosa Bonheur", "title": "Ploughing in the Nivernais", "year": "1849", "hall": None, "inventory_number": "RF 64", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Rosa%20Bonheur%20-%20Ploughing%20in%20Nevers%20-%20Google%20Art%20Project.jpg", "estimate_low": 1.5, "estimate_high": 4, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_88", "artist": "Jean-Léon Gérôme", "title": "Young Greeks Attending a Cock Fight", "year": "1846", "hall": None, "inventory_number": "RF 88", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-L%C3%A9on%20G%C3%A9r%C3%B4me%20-%20Young%20Greeks%20Attending%20a%20Cock%20Fight%20-%20Google%20Art%20Project.jpg", "estimate_low": 4, "estimate_high": 9, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2450", "artist": "Frédéric Bazille", "title": "The Pink Dress", "year": "1864", "hall": None, "inventory_number": "RF 2450", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Fr%C3%A9d%C3%A9ric%20Bazille%20-%20The%20Pink%20Dress%20-%20Google%20Art%20Project.jpg", "estimate_low": 4, "estimate_high": 9, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2778", "artist": "Claude Monet", "title": "Régates à Argenteuil", "year": "1872", "hall": None, "inventory_number": "RF 2778", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Regattas%20at%20Argenteuil%20-%20Google%20Art%20Project.jpg", "estimate_low": 32, "estimate_high": 44, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1983_6", "artist": "Claude Monet", "title": "The artist's garden at Giverny", "year": "1900", "hall": None, "inventory_number": "RF 1983 6", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Monet%20-%20Monets%20Garten%20in%20Giverny.jpg", "estimate_low": 25, "estimate_high": 45, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1976", "artist": "Edgar Degas", "title": "The Ballet Class", "year": "1871", "hall": None, "inventory_number": "RF 1976", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20The%20Ballet%20Class%20-%20Google%20Art%20Project.jpg", "estimate_low": 30, "estimate_high": 55, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1990_7", "artist": "Jean-Léon Gérôme", "title": "Jerusalem", "year": "1867", "hall": None, "inventory_number": "RF 1990 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-L%C3%A9on%20G%C3%A9r%C3%B4me%20Consummatum%20est.jpg", "estimate_low": 2.5, "estimate_high": 6, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_lux_1439", "artist": "Frédéric Bazille", "title": "Bazille's Studio", "year": "1870", "hall": None, "inventory_number": "LUX 1439", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Fr%C3%A9d%C3%A9ric%20Bazille%20-%20Bazille%27s%20Studio%20-%20Google%20Art%20Project.jpg", "estimate_low": 10, "estimate_high": 20, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_876", "artist": "Gustave Caillebotte", "title": "Vue de toits", "year": "1878", "hall": None, "inventory_number": "RF 876", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Caillebotte%20-%20Rooftops%20in%20the%20Snow%20%28snow%20effect%29%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 30, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1981_33", "artist": "William-Adolphe Bouguereau", "title": "The Dance", "year": "1856", "hall": None, "inventory_number": "RF 1981 33", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20%281825-1905%29%20-%20The%20Dance%20%281856%29.jpg", "estimate_low": 2.5, "estimate_high": 6, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1937_7", "artist": "Henri Rousseau", "title": "The Snake Charmer", "year": "1907", "hall": None, "inventory_number": "RF 1937 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/HENRI%20ROUSSEAU%20-%20La%20Encantadora%20de%20Serpientes%20%28Museo%20de%20Orsay%2C%20Par%C3%ADs%2C%201907.%20%C3%93leo%20sobre%20lienzo%2C%20169%20x%20189.5%20cm%29.jpg", "estimate_low": 30, "estimate_high": 55, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1952_17", "artist": "Vincent van Gogh", "title": "The siesta (after Millet)", "year": "1890", "hall": None, "inventory_number": "RF 1952 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20siesta%20%28after%20Millet%29%20-%20Google%20Art%20Project.jpg", "estimate_low": 20, "estimate_high": 38, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1961_6", "artist": "Paul Gauguin", "title": "Arearea", "year": "1892", "hall": None, "inventory_number": "RF 1961 6", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20Arearea%20-%20Google%20Art%20Project.jpg", "estimate_low": 70, "estimate_high": 105, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2749", "artist": "Frédéric Bazille", "title": "Réunion de famille", "year": "1867", "hall": None, "inventory_number": "RF 2749", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/R%C3%A9union%20de%20famille%20-%20Fr%C3%A9d%C3%A9ric%20Bazille%20-%20mus%C3%A9e%20d%27Orsay%20RF%202749.jpg", "estimate_low": 12, "estimate_high": 24, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1944_17", "artist": "Édouard Manet", "title": "The Reading", "year": "1865", "hall": None, "inventory_number": "RF 1944 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20005.jpg", "estimate_low": 6, "estimate_high": 11, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2849", "artist": "Berthe Morisot", "title": "The Cradle", "year": "1872", "hall": None, "inventory_number": "RF 2849", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Berthe%20Morisot%20-%20The%20Cradle%20-%20Google%20Art%20Project.jpg", "estimate_low": 10, "estimate_high": 20, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2795", "artist": "Pierre-Auguste Renoir", "title": "The Bathers", "year": "1918", "hall": None, "inventory_number": "RF 2795", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre%20Auguste%20Renoir%20-%20The%20Bathers%20-%20Google%20Art%20Project.jpg", "estimate_low": 18, "estimate_high": 32, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_729", "artist": "Henri Fantin-Latour", "title": "A Studio at Les Batignolles", "year": "1870", "hall": None, "inventory_number": "RF 729", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20Fantin-Latour%20-%20A%20Studio%20at%20Les%20Batignolles%20-%20Google%20Art%20Project.jpg", "estimate_low": 12, "estimate_high": 25, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1970", "artist": "Paul Cézanne", "title": "La Maison du pendu, Auvers-sur-Oise", "year": "1874", "hall": None, "inventory_number": "RF 1970", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/La%20Maison%20du%20pendu%2C%20Auvers-sur-Oise%2C%20par%20Paul%20C%C3%A9zanne%2C%20FWN%2081.jpg", "estimate_low": 25, "estimate_high": 50, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_d2006_3_5", "artist": "Pierre-Auguste Renoir", "title": "Portrait of Frédéric Bazille Painting", "year": "1867", "hall": None, "inventory_number": "D2006.3.5", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20-%20Fr%C3%A9d%C3%A9ric%20Bazille.jpg", "estimate_low": 4, "estimate_high": 8, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1676", "artist": "Claude Monet", "title": "The Poppy Field near Argenteuil", "year": "1873", "hall": None, "inventory_number": "RF 1676", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Poppy%20Field%20-%20Google%20Art%20Project.jpg", "estimate_low": 38, "estimate_high": 55, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2617", "artist": "Paul Gauguin", "title": "La belle Angèle", "year": "1889", "hall": None, "inventory_number": "RF 2617", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20La%20Belle%20Ang%C3%A8le%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 30, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1959_18", "artist": "Édouard Manet", "title": "L'Asperge", "year": "1880", "hall": None, "inventory_number": "RF 1959 18", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Asparagus%20-%20Google%20Art%20Project.jpg", "estimate_low": 5, "estimate_high": 9, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1991", "artist": "Édouard Manet", "title": "Lola de Valence", "year": "1862", "hall": None, "inventory_number": "RF 1991", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Lola%20de%20Valence%20%281862%29%20-%20Edouard%20Manet%20%28Mus%C3%A9e%20d%27Orsay%2C%20Paris%29.jpg", "estimate_low": 9, "estimate_high": 16, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1977_12", "artist": "Édouard Manet", "title": "Portrait of Monsieur and Madame Auguste Manet", "year": "1860", "hall": None, "inventory_number": "RF 1977 12", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Portrait%20of%20M.%20and%20Mme.%20Auguste%20Manet%20%281860%29%20-%20Edouard%20Manet%20%28Mus%C3%A9e%20d%27Orsay%2C%20Paris%29.jpg", "estimate_low": 9, "estimate_high": 16, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1965_14", "artist": "Vincent van Gogh", "title": "L'Italienne", "year": "1887", "hall": None, "inventory_number": "RF 1965 14", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20Italian%20Woman%20-%20Google%20Art%20Project.jpg", "estimate_low": 25, "estimate_high": 42, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_4046", "artist": "Edgar Degas", "title": "The Tub", "year": "1886", "hall": None, "inventory_number": "RF 4046", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20Le%20Tub%20%281886%20Mus%C3%A9e%20d%27Orsay%29.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2010_7", "artist": "William-Adolphe Bouguereau", "title": "Equality Before Death", "year": "1848", "hall": None, "inventory_number": "RF 2010 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Bouguereau%20-%20%C3%A9galit%C3%A9%20devant%20la%20mort%201848.jpg", "estimate_low": 3.5, "estimate_high": 7, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_3666", "artist": "Pierre-Auguste Renoir", "title": "Claude Monet", "year": "1875", "hall": None, "inventory_number": "RF 3666", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Auguste%20Renoir%20-%20Claude%20Monet%20-%20Google%20Art%20Project.jpg", "estimate_low": 10, "estimate_high": 18, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_do_1986_16", "artist": "Albert Edelfelt", "title": "Portrait of Louis Pasteur", "year": "1885", "hall": None, "inventory_number": "DO 1986 16", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Albert%20Edelfelt%20-%20Louis%20Pasteur%20-%201885.jpg", "estimate_low": 1.5, "estimate_high": 3.5, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1994_2", "artist": "Paul Gauguin", "title": "Portrait of the Artist with the Yellow Christ", "year": "1890", "hall": None, "inventory_number": "RF 1994 2", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20Portrait%20of%20the%20Artist%20with%20the%20Yellow%20Christ%20%281890-91%29.jpg", "estimate_low": 10, "estimate_high": 20, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2010_4", "artist": "William-Adolphe Bouguereau", "title": "The Oreads", "year": "1902", "hall": None, "inventory_number": "RF 2010 4", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20-%20Les%20Or%C3%A9ades.jpg", "estimate_low": 4, "estimate_high": 9, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1994", "artist": "Édouard Manet", "title": "Suzanne Manet Playing the Piano", "year": "1867", "hall": None, "inventory_number": "RF 1994", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/%C3%89douard%20Manet%20-%20Madame%20Manet%20ou%20Piano.jpg", "estimate_low": 6, "estimate_high": 11, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2242", "artist": "Henri de Toulouse-Lautrec", "title": "La Toilette", "year": "1889", "hall": None, "inventory_number": "RF 2242", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/%28Albi%29%20Rousse%20%28La%20Toilette%29%20-%201889%20-%20Henri%20de%20Toulouse-Lautrec%20-%20Mus%C3%A9e%20d%27Orsay%2C%20Paris.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2817", "artist": "Paul Cézanne", "title": "Still Life with Onions", "year": "1898", "hall": None, "inventory_number": "RF 2817", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20C%C3%A9zanne%20-%20Still%20Life%20with%20Onions%20-%20Google%20Art%20Project.jpg", "estimate_low": 30, "estimate_high": 50, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2740", "artist": "Pierre-Auguste Renoir", "title": "Torse, effet de soleil", "year": "1875", "hall": None, "inventory_number": "RF 2740", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Torso%20Effect%20of%20Sunlight%20Renoir%201876.jpg", "estimate_low": 10, "estimate_high": 18, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2011", "artist": "Claude Monet", "title": "A Cart on the Snowy Road at Honfleur", "year": "1865", "hall": None, "inventory_number": "RF 2011", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Monet%2C%20A%20Cart%20on%20the%20Snowy%20Road%20at%20Honfleur%20%281865%20or%201867%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_inv_10168", "artist": "Edouard Louis Dubufe", "title": "The Congress of Paris", "year": "1856", "hall": None, "inventory_number": "INV 10168", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Dubufe%20Congr%C3%A8s%20de%20Paris.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1959_5", "artist": "Paul Gauguin", "title": "Vairumati", "year": "1897", "hall": None, "inventory_number": "RF 1959 5", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20135.jpg", "estimate_low": 25, "estimate_high": 45, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1664", "artist": "Henri Fantin-Latour", "title": "Homage to Delacroix", "year": "1864", "hall": None, "inventory_number": "RF 1664", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Hommage%20%C3%A0%20Delacroix%20-%20Henri%20Fantin-Latour.jpg", "estimate_low": 10, "estimate_high": 20, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1966_7", "artist": "Paul Gauguin", "title": "Self-portrait with hat", "year": "1893", "hall": None, "inventory_number": "RF 1966 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20111.jpg", "estimate_low": 8, "estimate_high": 16, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2173", "artist": "Henri Fantin-Latour", "title": "Around the Piano", "year": "1885", "hall": None, "inventory_number": "RF 2173", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20fantin-latour%2C%20attorno%20al%20piano%2C%201885%20-%20frameless.jpg", "estimate_low": 6, "estimate_high": 14, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1993", "artist": "Édouard Manet", "title": "Clair de lune sur le port de Boulogne", "year": "1869", "hall": None, "inventory_number": "RF 1993", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Ed.%20Manet.%20Clair%20de%20lune%20sur%20le%20port%20de%20Boulogne.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2774", "artist": "Claude Monet", "title": "The Luncheon", "year": "1873", "hall": None, "inventory_number": "RF 2774", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Monet%20Luncheon.jpg", "estimate_low": 10, "estimate_high": 25, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2244", "artist": "Pierre-Auguste Renoir", "title": "Portrait of Madame Charpentier", "year": "1876", "hall": None, "inventory_number": "RF 2244", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20-%20Madame%20Charpentier%20-%2001.jpg", "estimate_low": 20, "estimate_high": 32, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_bx_d_18", "artist": "Henri Gervex", "title": "Rolla", "year": "1878", "hall": None, "inventory_number": "Bx D 18", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20Gervex%20-%20Rolla%2003.jpg", "estimate_low": 1.8, "estimate_high": 3.5, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1967_5", "artist": "Frédéric Bazille", "title": "L'Ambulance improvisée", "year": "1865", "hall": None, "inventory_number": "RF 1967 5", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Bazille%20L%27Ambulance%20improvis%C3%A9e%201865.jpg", "estimate_low": 5, "estimate_high": 10, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1978", "artist": "Edgar Degas", "title": "Ballet Rehearsal on Stage", "year": "1874", "hall": None, "inventory_number": "RF 1978", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20Ballet%20Rehearsal%20on%20Stage%20-%20Google%20Art%20Project.jpg", "estimate_low": 22, "estimate_high": 40, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2325", "artist": "Vincent van Gogh", "title": "Restaurant de la Sirène à Asnières", "year": "1887", "hall": None, "inventory_number": "RF 2325", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Van%20Gogh%20-%20Das%20Restaurant%20de%20la%20Sir%C3%A9ne%20in%20Asni%C3%A9res.jpeg", "estimate_low": 10, "estimate_high": 20, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1944_9", "artist": "Vincent van Gogh", "title": "Portrait of Eugène Boch", "year": "1888", "hall": None, "inventory_number": "RF 1944 9", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20Eug%C3%A8ne%20Boch%20-%20Google%20Art%20Project.jpg", "estimate_low": 35, "estimate_high": 60, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1951_40", "artist": "Alfred Sisley", "title": "Vue du canal Saint-Martin", "year": "1870", "hall": None, "inventory_number": "RF 1951 40", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Sisley%2C%20St%20Martin%20Canal%201870.jpg", "estimate_low": 4, "estimate_high": 8, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1973_25", "artist": "Vincent van Gogh", "title": "Hôpital Saint-Paul à Saint-Rémy-de-Provence", "year": "1889", "hall": None, "inventory_number": "RF 1973 25", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Hospital%20in%20Saint-Remy.jpg", "estimate_low": 14, "estimate_high": 26, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1955_20", "artist": "Paul Cézanne", "title": "Pont de Maincy", "year": "1879", "hall": None, "inventory_number": "RF 1955 20", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pont%20de%20Maincy%2C%20par%20Paul%20C%C3%A9zanne.jpg", "estimate_low": 20, "estimate_high": 40, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2417", "artist": "Edgar Degas", "title": "L'Orchestre de l'Opéra", "year": "1868", "hall": None, "inventory_number": "RF 2417", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20The%20Orchestra%20at%20the%20Opera%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_3736", "artist": "Edgar Degas", "title": "Lorenzo Pagans and Auguste de Gas", "year": "1871", "hall": None, "inventory_number": "RF 3736", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20Lorenzo%20Pagans%20and%20Auguste%20de%20Gas%20-%20Google%20Art%20Project.jpg", "estimate_low": 8, "estimate_high": 16, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1972", "artist": "Paul Cézanne", "title": "Apples and Oranges", "year": "1899", "hall": None, "inventory_number": "RF 1972", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Nature%20morte%20aux%20pommes%20et%20aux%20oranges%2C%20par%20Paul%20C%C3%A9zanne.jpg", "estimate_low": 35, "estimate_high": 55, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1959", "artist": "Henri Fantin-Latour", "title": "Un coin de table", "year": "1872", "hall": None, "inventory_number": "RF 1959", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20Fantin-Latour%20-%20By%20the%20Table%20-%20Google%20Art%20Project.jpg", "estimate_low": 10, "estimate_high": 20, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_inv_3451", "artist": "Thomas Couture", "title": "The Romans of the Decadence", "year": "1847", "hall": None, "inventory_number": "INV 3451", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Thomas%20Couture%20-%20Romans%20during%20the%20Decadence%20-%20Google%20Art%20Project.jpg", "estimate_low": 0.8, "estimate_high": 2, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1956_13", "artist": "Paul Cézanne", "title": "La Femme à la cafetière (Woman with a Coffeepot)", "year": "1895", "hall": None, "inventory_number": "RF 1956 13", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20C%C3%A9zanne%20-%20Woman%20with%20a%20Coffeepot%20-%20Google%20Art%20Project.jpg", "estimate_low": 10, "estimate_high": 20, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1937_41", "artist": "Claude Monet", "title": "The Railway Bridge at Argenteuil", "year": "1874", "hall": None, "inventory_number": "RF 1937 41", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Le%20Pont%20d%27Argenteuil%20-%20Claude%20Monet.jpg", "estimate_low": 35, "estimate_high": 45, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2621", "artist": "Claude Monet", "title": "Woman with a Parasol, facing left", "year": "1886", "hall": None, "inventory_number": "RF 2621", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Femme%20%C3%A0%20l%27ombrelle%20tourn%C3%A9e%20vers%20la%20gauche%20-%20Claude%20Monnet%20-%20Mus%C3%A9e%20d%27Orsay%20RF%202621.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2661", "artist": "Édouard Manet", "title": "Portrait of Stéphane Mallarmé", "year": "1876", "hall": None, "inventory_number": "RF 2661", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20St%C3%A9phane%20Mallarm%C3%A9%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_1963_3", "artist": "Claude Monet", "title": "Camille Monet on her deathbed", "year": "1879", "hall": None, "inventory_number": "RF 1963 3", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Camille%20Monet%20sur%20son%20lit%20de%20mort.JPG", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_lux_367", "artist": "Camille Pissarro", "title": "The Red Roofs, Côte Saint-Denis at Pontoise, Winter Effect", "year": "1877", "hall": None, "inventory_number": "LUX 367", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Camille%20Pissarro%20011.jpg", "estimate_low": 8, "estimate_high": 18, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2020", "artist": "Alfred Sisley", "title": "Flooding at Port-Marly", "year": "1876", "hall": None, "inventory_number": "RF 2020", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/La%20inundaci%C3%B3n%20en%20Port%20Marly%2C%20por%20Alfred%20Sisley.jpg", "estimate_low": 7, "estimate_high": 14, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_8048", "artist": "Claude Monet", "title": "La Rue Montorgueil", "year": "1878", "hall": None, "inventory_number": "8048", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Rue%20Montorgueil%20in%20Paris.%20Celebration%20of%20June%2030%2C%201878%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True, "museum_id": "orsay"},
    {"id": "orsay_rf_2787", "artist": "Alfred Sisley", "title": "The Regatta at Molesey", "year": "1874", "hall": None, "inventory_number": "RF 2787", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Alfred%20Sisley%20050.jpg", "estimate_low": 6, "estimate_high": 12, "needs_editorial_review": True, "museum_id": "orsay"},
    # Manual editorial addition (#101, not from the sitelinks-ranked Top 100 pull) —
    # this is the spec's own flagship walkthrough example (§7.4) and the original
    # demo catalog's very first entry. Real Wikidata record (Q17496088, RF 2006),
    # it just has 0 Wikidata sitelinks so it never surfaced in the automated ranking.
    {"id": "orsay_rf_2006", "artist": "Claude Monet", "title": "Vétheuil, Sunset", "year": "1900", "hall": None, "inventory_number": "RF 2006", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20monet%2C%20v%C3%A9theuil%2C%20sole%20al%20tramonto%2C%201900%20ca.JPG", "estimate_low": 20, "estimate_high": 40, "needs_editorial_review": True, "museum_id": "orsay"},

    # --- Musée de l'Orangerie (Phase 3 Étape 1 pilot) -----------------------
    # Built via Wikidata CirrusSearch haswbstatement:P195=Q726781 (WDQS/SPARQL
    # was in a sustained outage — see README), then wbgetentities for full
    # claims. 19 raw hits; one (Q60363894, "Jean Walter-Paul Guillaume
    # Collection", P31=Q27699276 "collection") isn't an artwork and was
    # dropped, leaving these 18. estimate_low/high are intentionally None —
    # Layer 2 (estimates, why/where/rarity, Kids-mode review) is a separate,
    # human-gated step per museum, not written yet for this museum.
    # 3 of the 18 have NO free image (Wikidata P18 empty, no Commons file
    # found either): Portrait de Mademoiselle Chanel and Portrait de
    # Guillaume Apollinaire (both Marie Laurencin, d.1956 -> public domain
    # 2027-01-01) and Portrait de Paul Guillaume (Kees van Dongen, d.1968 ->
    # public domain 2039-01-01) — still under copyright, not merely a data
    # gap. Excluded from DEMO_ARTWORKS for now since the recognition
    # pipeline requires a reference image; kept here as a record of what
    # exists but can't be added yet.
    {"id": "orangerie_rf_1960_44", "artist": "Amedeo Modigliani", "title": "Portrait of Paul Guillaume, Novo Pilota", "year": "1915", "hall": None, "inventory_number": "RF 1960-44", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Modigliani%2C%20Amedeo%20-%20Paul%20Guillaume.%20Nova%20Pilota.jpg", "estimate_low": 7.4, "estimate_high": 13.8, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_rf_1960_25", "artist": "Henri Rousseau", "title": "The Wedding Party", "year": "1905", "hall": None, "inventory_number": "RF 1960-25", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20Rousseau%2C%20dit%20le%20Douanier%20-%20The%20Wedding%20Party%20-%20Google%20Art%20Project.jpg", "estimate_low": 9.2, "estimate_high": 18.4, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_rf_1960_46", "artist": "Amedeo Modigliani", "title": "Red-Haired Girl", "year": "1915", "hall": None, "inventory_number": "RF 1960-46", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Amedeo%20Modigliani%20-%20Fille%20rousse.jpg", "estimate_low": 4.6, "estimate_high": 9.2, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_rf_1960_36", "artist": "André Derain", "title": "Portrait of Madame Paul Guillaume with a Large Hat", "year": "1928", "hall": None, "inventory_number": "RF 1960-36", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Portrait%20de%20Madame%20Paul%20Guillaume%20au%20grand%20chapeau.jpg", "estimate_low": 0.3, "estimate_high": 1.1, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_rf_1963_30", "artist": "Henri Rousseau", "title": "Walkers in a Park", "year": "1905", "hall": None, "inventory_number": "RF 1963 30", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Rousseau%20-%20Promeneurs%20dans%20un%20parc%2C%20entre%201900%20et%201910%2C%20RF%201963%2030.jpg", "estimate_low": 2.8, "estimate_high": 6.4, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_inv_20100", "artist": "Claude Monet", "title": "Water Lilies: The Clouds", "year": "1920", "hall": None, "inventory_number": "INV 20100", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Water%20Lilies%20-%20The%20Clouds%20-%20Google%20Art%20Project.jpg", "estimate_low": 23.0, "estimate_high": 41.4, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_inv_20106", "artist": "Claude Monet", "title": "Water Lilies: Clear Morning with Willows", "year": "1920", "hall": None, "inventory_number": "INV 20106", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Water%20Lilies%20-%20Clear%20Morning%20with%20Willows%20-%20Google%20Art%20Project.jpg", "estimate_low": 18.4, "estimate_high": 35.0, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_inv_20107", "artist": "Claude Monet", "title": "Water Lilies: Tree Reflections", "year": "1920", "hall": None, "inventory_number": "INV 20107", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Water%20Lilies%20-%20Tree%20Reflections%20-%20Google%20Art%20Project.jpg", "estimate_low": 16.6, "estimate_high": 32.2, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_inv_20102", "artist": "Claude Monet", "title": "Water Lilies: Green Reflections", "year": "1920", "hall": None, "inventory_number": "INV 20102", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Water%20Lilies%20-%20Green%20Reflections%20-%20Google%20Art%20Project.jpg", "estimate_low": 25.8, "estimate_high": 44.2, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_inv_20101", "artist": "Claude Monet", "title": "Water Lilies: Morning", "year": "1920", "hall": None, "inventory_number": "INV 20101", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Water%20Lilies%20-%20Morning%20-%20Google%20Art%20Project.jpg", "estimate_low": 20.2, "estimate_high": 36.8, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_inv_20104", "artist": "Claude Monet", "title": "Water Lilies: The Two Willows", "year": "1920", "hall": None, "inventory_number": "INV 20104", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Water%20Lilies%20-%20The%20Two%20Willows%20-%20Google%20Art%20Project.jpg", "estimate_low": 18.4, "estimate_high": 35.0, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_rf_1960_47", "artist": "Alfred Sisley", "title": "The Road from Montbuisson to Louveciennes", "year": "1875", "hall": None, "inventory_number": "RF 1960-47", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Sisley%20Orangerie%2002.jpg", "estimate_low": 3.7, "estimate_high": 7.4, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_inv_20103", "artist": "Claude Monet", "title": "Water Lilies: Setting Sun", "year": "1920", "hall": None, "inventory_number": "INV 20103", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Water%20Lilies%20-%20Setting%20Sun%20-%20Google%20Art%20Project.jpg", "estimate_low": 23.0, "estimate_high": 41.4, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_rf_1963_10", "artist": "Paul Cézanne", "title": "Still Life, Pears and Green Apples", "year": "1873", "hall": None, "inventory_number": "RF 1963-10", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Nature%20morte%2C%20poire%20et%20pommes%20vertes.JPG", "estimate_low": 7.4, "estimate_high": 16.6, "needs_editorial_review": True, "museum_id": "orangerie"},
    {"id": "orangerie_rf_1963_104", "artist": "Maurice Utrillo", "title": "Butte Pinson", "year": "1905", "hall": None, "inventory_number": "RF 1963 104", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Maurice%20Utrillo%20-%20Butte%20Pinson%20%281905-1908%29.jpg", "estimate_low": 0.4, "estimate_high": 0.9, "needs_editorial_review": True, "museum_id": "orangerie"},
]

CONFIDENCE_AUTO = 0.92
CONFIDENCE_REVIEW = 0.82


def _log_recognition_event(event: str, **properties) -> None:
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **properties,
    }
    print(json.dumps(payload, ensure_ascii=False, default=str), flush=True)
    record_product_event_from_server(event, properties)


def _openai_chat_completion_with_retries(client, **kwargs):
    attempts = max(1, OPENAI_RECOGNITION_RETRIES + 1)
    last_error: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            last_error = exc
            if attempt >= attempts - 1:
                break
            time.sleep(0.45 * (2 ** attempt))
    raise last_error or RuntimeError("OpenAI recognition request failed")


_OPENAI_RECOGNITION_CLIENT = None


def _recognition_openai_client():
    """Reuse provider connections across recognition stages in a warm process."""
    global _OPENAI_RECOGNITION_CLIENT
    if _OPENAI_RECOGNITION_CLIENT is None:
        from openai import OpenAI  # imported lazily so UI-only dev can import the module

        _OPENAI_RECOGNITION_CLIENT = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_RECOGNITION_TIMEOUT_SECONDS)
    return _OPENAI_RECOGNITION_CLIENT


def _new_latency_profile(attempt_id: str) -> dict:
    return {"attempt_id": attempt_id, "started": time.perf_counter(), "stages": []}


def _record_latency_stage(profile: Optional[dict], name: str, started: float, **metadata) -> None:
    if profile is None:
        return
    stage = {"name": name, "ms": round((time.perf_counter() - started) * 1000, 2)}
    stage.update({key: value for key, value in metadata.items() if value is not None})
    profile["stages"].append(stage)


def _timed(profile: Optional[dict], name: str, fn: Callable[[], Any], **metadata):
    started = time.perf_counter()
    try:
        return fn()
    finally:
        _record_latency_stage(profile, name, started, **metadata)


def _latency_profile_summary(profile: Optional[dict]) -> Optional[dict]:
    if profile is None:
        return None
    return {
        "attempt_id": profile["attempt_id"],
        "total_server_ms": round((time.perf_counter() - profile["started"]) * 1000, 2),
        "stages": profile["stages"],
    }


def recognize_open(
    image_base64: str,
    museum_id: str,
    institution_context: Optional[str] = None,
    profile: Optional[dict] = None,
) -> dict:
    """
    Open recognition — no candidate list in the prompt at all. A 13-photo
    real-world test showed the closed-catalog prompt (and even the two-stage
    visual-verification version) sometimes forces a wrong catalog id when the
    right answer isn't in the list, or is a same-artist neighbour of it — the
    model has to pick *something* from what it's given. Asking openly, the
    way a plain ChatGPT query would, lets the model say "I don't know this
    specific work" instead of guessing from a constrained menu.
    """
    client = _recognition_openai_client()
    museum_context = institution_context or (
        f"{museum_id or 'an unknown museum'}. The final identity must later be "
        "resolved against ELYIO's global catalog."
    )
    generic_instruction = "When the museum is unknown, identify a recognizable work by likely title and artist from the image alone; do not wait for a museum catalog and use null only when evidence is genuinely insufficient. " if not museum_id else ""
    system_prompt = (
        "You are the first visual-analysis pass for a museum recognition system. "
        f"Context: the visitor is likely inside {museum_context}\n\n"
        f"Identify only what is visually and art-historically supportable from the image. {generic_instruction}"
        "If uncertain, keep recognized=false or confidence low. Do not fabricate identifiers. "
        "Do not output an ARK, accession id, database id, or any identifier not visible in the image.\n\n"
        "Describe observable evidence before naming a work. OCR any visible wall-label/frame/inventory text. "
        "Respond with one strict JSON object only, no prose, no markdown fences, with this shape: "
        '{"recognized": true|false, '
        '"is_artwork_photo": true|false, "image_quality": "<good|partial|label_only|room_only|blank|unusable>", '
        '"non_artwork_reason": "<reason or null>", '
        '"object_category": "<painting|sculpture|antiquity|decorative art|drawing|object|unknown>", '
        '"likely_artist": "<artist or null>", "likely_title": "<title or null>", '
        '"period_guess": "<period/date clue or null>", "material_guess": "<material or null>", '
        '"depicted_subject": "<subject or null>", "inscriptions_visible": ["visible text", "..."], '
        '"dominant_visual_features": ["observable feature", "..."], '
        '"distinctive_features": ["specific distinguishing clue", "..."], '
        '"visual_search_description": "<one concise evidence-only search phrase, or null>", '
        '"confidence_artist": <0-1 float>, "confidence_title": <0-1 float>, '
        '"confidence": <0-1 float>, '
        '"alternative_candidates": [{"artist": "<artist or null>", "title": "<title or null>", "confidence": <0-1 float>}]}'
    )

    request_started = time.perf_counter()
    retry_count = 0
    parse_failures = 0
    provider_outcome = "OTHER_PROVIDER_EXCEPTION"
    response_shape = "unknown"
    data = None
    provider_attempts = 0
    retry_reasons = []
    max_empty_attempts = 2
    for attempt in range(max_empty_attempts):
        try:
            provider_attempts += 1
            resp = _timed(
                profile,
                "external_model.stage1_openai",
                lambda: _openai_chat_completion_with_retries(
                    client,
                    model=RECOGNITION_MODEL,
                    max_tokens=700,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                            {"type": "text", "text": "Analyze this museum visitor photo for artwork recognition."}
                        ]}
                    ],
                ),
                provider="openai",
                model=RECOGNITION_MODEL,
                role="stage1_visual_analysis",
            )
            choice = resp.choices[0] if getattr(resp, "choices", None) else None
            content = getattr(getattr(choice, "message", None), "content", None)
            response_shape = "choices_message_content" if content is not None else "missing_message_content"
            if not isinstance(content, str) or not content.strip():
                provider_outcome = "SUCCESS_EMPTY"
                if attempt + 1 < max_empty_attempts:
                    retry_count += 1
                    retry_reasons.append("empty_response")
                    continue
                data = {}
                break
            try:
                data = json.loads(content)
            except (TypeError, json.JSONDecodeError):
                parse_failures += 1
                provider_outcome = "MALFORMED_RESPONSE"
                if attempt + 1 < max_empty_attempts:
                    retry_count += 1
                    retry_reasons.append("malformed_response")
                    continue
                data = {}
                break
            provider_outcome = "SUCCESS_RECOGNIZED" if data.get("recognized") else "SUCCESS_UNRECOGNIZED_WITH_CLUES"
            break
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            if status == 429:
                provider_outcome = "PROVIDER_RATE_LIMIT"
            elif isinstance(status, int) and status >= 500:
                provider_outcome = "PROVIDER_5XX"
            elif isinstance(exc, (TimeoutError, ConnectionError)):
                provider_outcome = "PROVIDER_TIMEOUT" if isinstance(exc, TimeoutError) else "NETWORK_ERROR"
            else:
                provider_outcome = "OTHER_PROVIDER_EXCEPTION"
            provider_attempts += OPENAI_RECOGNITION_RETRIES
            diagnostic = {
                "model": RECOGNITION_MODEL,
                "provider_outcome": provider_outcome,
                "response_shape": response_shape,
                "parse_success": False,
                "recognized_present": False,
                "recognized": False,
                "title_present": False,
                "visual_clues_count": 0,
                "retry_count": retry_count,
                "retry_reasons": retry_reasons,
                "provider_attempts": provider_attempts,
                "parse_failures": parse_failures,
                "latency_s": round(time.perf_counter() - request_started, 4),
            }
            setattr(exc, "_stage1_diagnostic", diagnostic)
            raise
    if data is None:
        data = {}
    data.setdefault("recognized", bool(data.get("likely_title") or data.get("likely_artist") or data.get("dominant_visual_features") or data.get("distinctive_features")))
    data.setdefault("is_artwork_photo", bool(data.get("recognized")))
    data.setdefault("image_quality", "unknown")
    data.setdefault("non_artwork_reason", None)
    data.setdefault("likely_artist", data.get("artist"))
    data.setdefault("likely_title", data.get("title"))
    data.setdefault("artist", data.get("likely_artist"))
    data.setdefault("title", data.get("likely_title"))
    data.setdefault("object_category", data.get("object_type", "unknown"))
    data.setdefault("object_type", data.get("object_category", "unknown"))
    data.setdefault("period_guess", None)
    data.setdefault("material_guess", None)
    data.setdefault("depicted_subject", None)
    data.setdefault("inscriptions_visible", [])
    data.setdefault("dominant_visual_features", [])
    data.setdefault("distinctive_features", [])
    data.setdefault("visual_search_description", None)
    data["visual_clues"] = [
        *[str(x) for x in [data.get("visual_search_description")] if x],
        *[str(x) for x in data.get("visual_clues", []) if x],
        *[str(x) for x in data.get("dominant_visual_features", []) if x],
        *[str(x) for x in data.get("distinctive_features", []) if x],
        *[str(x) for x in data.get("inscriptions_visible", []) if x],
        *[str(x) for x in [data.get("period_guess"), data.get("material_guess"), data.get("depicted_subject")] if x],
    ]
    data.setdefault("alternative_candidates", [])
    data.setdefault("confidence", 0.0)
    if provider_outcome.startswith("SUCCESS_"):
        provider_outcome = (
            "SUCCESS_RECOGNIZED"
            if data.get("recognized")
            else "SUCCESS_UNRECOGNIZED_WITH_CLUES"
            if data.get("title") or data.get("visual_clues")
            else "SUCCESS_EMPTY"
        )
    data["_stage1_diagnostic"] = {
        "model": RECOGNITION_MODEL,
        "provider_outcome": provider_outcome,
        "response_shape": response_shape,
        "parse_success": parse_failures == 0 and provider_outcome.startswith("SUCCESS_"),
        "recognized_present": "recognized" in data,
        "recognized": bool(data.get("recognized")),
        "title_present": bool(data.get("title")),
        "visual_clues_count": len(data.get("visual_clues") or []),
        "retry_count": retry_count,
        "retry_reasons": retry_reasons,
        "provider_attempts": provider_attempts,
        "parse_failures": parse_failures,
        "latency_s": round(time.perf_counter() - request_started, 4),
    }
    return data


_ARTICLE_RE = re.compile(r"\b(the|a|an|la|le|les|l'|un|une)\b", re.IGNORECASE)
_RECOGNITION_STOPWORDS = {
    "and", "with", "from", "dans", "avec", "des", "les", "une", "pour",
    "the", "this", "that", "work", "artwork", "object", "museum", "ancient",
    "possibly", "likely", "visible", "small", "large", "round", "oval",
}
_RECOGNITION_SYNONYM_GROUPS = [
    {"painting", "peinture", "tableau", "canvas", "toile", "huile", "oil"},
    {"sculpture", "statue", "statuette", "relief", "marble", "marbre", "stone", "pierre"},
    {"antiquity", "antiquities", "antique", "egyptian", "egypt", "egypte", "egyptien", "oriental", "mesopotamian", "mesopotamie"},
    {"decorative", "decor", "decoration", "ornament", "ornement", "objet"},
    {"islamic", "islam", "islamique"},
    {"ceramic", "ceramique", "faience", "porcelain", "porcelaine", "glazed", "glacure", "glacure"},
    {"metal", "metalwork", "metallic", "metallique", "metal", "bronze", "copper", "cuivre", "alloy", "alliage"},
    {"wood", "bois", "grenadille"},
    {"gold", "gilded", "dore", "or"},
    {"silver", "argent", "inlaid", "inlay", "inlays", "incruste", "incrustation"},
    {"enamel", "email", "emaux", "grisaille"},
    {"inscription", "inscriptions", "writing", "script", "text", "texte", "ecriture", "hieroglyph", "hieroglyphic", "hieroglyphs", "hieroglyphe", "scribe"},
    {"eye", "eyes", "oeil", "yeux", "pupil", "iris", "regard"},
    {"cubit", "rod", "measuring", "measurement", "measure", "coudee", "regle", "graduation", "markings"},
    {"plaque", "panel", "plate", "rectangular", "rectangle", "rectangulaire"},
    {"basin", "bowl", "dish", "vessel", "vase", "recipient", "recipent", "recipient", "bassin", "coupe", "plat", "shallow"},
    {"automaton", "automate", "mechanical", "paon", "peacock", "bird", "oiseau"},
    {"animal", "animals", "lion", "bull", "bird", "horse", "serpent", "dragon", "lionne", "taureau", "cheval"},
    {"female", "woman", "femme", "aphrodite", "venus", "nike", "draped", "drapery", "draperie", "himation", "chiton"},
    {"missing", "fragment", "incomplete", "manque", "lacune", "fragmentaire", "incomplet"},
    {"ship", "prow", "navire", "proue", "base", "socle"},
    {"medallion", "medaillon", "central", "centre"},
    {"vegetal", "floral", "flower", "plant", "feuillage", "vegetal", "fleur", "palmette"},
    {"geometric", "geometry", "geometrical", "geometrique", "radial", "pattern", "motif", "patterned"},
    {"portrait", "face", "visage", "head", "tete", "bust", "buste"},
    {"battle", "war", "combat", "guerre", "victory", "victoire", "soldier", "soldat"},
    {"coronation", "couronnement", "napoleon", "ceremony", "ceremonie"},
    {"raft", "radeau", "shipwreck", "naufrage", "medusa", "meduse"},
    {"liberty", "liberte", "tricolor", "tricolore", "flag", "drapeau", "barricade"},
]
_RECOGNITION_SYNONYMS: dict[str, set[str]] = {}
for _group in _RECOGNITION_SYNONYM_GROUPS:
    for _term in _group:
        _RECOGNITION_SYNONYMS.setdefault(_term.lower(), set()).update(_group)


def _normalize_for_matching(s: str) -> str:
    """Strips leading/embedded articles (EN+FR) before fuzzy comparison —
    without this, "Ballet Rehearsal on Stage" vs "The Rehearsal Onstage"
    loses points purely on "The"/"Ballet", not on anything meaningful."""
    if not s:
        return ""
    s = s.replace("’", "'")
    try:
        import unicodedata
        s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    except Exception:
        pass
    s = _ARTICLE_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


# Candidate threshold for the fuzzy text match (§ hybrid redesign). This used
# to BE the accept/reject decision (0.90) — it no longer is. It now only
# decides "is this worth a visual check", because a pure text threshold
# cannot safely be that decision on its own:
#   - Re-scoring the 32 near-misses from the pure-fuzzy version with
#     article-stripping + max(token_sort_ratio, partial_ratio) recovers most
#     of them (e.g. "Dante and Virgil in Hell" vs model's "Dante and Virgil"
#     goes 0.870 -> 1.000; "La Rue Montorgueil" vs the model's long official
#     title goes 0.637 -> 1.000) — genuine near-misses now score 0.72-1.00.
#   - But partial_ratio also creates NEW false-positive risk for short
#     catalog titles: the model wrongly identifying a photo as Manet's "Study
#     of Olympia" scores a PERFECT 1.000 against our "Olympia" entry, purely
#     because "Olympia" is a substring of the model's (wrong) answer. No
#     text-only threshold can filter that out — "Study of Olympia" is real
#     art-history vocabulary, not noise.
#   - The Cézanne case that motivated this whole redesign — "Still Life with
#     Onions" vs the model's "The Kitchen Table" (a different, real Cézanne
#     still life) — scores only 0.600, well below any threshold high enough
#     to be a safe final answer.
# Given text-only scoring can't be both permissive enough to catch the
# Cézanne case AND strict enough to reject the Olympia case, the threshold's
# job changes: 0.55 (comfortably under the Cézanne case's 0.600) casts a wide
# net for "plausible candidate", and visual_verify_single_candidate() below —
# not this number — is what actually decides match vs no-match.
FUZZY_CANDIDATE_THRESHOLD = 0.55
FUZZY_ARTIST_GATE = 0.5  # candidates below this artist-name similarity are never considered


def fuzzy_match_catalog(artist: Optional[str], title: Optional[str], candidates: List[dict]):
    """Rank caller-supplied museum-scoped candidates by artist/title text.

    Museum scoping intentionally happens before this function, in the DB
    catalog query. The matcher must not fetch or filter a global catalog on
    its own.
    """
    from rapidfuzz import fuzz  # imported lazily, same rationale as the openai import above

    if not title:
        return None, 0.0, None

    title_n = _normalize_for_matching(title)
    artist_n = _normalize_for_matching(artist or "")

    scored = []
    for a in candidates:
        candidate_artist_n = _normalize_for_matching(a.get("artist") or "")
        if artist_n and candidate_artist_n:
            artist_score = fuzz.token_sort_ratio(artist_n, candidate_artist_n) / 100
            if artist_score < FUZZY_ARTIST_GATE:
                continue
        else:
            artist_score = None
        cat_title_n = _normalize_for_matching(a["title"])
        title_score = max(
            fuzz.token_sort_ratio(title_n, cat_title_n),
            fuzz.partial_ratio(title_n, cat_title_n),
        ) / 100
        combined = title_score if artist_score is None else 0.35 * artist_score + 0.65 * title_score
        scored.append((combined, a))

    if not scored:
        return None, 0.0, None
    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best = scored[0]
    runner_up = scored[1][1] if len(scored) > 1 and scored[1][0] >= 0.5 else None
    return best, best_score, runner_up


def _tokens(value: Optional[str]) -> set[str]:
    if not value:
        return set()
    value = _normalize_for_matching(value).lower()
    raw = {t for t in re.findall(r"[a-z0-9]{3,}", value) if t not in _RECOGNITION_STOPWORDS}
    expanded = set(raw)
    for token in raw:
        expanded.update(_RECOGNITION_SYNONYMS.get(token, set()))
    return {t for t in expanded if len(t) >= 3 and t not in _RECOGNITION_STOPWORDS}


def _candidate_search_text(candidate: dict) -> str:
    parts = [
        candidate.get("title"),
        candidate.get("artist"),
        candidate.get("year"),
        candidate.get("inventory_number"),
        candidate.get("department"),
        candidate.get("hall"),
        candidate.get("object_type"),
        candidate.get("materials_and_techniques"),
        candidate.get("description"),
        candidate.get("provenance"),
        candidate.get("object_history"),
        candidate.get("historical_context"),
        candidate.get("current_location_raw"),
        candidate.get("source_record_id"),
    ]
    source_urls = candidate.get("source_urls") or []
    if isinstance(source_urls, list):
        parts.extend(str(x) for x in source_urls)
    creator_labels = candidate.get("creator_labels") or []
    if isinstance(creator_labels, list):
        parts.extend(str(x) for x in creator_labels)
    tags = candidate.get("tags") or []
    if isinstance(tags, list):
        parts.extend(str(x) for x in tags)
    return " ".join(str(x) for x in parts if x)


def rank_catalog_candidates(vision: dict, candidates: List[dict], hall_hint: Optional[str] = None, limit: int = 5) -> list[dict]:
    """Hybrid text/clue rank over already museum-scoped DB candidates.

    This deliberately accepts the candidate list from the caller instead of
    fetching anything globally; museum isolation belongs in get_recognition_candidates().
    """
    from rapidfuzz import fuzz

    if not candidates:
        return []
    artist = vision.get("artist")
    title = vision.get("title")
    object_type = vision.get("object_type") or vision.get("object_category")
    confidence_title = float(vision.get("confidence_title", vision.get("confidence", 0)) or 0)
    confidence_artist = float(vision.get("confidence_artist", vision.get("confidence", 0)) or 0)
    visual_clues = vision.get("visual_clues") or []
    extra_clues = [
        vision.get("period_guess"),
        vision.get("material_guess"),
        vision.get("depicted_subject"),
        *(vision.get("inscriptions_visible") or []),
        *(vision.get("dominant_visual_features") or []),
        *(vision.get("distinctive_features") or []),
    ]
    visual_clues = [*visual_clues, *[x for x in extra_clues if x]]
    alt_candidates = vision.get("alternative_candidates") or []

    query_title = _normalize_for_matching(title or "")
    query_artist = _normalize_for_matching(artist or "")
    clue_tokens = _tokens(" ".join(str(x) for x in visual_clues))
    object_tokens = _tokens(object_type)
    hall_tokens = _tokens(hall_hint)
    candidate_tokens: dict[str, set[str]] = {}
    document_frequency: dict[str, int] = {}
    for candidate in candidates:
        tokens = _tokens(_candidate_search_text(candidate))
        candidate_tokens[candidate["id"]] = tokens
        for token in tokens:
            document_frequency[token] = document_frequency.get(token, 0) + 1

    def weighted_overlap(query_tokens: set[str], search_tokens: set[str], cap_terms: int = 14) -> float:
        if not query_tokens:
            return 0.0
        import math
        weighted = [
            (token, math.log((len(candidates) + 1) / (document_frequency.get(token, 0) + 1)) + 1.0)
            for token in query_tokens
        ]
        weighted.sort(key=lambda item: item[1], reverse=True)
        weighted = weighted[:cap_terms]
        denom = sum(weight for _token, weight in weighted)
        if denom <= 0:
            return 0.0
        hit = sum(weight for token, weight in weighted if token in search_tokens)
        return hit / denom

    scored: list[tuple[float, dict, dict]] = []
    for candidate in candidates:
        candidate_title = _normalize_for_matching(candidate.get("title") or "")
        candidate_artist = _normalize_for_matching(candidate.get("artist") or "")
        search_text = _candidate_search_text(candidate)
        search_tokens = candidate_tokens.get(candidate["id"]) or _tokens(search_text)

        title_score = 0.0
        if query_title and confidence_title >= 0.35:
            title_score = max(fuzz.token_sort_ratio(query_title, candidate_title), fuzz.partial_ratio(query_title, candidate_title)) / 100
        alt_title_score = 0.0
        for alt in alt_candidates:
            alt_title = _normalize_for_matching((alt or {}).get("title") or "")
            if alt_title:
                alt_title_score = max(alt_title_score, fuzz.token_sort_ratio(alt_title, candidate_title) / 100, fuzz.partial_ratio(alt_title, candidate_title) / 100)
        title_score = max(title_score, alt_title_score * 0.92)

        artist_score = 0.0
        if query_artist and candidate_artist and confidence_artist >= 0.35:
            artist_score = fuzz.token_sort_ratio(query_artist, candidate_artist) / 100

        clue_score = 0.0
        if clue_tokens:
            clue_score = weighted_overlap(clue_tokens, search_tokens)

        object_score = 0.0
        if object_tokens:
            object_score = weighted_overlap(object_tokens, search_tokens, cap_terms=6)

        ocr_tokens = _tokens(" ".join(str(x) for x in vision.get("inscriptions_visible") or []))
        ocr_score = 0.0
        if ocr_tokens:
            ocr_score = weighted_overlap(ocr_tokens, search_tokens, cap_terms=10)

        hall_score = 0.0
        if hall_tokens:
            hall_score = len(hall_tokens & search_tokens) / max(1, len(hall_tokens))

        priority = candidate.get("priority")
        priority_score = 0.0
        if isinstance(priority, (int, float)):
            priority_score = max(0.0, min(0.08, (120 - float(priority)) / 1500))

        if candidate.get("artist") is None or candidate_artist in {"anonyme", "anonymous"} or not query_title:
            score = (
                0.18 * title_score
                + 0.06 * artist_score
                + 0.38 * min(clue_score, 1.0)
                + 0.14 * min(ocr_score, 1.0)
                + 0.16 * min(object_score, 1.0)
                + 0.04 * min(hall_score, 1.0)
                + priority_score
            )
        else:
            score = (
                0.42 * title_score
                + 0.18 * artist_score
                + 0.19 * min(clue_score, 1.0)
                + 0.08 * min(ocr_score, 1.0)
                + 0.08 * min(object_score, 1.0)
                + 0.03 * min(hall_score, 1.0)
                + priority_score
            )
        if title_score >= 0.95:
            score = max(score, 0.72 + 0.08 * artist_score + priority_score)
        elif title_score >= 0.82 and not query_artist:
            score = max(score, 0.58 + priority_score)
        # Anonymous Louvre antiquities/decorative objects can be identifiable
        # without artist/title if visual/object/room metadata line up.
        if not query_title and not query_artist:
            score = (
                0.40 * min(clue_score, 1.0)
                + 0.22 * min(object_score, 1.0)
                + 0.18 * min(ocr_score, 1.0)
                + 0.12 * min(hall_score, 1.0)
                + priority_score
            )

        scored.append((score, candidate, {
            "title_score": round(title_score, 3),
            "artist_score": round(artist_score, 3),
            "visual_clue_score": round(min(clue_score, 1.0), 3),
            "ocr_score": round(min(ocr_score, 1.0), 3),
            "object_type_score": round(min(object_score, 1.0), 3),
            "room_score": round(min(hall_score, 1.0), 3),
        }))

    scored.sort(key=lambda item: item[0], reverse=True)
    ranked = []
    for score, candidate, signals in scored[:limit]:
        ranked.append({"candidate": candidate, "score": round(score, 4), "signals": signals})
    return ranked


def _stage2_artist_match_allowed(vision: dict, candidate: Optional[dict]) -> bool:
    """Reject verifier overreach when the model confidently names a different artist.

    Stage 2 is allowed to reason visually among scoped catalog candidates, but it
    should not turn "this resembles a different work by another artist" into a
    catalog match. This specifically protects cross-museum lookalikes such as
    different portraits of the same sitter.
    """
    if not candidate:
        return False
    query_artist = vision.get("artist") or vision.get("likely_artist")
    candidate_artist = candidate.get("artist")
    if not query_artist or not candidate_artist:
        return True
    confidence_artist = float(vision.get("confidence_artist", vision.get("confidence", 0)) or 0)
    if confidence_artist < 0.75:
        return True

    from rapidfuzz import fuzz

    query_artist_n = _normalize_for_matching(str(query_artist)).lower()
    candidate_artist_n = _normalize_for_matching(str(candidate_artist)).lower()
    if query_artist_n and (
        query_artist_n in candidate_artist_n
        or candidate_artist_n in query_artist_n
    ):
        return True
    query_tokens = _tokens(query_artist_n)
    candidate_tokens = _tokens(candidate_artist_n)
    if query_tokens and candidate_tokens:
        overlap = len(query_tokens & candidate_tokens) / max(1, min(len(query_tokens), len(candidate_tokens)))
        if overlap >= 0.67:
            return True

    score = fuzz.token_sort_ratio(query_artist_n, candidate_artist_n) / 100
    return score >= 0.58


# One reference image per verified candidate, cached to disk — Wikimedia
# Commons rate-limits repeated bot traffic (HTTP 429) on re-fetch.
REFERENCE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".reference_cache")
REFERENCE_IMAGE_UA = "AURA-MVP-backend/1.0 (contact: repo owner)"
REFERENCE_MEMORY_CACHE_MAX_ENTRIES = int(os.environ.get("REFERENCE_MEMORY_CACHE_MAX_ENTRIES", "128"))
_REFERENCE_MEMORY_CACHE: OrderedDict[str, str] = OrderedDict()
_REFERENCE_MEMORY_CACHE_LOCK = Lock()

# One real catalog work (Renoir, Bal du moulin de la Galette) turned out to
# have a 717MB / 1.24-BILLION-pixel original on Wikimedia — `raw = resp.read()`
# buffered that whole file into memory before PIL ever saw it, which alone
# exceeds a small container's total RAM (confirmed: OOM-killed a 512MB *and*
# a 1024MB Fly machine, since the failure is proportional to file size, not
# fixed). Two independent guards against this, not just one:
REFERENCE_MAX_ORIGINAL_BYTES = 50 * 1024 * 1024  # refuse to stream/decode an original bigger than this
REFERENCE_SAFE_MEGAPIXELS = 20_000_000  # log a warning if even a "successfully fetched" image is this large


def _urlopen_with_retry(req, timeout: int = 30, max_attempts: int = 3):
    """Wikimedia Commons rate-limits (HTTP 429) hard enough that a bulk
    warm-up sweep across the whole catalog reliably trips it — confirmed
    live during a Docker build, where it killed the build outright with no
    retry logic at all. Backs off (2s, 4s, 8s...) only on 429; any other
    HTTPError propagates immediately, same as before."""
    import time
    import urllib.error
    import urllib.request

    for attempt in range(1, max_attempts + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_attempts:
                wait = 2 ** attempt
                print(f"[reference-image] HTTP 429 from Wikimedia, retrying in {wait}s "
                      f"(attempt {attempt}/{max_attempts})")
                time.sleep(wait)
                continue
            raise


def _wikimedia_thumbnail_url(image_url: str, width: int = 512) -> Optional[str]:
    """Primary path: ask Wikimedia's Special:FilePath for an already-downsized,
    server-generated (and server-cached) thumbnail via its `width` query param,
    instead of ever downloading the original. Confirmed live: the Renoir case's
    717MB original becomes a 259KB, 960px-wide thumbnail this way — several
    thousand times less data for the exact same picture."""
    import urllib.parse

    parsed = urllib.parse.urlsplit(image_url)
    if "Special:FilePath" not in parsed.path:
        return None
    safe_path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/:")
    query = dict(urllib.parse.parse_qsl(parsed.query))
    query["width"] = str(width)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, safe_path, urllib.parse.urlencode(query), parsed.fragment)
    )


def _decode_and_resize(raw: bytes, target_w: int = 512):
    """Shared decode path for both the thumbnail and the fallback-original
    bytes — deliberately never trusts the caller to have already-small bytes.
    img.draft() lets libjpeg downsample DURING decode (to the nearest of
    1/1, 1/2, 1/4, 1/8) instead of fully expanding the image into memory
    first and cropping after; harmless/near-no-op on an already-small
    thumbnail, but on an oversized original it's the difference between a
    multi-GB decode and a two-digit-MB one."""
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(raw))  # lazy — reads only the header, no pixel decode yet
    w, h = img.size
    if w * h > REFERENCE_SAFE_MEGAPIXELS:
        print(f"[reference-image] WARNING: source is {w}x{h} ({w * h / 1e6:.0f} MP), "
              f"over the {REFERENCE_SAFE_MEGAPIXELS / 1e6:.0f}MP safety threshold — "
              f"forcing a downsampled decode via JPEG draft mode")
    img.draft("RGB", (target_w, target_w))  # no-op on non-JPEG / already-small images
    img = img.convert("RGB")
    w, h = img.size
    new_h = round(h * (target_w / w)) if w else target_w
    return img.resize((target_w, new_h), Image.LANCZOS)


def _fetch_reference_image_original_bytes(image_url: str) -> bytes:
    """Fallback path, only used if the Wikimedia thumbnail service itself is
    unreachable or the URL isn't a Special:FilePath link. Streams in chunks
    with a hard byte cap enforced both from the Content-Length header (fails
    fast, before downloading anything) and live during the read (in case the
    header is missing or wrong) — never buffers an unbounded response."""
    import urllib.request

    req = urllib.request.Request(image_url, headers={"User-Agent": REFERENCE_IMAGE_UA})
    with _urlopen_with_retry(req, timeout=30) as resp:
        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) > REFERENCE_MAX_ORIGINAL_BYTES:
            raise RuntimeError(
                f"reference image original is {int(content_length) / 1e6:.0f}MB, over the "
                f"{REFERENCE_MAX_ORIGINAL_BYTES / 1e6:.0f}MB hard limit — refusing to download it"
            )
        chunks, total = [], 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > REFERENCE_MAX_ORIGINAL_BYTES:
                raise RuntimeError(
                    f"reference image original exceeded the {REFERENCE_MAX_ORIGINAL_BYTES / 1e6:.0f}MB "
                    f"hard limit mid-download (Content-Length was missing or wrong) — aborting"
                )
            chunks.append(chunk)
        return b"".join(chunks)


def _reference_cache_key(artwork: dict) -> str:
    """Stable identity plus source fingerprint, so changing the approved source
    invalidates cached bytes without any recognition-policy inference."""
    identity = artwork.get("recognition_asset_id") or artwork["id"]
    source = artwork.get("image_url") or ""
    source_fingerprint = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"{identity}|{source_fingerprint}|w=512|jpeg-q85"


def _reference_cache_path(artwork: dict) -> str:
    cache_filename = hashlib.sha256(_reference_cache_key(artwork).encode("utf-8")).hexdigest()
    return os.path.join(REFERENCE_CACHE_DIR, f"{cache_filename}.jpg")


def _local_reference_available(artwork: dict) -> bool:
    return os.path.exists(_reference_cache_path(artwork))


def _fetch_reference_image_b64(
    artwork: dict,
    allow_remote: bool = True,
    profile: Optional[dict] = None,
) -> str:
    cache_key = _reference_cache_key(artwork)
    with _REFERENCE_MEMORY_CACHE_LOCK:
        cached = _REFERENCE_MEMORY_CACHE.get(cache_key)
        if cached is not None:
            _REFERENCE_MEMORY_CACHE.move_to_end(cache_key)
    if cached is not None:
        _record_latency_stage(profile, "reference_image.cache_hit", time.perf_counter(), storage="memory")
        return cached

    os.makedirs(REFERENCE_CACHE_DIR, exist_ok=True)
    cache_path = _reference_cache_path(artwork)
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        _record_latency_stage(profile, "reference_image.cache_hit", time.perf_counter(), storage="filesystem")
        _store_reference_memory_cache(cache_key, encoded)
        return encoded

    _record_latency_stage(profile, "reference_image.cache_miss", time.perf_counter())
    if not allow_remote:
        raise RuntimeError("reference_image_not_cached")

    import urllib.request

    raw = None
    thumb_url = _wikimedia_thumbnail_url(artwork["image_url"], width=512)
    if thumb_url:
        try:
            req = urllib.request.Request(thumb_url, headers={"User-Agent": REFERENCE_IMAGE_UA})
            raw = _timed(
                profile,
                "reference_image.network_fetch",
                lambda: _read_reference_thumbnail(req),
                source="wikimedia_thumbnail",
            )
        except Exception as e:
            print(f"[reference-image] thumbnail fetch failed for {artwork['id']} ({e}), "
                  f"falling back to the original with a hard size cap")
            raw = None

    if raw is None:
        raw = _timed(
            profile,
            "reference_image.network_fetch",
            lambda: _fetch_reference_image_original_bytes(artwork["image_url"]),
            source="original",
        )

    img = _decode_and_resize(raw, target_w=512)
    img.save(cache_path, format="JPEG", quality=85)
    with open(cache_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    _store_reference_memory_cache(cache_key, encoded)
    return encoded


def _read_reference_thumbnail(req) -> bytes:
    with _urlopen_with_retry(req, timeout=30) as resp:
        return resp.read()


def _store_reference_memory_cache(cache_key: str, encoded: str) -> None:
    if REFERENCE_MEMORY_CACHE_MAX_ENTRIES <= 0:
        return
    with _REFERENCE_MEMORY_CACHE_LOCK:
        _REFERENCE_MEMORY_CACHE[cache_key] = encoded
        _REFERENCE_MEMORY_CACHE.move_to_end(cache_key)
        while len(_REFERENCE_MEMORY_CACHE) > REFERENCE_MEMORY_CACHE_MAX_ENTRIES:
            _REFERENCE_MEMORY_CACHE.popitem(last=False)


def _reference_verification_allowed(candidate: dict) -> bool:
    """Only external, rights-cleared reference URLs may be fetched for verifier.

    Louvre/RMN image references are metadata-only and must never be fetched by
    recognition. Current Orsay/Orangerie verified references are Wikimedia
    URLs, so this preserves existing behavior while keeping Louvre safe.
    """
    image_url = candidate.get("image_url")
    if not image_url:
        return False
    import urllib.parse

    parsed = urllib.parse.urlsplit(image_url)
    # RecognitionAsset selection is the explicit DB-backed gate. Once an
    # asset has been selected by catalog.py, the verifier may populate its
    # bounded local cache from that asset's HTTPS source. Provider hosts do
    # not belong in core recognition conditionals.
    if candidate.get("recognition_asset_id"):
        return parsed.scheme == "https" and bool(parsed.hostname)
    return parsed.hostname in {"commons.wikimedia.org", "upload.wikimedia.org"}


def _controlled_preview_only(db: Session, institution_id: str) -> bool:
    institution = db.get(Museum, institution_id)
    return bool(institution and (institution.content_policy or {}).get("controlled_preview_only") is True)


# ---- Image proxy (Recap PNG export) ---------------------------------------
# canvas.drawImage() refuses cross-origin Wikimedia images outright (a real
# browser security restriction: reading pixels back out via toBlob/toDataURL
# taints the canvas unless the image was served with a CORS header) -- the
# Recap poster's shareable PNG export drew solid accent-color blocks instead
# of the actual paintings because of this. This endpoint re-fetches the same
# image server-side (where CORS doesn't apply) and re-serves it with our own
# CORS header via the CORSMiddleware already configured above, so the
# frontend's `img.crossOrigin = "anonymous"` + drawImage works.
IMAGE_PROXY_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".image_proxy_cache")
# Reachable from any browser with no auth -- without an allowlist this would
# be an open server-side URL fetcher (internal-network probing, arbitrary
# outbound requests billed to us, etc). Only the two Wikimedia hosts this
# catalog's image_url fields actually use are allowed; nothing else.
IMAGE_PROXY_ALLOWED_HOSTS = {"commons.wikimedia.org", "upload.wikimedia.org"}


def _validate_proxy_url(url: str) -> None:
    import urllib.parse

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="invalid image URL")
    if parsed.hostname not in IMAGE_PROXY_ALLOWED_HOSTS:
        raise HTTPException(status_code=400, detail="host not allowed")


def _fetch_proxy_image_bytes(url: str, width: int = 512) -> bytes:
    """Same fetch/resize pipeline as _fetch_reference_image_b64 above (same
    Wikimedia-thumbnail-first strategy, same size guards against the 717MB-
    original case) -- keyed by a hash of the URL instead of a catalog id,
    since this serves the Recap poster's photo thumbnails (and, since the
    desktop shell work, the atmospheric Orsay clock backdrop) rather than
    the recognition-verification path. Returns raw JPEG bytes (this is
    served directly as an image response) rather than the other function's
    base64 (embedded in a vision-model prompt).

    `width` is part of the cache key (not just the URL) -- the same source
    URL now legitimately needs two different rendered sizes for two
    different callers (512px thumbnails vs. a larger desktop backdrop), and
    keying on URL alone would let whichever size got requested first
    silently poison the cache for every other caller of the same URL."""
    os.makedirs(IMAGE_PROXY_CACHE_DIR, exist_ok=True)
    cache_key = hashlib.sha256(f"{url}|w={width}".encode("utf-8")).hexdigest()
    cache_path = os.path.join(IMAGE_PROXY_CACHE_DIR, f"{cache_key}.jpg")
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return f.read()

    import urllib.request

    raw = None
    thumb_url = _wikimedia_thumbnail_url(url, width=width)
    if thumb_url:
        try:
            req = urllib.request.Request(thumb_url, headers={"User-Agent": REFERENCE_IMAGE_UA})
            with _urlopen_with_retry(req, timeout=30) as resp:
                raw = resp.read()
        except Exception as e:
            print(f"[image-proxy] thumbnail fetch failed for {url} ({e}), falling back to the original")
            raw = None

    if raw is None:
        raw = _fetch_reference_image_original_bytes(url)

    img = _decode_and_resize(raw, target_w=width)
    img.save(cache_path, format="JPEG", quality=85)
    with open(cache_path, "rb") as f:
        return f.read()


def visual_verify_single_candidate(
    image_base64: str,
    candidate: dict,
    allow_remote_reference_fetch: bool = True,
    profile: Optional[dict] = None,
    recognition_request_id: Optional[str] = None,
) -> dict:
    """
    The step that actually catches what text matching structurally cannot:
    is this the SAME painting, or just a same-artist/same-title-sounding one?
    Exactly one reference image — not three like the old two-stage design —
    because by this point fuzzy_match_catalog() has already narrowed it to
    one specific claim to check, not a shortlist to pick from.
    """
    if not candidate.get("image_url"):
        return {"is_match": False, "confidence": 0.0, "reason": "missing_reference_image"}
    if not _reference_verification_allowed(candidate):
        return {"is_match": False, "confidence": 0.0, "reason": "reference_verification_not_allowed_for_url"}

    client = _recognition_openai_client()
    if recognition_request_id:
        _log_recognition_event("recognition.reference_fetch_started", recognition_request_id=recognition_request_id, stage="reference_fetch", stage_status="started", artwork_id=candidate.get("id"))
    ref_b64 = _timed(
        profile,
        "reference_image.fetch_single",
        lambda: _fetch_reference_image_b64(
            candidate,
            allow_remote=allow_remote_reference_fetch,
            profile=profile,
        ),
        artwork_id=candidate.get("id"),
    )
    if recognition_request_id:
        _log_recognition_event("recognition.reference_fetch_completed", recognition_request_id=recognition_request_id, stage="reference_fetch", stage_status="completed", artwork_id=candidate.get("id"))
    candidate_artist = candidate.get("artist") or "creator not specified"

    system_prompt = (
        "You are verifying whether a museum visitor's photo shows the SAME specific artwork as "
        "a reference image — not just a similar or same-artist work, and not just a work with a "
        "similar-sounding title. A different painting by the same artist, or a different work that "
        "happens to share a generic title, does NOT count as a match — only the same physical "
        f'object counts. The reference image is: {candidate_artist} — "{candidate["title"]}" '
        f'({candidate["year"]}).\n\n'
        'Respond with a single valid json object only, no prose, no markdown fences: '
        '{"is_match": true or false, "confidence": <0-1 float, how confident you are in this judgment>}.'
    )

    if recognition_request_id:
        _log_recognition_event("recognition.verifier_started", recognition_request_id=recognition_request_id, stage="verifier_provider", stage_status="started")
    resp = _timed(
        profile,
        "external_model.visual_verify_single",
        lambda: _openai_chat_completion_with_retries(
            client,
            model=VISUAL_VERIFY_MODEL,
            max_tokens=50,  # {"is_match": true/false, "confidence": 0.NN} needs ~15-20 tokens; 50 leaves margin
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": "Visitor's photo:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "text": "Reference image:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ref_b64}"}},
                    {"type": "text", "text": "Is this the same specific artwork?"}
                ]}
            ],
        ),
        provider="openai",
        model=VISUAL_VERIFY_MODEL,
        role="single_reference_verifier",
    )
    verdict = json.loads(resp.choices[0].message.content)
    if recognition_request_id:
        _log_recognition_event("recognition.verifier_completed", recognition_request_id=recognition_request_id, stage="verifier_provider", stage_status="completed")
    return verdict


def visual_verify_reference_candidates(
    image_base64: str,
    ranked: list[dict],
    allow_remote_reference_fetch: bool = True,
    profile: Optional[dict] = None,
) -> dict:
    """Choose among at most three real references in one bounded model call.

    This is used only after cheap institution-scoped retrieval.  It replaces
    sequential candidate calls; canonical attachment still requires explicit
    same-object visual evidence and the model may always return NO_MATCH.
    """
    usable = [
        row for row in ranked[:3]
        if row["candidate"].get("image_url") and _reference_verification_allowed(row["candidate"])
    ]
    if not usable:
        return {"decision": "NO_MATCH", "chosen_id": None, "confidence": 0.0, "reason": "no_reference_candidates"}
    client = _recognition_openai_client()
    allowed_ids = [row["candidate"]["id"] for row in usable]
    content: list[dict] = [
        {"type": "text", "text": "Visitor photo:"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
    ]
    for index, row in enumerate(usable, 1):
        candidate = row["candidate"]
        reference = _timed(
            profile,
            "reference_image.fetch_candidate",
            lambda candidate=candidate: _fetch_reference_image_b64(candidate, allow_remote=allow_remote_reference_fetch),
            artwork_id=candidate.get("id"),
        )
        content.extend([
            {"type": "text", "text": f"Reference {index}: {json.dumps(_candidate_summary(candidate), ensure_ascii=False)}"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{reference}"}},
        ])
    content.append({"type": "text", "text": "Return the same physical artwork only, or NO_MATCH."})
    response = _timed(
        profile,
        "external_model.visual_verify_references",
        lambda: _openai_chat_completion_with_retries(
            client,
            model=VISUAL_VERIFY_MODEL,
            max_tokens=180,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": (
                    "Compare the visitor photo against at most three institution-scoped reference images. "
                    "Choose an id only when it is the SAME specific physical artwork. Similar subject, palette, "
                    "artist, series, or title is insufficient. Prefer NO_MATCH over a wrong attachment. Return "
                    "strict JSON: {\"decision\":\"MATCH|NEEDS_CONFIRMATION|NO_MATCH\",\"chosen_id\":"
                    "\"<provided id or null>\",\"confidence\":<0-1>,\"reason\":\"short evidence\"}."
                )},
                {"role": "user", "content": content},
            ],
        ),
        provider="openai",
        model=VISUAL_VERIFY_MODEL,
        role="reference_candidate_verifier",
    )
    data = json.loads(response.choices[0].message.content)
    if data.get("chosen_id") not in allowed_ids:
        data.update({"decision": "NO_MATCH", "chosen_id": None, "confidence": 0.0})
    data.setdefault("decision", "NO_MATCH"); data.setdefault("chosen_id", None)
    data.setdefault("confidence", 0.0); data.setdefault("reason", "")
    data["reference_candidate_count"] = len(usable)
    return data


def _candidate_summary(candidate: dict) -> dict:
    return {
        "id": candidate.get("id"),
        "ark_id": candidate.get("source_record_id"),
        "title": candidate.get("title"),
        "artist_or_creator": candidate.get("artist") or candidate.get("creator_labels"),
        "date": candidate.get("year"),
        "object_type": candidate.get("object_type"),
        "material": candidate.get("materials_and_techniques"),
        "dimensions": candidate.get("dimensions"),
        "department": candidate.get("department"),
        "room": candidate.get("hall") or candidate.get("room"),
        "inventory_number": candidate.get("inventory_number"),
        "description": candidate.get("description"),
        "history": candidate.get("object_history") or candidate.get("historical_context"),
    }


def verify_top_candidates_with_openai(
    image_base64: str,
    vision: dict,
    ranked: list[dict],
    profile: Optional[dict] = None,
) -> dict:
    """Second-pass Louvre-style verifier.

    OpenAI compares the visitor image with our DB-ranked top candidates only.
    It may choose one provided candidate id, request confirmation, or return
    NO_MATCH. This never fetches reference images and never sends the full
    500-record catalog to OpenAI.
    """
    if not ranked:
        return {"decision": "NO_MATCH", "chosen_id": None, "confidence": 0.0, "reason": "no_candidates"}

    client = _recognition_openai_client()
    candidate_summaries = [_candidate_summary(row["candidate"]) for row in ranked[:5]]
    allowed_ids = [c["id"] for c in candidate_summaries if c.get("id")]
    has_space_candidate = any(
        str(c.get("object_type") or "").lower() in {"space", "room", "interior", "gallery", "hall"}
        for c in candidate_summaries
    )
    space_instruction = (
        "Some provided candidates may be curated rooms or palace spaces. If a room/interior image matches one of those provided space candidates, it may be a valid MATCH. "
        if has_space_candidate
        else ""
    )
    system_prompt = (
        "You are the final verifier for a museum recognition system. "
        "You are given one visitor image and exactly five database candidates from ELYIO's museum-scoped catalog. "
        "First decide whether the visitor image actually contains a visible artwork/object. "
        f"{space_instruction}"
        "A blank wall, label-only image with no matching label text, random object, or unusable image must return NO_MATCH. "
        "A room-only image must return NO_MATCH unless it clearly matches one of the provided curated room/space candidates. "
        "Use the image evidence and the candidate metadata to choose exactly one candidate only if supported. "
        "If the image is ambiguous, too partial, label-only with no matching label text, or none of the candidates fit, return NO_MATCH. "
        "You must not invent IDs. chosen_id must be one of the provided ids or null.\n\n"
        "Return strict JSON only: "
        '{"decision":"MATCH|NEEDS_CONFIRMATION|NO_MATCH","chosen_id":"<one provided id or null>",'
        '"confidence":<0-1 float>,"runner_up":"<provided id or null>",'
        '"reason":"short reason","observable_evidence":["evidence","..."]}'
    )
    user_text = json.dumps(
        {
            "stage1_visual_analysis": vision,
            "allowed_candidate_ids": allowed_ids,
            "candidates": candidate_summaries,
        },
        ensure_ascii=False,
    )
    resp = _timed(
        profile,
        "external_model.topn_metadata_verifier",
        lambda: _openai_chat_completion_with_retries(
            client,
            model=VISUAL_VERIFY_MODEL,
            max_tokens=550,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "text": user_text},
                ]},
            ],
        ),
        provider="openai",
        model=VISUAL_VERIFY_MODEL,
        role="topn_metadata_verifier",
    )
    data = json.loads(resp.choices[0].message.content)
    if data.get("chosen_id") not in allowed_ids:
        data["decision"] = "NO_MATCH"
        data["chosen_id"] = None
        data["confidence"] = 0.0
    data.setdefault("decision", "NO_MATCH")
    data.setdefault("chosen_id", None)
    data.setdefault("confidence", 0.0)
    data.setdefault("runner_up", None)
    data.setdefault("reason", "")
    data.setdefault("observable_evidence", [])
    return data


def recognize_with_vision(
    image_base64: str,
    museum_id: str,
    hall_hint: Optional[str],
    candidates: List[dict],
    benchmark_mode: Optional[str] = None,
    institution_config: Optional[InstitutionRuntimeConfig] = None,
    profile: Optional[dict] = None,
    recognition_request_id: Optional[str] = None,
) -> dict:
    """
    Hybrid: open recognition (no candidate list) -> fuzzy text match against
    the DB-backed, museum-scoped catalog -> up to TWO visual verification calls, but only when a
    candidate was actually found. Two fast paths skip the visual call
    entirely (model recognized nothing, or nothing in the catalog is even
    textually close); only a real candidate pays the extra latency. See
    FUZZY_CANDIDATE_THRESHOLD and visual_verify_single_candidate() for why
    both stages are necessary — neither alone can be both safe and
    accurate. Layer 2 editorial content (estimates, why/where/rarity) is
    still only ever pulled from our reviewed database after a confirmed
    match — the model never generates it, at either stage.

    Runner-up retry (full-catalog audit, 2026-08): on a full 101-image
    self-recognition run, 23/26 no-matches had visual_verify correctly
    reject the TOP text candidate -- because it was the WRONG catalog
    entry, not the true source. Cause: fuzzy_match_catalog only ever tried
    its single best-scoring candidate; when the model answers in French (or
    another non-catalog title variant), its text score against the TRUE
    match can end up lower than a same-artist decoy's coincidental score
    (rapidfuzz's character-level ratio doesn't know French from noise, and
    "Manet"/"Monet" are one Levenshtein edit apart, which can tip the
    artist-similarity component too). Spot-checking runner_up against those
    same cases: it recovers the true match in some (Régates à Argenteuil,
    Vue de toits, Portrait of the Artist with the Yellow Christ) but not
    all (Luncheon on the Grass, Lola de Valence) -- a real, partial
    improvement, not a full fix. Trying the runner-up costs one extra
    visual_verify call, and ONLY when the top candidate was already
    rejected, so it can't make an already-fast match slower, and Stage 2 is
    still the only thing that can ever return an artwork_id either way --
    this doesn't loosen the confident-wrong guarantee at all.
    """
    policy = institution_config.recognition_policy if institution_config else "ASSET_VERIFY"
    fuzzy_threshold = institution_config.fuzzy_candidate_threshold if institution_config else FUZZY_CANDIDATE_THRESHOLD
    candidate_limit = institution_config.max_candidates if institution_config else 5
    prompt_context = institution_config.prompt_context if institution_config else None
    confidence_auto = institution_config.confidence_auto if institution_config else 0.92

    def verifier_confidence(verdict: dict) -> float:
        """Keep the verifier's explicit caution from becoming auto-acceptance.

        The model decision and its numeric confidence are separate signals. A
        NEEDS_CONFIRMATION verdict may be highly confident that the candidate
        is *likely*, but it must remain below the institution's auto-accept
        boundary so the existing visitor-resolution contract stays reachable.
        This does not lower either configured threshold.
        """
        value = float(verdict.get("confidence", 0) or 0)
        if verdict.get("decision") == "NEEDS_CONFIRMATION":
            return min(value, max(0.0, confidence_auto - 0.001))
        return value

    def preserve_same_artist_confusion(verdict: dict, candidate_rows: list[dict]) -> dict:
        """Do not auto-accept an unsupported metadata seed in a confusion family.

        Visual retrieval is non-authoritative, but disagreement is useful
        safety evidence. If a verifier selects the metadata-only seed while a
        different work by the same artist is also in the bounded confusion
        set, retain the catalog candidate as NEEDS_CONFIRMATION instead of
        presenting it as certain. The verifier still establishes identity;
        this rule only controls visitor resolution.
        """
        if verdict.get("decision") != "MATCH" or not verdict.get("chosen_id"):
            if verdict.get("decision") == "NEEDS_CONFIRMATION" and verdict.get("chosen_id"):
                verdict = dict(verdict)
                verdict.setdefault("finalization_reason", "CONFIRMATION_VERIFIER_AMBIGUITY")
            return verdict
        chosen_row = next((row for row in candidate_rows if row["candidate"]["id"] == verdict["chosen_id"]), None)
        if not chosen_row:
            return verdict
        # A reference verifier can establish strong same-image evidence, but
        # a confident Stage-1 attribution to another artist is contradictory
        # evidence. Keep the candidate visible for confirmation rather than
        # silently auto-attaching it. This is especially important for
        # visually related panels, versions and workshop compositions.
        if not _stage2_artist_match_allowed(ident, chosen_row["candidate"]):
            verdict = dict(verdict)
            verdict["decision"] = "NEEDS_CONFIRMATION"
            verdict["finalization_reason"] = "CONFIRMATION_VERIFIER_AMBIGUITY"
            verdict["reason"] = (
                f'{verdict.get("reason", "")} '
                "Stage-1 artist attribution conflicts with the reference candidate."
            ).strip()
            return verdict
        # Stage 1 and the verifier are both model-mediated and therefore are
        # not independent visual evidence.  A metadata-seeded candidate that
        # never appears in local visual retrieval must not become a confident
        # canonical attachment solely because those two model calls agree.
        # Keep the candidate available for explicit visitor confirmation.
        if chosen_row.get("signals", {}).get("visual_retrieval_rank") is None:
            verdict = dict(verdict)
            verdict["decision"] = "NEEDS_CONFIRMATION"
            verdict["finalization_reason"] = "CONFIRMATION_WEAK_VISUAL_CONCORDANCE"
            verdict["reason"] = (
                f'{verdict.get("reason", "")} '
                "Independent visual retrieval did not support this metadata candidate."
            ).strip()
            return verdict
        verdict = dict(verdict)
        verdict.setdefault("finalization_reason", "AUTO_ACCEPT_VISUAL_CONCORDANCE")
        chosen_artist = str(chosen_row["candidate"].get("artist") or "").strip().casefold()
        if not chosen_artist:
            return verdict
        same_artist_competitor = any(
            row["candidate"]["id"] != verdict["chosen_id"]
            and str(row["candidate"].get("artist") or "").strip().casefold() == chosen_artist
            for row in candidate_rows
        )
        if same_artist_competitor:
            verdict = dict(verdict)
            verdict["decision"] = "NEEDS_CONFIRMATION"
            verdict["finalization_reason"] = "CONFIRMATION_VERIFIER_AMBIGUITY"
            verdict["reason"] = f'{verdict.get("reason", "")} Same-artist retrieval evidence remains ambiguous.'.strip()
        return verdict
    if not prompt_context and institution_config:
        prompt_context = (
            f"{institution_config.display_name}. The final identity must later be resolved "
            "against ELYIO's institution-scoped catalog."
        )
    if not museum_id and recognition_request_id:
        _log_recognition_event("recognition.generic_identification_started", recognition_request_id=recognition_request_id, stage="generic_identification", stage_status="started")
    ident = _timed(
        profile,
        "recognition.stage1_open",
        lambda: recognize_open(image_base64, museum_id, prompt_context, profile=profile)
        if prompt_context
        else recognize_open(image_base64, museum_id, profile=profile),
    )
    if not museum_id and recognition_request_id:
        _log_recognition_event("recognition.generic_identification_completed", recognition_request_id=recognition_request_id, stage="generic_identification", stage_status="completed", identified_title_present=bool(ident.get("title")), identified_artist_present=bool(ident.get("artist")), outcome="identified" if ident.get("title") or ident.get("artist") else "unknown")
    artist, title = ident.get("artist"), ident.get("title")
    model_confidence = float(ident.get("confidence", 0) or 0)

    image_quality = ident.get("image_quality")
    non_artwork_reason = str(ident.get("non_artwork_reason") or "").lower()
    is_curated_space_photo = (
        policy == "TOP_N_METADATA"
        and image_quality == "good"
        and any(term in non_artwork_reason for term in ["room", "interior", "hall", "gallery"])
        and bool(ident.get("visual_clues") or ident.get("visual_search_description") or ident.get("distinctive_features"))
    )
    if (ident.get("is_artwork_photo") is False and not is_curated_space_photo) or image_quality in {"blank", "room_only", "unusable"}:
        return {
            "artwork_id": None,
            "confidence": 0.0,
            "alternatives": [],
            "recognized_but_not_cataloged": {"artist": artist, "title": title},
            "vision": ident,
            "top_candidates": [],
            "stage2_verifier": {
                "decision": "NO_MATCH",
                "chosen_id": None,
                "confidence": 0.0,
                "reason": ident.get("non_artwork_reason") or f"image_quality={ident.get('image_quality')}",
                "observable_evidence": [],
            },
        }

    if not ident.get("recognized") and not title and not ident.get("visual_clues"):
        return {"artwork_id": None, "confidence": 0.0, "alternatives": []}  # fast path: nothing recognized

    # Metadata ranking is cheap, so retain a wider diagnostic/retrieval pool
    # even though expensive verification remains strictly bounded.
    if not museum_id and recognition_request_id:
        _log_recognition_event("recognition.global_reconciliation_started", recognition_request_id=recognition_request_id, stage="global_reconciliation", stage_status="started")
    metadata_ranked = _timed(
        profile,
        "catalog.metadata_ranking",
        lambda: rank_catalog_candidates(
            ident, candidates, hall_hint=hall_hint, limit=max(candidate_limit, 20)
        ),
        candidate_count=len(candidates),
    )
    if not museum_id and recognition_request_id:
        _log_recognition_event("recognition.global_reconciliation_completed", recognition_request_id=recognition_request_id, stage="global_reconciliation", stage_status="completed", catalog_match_count=len(metadata_ranked))
    ranked = metadata_ranked[:candidate_limit]
    if not museum_id and recognition_request_id:
        _log_recognition_event("recognition.generic_shortlist_ready", recognition_request_id=recognition_request_id, stage="global_reconciliation", stage_status="completed", shortlist_count=len(ranked), match_strength=(ranked[0].get("score") if ranked else 0.0))
    if policy == "ASSET_VERIFY" and any(candidate.get("visual_descriptor") for candidate in candidates):
        visual_ranked = _timed(
            profile,
            "catalog.visual_descriptor_ranking",
            lambda: rank_visual_candidates(image_base64, candidates, limit=candidate_limit),
            candidate_count=len(candidates),
        )
        # Preserve the strongest metadata hypothesis first.  A visual
        # candidate becomes the bounded runner-up (or first when metadata is
        # weak); the existing reference verifier remains the only component
        # allowed to attach canonical identity.
        ordered: list[dict] = []
        metadata_first = metadata_ranked[0] if metadata_ranked else None
        if metadata_first and float(metadata_first["score"]) >= fuzzy_threshold:
            ordered.append(metadata_first)
        for visual in visual_ranked:
            candidate = visual["candidate"]
            metadata = next((row for row in metadata_ranked if row["candidate"]["id"] == candidate["id"]), None)
            ordered.append(metadata or {
                "candidate": candidate,
                "score": 0.0,
                "signals": {},
            })
            ordered[-1]["signals"] = {
                **ordered[-1].get("signals", {}),
                "visual_retrieval_rank": visual["visual_rank"],
                "visual_descriptor_distance": visual["distance"],
            }
        ordered.extend(metadata_ranked)
        seen: set[str] = set()
        ranked = []
        for row in ordered:
            candidate_id = row["candidate"]["id"]
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            ranked.append(row)
            if len(ranked) >= candidate_limit:
                break
    if not ranked:
        return {
            "artwork_id": None,
            "confidence": 0.0,
            "alternatives": [],
            "recognized_but_not_cataloged": {"artist": artist, "title": title},
            "vision": ident,
        }

    top = ranked[0]
    match = top["candidate"]
    match_score = float(top["score"])
    runner_up = ranked[1]["candidate"] if len(ranked) > 1 and ranked[1]["score"] >= 0.45 else None
    alternatives = [row["candidate"]["id"] for row in ranked[1:3]]

    if benchmark_mode == "vision_metadata_only":
        final_confidence = min(0.90, max(0.0, (0.55 * model_confidence) + (0.45 * min(match_score, 1.0))))
        return {
            "artwork_id": match["id"] if match and match_score >= 0.30 else None,
            "confidence": final_confidence if match and match_score >= 0.30 else 0.0,
            "alternatives": alternatives,
            "recognition_mode": "VISION_METADATA_ONLY",
            "vision": ident,
            "top_candidates": [
                {"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]}
                for row in ranked[:5]
            ],
        }

    if not match or match_score < fuzzy_threshold:
        if policy != "TOP_N_METADATA":
            return {  # fast path: recognized something, but nothing catalog-adjacent
                "artwork_id": None,
                "confidence": 0.0,
                "alternatives": [],
                "recognized_but_not_cataloged": {"artist": artist, "title": title},
                "vision": ident,
                "top_candidates": [{"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]} for row in ranked[:3]],
            }

    if policy == "TOP_N_METADATA":
        topn_verdict = verify_top_candidates_with_openai(
            image_base64,
            ident,
            ranked[:candidate_limit],
            profile=profile,
        )
        topn_verdict = preserve_same_artist_confusion(topn_verdict, ranked)
        chosen_id = topn_verdict.get("chosen_id")
        if topn_verdict.get("decision") in {"MATCH", "NEEDS_CONFIRMATION"} and chosen_id:
            chosen = next((row["candidate"] for row in ranked if row["candidate"]["id"] == chosen_id), None)
            if not _stage2_artist_match_allowed(ident, chosen):
                topn_verdict["decision"] = "NO_MATCH"
                topn_verdict["chosen_id"] = None
                topn_verdict["confidence"] = 0.0
                topn_verdict["reason"] = (
                    "Rejected catalog attachment because the visual analysis "
                    "identified a different artist from the scoped candidate."
                )
            else:
                has_local_asset = bool(chosen and _reference_verification_allowed(chosen) and _local_reference_available(chosen))
                return {
                    "artwork_id": chosen_id,
                    "confidence": verifier_confidence(topn_verdict),
                    "alternatives": [
                        row["candidate"]["id"]
                        for row in ranked[:candidate_limit]
                        if row["candidate"]["id"] != chosen_id
                    ][:3],
                    "recognition_mode": "VISION_PLUS_ASSET" if has_local_asset else "VISION_READY",
                    "vision": ident,
                    "top_candidates": [
                        {"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]}
                        for row in ranked[:5]
                    ],
                    "stage2_verifier": topn_verdict,
                }
        return {
            "artwork_id": None,
            "confidence": float(topn_verdict.get("confidence", 0) or 0),
            "alternatives": [
                row["candidate"]["id"]
                for row in ranked[:3]
            ],
            "recognized_but_not_cataloged": {"artist": artist, "title": title},
            "vision": ident,
            "top_candidates": [
                {"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]}
                for row in ranked[:candidate_limit]
            ],
            "stage2_verifier": topn_verdict,
        }

    if _reference_verification_allowed(match):
        if any(row["candidate"].get("visual_descriptor") for row in ranked):
            if recognition_request_id:
                _log_recognition_event("recognition.reference_fetch_started", recognition_request_id=recognition_request_id, stage="reference_fetch", stage_status="started")
            if recognition_request_id:
                _log_recognition_event("recognition.verifier_started", recognition_request_id=recognition_request_id, stage="verifier_provider", stage_status="started")
            verdict = visual_verify_reference_candidates(image_base64, ranked, profile=profile)
            if recognition_request_id:
                _log_recognition_event("recognition.reference_fetch_completed", recognition_request_id=recognition_request_id, stage="reference_fetch", stage_status="completed")
            if recognition_request_id:
                _log_recognition_event("recognition.verifier_completed", recognition_request_id=recognition_request_id, stage="verifier_provider", stage_status="completed")
            verdict = preserve_same_artist_confusion(verdict, ranked)
            chosen_id = verdict.get("chosen_id")
            if verdict.get("decision") in {"MATCH", "NEEDS_CONFIRMATION"} and chosen_id:
                return {
                    "artwork_id": chosen_id,
                    "confidence": verifier_confidence(verdict),
                    "alternatives": [row["candidate"]["id"] for row in ranked if row["candidate"]["id"] != chosen_id][:3],
                    "recognition_mode": "VISION_PLUS_ASSET",
                    "vision": ident,
                    "top_candidates": [{"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]} for row in ranked[:5]],
                    "stage2_verifier": verdict,
                }
            return {
                "artwork_id": None,
                "confidence": float(verdict.get("confidence", 0) or 0),
                "alternatives": [row["candidate"]["id"] for row in ranked[:3]],
                "recognized_but_not_cataloged": {"artist": artist, "title": title},
                "vision": ident,
                "top_candidates": [{"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]} for row in ranked[:5]],
                "stage2_verifier": verdict,
            }
        verdict = visual_verify_single_candidate(image_base64, match, profile=profile, recognition_request_id=recognition_request_id)  # slow path
        if verdict.get("is_match"):
            visual_confidence = float(verdict.get("confidence", 0) or 0)
            final_confidence = min(max(model_confidence, match_score), visual_confidence)
            return {
                "artwork_id": match["id"],
                "confidence": final_confidence,
                "alternatives": alternatives,
                "recognition_mode": "VISION_PLUS_ASSET",
                "vision": ident,
                "top_candidates": [{"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]} for row in ranked[:5]],
            }

        # Top candidate visually rejected -- try the runner-up only if it also
        # has a rights-allowed external reference image.
        if runner_up and _reference_verification_allowed(runner_up):
            runner_verdict = visual_verify_single_candidate(image_base64, runner_up, profile=profile, recognition_request_id=recognition_request_id)
            if runner_verdict.get("is_match"):
                visual_confidence = float(runner_verdict.get("confidence", 0) or 0)
                final_confidence = min(max(model_confidence, match_score), visual_confidence)
                return {
                    "artwork_id": runner_up["id"],
                    "confidence": final_confidence,
                    "alternatives": [match["id"]],
                    "recognition_mode": "VISION_PLUS_ASSET",
                    "vision": ident,
                    "top_candidates": [{"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]} for row in ranked[:5]],
                }

        return {
            "artwork_id": None,
            "confidence": 0.0,
            "alternatives": alternatives,
            "recognized_but_not_cataloged": {"artist": artist, "title": title},
            "vision": ident,
            "top_candidates": [{"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]} for row in ranked[:5]],
        }

    # Louvre/non-asset path: OpenAI visual analysis + museum-scoped catalog
    # ranking can return an answer without fetching any reference image.
    # Confidence is intentionally capped below auto-match for weaker catalog
    # evidence so the existing confirmation UX absorbs ambiguity.
    final_confidence = min(0.94, max(0.0, (0.55 * model_confidence) + (0.45 * min(match_score, 1.0))))
    if match_score < 0.68:
        final_confidence = min(final_confidence, 0.80)
    elif match_score < 0.78:
        final_confidence = min(final_confidence, 0.88)
    return {
        "artwork_id": match["id"],
        "confidence": final_confidence,
        "alternatives": alternatives,
        "recognition_mode": "VISION_READY",
        "vision": ident,
        "top_candidates": [{"artwork_id": row["candidate"]["id"], "score": row["score"], "signals": row["signals"]} for row in ranked[:5]],
    }


# ---- Schemas ----------------------------------------------------------
class RecognizeRequest(BaseModel):
    image_base64: str
    museum_id: Optional[str] = None
    hall_hint: Optional[str] = None
    locale: str = "en"
    benchmark_mode: Optional[str] = None  # test-only: vision_metadata_only
    recognition_attempt_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    session_id: Optional[str] = None

    @field_validator("recognition_attempt_id", "anonymous_id", "session_id")
    @classmethod
    def recognition_ids_are_uuids(cls, value: Optional[str]):
        if value is None:
            return value
        try:
            return str(uuid.UUID(value))
        except ValueError as exc:
            raise ValueError("identifier must be a UUID") from exc


class RecognizedButNotCataloged(BaseModel):
    artist: Optional[str] = None
    title: Optional[str] = None


class RecognizeResponse(BaseModel):
    status: str  # "matched" | "needs_confirmation" | "no_match"
    artwork_id: Optional[str] = None
    confidence: float
    alternatives: List[str] = []
    recognition_mode: Optional[str] = None  # VISION_READY | VISION_PLUS_ASSET
    vision: Optional[dict] = None
    top_candidates: List[dict] = []
    stage2_verifier: Optional[dict] = None
    # Open recognition identified *something* (artist/title), but it didn't
    # fuzzy-match any catalog entry — never shown to the visitor as a full
    # card (no reviewed estimate/editorial text exists for it), but useful
    # for us to see what the model actually recognized outside the catalog.
    recognized_but_not_cataloged: Optional[RecognizedButNotCataloged] = None
    recognition_attempt_id: Optional[str] = None
    timings: Optional[dict] = None
    recognition_request_id: Optional[str] = None


class VisitCreate(BaseModel):
    museum_id: str
    locale: str = "en"


class VisitArtworkAdd(BaseModel):
    artwork_id: str
    confidence: float
    added: bool = False


class ExistingMarketContext(BaseModel):
    amountMillions: Optional[float] = None
    currency: Optional[str] = None
    workTitle: Optional[str] = None
    year: Optional[str] = None
    sourceReference: Optional[str] = None
    confidence: Optional[str] = None


class IndicativeValueRequest(BaseModel):
    artist: Optional[str] = None
    title: Optional[str] = None
    date: Optional[str] = None
    object_type: Optional[str] = None
    medium: Optional[str] = None
    dimensions: Optional[str] = None
    museum: Optional[str] = None
    movement: Optional[str] = None
    collection_importance: Optional[str] = None
    existing_market_context: Optional[ExistingMarketContext] = None


class IndicativeEstimate(BaseModel):
    currency: str
    low_eur: float
    high_eur: float
    valuation_band_id: str
    confidence: str
    short_reason: str
    assumptions: List[str]
    model: Optional[str] = None
    version: str
    generated_at: str
    grounding_fingerprint: str
    disclaimer: Optional[str] = None


class IndicativeValueResponse(BaseModel):
    eligible: bool
    reason: Optional[str] = None
    estimate: Optional[IndicativeEstimate] = None


INDICATIVE_VALUE_VERSION = "ai-indicative-estimate-v4"
INDICATIVE_VALUE_DISCLAIMER = (
    "ELYIO indicative estimate for scale only; not an appraisal, insurance value, offer price, or sale estimate."
)
MAX_AI_INDICATIVE_EUR = 1_000_000_000
VALUATION_BANDS: dict[str, tuple[int, int]] = {
    "V01": (100_000, 250_000),
    "V02": (250_000, 500_000),
    "V03": (500_000, 1_000_000),
    "V04": (1_000_000, 2_000_000),
    "V05": (2_000_000, 5_000_000),
    "V06": (5_000_000, 10_000_000),
    "V07": (10_000_000, 20_000_000),
    "V08": (20_000_000, 40_000_000),
    "V09": (40_000_000, 70_000_000),
    "V10": (70_000_000, 120_000_000),
    "V11": (120_000_000, 200_000_000),
    "V12": (200_000_000, 350_000_000),
    "V13": (350_000_000, 600_000_000),
    "V14": (600_000_000, 1_000_000_000),
}


def _indicative_value_fingerprint(req: IndicativeValueRequest) -> str:
    payload = {
        "version": INDICATIVE_VALUE_VERSION,
        "artist": req.artist,
        "title": req.title,
        "date": req.date,
        "object_type": req.object_type,
        "medium": req.medium,
        "dimensions": req.dimensions,
        "museum": req.museum,
        "movement": req.movement,
        "collection_importance": req.collection_importance,
        "market_context": req.existing_market_context.model_dump() if req.existing_market_context else None,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _indicative_value_eligible(req: IndicativeValueRequest) -> tuple[bool, str]:
    if not req.artist or not req.title:
        return False, "artist/title required"
    text = " ".join(
        x for x in [
            req.artist,
            req.title,
            req.object_type,
            req.medium,
            req.movement,
            req.collection_importance,
        ] if x
    ).lower()
    if re.search(r"(human remains|mummy|funerary|coin|fragment|weapon|armor|armour|ritual|sarcophagus|room|palace|architecture|chapel|tomb)", text):
        return False, "object category not suitable for market-range presentation"
    if re.search(r"(painting|oil|canvas|panel|portrait|self-portrait|drawing|pastel|watercolor|sculpture|statue|marble|bronze|bust|vase|bowl|ceramic|porcelain|decorative)", text):
        return True, "eligible fine/decorative art"
    if re.search(r"(monet|renoir|degas|cezanne|cézanne|gauguin|manet|van gogh|picasso|rodin|titian|leonardo|antonello|raphael|rembrandt|courbet|morisot|sisley)", text):
        return True, "eligible known art-market artist"
    return False, "insufficient evidence for indicative range"


def _normalize_indicative_estimate(data: Dict[str, Any], req: IndicativeValueRequest, fingerprint: str) -> Optional[dict]:
    band_id = str(data.get("valuation_band_id") or "").upper().strip()
    if band_id not in VALUATION_BANDS:
        print(json.dumps({
            "event": "indicative_value_rejected",
            "version": INDICATIVE_VALUE_VERSION,
            "reason": "invalid_band",
            "band": band_id,
            "artist": req.artist,
            "title": req.title,
        }, ensure_ascii=False))
        return None
    low_eur, high_eur = VALUATION_BANDS[band_id]
    confidence = str(data.get("confidence") or "LOW").upper()
    if confidence not in {"HIGH", "MEDIUM", "LOW"}:
        confidence = "LOW"
    high_cap_eur = _indicative_high_cap_eur(req, confidence)
    if high_eur > high_cap_eur:
        original_band = band_id
        band_id = _highest_band_with_high_at_or_below(high_cap_eur)
        low_eur, high_eur = VALUATION_BANDS[band_id]
        print(json.dumps({
            "event": "indicative_value_band_downgraded",
            "version": INDICATIVE_VALUE_VERSION,
            "reason": "market_anchor_or_confidence_cap",
            "artist": req.artist,
            "title": req.title,
            "original_band": original_band,
            "accepted_band": band_id,
            "confidence": confidence,
            "cap_eur": high_cap_eur,
            "has_market_anchor": bool(req.existing_market_context and req.existing_market_context.amountMillions),
        }, ensure_ascii=False))
    if not (math.isfinite(low_eur) and math.isfinite(high_eur)):
        return None
    if not (low_eur > 0 and high_eur > low_eur):
        return None
    if high_eur / low_eur > 10:
        return None
    if high_eur > MAX_AI_INDICATIVE_EUR:
        return None
    assumptions = data.get("assumptions")
    if not isinstance(assumptions, list):
        assumptions = []
    assumptions = [str(x)[:180] for x in assumptions if str(x).strip()][:5]
    if not assumptions:
        assumptions = ["Hypothetical scale estimate only.", "The museum work is not for sale."]
    return {
        "currency": "EUR",
        "low_eur": low_eur,
        "high_eur": high_eur,
        "valuation_band_id": band_id,
        "confidence": confidence,
        "short_reason": str(data.get("short_reason") or "Indicative range based on supplied artwork facts and market context.")[:260],
        "assumptions": assumptions,
        "model": INDICATIVE_VALUE_MODEL,
        "version": INDICATIVE_VALUE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "grounding_fingerprint": fingerprint,
        "disclaimer": INDICATIVE_VALUE_DISCLAIMER,
    }


def _indicative_high_cap_eur(req: IndicativeValueRequest, confidence: str) -> float:
    context_cap = _market_context_high_cap_eur(req, confidence)
    if context_cap:
        return context_cap
    # No trusted artist-market anchor means museum fame alone cannot justify
    # the top of the ladder. LOW confidence remains display-only on the
    # frontend and is intentionally capped at a modest broad range.
    if confidence == "HIGH":
        return 120_000_000
    if confidence == "MEDIUM":
        return 70_000_000
    return 10_000_000


def _heuristic_indicative_estimate(req: IndicativeValueRequest, fingerprint: str) -> Optional[dict]:
    context = req.existing_market_context
    if not context or not context.amountMillions or not context.currency:
        return None
    multiplier = 0.92 if context.currency in {"USD", "USD_MILLION"} else 1.17 if context.currency in {"GBP", "GBP_MILLION"} else 1.0
    eur_millions = context.amountMillions * multiplier
    text = " ".join(x for x in [req.title, req.object_type, req.medium, req.collection_importance] if x).lower()
    if re.search(r"(mona lisa|joconde|masterpiece|iconic|highlight|self-portrait|autoportrait)", text):
        midpoint = eur_millions * 0.72
    elif re.search(r"(painting|oil|canvas|panel|portrait)", text):
        midpoint = eur_millions * 0.28
    elif re.search(r"(sculpture|statue|marble|bronze|bust)", text):
        midpoint = eur_millions * 0.21
    else:
        midpoint = eur_millions * 0.09
    band_id = _valuation_band_for_midpoint_eur(midpoint * 1_000_000)
    return _normalize_indicative_estimate(
        {
            "valuation_band_id": band_id,
            "confidence": "LOW" if (context.confidence or "").upper() != "HIGH" else "MEDIUM",
            "short_reason": "Fallback indicative range derived from supplied trusted artist-market context.",
            "assumptions": [
                "Hypothetical scale estimate only.",
                "The museum work is not for sale.",
                "No invented auction citations were used.",
            ],
        },
        req,
        fingerprint,
    )


def _valuation_band_for_midpoint_eur(midpoint_eur: float) -> str:
    if not math.isfinite(midpoint_eur) or midpoint_eur <= 0:
        return "V01"
    for band_id, (low, high) in VALUATION_BANDS.items():
        if low <= midpoint_eur <= high:
            return band_id
    return "V14"


def _market_context_high_cap_eur(req: IndicativeValueRequest, confidence: str) -> Optional[float]:
    context = req.existing_market_context
    if not context or not context.amountMillions or not context.currency:
        return None
    multiplier = 0.92 if context.currency in {"USD", "USD_MILLION"} else 1.17 if context.currency in {"GBP", "GBP_MILLION"} else 1.0
    context_eur = context.amountMillions * multiplier * 1_000_000
    if not math.isfinite(context_eur) or context_eur <= 0:
        return None
    cap_multiple = 3.0 if confidence == "HIGH" else 2.5 if confidence == "MEDIUM" else 1.25
    return min(MAX_AI_INDICATIVE_EUR, context_eur * cap_multiple)


def _highest_band_with_high_at_or_below(max_high_eur: float) -> str:
    selected = "V01"
    for band_id, (_low, high) in VALUATION_BANDS.items():
        if high <= max_high_eur:
            selected = band_id
    return selected


@app.post("/v1/indicative-value", response_model=IndicativeValueResponse)
def indicative_value(req: IndicativeValueRequest):
    eligible, reason = _indicative_value_eligible(req)
    if not eligible:
        return IndicativeValueResponse(eligible=False, reason=reason)
    fingerprint = _indicative_value_fingerprint(req)
    if fingerprint in INDICATIVE_VALUE_CACHE:
        return IndicativeValueResponse(eligible=True, estimate=INDICATIVE_VALUE_CACHE[fingerprint])
    if not OPENAI_API_KEY:
        estimate = _heuristic_indicative_estimate(req, fingerprint)
        if estimate:
            INDICATIVE_VALUE_CACHE[fingerprint] = estimate
            return IndicativeValueResponse(eligible=True, estimate=estimate)
        return IndicativeValueResponse(eligible=False, reason="OpenAI key unavailable and no trusted market context supplied")

    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_RECOGNITION_TIMEOUT_SECONDS)
    system_prompt = (
        "You produce ELYIO indicative market ranges for museum visitors. "
        "This is a hypothetical scale estimate, not an appraisal, insurance value, offer price, or claim that the museum work can be sold. "
        "Use ONLY the supplied facts and supplied market context. Do not invent citations, auction houses, sale dates, comparable work names, provenance, or prices. "
        "You must choose exactly one valuation_band_id from this EUR ladder; do not output raw money numbers. "
        "Bands: V01 €0.1-0.25M; V02 €0.25-0.5M; V03 €0.5-1M; V04 €1-2M; V05 €2-5M; V06 €5-10M; V07 €10-20M; "
        "V08 €20-40M; V09 €40-70M; V10 €70-120M; V11 €120-200M; V12 €200-350M; V13 €350-600M; V14 €600M-1B. "
        "If trusted artist-market context is supplied, do not choose a band many multiples above it unless the supplied facts make exceptional importance explicit. "
        "If no trusted market context is supplied, do not use museum fame alone to choose V11 or above. "
        "If evidence is weak, choose LOW confidence and a conservative band rather than fake precision. "
        "Respond with one strict JSON object only: "
        '{"valuation_band_id":"V01|V02|...|V14","confidence":"HIGH|MEDIUM|LOW","short_reason":"...","assumptions":["..."]}'
    )
    try:
        resp = _openai_chat_completion_with_retries(
            client,
            model=INDICATIVE_VALUE_MODEL,
            max_tokens=450,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(req.model_dump(), ensure_ascii=False)},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        estimate = _normalize_indicative_estimate(data, req, fingerprint)
    except Exception:
        estimate = _heuristic_indicative_estimate(req, fingerprint)
    if not estimate:
        return IndicativeValueResponse(eligible=False, reason="estimate validation failed")
    INDICATIVE_VALUE_CACHE[fingerprint] = estimate
    return IndicativeValueResponse(eligible=True, estimate=estimate)


def _log_uncataloged_sighting(
    artist: Optional[str], title: Optional[str], museum_id: Optional[str],
    db: Optional[Session] = None,
) -> None:
    """Best-effort institution-scoped demand signal; never canonical data."""
    if not artist or not title:
        return

    if db is None and SessionLocal is None:
        return
    owns_session = db is None
    db = db or SessionLocal()
    try:
        row = (
            db.query(UncatalogedSighting)
            .filter(
                UncatalogedSighting.artist == artist,
                UncatalogedSighting.title == title,
                UncatalogedSighting.museum_id == museum_id,
            )
            .first()
        )
        if row:
            row.count += 1
            row.last_seen_at = datetime.now(timezone.utc)
        else:
            db.add(UncatalogedSighting(artist=artist, title=title, museum_id=museum_id))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        if owns_session:
            db.close()


# ---- Recognition (§12, §8.3 confidence policy) -------------------------
@app.post("/v1/recognize", response_model=RecognizeResponse)
def recognize(
    req: RecognizeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    attempt_id = req.recognition_attempt_id or str(uuid.uuid4())
    recognition_request_id = f"rec_{uuid.uuid4().hex[:16]}"
    _log_recognition_event("recognition.request_received", recognition_request_id=recognition_request_id, endpoint="/v1/recognize", museum_context_present=bool(req.museum_id), museum_id=req.museum_id or None, locale=req.locale)
    profile = _new_latency_profile(attempt_id) if req.benchmark_mode == "latency_profile" else None

    if req.museum_id and _timed(profile, "api.controlled_preview_check", lambda: _controlled_preview_only(db, req.museum_id)) and not _trusted_internal_request(request):
        raise HTTPException(status_code=404, detail="institution not found")
    existing_attempt = _timed(profile, "db.attempt_idempotency_lookup", lambda: db.get(RecognitionAttempt, attempt_id))
    if existing_attempt is not None:
        if existing_attempt.response_payload:
            return RecognizeResponse(**existing_attempt.response_payload)
        raise HTTPException(status_code=409, detail="recognition attempt is already in progress")

    try:
        if req.museum_id:
            institution_config = _timed(
                profile,
                "db.institution_runtime_config",
                lambda: get_institution_runtime_config(db, req.museum_id),
            )
            candidates = _timed(
                profile,
                "db.recognition_candidates",
                lambda: get_recognition_candidates(db, req.museum_id, runtime_config=institution_config),
            )
        else:
            # Museum context is optional: open recognition can still identify
            # an uncatalogued work and use the existing AI fallback path.
            institution_config = None
            candidates = _timed(profile, "db.recognition_candidates_global", lambda: get_global_recognition_candidates(db))
        _log_recognition_event("recognition.context_resolved", recognition_request_id=recognition_request_id, endpoint="/v1/recognize", engine_path="museum_catalog" if req.museum_id else "generic", museum_context_present=bool(req.museum_id), museum_id=req.museum_id or None, locale=req.locale)
        _log_recognition_event("recognition.candidates_ready", recognition_request_id=recognition_request_id, candidate_count=len(candidates), stage="candidate_generation", stage_status="completed")
    except InstitutionNotReadyError as e:
        _log_recognition_event("recognition_configuration_error", museum_id=req.museum_id, reason="institution_not_ready", recognition_attempt_id=attempt_id)
        raise HTTPException(status_code=409, detail={"code": "institution_not_ready", "message": str(e)})
    except CatalogUnavailableError as e:
        _log_recognition_event("recognition_failed", museum_id=req.museum_id, reason="catalog_unavailable", recognition_attempt_id=attempt_id)
        raise HTTPException(status_code=503, detail=str(e))

    internal_test = _trusted_internal_request(request)
    _timed(profile, "db.analytics_identity_link", lambda: _link_analytics_identity(db, req.anonymous_id, current_user))
    _timed(profile, "db.analytics_session_validation", lambda: _validate_analytics_session(db, req.session_id, req.anonymous_id, current_user))
    attempt = RecognitionAttempt(
        recognition_attempt_id=attempt_id,
        anonymous_id=req.anonymous_id,
        user_id=str(current_user.id) if current_user else None,
        session_id=req.session_id,
        institution_id=req.museum_id or None,
        internal_test=internal_test,
    )
    db.add(attempt)
    _timed(profile, "db.attempt_create_commit", lambda: db.commit())
    _log_recognition_event("recognition.attempt_persisted", recognition_request_id=recognition_request_id, stage="attempt_persistence", stage_status="completed")
    started = time.perf_counter()

    def finish(response: RecognizeResponse, outcome: str) -> RecognizeResponse:
        response.recognition_request_id = recognition_request_id
        response.recognition_attempt_id = attempt_id
        attempt.completed_at = datetime.now(timezone.utc)
        attempt.terminal_outcome = outcome
        if outcome == "uncataloged_result":
            attempt.engine_outcome = "UNCATALOGED_IDENTIFIED"
            attempt.visitor_resolution = "GENERATED_RESULT"
        elif response.status == "matched":
            attempt.engine_outcome = "CATALOG_CANDIDATE_MATCHED"
            attempt.visitor_resolution = "AUTO_ACCEPTED"
        elif response.status == "needs_confirmation":
            attempt.engine_outcome = "CATALOG_CANDIDATE_MATCHED"
            attempt.visitor_resolution = "CONFIRMATION_REQUIRED"
        elif outcome == "no_match":
            attempt.engine_outcome = "NO_MATCH"
            attempt.visitor_resolution = "NO_RESULT"
        else:
            attempt.engine_outcome = "ENGINE_ERROR"
            attempt.visitor_resolution = "NO_RESULT"
        attempt.response_status = response.status
        attempt.artwork_id = response.artwork_id
        attempt.confidence = response.confidence
        attempt.recognition_mode = response.recognition_mode
        attempt.latency_ms = round((time.perf_counter() - started) * 1000)
        attempt.response_payload = response.model_dump(mode="json")
        _log_recognition_event("recognition.persistence_started", recognition_request_id=recognition_request_id, stage="result_persistence", stage_status="started")
        _timed(profile, "db.attempt_finish_commit", lambda: db.commit())
        _log_recognition_event("recognition.persistence_completed", recognition_request_id=recognition_request_id, stage="result_persistence", stage_status="completed")
        _log_recognition_event("recognition.response_success" if response.status in {"matched", "needs_confirmation"} else "recognition.response_no_match", recognition_request_id=recognition_request_id, stage_status="completed", http_status=200, outcome=response.status)
        response.timings = _latency_profile_summary(profile)
        return response

    def fail_request(outcome: str) -> None:
        attempt.completed_at = datetime.now(timezone.utc)
        attempt.terminal_outcome = outcome
        attempt.engine_outcome = "INVALID_INPUT" if outcome == "invalid_image" else "ENGINE_ERROR"
        attempt.visitor_resolution = "NO_RESULT"
        attempt.latency_ms = round((time.perf_counter() - started) * 1000)
        db.commit()

    if not req.image_base64:
        fail_request("invalid_image")
        _log_recognition_event("recognition.error", recognition_request_id=recognition_request_id, failed_stage="request_validation", error_code="RECOGNITION_INVALID_REQUEST", error_class="ValidationError", sanitized_error_message="image_base64 required", http_status=400, retryable=False)
        raise HTTPException(status_code=400, detail={"error_code": "RECOGNITION_INVALID_REQUEST", "message": "image_base64 required", "recognition_request_id": recognition_request_id})
    _log_recognition_event("recognition.request_validated", recognition_request_id=recognition_request_id, stage="request_validation", stage_status="completed")
    if len(req.image_base64) > MAX_RECOGNITION_IMAGE_BASE64_CHARS:
        fail_request("invalid_image")
        raise HTTPException(status_code=413, detail="image too large")
    try:
        _timed(profile, "image.base64_validation", lambda: base64.b64decode(req.image_base64, validate=True))
    except Exception:
        fail_request("invalid_image")
        raise HTTPException(status_code=400, detail="image_base64 is not valid base64")

    _log_recognition_event("recognition.stage1_started", recognition_request_id=recognition_request_id, stage="stage1_provider", museum_context_present=bool(req.museum_id))
    _log_recognition_event("recognition_started", museum_id=req.museum_id or None, locale=req.locale, recognition_attempt_id=attempt_id, recognition_request_id=recognition_request_id)

    if OPENAI_API_KEY:
        try:
            result = _timed(
                profile,
                "recognition.total",
                lambda: recognize_with_vision(
                    req.image_base64,
                    req.museum_id,
                    req.hall_hint,
                    candidates,
                    benchmark_mode=req.benchmark_mode,
                    institution_config=institution_config,
                    profile=profile,
                    recognition_request_id=recognition_request_id,
                ),
            )
            _log_recognition_event("recognition.stage1_completed", recognition_request_id=recognition_request_id, stage="stage1_provider", stage_status="completed")
        except Exception as e:
            _log_recognition_event(
                "recognition_failed",
                museum_id=req.museum_id,
                reason="ai_error",
                error_type=type(e).__name__,
                error_message=str(e)[:500],
                recognition_attempt_id=attempt_id,
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
            return finish(RecognizeResponse(status="no_match", confidence=0.0), "failed")

        artwork_id = result.get("artwork_id")
        confidence = float(result.get("confidence", 0))
        alternatives = result.get("alternatives", [])
        recognized_but_not_cataloged = result.get("recognized_but_not_cataloged")
        recognition_mode = result.get("recognition_mode")
        vision = result.get("vision")
        top_candidates = result.get("top_candidates", [])
        stage2_verifier = result.get("stage2_verifier")
        candidate_ids = {a["id"] for a in candidates}

        if not artwork_id or artwork_id not in candidate_ids:
            if recognized_but_not_cataloged:
                _log_uncataloged_sighting(
                    recognized_but_not_cataloged.get("artist"),
                    recognized_but_not_cataloged.get("title"), req.museum_id, db,
                )
            _log_recognition_event(
                "recognition_completed",
                museum_id=req.museum_id,
                status="no_match",
                catalog_match=False,
                confidence=confidence,
                ai_candidate=recognized_but_not_cataloged,
                resolved_artwork_id=None,
                recognition_attempt_id=attempt_id,
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
            return finish(RecognizeResponse(status="no_match", confidence=confidence,
                                      recognized_but_not_cataloged=recognized_but_not_cataloged,
                                      vision=vision, top_candidates=top_candidates,
                                      stage2_verifier=stage2_verifier), "uncataloged_result" if recognized_but_not_cataloged else "no_match")
        confidence_auto = institution_config.confidence_auto if institution_config else 0.92
        confidence_review = institution_config.confidence_review if institution_config else 0.75
        if confidence >= confidence_auto:
            _log_recognition_event(
                "recognition_completed",
                museum_id=req.museum_id,
                status="matched",
                catalog_match=True,
                confidence=confidence,
                resolved_artwork_id=artwork_id,
                recognition_mode=recognition_mode,
                recognition_attempt_id=attempt_id,
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
            return finish(RecognizeResponse(status="matched", artwork_id=artwork_id, confidence=confidence,
                                      recognition_mode=recognition_mode, vision=vision,
                                      top_candidates=top_candidates,
                                      stage2_verifier=stage2_verifier), "success")
        elif confidence >= confidence_review:
            _log_recognition_event(
                "recognition_completed",
                museum_id=req.museum_id,
                status="needs_confirmation",
                catalog_match=True,
                confidence=confidence,
                resolved_artwork_id=artwork_id,
                recognition_mode=recognition_mode,
                recognition_attempt_id=attempt_id,
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
            return finish(RecognizeResponse(status="needs_confirmation", artwork_id=artwork_id,
                                      confidence=confidence, alternatives=alternatives,
                                      recognition_mode=recognition_mode, vision=vision,
                                      top_candidates=top_candidates,
                                      stage2_verifier=stage2_verifier), "success")
        else:
            _log_recognition_event(
                "recognition_completed",
                museum_id=req.museum_id,
                status="no_match",
                catalog_match=False,
                confidence=confidence,
                resolved_artwork_id=artwork_id,
                recognition_mode=recognition_mode,
                recognition_attempt_id=attempt_id,
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
            return finish(RecognizeResponse(status="no_match", confidence=confidence,
                                      recognition_mode=recognition_mode, vision=vision,
                                      top_candidates=top_candidates,
                                      stage2_verifier=stage2_verifier), "no_match")

    # Development-only fallback mock. Production should fail explicitly when
    # the AI provider is not configured, never return a random artwork.
    if not ALLOW_RECOGNITION_MOCK:
        _log_recognition_event("recognition_failed", museum_id=req.museum_id, reason="openai_key_missing", recognition_attempt_id=attempt_id)
        fail_request("failed")
        raise HTTPException(status_code=503, detail="recognition is not configured")
    if not candidates:
        _log_recognition_event("recognition_completed", museum_id=req.museum_id, status="no_match", catalog_match=False, confidence=0.0, recognition_attempt_id=attempt_id)
        return finish(RecognizeResponse(status="no_match", confidence=0.0), "no_match")
    candidate = random.choice(candidates)
    confidence = round(random.uniform(0.75, 0.99), 3)
    confidence_auto = institution_config.confidence_auto if institution_config else 0.92
    confidence_review = institution_config.confidence_review if institution_config else 0.75
    if confidence >= confidence_auto:
        return finish(RecognizeResponse(status="matched", artwork_id=candidate["id"], confidence=confidence), "success")
    elif confidence >= confidence_review:
        alts = [a["id"] for a in random.sample(candidates, k=min(2, len(candidates)))]
        return finish(RecognizeResponse(status="needs_confirmation", artwork_id=candidate["id"],
                                  confidence=confidence, alternatives=alts), "success")
    else:
        return finish(RecognizeResponse(status="no_match", confidence=confidence), "no_match")


# ---- Museums (Phase 2 §1: geofence generalization) -----------------------
class MuseumOut(BaseModel):
    id: str
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    geofence_radius_m: int
    external_source: Optional[str] = None
    external_id: Optional[str] = None
    slug: Optional[str] = None
    common_name: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    website_url: Optional[str] = None
    collection_categories: List[str] = []
    notable_terms: List[str] = []
    source: Optional[str] = None
    source_updated_at: Optional[str] = None
    experience_level: str = "AI_GUIDE"
    curated_artwork_count: int = 0
    country_code: Optional[str] = None
    timezone: Optional[str] = None
    default_locale: Optional[str] = None
    supported_locales: List[str] = []
    display_currency: Optional[str] = None


@app.get("/v1/museums", response_model=List[MuseumOut])
def list_museums(
    request: Request,
    q: Optional[str] = None,
    city: Optional[str] = None,
    region: Optional[str] = None,
    include_controlled_preview: bool = False,
    limit: int = Query(1500, ge=1, le=1500),
    db: Session = Depends(get_db),
):
    """Public museum directory.

    The response stays deliberately lightweight: directory metadata only,
    never artwork catalogs. CURATED means a museum has ELYIO catalog coverage;
    AI_GUIDE means recognition can still run and fall back to the AI result.
    """
    query = db.query(Museum).filter(Museum.active.is_(True))
    if q:
        needle = f"%{q.lower()}%"
        query = query.filter(
            or_(
                func.lower(Museum.name).like(needle),
                func.lower(Museum.common_name).like(needle),
                func.lower(Museum.city).like(needle),
                func.lower(Museum.external_id).like(needle),
            )
        )
    if city:
        query = query.filter(func.lower(Museum.city) == city.lower())
    if region:
        query = query.filter(func.lower(Museum.region) == region.lower())

    rows = (
        query.outerjoin(InstitutionProfile, InstitutionProfile.institution_id == Museum.id).order_by(
            case((Museum.experience_level == "CURATED", 0), else_=1),
            InstitutionProfile.directory_priority.asc().nullslast(),
            Museum.city.asc().nullslast(),
            Museum.name.asc(),
        )
        .limit(limit)
        .all()
    )
    allow_controlled = include_controlled_preview and _trusted_internal_request(request)
    rows = [
        row for row in rows
        if allow_controlled or (row.content_policy or {}).get("controlled_preview_only") is not True
    ]
    museum_ids = [row.id for row in rows]
    counts = {
        museum_id: count
        for museum_id, count in (
            db.query(Artwork.museum_id, func.count(Artwork.id))
            .filter(Artwork.museum_id.in_(museum_ids))
            .group_by(Artwork.museum_id)
            .all()
            if museum_ids
            else []
        )
    }
    for museum_id in museum_ids:
        try:
            counts[museum_id] = count_catalog_artworks(db, museum_id)
        except InstitutionNotReadyError:
            # Directory remains available while diagnostics expose the missing
            # profile; recognition itself still fails closed.
            counts[museum_id] = 0
    return [
        MuseumOut(
            id=row.id,
            name=row.name,
            lat=row.lat,
            lng=row.lng,
            geofence_radius_m=row.geofence_radius_m or 150,
            external_source=row.external_source,
            external_id=row.external_id,
            slug=row.slug,
            common_name=row.common_name,
            city=row.city,
            department=row.department,
            region=row.region,
            address=row.address,
            postal_code=row.postal_code,
            website_url=row.website_url,
            collection_categories=row.collection_categories or [],
            notable_terms=row.notable_terms or [],
            source=row.source_url,
            source_updated_at=row.source_updated_at.date().isoformat() if row.source_updated_at else None,
            experience_level=row.experience_level or "AI_GUIDE",
            curated_artwork_count=counts.get(row.id, 0),
            country_code=row.country_code,
            timezone=row.timezone,
            default_locale=row.default_locale,
            supported_locales=row.supported_locales or [],
            display_currency=row.display_currency,
        )
        for row in rows
    ]


# ---- Artworks -----------------------------------------------------------
@app.get("/v1/artworks/{artwork_id}")
def get_artwork_detail(artwork_id: str, request: Request, locale: str = "en", mode: str = "normal", db: Session = Depends(get_db)):
    raw_artwork = db.get(Artwork, artwork_id)
    if raw_artwork and _controlled_preview_only(db, raw_artwork.museum_id) and not _trusted_internal_request(request):
        raise HTTPException(status_code=404, detail="artwork not found")
    try:
        art = get_catalog_artwork(db, artwork_id)
    except CatalogUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not art:
        raise HTTPException(status_code=404, detail="artwork not found")
    localizations = (
        db.query(ArtworkLocalization)
        .filter(ArtworkLocalization.artwork_id == artwork_id)
        .order_by(ArtworkLocalization.locale.asc(), ArtworkLocalization.mode.asc())
        .all()
    )
    return {
        **art,
        "locale": locale,
        "mode": mode,
        "localizations": [
            {
                "locale": row.locale,
                "mode": row.mode or "normal",
                "title": row.title,
                "analogy": row.analogy,
                "why_it_matters": row.why_it_matters,
                "where_to_look": row.where_to_look,
                "rarity_note": row.rarity_note,
                "audio_script": row.audio_script,
                "audio_url": row.audio_url,
                "editorial_status": row.editorial_status,
            }
            for row in localizations
        ],
    }


@app.get("/v1/image-proxy")
def image_proxy(url: str, width: int = Query(512, ge=64, le=2048)):
    """Server-side fetch + resize + on-disk cache for a Wikimedia image URL,
    re-served with our own CORS header (via the CORSMiddleware configured
    above) so the frontend's canvas export can draw it -- see
    _fetch_proxy_image_bytes's doc comment for why this exists at all.
    Allowlisted to Wikimedia hosts only: this is a public, unauthenticated
    GET, so it must not become a general-purpose open proxy.

    `width` defaults to 512 (existing callers -- Recap thumbnails, the
    mobile Home hero -- are unaffected) and is clamped to [64, 2048]: the
    lower bound keeps this a real thumbnail proxy rather than an arbitrary
    pixel-fetch primitive, the upper bound stays under the Orsay clock
    source's real 2048px height (3072x2048, checked directly against
    Wikimedia's API) so no caller can force an upscale, and more generally
    caps how much cache-bloat/Wikimedia bandwidth an unauthenticated width
    value can cause."""
    _validate_proxy_url(url)
    try:
        image_bytes = _fetch_proxy_image_bytes(url, width=width)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"image proxy fetch failed: {e}")
    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        # Immutable + long max-age: the cache key is a hash of the URL, and
        # Wikimedia file revisions at a fixed URL don't change in practice
        # for this catalog's purposes -- same convention as the on-disk cache
        # never re-checking freshness once a file exists.
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )


# ---- Visits (§12) — real Supabase-backed, requires a signed-in user ------
# Registration (email magic link + Google; Apple deferred) now happens on
# Home before "Begin your visit" is reachable at all, so every one of these
# requires a verified JWT (get_current_user, app/auth.py) — a Visit can no
# longer exist without a real user_id, matching models.py's Visit.user_id
# being NOT NULL now (it used to default anonymous=True).
def _get_owned_visit(visit_id: str, current_user: User, db: Session) -> Visit:
    # 404 (not 403) whether the visit doesn't exist or belongs to someone
    # else — doesn't confirm to a caller which case it is.
    visit = db.get(Visit, visit_id)
    if not visit or visit.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="visit not found")
    return visit


@app.post("/v1/visits")
def create_visit(
    body: VisitCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visit = Visit(id=str(uuid.uuid4()), user_id=current_user.id, museum_id=body.museum_id, locale=body.locale)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return {
        "id": visit.id,
        "museum_id": visit.museum_id,
        "locale": visit.locale,
        "started_at": visit.started_at.isoformat(),
        "completed_at": None,
        "artworks": [],
    }


@app.post("/v1/visits/{visit_id}/artworks")
def add_visit_artwork(
    visit_id: str,
    body: VisitArtworkAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visit = _get_owned_visit(visit_id, current_user, db)
    try:
        artwork = get_catalog_artwork(db, body.artwork_id)
    except CatalogUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not artwork or artwork.get("museum_id") != visit.museum_id:
        raise HTTPException(status_code=404, detail="artwork not found")
    db.add(VisitArtwork(visit_id=visit.id, artwork_id=body.artwork_id, confidence=body.confidence, added=body.added))
    db.commit()
    count = db.query(VisitArtwork).filter(VisitArtwork.visit_id == visit.id).count()
    return {"ok": True, "count": count}


@app.get("/v1/visits/{visit_id}/progress")
def visit_progress(
    visit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visit = _get_owned_visit(visit_id, current_user, db)

    seen_ids = {va.artwork_id for va in visit.artworks}
    try:
        seen = get_catalog_artworks_by_ids(db, visit.museum_id, seen_ids)
        catalog_count = count_catalog_artworks(db, visit.museum_id)
    except CatalogUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    artists = {a["artist"] for a in seen if a.get("artist")}
    aggregate_values = [value for a in seen if (value := aggregate_eligible_value(a)) is not None]
    value_low = sum(value["low"] for value in aggregate_values)
    value_high = sum(value["high"] for value in aggregate_values)
    market_context_count = sum(1 for a in seen if (a.get("value_reveal") or {}).get("mode") == "MARKET_CONTEXT")
    beyond_market_count = sum(1 for a in seen if (a.get("value_reveal") or {}).get("mode") == "BEYOND_MARKET")
    unvalued_count = len(seen) - len(aggregate_values) - market_context_count - beyond_market_count

    return {
        "works_count": len(seen),
        "artists_count": len(artists),
        "value_low_eur_m": value_low,
        "value_high_eur_m": value_high,
        "estimated_value_artwork_count": len(aggregate_values),
        "market_context_count": market_context_count,
        "beyond_market_count": beyond_market_count,
        "unvalued_count": unvalued_count,
        "route_completion_pct": round(100 * len(seen) / catalog_count, 1) if catalog_count else 0.0,
    }


@app.post("/v1/visits/{visit_id}/complete")
def complete_visit(
    visit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    visit = _get_owned_visit(visit_id, current_user, db)
    visit.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "completed_at": visit.completed_at.isoformat()}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "release": {
            "git_sha": os.environ.get("GIT_COMMIT_SHA", "unknown"),
            "build_timestamp": os.environ.get("BUILD_TIMESTAMP", "unknown"),
            "environment": os.environ.get("DEPLOYMENT_ENV", "unknown"),
        },
    }
