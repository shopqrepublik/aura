"""
AURA backend — FastAPI skeleton implementing the API contract from spec §12.

Recognition strategy (revised): instead of a DINOv2/CLIP + FAISS embedding
pipeline (§8.2's default), this uses vision-LLM matching against a closed
candidate list — which §8.2 step 5 already anticipated as "optional
multimodal verification". Promoting it to the primary method trades
per-scan latency/cost for a much smaller build (no reference-embedding
collection, no vector index to maintain). It still respects the spec's
core principle in §8.1: retrieval against a controlled set, not open
generation — the model can only return an artwork_id that exists in
CATALOG, never invent one.

Requires ANTHROPIC_API_KEY in the environment (or a .env file, see
.env.example). Falls back to the old random mock if the key is missing, so
the frontend keeps working without a key during UI development.

Run:
    pip install -r requirements.txt
    copy the repo-root .env.example to .env and fill in ANTHROPIC_API_KEY
    uvicorn app.main:app --reload --port 8090
"""
import base64
import json
import os
import random
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
    allow_origins=["*"],  # tighten before real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
RECOGNITION_MODEL = "claude-sonnet-5"


# ---- In-memory demo store (replace with Supabase/Postgres session) --------
VISITS: dict = {}

DEMO_ARTWORKS = [
    {"id": "orsay_rf_1995_10", "artist": "Gustave Courbet", "title": "L'Origine du monde", "year": "1866", "hall": None, "inventory_number": "RF 1995 10", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Origin-of-the-World.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1668", "artist": "Édouard Manet", "title": "Luncheon on the Grass", "year": "1863", "hall": None, "inventory_number": "RF 1668", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Luncheon%20on%20the%20Grass%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2739", "artist": "Pierre-Auguste Renoir", "title": "Bal du moulin de la Galette", "year": "1876", "hall": None, "inventory_number": "RF 2739", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Renoir%2C%20Pierre-Auguste%20-%20Dance%20at%20Le%20Moulin%20de%20la%20Galette%2C%201876.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_644", "artist": "Édouard Manet", "title": "Olympia", "year": "1863", "hall": None, "inventory_number": "RF 644", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Olympia%20-%20Google%20Art%20Project%203.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1975_19", "artist": "Vincent van Gogh", "title": "Starry Night Over the Rhone", "year": "1888", "hall": None, "inventory_number": "RF 1975 19", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20Starry%20Night%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1951_42", "artist": "Vincent van Gogh", "title": "The Church at Auvers", "year": "1890", "hall": None, "inventory_number": "RF 1951 42", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20Church%20in%20Auvers-sur-Oise%2C%20View%20from%20the%20Chevet%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_325", "artist": "Gustave Courbet", "title": "A Burial at Ornans", "year": "1849-1850", "hall": None, "inventory_number": "RF 325", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Courbet%20-%20A%20Burial%20at%20Ornans%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_253", "artist": "William-Adolphe Bouguereau", "title": "The Birth of Venus", "year": "1879", "hall": None, "inventory_number": "RF 253", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20%281825-1905%29%20-%20The%20Birth%20of%20Venus%20%281879%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_699", "artist": "James McNeill Whistler", "title": "Whistler's Mother", "year": "1871", "hall": None, "inventory_number": "RF 699", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Whistlers%20Mother%20high%20res.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2257", "artist": "Gustave Courbet", "title": "The Painter's Studio", "year": "1854-1855", "hall": None, "inventory_number": "RF 2257", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Courbet%20LAtelier%20du%20peintre.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1984", "artist": "Edgar Degas", "title": "L'Absinthe", "year": "1875", "hall": None, "inventory_number": "RF 1984", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20In%20a%20Caf%C3%A9%20-%20Google%20Art%20Project%202.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_219", "artist": "Jean-Auguste-Dominique Ingres", "title": "The Source", "year": "1856", "hall": None, "inventory_number": "RF 219", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean%20Auguste%20Dominique%20Ingres%20-%20The%20Spring%20-%20Google%20Art%20Project%202.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2772", "artist": "Édouard Manet", "title": "The Balcony", "year": "1868", "hall": None, "inventory_number": "RF 2772", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20The%20Balcony%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_592", "artist": "Jean-François Millet", "title": "The Gleaners", "year": "1857", "hall": None, "inventory_number": "RF 592", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-Fran%C3%A7ois%20Millet%20-%20Gleaners%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2738", "artist": "Pierre-Auguste Renoir", "title": "La Balançoire", "year": "1876", "hall": None, "inventory_number": "RF 2738", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Swing-Renoir.jpeg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2010_8", "artist": "William-Adolphe Bouguereau", "title": "Dante and Virgil in Hell", "year": "1850", "hall": None, "inventory_number": "RF 2010 8", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William%20Bouguereau%20-%20Dante%20and%20Virgile%20-%20Google%20Art%20Project%202.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_755", "artist": "Pierre-Auguste Renoir", "title": "Girls at the Piano", "year": "1892", "hall": None, "inventory_number": "RF 755", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Auguste%20Renoir%20-%20Young%20Girls%20at%20the%20Piano%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2765", "artist": "Paul Gauguin", "title": "Tahitian Women on the Beach", "year": "1890", "hall": None, "inventory_number": "RF 2765", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20056.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2773", "artist": "Claude Monet", "title": "Women in the Garden", "year": "1866", "hall": None, "inventory_number": "RF 2773", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20024.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_273", "artist": "Alexandre Cabanel", "title": "The Birth of Venus", "year": "1863", "hall": None, "inventory_number": "RF 273", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Alexandre%20Cabanel%20-%20The%20Birth%20of%20Venus%20-%20Google%20Art%20Project%202.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1949_17", "artist": "Vincent van Gogh", "title": "Self-portrait", "year": "1889", "hall": None, "inventory_number": "RF 1949 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20Self-Portrait%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1992", "artist": "Édouard Manet", "title": "The Fifer", "year": "1866", "hall": None, "inventory_number": "RF 1992", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Manet%2C%20Edouard%20-%20Young%20Flautist%2C%20or%20The%20Fifer%2C%201866%20%282%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_051804048", "artist": "Jean-François Millet", "title": "The Angelus", "year": "1858", "hall": None, "inventory_number": "RF 051804048", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/JEAN-FRAN%C3%87OIS%20MILLET%20-%20El%20%C3%81ngelus%20%28Museo%20de%20Orsay%2C%201857-1859.%20%C3%93leo%20sobre%20lienzo%2C%2055.5%20x%2066%20cm%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2210", "artist": "Edgar Degas", "title": "The Bellelli Family", "year": "1858", "hall": None, "inventory_number": "RF 2210", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20The%20Bellelli%20Family%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1984_164", "artist": "Claude Monet", "title": "The Magpie", "year": "1868", "hall": None, "inventory_number": "RF 1984 164", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Magpie%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2718", "artist": "Gustave Caillebotte", "title": "Les raboteurs de parquet", "year": "1875", "hall": None, "inventory_number": "RF 2718", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Caillebotte%20-%20The%20Floor%20Planers%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2511", "artist": "Georges Seurat", "title": "The Circus", "year": "1891", "hall": None, "inventory_number": "RF 2511", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Georges%20Seurat%20-%20The%20Circus%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1978_13", "artist": "Pierre-Auguste Renoir", "title": "Dance in the City", "year": "1883", "hall": None, "inventory_number": "RF 1978 13", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20019.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1979_64", "artist": "Pierre-Auguste Renoir", "title": "Dance in the Country", "year": "1883", "hall": None, "inventory_number": "RF 1979 64", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre%20Auguste%20Renoir%20-%20Country%20Dance%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1998_30", "artist": "Édouard Manet", "title": "Berthe Morisot with a Bouquet of Violets", "year": "1872", "hall": None, "inventory_number": "RF 1998 30", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Berthe%20Morisot%20With%20a%20Bouquet%20of%20Violets%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1957_7", "artist": "Claude Monet", "title": "Le Déjeuner sur l'herbe", "year": "1865", "hall": None, "inventory_number": "RF 1957 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Le%20dejeurner%20sur%20l%27herbe%20%28left%20panel%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2205", "artist": "Édouard Manet", "title": "Portrait of Emile Zola", "year": "1868", "hall": None, "inventory_number": "RF 2205", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20049.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_338", "artist": "Gustave Courbet", "title": "The Wounded Man", "year": "1844", "hall": None, "inventory_number": "RF 338", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Portrait%20of%20the%20Artist%20called%20The%20Wounded%20Man%20%28L%27homme%20bless%C3%A9%29%20by%20Gustave%20Courbet.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_64", "artist": "Rosa Bonheur", "title": "Ploughing in the Nivernais", "year": "1849", "hall": None, "inventory_number": "RF 64", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Rosa%20Bonheur%20-%20Ploughing%20in%20Nevers%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_88", "artist": "Jean-Léon Gérôme", "title": "Young Greeks Attending a Cock Fight", "year": "1846", "hall": None, "inventory_number": "RF 88", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-L%C3%A9on%20G%C3%A9r%C3%B4me%20-%20Young%20Greeks%20Attending%20a%20Cock%20Fight%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2450", "artist": "Frédéric Bazille", "title": "The Pink Dress", "year": "1864", "hall": None, "inventory_number": "RF 2450", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Fr%C3%A9d%C3%A9ric%20Bazille%20-%20The%20Pink%20Dress%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2778", "artist": "Claude Monet", "title": "Régates à Argenteuil", "year": "1872", "hall": None, "inventory_number": "RF 2778", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Regattas%20at%20Argenteuil%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1983_6", "artist": "Claude Monet", "title": "The artist's garden at Giverny", "year": "1900", "hall": None, "inventory_number": "RF 1983 6", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Monet%20-%20Monets%20Garten%20in%20Giverny.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1976", "artist": "Edgar Degas", "title": "The Ballet Class", "year": "1871", "hall": None, "inventory_number": "RF 1976", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20The%20Ballet%20Class%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1990_7", "artist": "Jean-Léon Gérôme", "title": "Jerusalem", "year": "1867", "hall": None, "inventory_number": "RF 1990 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Jean-L%C3%A9on%20G%C3%A9r%C3%B4me%20Consummatum%20est.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_lux_1439", "artist": "Frédéric Bazille", "title": "Bazille's Studio", "year": "1870", "hall": None, "inventory_number": "LUX 1439", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Fr%C3%A9d%C3%A9ric%20Bazille%20-%20Bazille%27s%20Studio%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_876", "artist": "Gustave Caillebotte", "title": "Vue de toits", "year": "1878", "hall": None, "inventory_number": "RF 876", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Gustave%20Caillebotte%20-%20Rooftops%20in%20the%20Snow%20%28snow%20effect%29%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1981_33", "artist": "William-Adolphe Bouguereau", "title": "The Dance", "year": "1856", "hall": None, "inventory_number": "RF 1981 33", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20%281825-1905%29%20-%20The%20Dance%20%281856%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1937_7", "artist": "Henri Rousseau", "title": "The Snake Charmer", "year": "1907", "hall": None, "inventory_number": "RF 1937 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/HENRI%20ROUSSEAU%20-%20La%20Encantadora%20de%20Serpientes%20%28Museo%20de%20Orsay%2C%20Par%C3%ADs%2C%201907.%20%C3%93leo%20sobre%20lienzo%2C%20169%20x%20189.5%20cm%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1952_17", "artist": "Vincent van Gogh", "title": "The siesta (after Millet)", "year": "1890", "hall": None, "inventory_number": "RF 1952 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20siesta%20%28after%20Millet%29%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1961_6", "artist": "Paul Gauguin", "title": "Arearea", "year": "1892", "hall": None, "inventory_number": "RF 1961 6", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20Arearea%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2749", "artist": "Frédéric Bazille", "title": "Réunion de famille", "year": "1867", "hall": None, "inventory_number": "RF 2749", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/R%C3%A9union%20de%20famille%20-%20Fr%C3%A9d%C3%A9ric%20Bazille%20-%20mus%C3%A9e%20d%27Orsay%20RF%202749.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1944_17", "artist": "Édouard Manet", "title": "The Reading", "year": "1865", "hall": None, "inventory_number": "RF 1944 17", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20005.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2849", "artist": "Berthe Morisot", "title": "The Cradle", "year": "1872", "hall": None, "inventory_number": "RF 2849", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Berthe%20Morisot%20-%20The%20Cradle%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2795", "artist": "Pierre-Auguste Renoir", "title": "The Bathers", "year": "1918", "hall": None, "inventory_number": "RF 2795", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre%20Auguste%20Renoir%20-%20The%20Bathers%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_729", "artist": "Henri Fantin-Latour", "title": "A Studio at Les Batignolles", "year": "1870", "hall": None, "inventory_number": "RF 729", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Henri%20Fantin-Latour%20-%20A%20Studio%20at%20Les%20Batignolles%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1970", "artist": "Paul Cézanne", "title": "La Maison du pendu, Auvers-sur-Oise", "year": "1874", "hall": None, "inventory_number": "RF 1970", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/La%20Maison%20du%20pendu%2C%20Auvers-sur-Oise%2C%20par%20Paul%20C%C3%A9zanne%2C%20FWN%2081.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_d2006_3_5", "artist": "Pierre-Auguste Renoir", "title": "Portrait of Frédéric Bazille Painting", "year": "1867", "hall": None, "inventory_number": "D2006.3.5", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20-%20Fr%C3%A9d%C3%A9ric%20Bazille.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1676", "artist": "Claude Monet", "title": "The Poppy Field near Argenteuil", "year": "1873", "hall": None, "inventory_number": "RF 1676", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Poppy%20Field%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2617", "artist": "Paul Gauguin", "title": "La belle Angèle", "year": "1889", "hall": None, "inventory_number": "RF 2617", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20La%20Belle%20Ang%C3%A8le%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1959_18", "artist": "Édouard Manet", "title": "L'Asperge", "year": "1880", "hall": None, "inventory_number": "RF 1959 18", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20Asparagus%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1991", "artist": "Édouard Manet", "title": "Lola de Valence", "year": "1862", "hall": None, "inventory_number": "RF 1991", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Lola%20de%20Valence%20%281862%29%20-%20Edouard%20Manet%20%28Mus%C3%A9e%20d%27Orsay%2C%20Paris%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1977_12", "artist": "Édouard Manet", "title": "Portrait of Monsieur and Madame Auguste Manet", "year": "1860", "hall": None, "inventory_number": "RF 1977 12", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Portrait%20of%20M.%20and%20Mme.%20Auguste%20Manet%20%281860%29%20-%20Edouard%20Manet%20%28Mus%C3%A9e%20d%27Orsay%2C%20Paris%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1965_14", "artist": "Vincent van Gogh", "title": "L'Italienne", "year": "1887", "hall": None, "inventory_number": "RF 1965 14", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Vincent%20van%20Gogh%20-%20The%20Italian%20Woman%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_4046", "artist": "Edgar Degas", "title": "The Tub", "year": "1886", "hall": None, "inventory_number": "RF 4046", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edgar%20Degas%20-%20Le%20Tub%20%281886%20Mus%C3%A9e%20d%27Orsay%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2010_7", "artist": "William-Adolphe Bouguereau", "title": "Equality Before Death", "year": "1848", "hall": None, "inventory_number": "RF 2010 7", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Bouguereau%20-%20%C3%A9galit%C3%A9%20devant%20la%20mort%201848.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_3666", "artist": "Pierre-Auguste Renoir", "title": "Claude Monet", "year": "1875", "hall": None, "inventory_number": "RF 3666", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Auguste%20Renoir%20-%20Claude%20Monet%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_do_1986_16", "artist": "Albert Edelfelt", "title": "Portrait of Louis Pasteur", "year": "1885", "hall": None, "inventory_number": "DO 1986 16", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Albert%20Edelfelt%20-%20Louis%20Pasteur%20-%201885.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1994_2", "artist": "Paul Gauguin", "title": "Portrait of the Artist with the Yellow Christ", "year": "1890", "hall": None, "inventory_number": "RF 1994 2", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Paul%20Gauguin%20-%20Portrait%20of%20the%20Artist%20with%20the%20Yellow%20Christ%20%281890-91%29.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2010_4", "artist": "William-Adolphe Bouguereau", "title": "The Oreads", "year": "1902", "hall": None, "inventory_number": "RF 2010 4", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/William-Adolphe%20Bouguereau%20-%20Les%20Or%C3%A9ades.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1994", "artist": "Édouard Manet", "title": "Suzanne Manet Playing the Piano", "year": "1867", "hall": None, "inventory_number": "RF 1994", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/%C3%89douard%20Manet%20-%20Madame%20Manet%20ou%20Piano.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
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
    {"id": "orsay_rf_2774", "artist": "Claude Monet", "title": "The Luncheon", "year": "1873", "hall": None, "inventory_number": "RF 2774", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Monet%20Luncheon.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2244", "artist": "Pierre-Auguste Renoir", "title": "Portrait of Madame Charpentier", "year": "1876", "hall": None, "inventory_number": "RF 2244", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20-%20Madame%20Charpentier%20-%2001.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
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
    {"id": "orsay_rf_1937_41", "artist": "Claude Monet", "title": "The Railway Bridge at Argenteuil", "year": "1874", "hall": None, "inventory_number": "RF 1937 41", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Le%20Pont%20d%27Argenteuil%20-%20Claude%20Monet.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2621", "artist": "Claude Monet", "title": "Woman with a Parasol, facing left", "year": "1886", "hall": None, "inventory_number": "RF 2621", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Femme%20%C3%A0%20l%27ombrelle%20tourn%C3%A9e%20vers%20la%20gauche%20-%20Claude%20Monnet%20-%20Mus%C3%A9e%20d%27Orsay%20RF%202621.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2661", "artist": "Édouard Manet", "title": "Portrait of Stéphane Mallarmé", "year": "1876", "hall": None, "inventory_number": "RF 2661", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Edouard%20Manet%20-%20St%C3%A9phane%20Mallarm%C3%A9%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_1963_3", "artist": "Claude Monet", "title": "Camille Monet on her deathbed", "year": "1879", "hall": None, "inventory_number": "RF 1963 3", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20Camille%20Monet%20sur%20son%20lit%20de%20mort.JPG", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_lux_367", "artist": "Camille Pissarro", "title": "The Red Roofs, Côte Saint-Denis at Pontoise, Winter Effect", "year": "1877", "hall": None, "inventory_number": "LUX 367", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Camille%20Pissarro%20011.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2020", "artist": "Alfred Sisley", "title": "Flooding at Port-Marly", "year": "1876", "hall": None, "inventory_number": "RF 2020", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/La%20inundaci%C3%B3n%20en%20Port%20Marly%2C%20por%20Alfred%20Sisley.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_8048", "artist": "Claude Monet", "title": "La Rue Montorgueil", "year": "1878", "hall": None, "inventory_number": "8048", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Claude%20Monet%20-%20The%20Rue%20Montorgueil%20in%20Paris.%20Celebration%20of%20June%2030%2C%201878%20-%20Google%20Art%20Project.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
    {"id": "orsay_rf_2787", "artist": "Alfred Sisley", "title": "The Regatta at Molesey", "year": "1874", "hall": None, "inventory_number": "RF 2787", "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Alfred%20Sisley%20050.jpg", "estimate_low": None, "estimate_high": None, "needs_editorial_review": True},
]

CONFIDENCE_AUTO = 0.92
CONFIDENCE_REVIEW = 0.82


def build_catalog_prompt(candidates: list) -> str:
    lines = [f'- id="{a["id"]}" | {a["artist"]} — "{a["title"]}" ({a["year"]}), Hall {a["hall"] or "unknown"}'
             for a in candidates]
    return "\n".join(lines)


def recognize_with_vision(image_base64: str, museum_id: str, hall_hint: Optional[str]) -> dict:
    """
    Retrieval against a CLOSED list (§8.1 principle): the model is only ever
    allowed to answer with an id that appears in the catalog below, or null.
    This is the key guardrail that keeps a vision-LLM approach from turning
    into open, hallucination-prone generation.
    """
    import anthropic  # imported lazily so the module still loads without the package during UI-only dev

    candidates = [a for a in DEMO_ARTWORKS]  # TODO: filter by museum_id/hall_hint once catalog is bigger
    catalog = build_catalog_prompt(candidates)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system_prompt = (
        "You identify which artwork from a CLOSED catalog is shown in a museum visitor's photo. "
        "You must answer ONLY with one of the ids in the catalog below, or null if none match — "
        "never invent an id or describe an artwork not in this list.\n\n"
        f"CATALOG (museum: {museum_id}, hall hint: {hall_hint or 'none'}):\n{catalog}\n\n"
        'Respond with ONLY compact JSON: {"artwork_id": "<id or null>", "confidence": <0-1 float>, '
        '"alternatives": ["<id>", ...]}. No prose, no markdown fences.'
    )

    resp = client.messages.create(
        model=RECOGNITION_MODEL,
        max_tokens=300,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64}},
                {"type": "text", "text": "Which catalog artwork is this?"}
            ]
        }]
    )
    raw = "".join(block.text for block in resp.content if block.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


# ---- Schemas ----------------------------------------------------------
class RecognizeRequest(BaseModel):
    image_base64: str
    museum_id: str
    hall_hint: Optional[str] = None
    locale: str = "en"


class RecognizeResponse(BaseModel):
    status: str  # "matched" | "needs_confirmation" | "no_match"
    artwork_id: Optional[str] = None
    confidence: float
    alternatives: List[str] = []


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

    if ANTHROPIC_API_KEY:
        try:
            result = recognize_with_vision(req.image_base64, req.museum_id, req.hall_hint)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"recognition failed: {e}")

        artwork_id = result.get("artwork_id")
        confidence = float(result.get("confidence", 0))
        alternatives = result.get("alternatives", [])

        if not artwork_id or artwork_id not in {a["id"] for a in DEMO_ARTWORKS}:
            return RecognizeResponse(status="no_match", confidence=confidence)
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
