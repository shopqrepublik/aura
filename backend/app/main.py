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
  4. Current — hybrid: open recognition -> fuzzy_match_catalog() (candidate
     screen, not a final answer) -> visual_verify_single_candidate() (ONE
     reference image, only when a candidate was actually found). Two fast
     paths skip the vision call entirely: nothing recognized, or nothing
     catalog-adjacent by text. Text matching's job is now recall (find
     plausible candidates, tolerate false positives like the model saying
     "Study of Olympia" scoring high against our "Olympia" entry); the
     visual step's job is precision (reject same-title/same-artist
     look-alikes that don't actually match on pixels — this is what catches
     a Cézanne still life confidently misidentified as a different, real
     Cézanne still life, which pure text similarity structurally cannot).

Requires OPENAI_API_KEY in the environment (or a .env file, see
.env.example). Falls back to the old random mock if the key is missing, so
the frontend keeps working without a key during UI development.

Run:
    pip install -r requirements.txt
    copy the repo-root .env.example to .env and fill in OPENAI_API_KEY
    uvicorn app.main:app --reload --port 8090
"""
import base64
import json
import os
import random
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()  # reads .env from the repo root if present; no-op otherwise

app = FastAPI(title="AURA API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://elyio.vercel.app",
        "https://elyio.co",
        "https://www.elyio.co",
        "http://localhost:3000",  # local web/ dev
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
RECOGNITION_MODEL = "gpt-4o"  # Stage 1 (open recognition) — drives accuracy, left alone per instructions
# Stage 2 (visual_verify_single_candidate) TRIED gpt-4o-mini to cut slow-path
# latency — rolled back. On the 101-catalog test it dropped 76/101 -> 71/101
# (2 confirmed false negatives on exact-title-match candidates gpt-4o accepted
# correctly), and on the 13 real-photo test it flipped BOTH previously-correct
# in-catalog matches (Cezanne onions, Vetheuil) to wrong rejections, 12/13 ->
# 11/13. Confident-wrong stayed at 0 in both cases — this is a real-accuracy
# regression, not a safety one — but "don't regress accuracy" was the explicit
# bar, so Stage 2 stays on gpt-4o. See README for the full before/after numbers.
VISUAL_VERIFY_MODEL = "gpt-4o"


# ---- In-memory demo store (replace with Supabase/Postgres session) --------
VISITS: dict = {}

DEMO_ARTWORKS = [
    {"id": "orsay_rf_1995_10", "artist": "Gustave Courbet", "title": "L'Origine du monde", "year": "1866", "hall": None, "inventory_number": "RF 1995 10", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Origin-of-the-World.jpg", "estimate_low": 14, "estimate_high": 22, "needs_editorial_review": True},
    {"id": "orsay_rf_1668", "artist": "Édouard Manet", "title": "Luncheon on the Grass", "year": "1863", "hall": None, "inventory_number": "RF 1668", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Luncheon%20on%20the%20Grass%20-%20Google%20Art%20Project.jpg", "estimate_low": 55, "estimate_high": 85, "needs_editorial_review": True},
    {"id": "orsay_rf_2739", "artist": "Pierre-Auguste Renoir", "title": "Bal du moulin de la Galette", "year": "1876", "hall": None, "inventory_number": "RF 2739", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Renoir%2C%20Pierre-Auguste%20-%20Dance%20at%20Le%20Moulin%20de%20la%20Galette%2C%201876.jpg", "estimate_low": 70, "estimate_high": 90, "needs_editorial_review": True},
    {"id": "orsay_rf_644", "artist": "Édouard Manet", "title": "Olympia", "year": "1863", "hall": None, "inventory_number": "RF 644", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Olympia%20-%20Google%20Art%20Project%203.jpg", "estimate_low": 55, "estimate_high": 85, "needs_editorial_review": True},
    {"id": "orsay_rf_1975_19", "artist": "Vincent van Gogh", "title": "Starry Night Over the Rhone", "year": "1888", "hall": None, "inventory_number": "RF 1975 19", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20Starry%20Night%20-%20Google%20Art%20Project.jpg", "estimate_low": 95, "estimate_high": 130, "needs_editorial_review": True},
    {"id": "orsay_rf_1951_42", "artist": "Vincent van Gogh", "title": "The Church at Auvers", "year": "1890", "hall": None, "inventory_number": "RF 1951 42", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20Church%20in%20Auvers-sur-Oise%2C%20View%20from%20the%20Chevet%20-%20Google%20Art%20Project.jpg", "estimate_low": 45, "estimate_high": 80, "needs_editorial_review": True},
    {"id": "orsay_rf_325", "artist": "Gustave Courbet", "title": "A Burial at Ornans", "year": "1849-1850", "hall": None, "inventory_number": "RF 325", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Courbet%20-%20A%20Burial%20at%20Ornans%20-%20Google%20Art%20Project.jpg", "estimate_low": 14, "estimate_high": 25, "needs_editorial_review": True},
    {"id": "orsay_rf_253", "artist": "William-Adolphe Bouguereau", "title": "The Birth of Venus", "year": "1879", "hall": None, "inventory_number": "RF 253", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20%281825-1905%29%20-%20The%20Birth%20of%20Venus%20%281879%29.jpg", "estimate_low": 3.5, "estimate_high": 8, "needs_editorial_review": True},
    {"id": "orsay_rf_699", "artist": "James McNeill Whistler", "title": "Whistler's Mother", "year": "1871", "hall": None, "inventory_number": "RF 699", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Whistlers%20Mother%20high%20res.jpg", "estimate_low": 2.5, "estimate_high": 6, "needs_editorial_review": True},
    {"id": "orsay_rf_2257", "artist": "Gustave Courbet", "title": "The Painter's Studio", "year": "1854-1855", "hall": None, "inventory_number": "RF 2257", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Courbet%20LAtelier%20du%20peintre.jpg", "estimate_low": 14, "estimate_high": 24, "needs_editorial_review": True},
    {"id": "orsay_rf_1984", "artist": "Edgar Degas", "title": "L'Absinthe", "year": "1875", "hall": None, "inventory_number": "RF 1984", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20In%20a%20Caf%C3%A9%20-%20Google%20Art%20Project%202.jpg", "estimate_low": 13, "estimate_high": 25, "needs_editorial_review": True},
    {"id": "orsay_rf_219", "artist": "Jean-Auguste-Dominique Ingres", "title": "The Source", "year": "1856", "hall": None, "inventory_number": "RF 219", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean%20Auguste%20Dominique%20Ingres%20-%20The%20Spring%20-%20Google%20Art%20Project%202.jpg", "estimate_low": 3, "estimate_high": 8, "needs_editorial_review": True},
    {"id": "orsay_rf_2772", "artist": "Édouard Manet", "title": "The Balcony", "year": "1868", "hall": None, "inventory_number": "RF 2772", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20The%20Balcony%20-%20Google%20Art%20Project.jpg", "estimate_low": 25, "estimate_high": 45, "needs_editorial_review": True},
    {"id": "orsay_rf_592", "artist": "Jean-François Millet", "title": "The Gleaners", "year": "1857", "hall": None, "inventory_number": "RF 592", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-Fran%C3%A7ois%20Millet%20-%20Gleaners%20-%20Google%20Art%20Project.jpg", "estimate_low": 2.5, "estimate_high": 7, "needs_editorial_review": True},
    {"id": "orsay_rf_2738", "artist": "Pierre-Auguste Renoir", "title": "La Balançoire", "year": "1876", "hall": None, "inventory_number": "RF 2738", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Swing-Renoir.jpeg", "estimate_low": 15, "estimate_high": 35, "needs_editorial_review": True},
    {"id": "orsay_rf_2010_8", "artist": "William-Adolphe Bouguereau", "title": "Dante and Virgil in Hell", "year": "1850", "hall": None, "inventory_number": "RF 2010 8", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William%20Bouguereau%20-%20Dante%20and%20Virgile%20-%20Google%20Art%20Project%202.jpg", "estimate_low": 3.5, "estimate_high": 7, "needs_editorial_review": True},
    {"id": "orsay_rf_755", "artist": "Pierre-Auguste Renoir", "title": "Girls at the Piano", "year": "1892", "hall": None, "inventory_number": "RF 755", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Auguste%20Renoir%20-%20Young%20Girls%20at%20the%20Piano%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2765", "artist": "Paul Gauguin", "title": "Tahitian Women on the Beach", "year": "1890", "hall": None, "inventory_number": "RF 2765", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20056.jpg", "estimate_low": 85, "estimate_high": 120, "needs_editorial_review": True},
    {"id": "orsay_rf_2773", "artist": "Claude Monet", "title": "Women in the Garden", "year": "1866", "hall": None, "inventory_number": "RF 2773", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20024.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_273", "artist": "Alexandre Cabanel", "title": "The Birth of Venus", "year": "1863", "hall": None, "inventory_number": "RF 273", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Alexandre%20Cabanel%20-%20The%20Birth%20of%20Venus%20-%20Google%20Art%20Project%202.jpg", "estimate_low": 1, "estimate_high": 3, "needs_editorial_review": True},
    {"id": "orsay_rf_1949_17", "artist": "Vincent van Gogh", "title": "Self-portrait", "year": "1889", "hall": None, "inventory_number": "RF 1949 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20Self-Portrait%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1992", "artist": "Édouard Manet", "title": "The Fifer", "year": "1866", "hall": None, "inventory_number": "RF 1992", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Manet%2C%20Edouard%20-%20Young%20Flautist%2C%20or%20The%20Fifer%2C%201866%20%282%29.jpg", "estimate_low": 25, "estimate_high": 45, "needs_editorial_review": True},
    {"id": "orsay_rf_051804048", "artist": "Jean-François Millet", "title": "The Angelus", "year": "1858", "hall": None, "inventory_number": "RF 051804048", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/JEAN-FRAN%C3%87OIS%20MILLET%20-%20El%20%C3%81ngelus%20%28Museo%20de%20Orsay%2C%201857-1859.%20%C3%93leo%20sobre%20lienzo%2C%2055.5%20x%2066%20cm%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2210", "artist": "Edgar Degas", "title": "The Bellelli Family", "year": "1858", "hall": None, "inventory_number": "RF 2210", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20The%20Bellelli%20Family%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1984_164", "artist": "Claude Monet", "title": "The Magpie", "year": "1868", "hall": None, "inventory_number": "RF 1984 164", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Magpie%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2718", "artist": "Gustave Caillebotte", "title": "Les raboteurs de parquet", "year": "1875", "hall": None, "inventory_number": "RF 2718", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Caillebotte%20-%20The%20Floor%20Planers%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2511", "artist": "Georges Seurat", "title": "The Circus", "year": "1891", "hall": None, "inventory_number": "RF 2511", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Georges%20Seurat%20-%20The%20Circus%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1978_13", "artist": "Pierre-Auguste Renoir", "title": "Dance in the City", "year": "1883", "hall": None, "inventory_number": "RF 1978 13", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20019.jpg", "estimate_low": 15, "estimate_high": 35, "needs_editorial_review": True},
    {"id": "orsay_rf_1979_64", "artist": "Pierre-Auguste Renoir", "title": "Dance in the Country", "year": "1883", "hall": None, "inventory_number": "RF 1979 64", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre%20Auguste%20Renoir%20-%20Country%20Dance%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 35, "needs_editorial_review": True},
    {"id": "orsay_rf_1998_30", "artist": "Édouard Manet", "title": "Berthe Morisot with a Bouquet of Violets", "year": "1872", "hall": None, "inventory_number": "RF 1998 30", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Berthe%20Morisot%20With%20a%20Bouquet%20of%20Violets%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True},
    {"id": "orsay_rf_1957_7", "artist": "Claude Monet", "title": "Le Déjeuner sur l'herbe", "year": "1865", "hall": None, "inventory_number": "RF 1957 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Le%20dejeurner%20sur%20l%27herbe%20%28left%20panel%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2205", "artist": "Édouard Manet", "title": "Portrait of Emile Zola", "year": "1868", "hall": None, "inventory_number": "RF 2205", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20049.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True},
    {"id": "orsay_rf_338", "artist": "Gustave Courbet", "title": "The Wounded Man", "year": "1844", "hall": None, "inventory_number": "RF 338", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Portrait%20of%20the%20Artist%20called%20The%20Wounded%20Man%20%28L%27homme%20bless%C3%A9%29%20by%20Gustave%20Courbet.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_64", "artist": "Rosa Bonheur", "title": "Ploughing in the Nivernais", "year": "1849", "hall": None, "inventory_number": "RF 64", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Rosa%20Bonheur%20-%20Ploughing%20in%20Nevers%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_88", "artist": "Jean-Léon Gérôme", "title": "Young Greeks Attending a Cock Fight", "year": "1846", "hall": None, "inventory_number": "RF 88", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-L%C3%A9on%20G%C3%A9r%C3%B4me%20-%20Young%20Greeks%20Attending%20a%20Cock%20Fight%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2450", "artist": "Frédéric Bazille", "title": "The Pink Dress", "year": "1864", "hall": None, "inventory_number": "RF 2450", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Fr%C3%A9d%C3%A9ric%20Bazille%20-%20The%20Pink%20Dress%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2778", "artist": "Claude Monet", "title": "Régates à Argenteuil", "year": "1872", "hall": None, "inventory_number": "RF 2778", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Regattas%20at%20Argenteuil%20-%20Google%20Art%20Project.jpg", "estimate_low": 32, "estimate_high": 44, "needs_editorial_review": True},
    {"id": "orsay_rf_1983_6", "artist": "Claude Monet", "title": "The artist's garden at Giverny", "year": "1900", "hall": None, "inventory_number": "RF 1983 6", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Monet%20-%20Monets%20Garten%20in%20Giverny.jpg", "estimate_low": 25, "estimate_high": 45, "needs_editorial_review": True},
    {"id": "orsay_rf_1976", "artist": "Edgar Degas", "title": "The Ballet Class", "year": "1871", "hall": None, "inventory_number": "RF 1976", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20The%20Ballet%20Class%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1990_7", "artist": "Jean-Léon Gérôme", "title": "Jerusalem", "year": "1867", "hall": None, "inventory_number": "RF 1990 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-L%C3%A9on%20G%C3%A9r%C3%B4me%20Consummatum%20est.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_lux_1439", "artist": "Frédéric Bazille", "title": "Bazille's Studio", "year": "1870", "hall": None, "inventory_number": "LUX 1439", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Fr%C3%A9d%C3%A9ric%20Bazille%20-%20Bazille%27s%20Studio%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_876", "artist": "Gustave Caillebotte", "title": "Vue de toits", "year": "1878", "hall": None, "inventory_number": "RF 876", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Caillebotte%20-%20Rooftops%20in%20the%20Snow%20%28snow%20effect%29%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1981_33", "artist": "William-Adolphe Bouguereau", "title": "The Dance", "year": "1856", "hall": None, "inventory_number": "RF 1981 33", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20%281825-1905%29%20-%20The%20Dance%20%281856%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1937_7", "artist": "Henri Rousseau", "title": "The Snake Charmer", "year": "1907", "hall": None, "inventory_number": "RF 1937 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/HENRI%20ROUSSEAU%20-%20La%20Encantadora%20de%20Serpientes%20%28Museo%20de%20Orsay%2C%20Par%C3%ADs%2C%201907.%20%C3%93leo%20sobre%20lienzo%2C%20169%20x%20189.5%20cm%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1952_17", "artist": "Vincent van Gogh", "title": "The siesta (after Millet)", "year": "1890", "hall": None, "inventory_number": "RF 1952 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20siesta%20%28after%20Millet%29%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1961_6", "artist": "Paul Gauguin", "title": "Arearea", "year": "1892", "hall": None, "inventory_number": "RF 1961 6", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20Arearea%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2749", "artist": "Frédéric Bazille", "title": "Réunion de famille", "year": "1867", "hall": None, "inventory_number": "RF 2749", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/R%C3%A9union%20de%20famille%20-%20Fr%C3%A9d%C3%A9ric%20Bazille%20-%20mus%C3%A9e%20d%27Orsay%20RF%202749.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1944_17", "artist": "Édouard Manet", "title": "The Reading", "year": "1865", "hall": None, "inventory_number": "RF 1944 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20005.jpg", "estimate_low": 6, "estimate_high": 11, "needs_editorial_review": True},
    {"id": "orsay_rf_2849", "artist": "Berthe Morisot", "title": "The Cradle", "year": "1872", "hall": None, "inventory_number": "RF 2849", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Berthe%20Morisot%20-%20The%20Cradle%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2795", "artist": "Pierre-Auguste Renoir", "title": "The Bathers", "year": "1918", "hall": None, "inventory_number": "RF 2795", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre%20Auguste%20Renoir%20-%20The%20Bathers%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_729", "artist": "Henri Fantin-Latour", "title": "A Studio at Les Batignolles", "year": "1870", "hall": None, "inventory_number": "RF 729", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20Fantin-Latour%20-%20A%20Studio%20at%20Les%20Batignolles%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1970", "artist": "Paul Cézanne", "title": "La Maison du pendu, Auvers-sur-Oise", "year": "1874", "hall": None, "inventory_number": "RF 1970", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/La%20Maison%20du%20pendu%2C%20Auvers-sur-Oise%2C%20par%20Paul%20C%C3%A9zanne%2C%20FWN%2081.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_d2006_3_5", "artist": "Pierre-Auguste Renoir", "title": "Portrait of Frédéric Bazille Painting", "year": "1867", "hall": None, "inventory_number": "D2006.3.5", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20-%20Fr%C3%A9d%C3%A9ric%20Bazille.jpg", "estimate_low": 4, "estimate_high": 8, "needs_editorial_review": True},
    {"id": "orsay_rf_1676", "artist": "Claude Monet", "title": "The Poppy Field near Argenteuil", "year": "1873", "hall": None, "inventory_number": "RF 1676", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Poppy%20Field%20-%20Google%20Art%20Project.jpg", "estimate_low": 38, "estimate_high": 55, "needs_editorial_review": True},
    {"id": "orsay_rf_2617", "artist": "Paul Gauguin", "title": "La belle Angèle", "year": "1889", "hall": None, "inventory_number": "RF 2617", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20La%20Belle%20Ang%C3%A8le%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1959_18", "artist": "Édouard Manet", "title": "L'Asperge", "year": "1880", "hall": None, "inventory_number": "RF 1959 18", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Asparagus%20-%20Google%20Art%20Project.jpg", "estimate_low": 5, "estimate_high": 9, "needs_editorial_review": True},
    {"id": "orsay_rf_1991", "artist": "Édouard Manet", "title": "Lola de Valence", "year": "1862", "hall": None, "inventory_number": "RF 1991", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Lola%20de%20Valence%20%281862%29%20-%20Edouard%20Manet%20%28Mus%C3%A9e%20d%27Orsay%2C%20Paris%29.jpg", "estimate_low": 9, "estimate_high": 16, "needs_editorial_review": True},
    {"id": "orsay_rf_1977_12", "artist": "Édouard Manet", "title": "Portrait of Monsieur and Madame Auguste Manet", "year": "1860", "hall": None, "inventory_number": "RF 1977 12", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Portrait%20of%20M.%20and%20Mme.%20Auguste%20Manet%20%281860%29%20-%20Edouard%20Manet%20%28Mus%C3%A9e%20d%27Orsay%2C%20Paris%29.jpg", "estimate_low": 9, "estimate_high": 16, "needs_editorial_review": True},
    {"id": "orsay_rf_1965_14", "artist": "Vincent van Gogh", "title": "L'Italienne", "year": "1887", "hall": None, "inventory_number": "RF 1965 14", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20Italian%20Woman%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_4046", "artist": "Edgar Degas", "title": "The Tub", "year": "1886", "hall": None, "inventory_number": "RF 4046", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20Le%20Tub%20%281886%20Mus%C3%A9e%20d%27Orsay%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2010_7", "artist": "William-Adolphe Bouguereau", "title": "Equality Before Death", "year": "1848", "hall": None, "inventory_number": "RF 2010 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Bouguereau%20-%20%C3%A9galit%C3%A9%20devant%20la%20mort%201848.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_3666", "artist": "Pierre-Auguste Renoir", "title": "Claude Monet", "year": "1875", "hall": None, "inventory_number": "RF 3666", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Auguste%20Renoir%20-%20Claude%20Monet%20-%20Google%20Art%20Project.jpg", "estimate_low": 10, "estimate_high": 18, "needs_editorial_review": True},
    {"id": "orsay_do_1986_16", "artist": "Albert Edelfelt", "title": "Portrait of Louis Pasteur", "year": "1885", "hall": None, "inventory_number": "DO 1986 16", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Albert%20Edelfelt%20-%20Louis%20Pasteur%20-%201885.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1994_2", "artist": "Paul Gauguin", "title": "Portrait of the Artist with the Yellow Christ", "year": "1890", "hall": None, "inventory_number": "RF 1994 2", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20Portrait%20of%20the%20Artist%20with%20the%20Yellow%20Christ%20%281890-91%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2010_4", "artist": "William-Adolphe Bouguereau", "title": "The Oreads", "year": "1902", "hall": None, "inventory_number": "RF 2010 4", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20-%20Les%20Or%C3%A9ades.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1994", "artist": "Édouard Manet", "title": "Suzanne Manet Playing the Piano", "year": "1867", "hall": None, "inventory_number": "RF 1994", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/%C3%89douard%20Manet%20-%20Madame%20Manet%20ou%20Piano.jpg", "estimate_low": 6, "estimate_high": 11, "needs_editorial_review": True},
    {"id": "orsay_rf_2242", "artist": "Henri de Toulouse-Lautrec", "title": "La Toilette", "year": "1889", "hall": None, "inventory_number": "RF 2242", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/%28Albi%29%20Rousse%20%28La%20Toilette%29%20-%201889%20-%20Henri%20de%20Toulouse-Lautrec%20-%20Mus%C3%A9e%20d%27Orsay%2C%20Paris.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2817", "artist": "Paul Cézanne", "title": "Still Life with Onions", "year": "1898", "hall": None, "inventory_number": "RF 2817", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20C%C3%A9zanne%20-%20Still%20Life%20with%20Onions%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2740", "artist": "Pierre-Auguste Renoir", "title": "Torse, effet de soleil", "year": "1875", "hall": None, "inventory_number": "RF 2740", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Torso%20Effect%20of%20Sunlight%20Renoir%201876.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2011", "artist": "Claude Monet", "title": "A Cart on the Snowy Road at Honfleur", "year": "1865", "hall": None, "inventory_number": "RF 2011", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Monet%2C%20A%20Cart%20on%20the%20Snowy%20Road%20at%20Honfleur%20%281865%20or%201867%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_inv_10168", "artist": "Edouard Louis Dubufe", "title": "The Congress of Paris", "year": "1856", "hall": None, "inventory_number": "INV 10168", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Dubufe%20Congr%C3%A8s%20de%20Paris.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1959_5", "artist": "Paul Gauguin", "title": "Vairumati", "year": "1897", "hall": None, "inventory_number": "RF 1959 5", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20135.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1664", "artist": "Henri Fantin-Latour", "title": "Homage to Delacroix", "year": "1864", "hall": None, "inventory_number": "RF 1664", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Hommage%20%C3%A0%20Delacroix%20-%20Henri%20Fantin-Latour.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1966_7", "artist": "Paul Gauguin", "title": "Self-portrait with hat", "year": "1893", "hall": None, "inventory_number": "RF 1966 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20111.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2173", "artist": "Henri Fantin-Latour", "title": "Around the Piano", "year": "1885", "hall": None, "inventory_number": "RF 2173", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20fantin-latour%2C%20attorno%20al%20piano%2C%201885%20-%20frameless.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1993", "artist": "Édouard Manet", "title": "Clair de lune sur le port de Boulogne", "year": "1869", "hall": None, "inventory_number": "RF 1993", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Ed.%20Manet.%20Clair%20de%20lune%20sur%20le%20port%20de%20Boulogne.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2774", "artist": "Claude Monet", "title": "The Luncheon", "year": "1873", "hall": None, "inventory_number": "RF 2774", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Monet%20Luncheon.jpg", "estimate_low": 10, "estimate_high": 25, "needs_editorial_review": True},
    {"id": "orsay_rf_2244", "artist": "Pierre-Auguste Renoir", "title": "Portrait of Madame Charpentier", "year": "1876", "hall": None, "inventory_number": "RF 2244", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20-%20Madame%20Charpentier%20-%2001.jpg", "estimate_low": 20, "estimate_high": 32, "needs_editorial_review": True},
    {"id": "orsay_bx_d_18", "artist": "Henri Gervex", "title": "Rolla", "year": "1878", "hall": None, "inventory_number": "Bx D 18", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20Gervex%20-%20Rolla%2003.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1967_5", "artist": "Frédéric Bazille", "title": "L'Ambulance improvisée", "year": "1865", "hall": None, "inventory_number": "RF 1967 5", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Bazille%20L%27Ambulance%20improvis%C3%A9e%201865.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1978", "artist": "Edgar Degas", "title": "Ballet Rehearsal on Stage", "year": "1874", "hall": None, "inventory_number": "RF 1978", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20Ballet%20Rehearsal%20on%20Stage%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2325", "artist": "Vincent van Gogh", "title": "Restaurant de la Sirène à Asnières", "year": "1887", "hall": None, "inventory_number": "RF 2325", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Van%20Gogh%20-%20Das%20Restaurant%20de%20la%20Sir%C3%A9ne%20in%20Asni%C3%A9res.jpeg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1944_9", "artist": "Vincent van Gogh", "title": "Portrait of Eugène Boch", "year": "1888", "hall": None, "inventory_number": "RF 1944 9", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20Eug%C3%A8ne%20Boch%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1951_40", "artist": "Alfred Sisley", "title": "Vue du canal Saint-Martin", "year": "1870", "hall": None, "inventory_number": "RF 1951 40", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Sisley%2C%20St%20Martin%20Canal%201870.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1973_25", "artist": "Vincent van Gogh", "title": "Hôpital Saint-Paul à Saint-Rémy-de-Provence", "year": "1889", "hall": None, "inventory_number": "RF 1973 25", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Hospital%20in%20Saint-Remy.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1955_20", "artist": "Paul Cézanne", "title": "Pont de Maincy", "year": "1879", "hall": None, "inventory_number": "RF 1955 20", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pont%20de%20Maincy%2C%20par%20Paul%20C%C3%A9zanne.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2417", "artist": "Edgar Degas", "title": "L'Orchestre de l'Opéra", "year": "1868", "hall": None, "inventory_number": "RF 2417", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20The%20Orchestra%20at%20the%20Opera%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_3736", "artist": "Edgar Degas", "title": "Lorenzo Pagans and Auguste de Gas", "year": "1871", "hall": None, "inventory_number": "RF 3736", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20Lorenzo%20Pagans%20and%20Auguste%20de%20Gas%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1972", "artist": "Paul Cézanne", "title": "Apples and Oranges", "year": "1899", "hall": None, "inventory_number": "RF 1972", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Nature%20morte%20aux%20pommes%20et%20aux%20oranges%2C%20par%20Paul%20C%C3%A9zanne.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1959", "artist": "Henri Fantin-Latour", "title": "Un coin de table", "year": "1872", "hall": None, "inventory_number": "RF 1959", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20Fantin-Latour%20-%20By%20the%20Table%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_inv_3451", "artist": "Thomas Couture", "title": "The Romans of the Decadence", "year": "1847", "hall": None, "inventory_number": "INV 3451", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Thomas%20Couture%20-%20Romans%20during%20the%20Decadence%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1956_13", "artist": "Paul Cézanne", "title": "La Femme à la cafetière (Woman with a Coffeepot)", "year": "1895", "hall": None, "inventory_number": "RF 1956 13", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20C%C3%A9zanne%20-%20Woman%20with%20a%20Coffeepot%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1937_41", "artist": "Claude Monet", "title": "The Railway Bridge at Argenteuil", "year": "1874", "hall": None, "inventory_number": "RF 1937 41", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Le%20Pont%20d%27Argenteuil%20-%20Claude%20Monet.jpg", "estimate_low": 35, "estimate_high": 45, "needs_editorial_review": True},
    {"id": "orsay_rf_2621", "artist": "Claude Monet", "title": "Woman with a Parasol, facing left", "year": "1886", "hall": None, "inventory_number": "RF 2621", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Femme%20%C3%A0%20l%27ombrelle%20tourn%C3%A9e%20vers%20la%20gauche%20-%20Claude%20Monnet%20-%20Mus%C3%A9e%20d%27Orsay%20RF%202621.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2661", "artist": "Édouard Manet", "title": "Portrait of Stéphane Mallarmé", "year": "1876", "hall": None, "inventory_number": "RF 2661", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20St%C3%A9phane%20Mallarm%C3%A9%20-%20Google%20Art%20Project.jpg", "estimate_low": 15, "estimate_high": 28, "needs_editorial_review": True},
    {"id": "orsay_rf_1963_3", "artist": "Claude Monet", "title": "Camille Monet on her deathbed", "year": "1879", "hall": None, "inventory_number": "RF 1963 3", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Camille%20Monet%20sur%20son%20lit%20de%20mort.JPG", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_lux_367", "artist": "Camille Pissarro", "title": "The Red Roofs, Côte Saint-Denis at Pontoise, Winter Effect", "year": "1877", "hall": None, "inventory_number": "LUX 367", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Camille%20Pissarro%20011.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2020", "artist": "Alfred Sisley", "title": "Flooding at Port-Marly", "year": "1876", "hall": None, "inventory_number": "RF 2020", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/La%20inundaci%C3%B3n%20en%20Port%20Marly%2C%20por%20Alfred%20Sisley.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_8048", "artist": "Claude Monet", "title": "La Rue Montorgueil", "year": "1878", "hall": None, "inventory_number": "8048", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Rue%20Montorgueil%20in%20Paris.%20Celebration%20of%20June%2030%2C%201878%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2787", "artist": "Alfred Sisley", "title": "The Regatta at Molesey", "year": "1874", "hall": None, "inventory_number": "RF 2787", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Alfred%20Sisley%20050.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    # Manual editorial addition (#101, not from the sitelinks-ranked Top 100 pull) —
    # this is the spec's own flagship walkthrough example (§7.4) and the original
    # demo catalog's very first entry. Real Wikidata record (Q17496088, RF 2006),
    # it just has 0 Wikidata sitelinks so it never surfaced in the automated ranking.
    {"id": "orsay_rf_2006", "artist": "Claude Monet", "title": "Vétheuil, Sunset", "year": "1900", "hall": None, "inventory_number": "RF 2006", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20monet%2C%20v%C3%A9theuil%2C%20sole%20al%20tramonto%2C%201900%20ca.JPG", "estimate_low": 20, "estimate_high": 40, "needs_editorial_review": True},
]

CONFIDENCE_AUTO = 0.92
CONFIDENCE_REVIEW = 0.82


def recognize_open(image_base64: str, museum_id: str) -> dict:
    """
    Open recognition — no candidate list in the prompt at all. A 13-photo
    real-world test showed the closed-catalog prompt (and even the two-stage
    visual-verification version) sometimes forces a wrong catalog id when the
    right answer isn't in the list, or is a same-artist neighbour of it — the
    model has to pick *something* from what it's given. Asking openly, the
    way a plain ChatGPT query would, lets the model say "I don't know this
    specific work" instead of guessing from a constrained menu.
    """
    from openai import OpenAI  # imported lazily so the module still loads without the package during UI-only dev

    client = OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = (
        "You are an art expert identifying an artwork photographed by a museum visitor "
        f"(likely at {museum_id or 'a French national museum'}). Identify the artist and title "
        "exactly as you recognize them, from your own knowledge — do NOT limit yourself to any "
        "predefined list. If you do not recognize the specific work, say so honestly (title: null) "
        "rather than guessing. Give the title in English if you know an accepted English title.\n\n"
        'Respond with a single valid json object only, no prose, no markdown fences: '
        '{"artist": "<artist name or null>", "title": "<title or null>", '
        '"confidence": <0-1 float, how confident you are in this identification>}.'
    )

    resp = client.chat.completions.create(
        model=RECOGNITION_MODEL,
        max_tokens=200,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                {"type": "text", "text": "What artwork is this?"}
            ]}
        ]
    )
    return json.loads(resp.choices[0].message.content)


_ARTICLE_RE = re.compile(r"\b(the|a|an|la|le|les|l'|un|une)\b", re.IGNORECASE)


def _normalize_for_matching(s: str) -> str:
    """Strips leading/embedded articles (EN+FR) before fuzzy comparison —
    without this, "Ballet Rehearsal on Stage" vs "The Rehearsal Onstage"
    loses points purely on "The"/"Ballet", not on anything meaningful."""
    if not s:
        return ""
    s = s.replace("’", "'")
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


def fuzzy_match_catalog(artist: Optional[str], title: Optional[str]):
    """Matches a freely-stated (artist, title) against DEMO_ARTWORKS. Returns
    (best_match_or_None, best_score, runner_up_or_None)."""
    from rapidfuzz import fuzz  # imported lazily, same rationale as the openai import above

    if not title:
        return None, 0.0, None

    title_n = _normalize_for_matching(title)
    artist_n = _normalize_for_matching(artist or "")

    scored = []
    for a in DEMO_ARTWORKS:
        artist_score = fuzz.token_sort_ratio(artist_n, _normalize_for_matching(a["artist"])) / 100
        if artist_score < FUZZY_ARTIST_GATE:
            continue
        cat_title_n = _normalize_for_matching(a["title"])
        title_score = max(
            fuzz.token_sort_ratio(title_n, cat_title_n),
            fuzz.partial_ratio(title_n, cat_title_n),
        ) / 100
        combined = 0.35 * artist_score + 0.65 * title_score
        scored.append((combined, a))

    if not scored:
        return None, 0.0, None
    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best = scored[0]
    runner_up = scored[1][1] if len(scored) > 1 and scored[1][0] >= 0.5 else None
    return best, best_score, runner_up


# One reference image per verified candidate, cached to disk — Wikimedia
# Commons rate-limits repeated bot traffic (HTTP 429) on re-fetch.
REFERENCE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".reference_cache")
REFERENCE_IMAGE_UA = "AURA-MVP-backend/1.0 (contact: repo owner)"

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
    query = dict(urllib.parse.parse_qsl(parsed.query))
    query["width"] = str(width)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
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


def _fetch_reference_image_b64(artwork: dict) -> str:
    os.makedirs(REFERENCE_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(REFERENCE_CACHE_DIR, f'{artwork["id"]}.jpg')
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")

    import urllib.request

    raw = None
    thumb_url = _wikimedia_thumbnail_url(artwork["image_url"], width=512)
    if thumb_url:
        try:
            req = urllib.request.Request(thumb_url, headers={"User-Agent": REFERENCE_IMAGE_UA})
            with _urlopen_with_retry(req, timeout=30) as resp:
                raw = resp.read()  # thumbnails are server-generated and always small
        except Exception as e:
            print(f"[reference-image] thumbnail fetch failed for {artwork['id']} ({e}), "
                  f"falling back to the original with a hard size cap")
            raw = None

    if raw is None:
        raw = _fetch_reference_image_original_bytes(artwork["image_url"])

    img = _decode_and_resize(raw, target_w=512)
    img.save(cache_path, format="JPEG", quality=85)
    with open(cache_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def visual_verify_single_candidate(image_base64: str, candidate: dict) -> dict:
    """
    The step that actually catches what text matching structurally cannot:
    is this the SAME painting, or just a same-artist/same-title-sounding one?
    Exactly one reference image — not three like the old two-stage design —
    because by this point fuzzy_match_catalog() has already narrowed it to
    one specific claim to check, not a shortlist to pick from.
    """
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    ref_b64 = _fetch_reference_image_b64(candidate)

    system_prompt = (
        "You are verifying whether a museum visitor's photo shows the SAME specific artwork as "
        "a reference image — not just a similar or same-artist work, and not just a work with a "
        "similar-sounding title. A different painting by the same artist, or a different work that "
        "happens to share a generic title, does NOT count as a match — only the same physical "
        f'object counts. The reference image is: {candidate["artist"]} — "{candidate["title"]}" '
        f'({candidate["year"]}).\n\n'
        'Respond with a single valid json object only, no prose, no markdown fences: '
        '{"is_match": true or false, "confidence": <0-1 float, how confident you are in this judgment>}.'
    )

    resp = client.chat.completions.create(
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
        ]
    )
    return json.loads(resp.choices[0].message.content)


def recognize_with_vision(image_base64: str, museum_id: str, hall_hint: Optional[str]) -> dict:
    """
    Hybrid: open recognition (no candidate list) -> fuzzy text match against
    DEMO_ARTWORKS -> ONE visual verification call, but only when a candidate
    was actually found. Two fast paths skip the visual call entirely (model
    recognized nothing, or nothing in the catalog is even textually close);
    only a real candidate pays the extra latency. See FUZZY_CANDIDATE_THRESHOLD
    and visual_verify_single_candidate() for why both stages are necessary —
    neither alone can be both safe and accurate. Layer 2 editorial content
    (estimates, why/where/rarity) is still only ever pulled from our reviewed
    database after a confirmed match — the model never generates it, at
    either stage.
    """
    ident = recognize_open(image_base64, museum_id)
    artist, title = ident.get("artist"), ident.get("title")
    model_confidence = float(ident.get("confidence", 0) or 0)

    if not title:
        return {"artwork_id": None, "confidence": 0.0, "alternatives": []}  # fast path: nothing recognized

    match, match_score, runner_up = fuzzy_match_catalog(artist, title)
    if not match or match_score < FUZZY_CANDIDATE_THRESHOLD:
        return {  # fast path: recognized something, but nothing catalog-adjacent
            "artwork_id": None,
            "confidence": 0.0,
            "alternatives": [],
            "recognized_but_not_cataloged": {"artist": artist, "title": title},
        }

    verdict = visual_verify_single_candidate(image_base64, match)  # slow path
    if not verdict.get("is_match"):
        return {
            "artwork_id": None,
            "confidence": 0.0,
            "alternatives": [],
            "recognized_but_not_cataloged": {"artist": artist, "title": title},
        }

    visual_confidence = float(verdict.get("confidence", 0) or 0)
    final_confidence = min(model_confidence, visual_confidence)
    alternatives = [runner_up["id"]] if runner_up else []
    return {"artwork_id": match["id"], "confidence": final_confidence, "alternatives": alternatives}


# ---- Schemas ----------------------------------------------------------
class RecognizeRequest(BaseModel):
    image_base64: str
    museum_id: str
    hall_hint: Optional[str] = None
    locale: str = "en"


class RecognizedButNotCataloged(BaseModel):
    artist: Optional[str] = None
    title: Optional[str] = None


class RecognizeResponse(BaseModel):
    status: str  # "matched" | "needs_confirmation" | "no_match"
    artwork_id: Optional[str] = None
    confidence: float
    alternatives: List[str] = []
    # Open recognition identified *something* (artist/title), but it didn't
    # fuzzy-match any catalog entry — never shown to the visitor as a full
    # card (no reviewed estimate/editorial text exists for it), but useful
    # for us to see what the model actually recognized outside the catalog.
    recognized_but_not_cataloged: Optional[RecognizedButNotCataloged] = None


class VisitCreate(BaseModel):
    museum_id: str
    locale: str = "en"


class VisitArtworkAdd(BaseModel):
    artwork_id: str
    confidence: float
    added: bool = False


# ---- Recognition (§12, §8.3 confidence policy) -------------------------
@app.post("/v1/recognize", response_model=RecognizeResponse)
def recognize(req: RecognizeRequest):
    if not req.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 required")

    if OPENAI_API_KEY:
        try:
            result = recognize_with_vision(req.image_base64, req.museum_id, req.hall_hint)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"recognition failed: {e}")

        artwork_id = result.get("artwork_id")
        confidence = float(result.get("confidence", 0))
        alternatives = result.get("alternatives", [])
        recognized_but_not_cataloged = result.get("recognized_but_not_cataloged")

        if not artwork_id or artwork_id not in {a["id"] for a in DEMO_ARTWORKS}:
            return RecognizeResponse(status="no_match", confidence=confidence,
                                      recognized_but_not_cataloged=recognized_but_not_cataloged)
        if confidence >= CONFIDENCE_AUTO:
            return RecognizeResponse(status="matched", artwork_id=artwork_id, confidence=confidence)
        elif confidence >= CONFIDENCE_REVIEW:
            return RecognizeResponse(status="needs_confirmation", artwork_id=artwork_id,
                                      confidence=confidence, alternatives=alternatives)
        else:
            return RecognizeResponse(status="no_match", confidence=confidence)

    # Fallback mock — lets frontend/UI work run without an API key.
    candidate = random.choice(DEMO_ARTWORKS)
    confidence = round(random.uniform(0.75, 0.99), 3)
    if confidence >= CONFIDENCE_AUTO:
        return RecognizeResponse(status="matched", artwork_id=candidate["id"], confidence=confidence)
    elif confidence >= CONFIDENCE_REVIEW:
        alts = [a["id"] for a in random.sample(DEMO_ARTWORKS, k=min(2, len(DEMO_ARTWORKS)))]
        return RecognizeResponse(status="needs_confirmation", artwork_id=candidate["id"],
                                  confidence=confidence, alternatives=alts)
    else:
        return RecognizeResponse(status="no_match", confidence=confidence)


# ---- Artworks -----------------------------------------------------------
@app.get("/v1/artworks/{artwork_id}")
def get_artwork(artwork_id: str, locale: str = "en", mode: str = "normal"):
    art = next((a for a in DEMO_ARTWORKS if a["id"] == artwork_id), None)
    if not art:
        raise HTTPException(status_code=404, detail="artwork not found")
    # Real implementation joins artworks + artwork_localizations(locale, mode)
    # + artwork_estimates, with English fallback per §10.
    return {**art, "locale": locale, "mode": mode}


# ---- Visits (§12) --------------------------------------------------------
@app.post("/v1/visits")
def create_visit(body: VisitCreate):
    visit_id = str(uuid.uuid4())
    VISITS[visit_id] = {
        "id": visit_id,
        "museum_id": body.museum_id,
        "locale": body.locale,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "artworks": [],
    }
    return VISITS[visit_id]


@app.post("/v1/visits/{visit_id}/artworks")
def add_visit_artwork(visit_id: str, body: VisitArtworkAdd):
    visit = VISITS.get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="visit not found")
    visit["artworks"].append(body.model_dump())
    return {"ok": True, "count": len(visit["artworks"])}


@app.get("/v1/visits/{visit_id}/progress")
def visit_progress(visit_id: str):
    visit = VISITS.get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="visit not found")

    seen_ids = {va["artwork_id"] for va in visit["artworks"]}
    seen = [a for a in DEMO_ARTWORKS if a["id"] in seen_ids]
    artists = {a["artist"] for a in seen}
    # estimate_low/high are null until an editor reviews them (§8.4, §11) — most
    # of the catalog has none yet, so unreviewed works simply don't add to the total.
    value_low = sum(a["estimate_low"] for a in seen if a["estimate_low"] is not None)
    value_high = sum(a["estimate_high"] for a in seen if a["estimate_high"] is not None)

    return {
        "works_count": len(seen),
        "artists_count": len(artists),
        "value_low_eur_m": value_low,
        "value_high_eur_m": value_high,
        "route_completion_pct": round(100 * len(seen) / len(DEMO_ARTWORKS), 1),
    }


@app.post("/v1/visits/{visit_id}/complete")
def complete_visit(visit_id: str):
    visit = VISITS.get(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="visit not found")
    visit["completed_at"] = datetime.now(timezone.utc).isoformat()
    return {"ok": True, "completed_at": visit["completed_at"]}


@app.get("/health")
def health():
    return {"status": "ok"}
