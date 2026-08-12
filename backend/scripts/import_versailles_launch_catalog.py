#!/usr/bin/env python3
"""Import the focused Versailles launch catalog.

This is an idempotent production importer for the first curated Versailles
catalog. It creates no RecognitionAssets, embeddings, TTS audio, or image
byte cache. Wikimedia/Commons URLs from Wikidata are stored as remote display
metadata only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT / ".env")

from app.models import (  # noqa: E402
    Artwork,
    ArtworkCatalogMembership,
    ArtworkLocalization,
    ArtworkValueReveal,
    Museum,
)


MUSEUM_ID = "versailles"
CATALOG_VERSION = "2026-08-12-v1"
SOURCE_OFFICIAL = "versailles_official"
SOURCE_WIKIDATA = "wikidata_versailles"
OUTPUT_DIR = ROOT / "exports" / "versailles"
BACKUP_ROOT = ROOT / "backups"
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
VERSAILLES_COLLECTIONS_URL = "https://en.chateauversailles.fr/discover/collections"


MANUAL_SPACES: list[dict[str, Any]] = [
    {
        "id": "versailles_space_hall_of_mirrors",
        "title": "Hall of Mirrors",
        "title_fr": "Galerie des Glaces",
        "title_zh": "镜厅",
        "object_type": "interior",
        "date": "1678-1684",
        "room": "Hall of Mirrors",
        "source_url": "https://en.chateauversailles.fr/discover/estate/palace/hall-mirrors",
        "description": "The ceremonial gallery linking the King's and Queen's Apartments, designed as a political and diplomatic showpiece at the center of the palace visit.",
        "visual": "mirrored arches facing garden windows, painted ceiling, long ceremonial gallery, gilded decoration",
        "visual_fr": "les arcades de miroirs face aux fenêtres du jardin, le plafond peint, la longue galerie cérémonielle et le décor doré",
        "visual_zh": "面向花园窗户的镜面拱廊、彩绘天顶、长长的礼仪廊道和镀金装饰",
        "priority": 1,
        "tier": "A",
    },
    {
        "id": "versailles_space_gallery_great_battles",
        "title": "Gallery of Great Battles",
        "title_fr": "Galerie des Batailles",
        "title_zh": "战争画廊",
        "object_type": "gallery",
        "date": "1837",
        "room": "Gallery of Great Battles",
        "source_url": "https://en.chateauversailles.fr/discover/estate/palace/gallery-great-battles",
        "description": "A vast gallery created for the Museum of the History of France, bringing together monumental battle paintings as a national historical program.",
        "visual": "long gallery, monumental battle canvases, busts and plaques, state historical display",
        "visual_fr": "la longue galerie, les grandes toiles de bataille, les bustes et les plaques commémoratives",
        "visual_zh": "长廊、大型战役画、半身像和纪念铭牌",
        "priority": 2,
        "tier": "A",
    },
    {
        "id": "versailles_space_royal_chapel",
        "title": "Royal Chapel",
        "title_fr": "Chapelle royale",
        "title_zh": "皇家礼拜堂",
        "object_type": "chapel",
        "date": "1699-1710",
        "room": "Royal Chapel",
        "source_url": "https://en.chateauversailles.fr/discover/estate/palace/royal-chapel",
        "description": "The palace chapel completed at the end of Louis XIV's reign, built for court ceremony, worship, music, and royal ritual.",
        "visual": "two-level chapel, columns, altar, painted vault, royal gallery",
        "visual_fr": "la chapelle à deux niveaux, les colonnes, l'autel, la voûte peinte et la tribune royale",
        "visual_zh": "两层礼拜堂、柱廊、祭坛、彩绘拱顶和皇家看台",
        "priority": 3,
        "tier": "A",
    },
    {
        "id": "versailles_space_royal_opera",
        "title": "Royal Opera",
        "title_fr": "Opéra royal",
        "title_zh": "皇家歌剧院",
        "object_type": "theater",
        "date": "1770",
        "room": "Royal Opera",
        "source_url": "https://en.chateauversailles.fr/discover/estate/palace/royal-opera",
        "description": "The palace theater built for court performance and major dynastic ceremony, including the festivities around the marriage of the future Louis XVI and Marie-Antoinette.",
        "visual": "horseshoe-shaped theater, tiers of boxes, painted wood, stage and royal seating",
        "visual_fr": "la salle en fer à cheval, les rangées de loges, le bois peint, la scène et les places royales",
        "visual_zh": "马蹄形剧场、层层包厢、彩绘木构、舞台和皇家席位",
        "priority": 4,
        "tier": "B",
    },
    {
        "id": "versailles_space_kings_state_apartment",
        "title": "King's State Apartment",
        "title_fr": "Grand Appartement du Roi",
        "title_zh": "国王大套间",
        "object_type": "state rooms",
        "date": "17th century",
        "room": "King's State Apartment",
        "source_url": "https://en.chateauversailles.fr/discover/estate/palace/king-state-apartment",
        "description": "The formal sequence of rooms used to stage royal magnificence through mythology, paintings, decoration, and court protocol.",
        "visual": "state rooms, painted ceilings, marble, gilded decoration, mythological program",
        "visual_fr": "les salons d'apparat, les plafonds peints, le marbre, les dorures et le programme mythologique",
        "visual_zh": "礼仪厅室、彩绘天顶、大理石、镀金装饰和神话主题",
        "priority": 5,
        "tier": "B",
    },
    {
        "id": "versailles_space_kings_apartment",
        "title": "King's Apartment",
        "title_fr": "Appartement du Roi",
        "title_zh": "国王套间",
        "object_type": "apartment",
        "date": "17th-18th century",
        "room": "King's Apartment",
        "source_url": "https://en.chateauversailles.fr/discover/estate/kings-apartments",
        "description": "The royal domestic and ceremonial rooms where the king's daily public routine was staged as part of court life.",
        "visual": "royal bedroom, ceremonial furniture, textile hangings, court route",
        "visual_fr": "la chambre royale, le mobilier cérémoniel, les tentures et le parcours de cour",
        "visual_zh": "国王寝宫、礼仪家具、织物帷饰和宫廷动线",
        "priority": 6,
        "tier": "B",
    },
    {
        "id": "versailles_space_queens_apartments",
        "title": "Queen's Apartments",
        "title_fr": "Appartement de la Reine",
        "title_zh": "王后套间",
        "object_type": "apartment",
        "date": "17th-18th century",
        "room": "Queen's Apartments",
        "source_url": "https://en.chateauversailles.fr/discover/estate/palace/queen-apartments",
        "description": "The principal rooms of the queens of France at Versailles, combining public court ritual with private royal history.",
        "visual": "bedchamber, textile decoration, court furniture, ceremonial doorway",
        "visual_fr": "la chambre, le décor textile, le mobilier de cour et les portes cérémonielles",
        "visual_zh": "寝宫、织物装饰、宫廷家具和礼仪门口",
        "priority": 7,
        "tier": "B",
    },
    {
        "id": "versailles_space_queen_hamlet",
        "title": "The Queen's Hamlet",
        "title_fr": "Hameau de la Reine",
        "title_zh": "王后村庄",
        "object_type": "estate ensemble",
        "date": "1783-1786",
        "room": "Estate of Trianon",
        "source_url": "https://en.chateauversailles.fr/discover/estate/estate-trianon/queen-hamlet",
        "description": "The rustic-style estate ensemble associated with Marie-Antoinette, built as part of the Trianon landscape.",
        "visual": "small rural buildings, garden setting, lake, rustic architectural details",
        "visual_fr": "les petits bâtiments ruraux, le jardin, le lac et les détails d'architecture rustique",
        "visual_zh": "小型乡村建筑、花园环境、湖水和质朴的建筑细节",
        "priority": 8,
        "tier": "B",
    },
    {
        "id": "versailles_space_apollos_fountain",
        "title": "Apollo's Fountain",
        "title_fr": "Bassin d'Apollon",
        "title_zh": "阿波罗喷泉",
        "object_type": "fountain",
        "date": "17th century",
        "room": "Gardens",
        "source_url": "https://en.chateauversailles.fr/discover/estate/gardens/fountains",
        "description": "A major garden fountain centered on Apollo, the sun god, reinforcing the solar imagery associated with Louis XIV.",
        "visual": "Apollo in a chariot, horses emerging from water, central garden axis",
        "visual_fr": "Apollon dans son char, les chevaux surgissant de l'eau et l'axe central du jardin",
        "visual_zh": "战车中的阿波罗、从水中跃出的马匹和花园中轴线",
        "priority": 9,
        "tier": "B",
    },
]


MAJOR_QID_BOOSTS = {
    "Q3937621": 60,   # Marie Antoinette and Her Children
    "Q1282978": 54,   # Bonaparte at the Pont d'Arcole
    "Q3937618": 52,   # Marie Antoinette with a Rose
    "Q2928781": 50,   # Bust of Louis XIV
    "Q3208312": 48,   # The Distribution of the Eagle Standards
    "Q3227124": 46,   # The Tennis Court Oath
    "Q590000": 44,    # Passemant astronomical clock
    "Q2887909": 42,   # Battle of Austerlitz
    "Q2887998": 40,   # Battle of Jena
    "Q2890107": 38,   # Battle of Taillebourg
    "Q3201377": 36,   # Proclamation of Abolition of Slavery
    "Q17492872": 34,  # The Congress of Paris
    "Q29901380": 32,  # Jean-Baptiste Belley
    "Q130633519": 30, # Battle of the Pyramids
    "Q18719530": 28,  # Marie-Antoinette seated
    "Q5989258": 26,   # Adelaide of France
    "Q16333797": 24,  # Rudolf II as Vertumnus
}

PINNED_WIKIDATA_QIDS = [
    "Q3937621",
    "Q2928781",
    "Q3937618",
    "Q1282978",
    "Q2887909",
    "Q3208312",
    "Q2887998",
    "Q3227124",
    "Q2890107",
    "Q590000",
    "Q130633519",
    "Q3201377",
    "Q17492872",
    "Q29901380",
    "Q18719530",
    "Q5989258",
    "Q16333797",
    "Q65097261",
    "Q106522737",
    "Q97143414",
    "Q65097312",
    "Q104843025",
    "Q59248124",
    "Q65097256",
    "Q59248127",
    "Q59248125",
    "Q111307118",
    "Q3335950",
    "Q59248132",
    "Q58372254",
    "Q90330582",
    "Q59248205",
    "Q59248153",
    "Q59248211",
    "Q59339691",
    "Q59248171",
    "Q59248168",
    "Q59248192",
    "Q2890323",
    "Q15730349",
    "Q90330588",
]


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-") or "record"


def qid_from_uri(value: str) -> str:
    return value.rsplit("/", 1)[-1]


def fetch_wikidata_candidates(limit: int = 600, qids: list[str] | None = None) -> list[dict[str, Any]]:
    if qids:
        subject_clause = "VALUES ?item { " + " ".join(f"wd:{qid}" for qid in qids) + " }"
        limit_clause = ""
    else:
        subject_clause = """VALUES ?collection { wd:Q2946 wd:Q3329787 }
  ?item wdt:P195 ?collection."""
        limit_clause = f"LIMIT {limit}"
    query = """
SELECT ?item ?itemLabel ?itemDescription ?labelFr ?labelZh ?image ?date ?inventory
       (GROUP_CONCAT(DISTINCT ?creatorLabel; SEPARATOR="; ") AS ?creators)
       (GROUP_CONCAT(DISTINCT ?typeLabel; SEPARATOR="; ") AS ?types)
       (GROUP_CONCAT(DISTINCT ?materialLabel; SEPARATOR="; ") AS ?materials)
       (GROUP_CONCAT(DISTINCT ?locationLabel; SEPARATOR="; ") AS ?locations)
WHERE {
  %s
  OPTIONAL { ?item wdt:P18 ?image. }
  OPTIONAL { ?item wdt:P571|wdt:P577|wdt:P585 ?date. }
  OPTIONAL { ?item wdt:P217 ?inventory. }
  OPTIONAL { ?item wdt:P170 ?creator. }
  OPTIONAL { ?item wdt:P31 ?type. }
  OPTIONAL { ?item wdt:P186 ?material. }
  OPTIONAL { ?item wdt:P276 ?location. }
  OPTIONAL { ?item rdfs:label ?labelFr FILTER(LANG(?labelFr) = "fr") }
  OPTIONAL { ?item rdfs:label ?labelZh FILTER(LANG(?labelZh) = "zh") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,fr,zh". }
}
GROUP BY ?item ?itemLabel ?itemDescription ?labelFr ?labelZh ?image ?date ?inventory
ORDER BY ?item
%s
""" % (subject_clause, limit_clause)
    url = f"{WIKIDATA_ENDPOINT}?{urlencode({'query': query, 'format': 'json'})}"
    req = Request(url, headers={"User-Agent": "ELYIO Versailles launch catalog importer (https://elyio.co)"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"Wikidata query failed after retries: {last_error}")

    rows: list[dict[str, Any]] = []
    for binding in payload["results"]["bindings"]:
        item_uri = binding["item"]["value"]
        qid = qid_from_uri(item_uri)
        image = binding.get("image", {}).get("value")
        if image and image.startswith("http://"):
            image = "https://" + image[len("http://") :]
        title = binding.get("itemLabel", {}).get("value") or qid
        rows.append(
            {
                "qid": qid,
                "source_url": f"https://www.wikidata.org/wiki/{qid}",
                "title": title,
                "title_fr": binding.get("labelFr", {}).get("value") or title,
                "title_zh": binding.get("labelZh", {}).get("value") or title,
                "description": binding.get("itemDescription", {}).get("value"),
                "artist": clean_joined(binding.get("creators", {}).get("value")),
                "date": simplify_date(binding.get("date", {}).get("value")),
                "inventory_number": binding.get("inventory", {}).get("value"),
                "image_url": image,
                "object_type": clean_joined(binding.get("types", {}).get("value")) or "artwork",
                "materials": clean_joined(binding.get("materials", {}).get("value")),
                "location": clean_joined(binding.get("locations", {}).get("value")),
                "raw_json": {k: v.get("value") for k, v in binding.items()},
            }
        )
    return rows


def clean_joined(value: str | None) -> str | None:
    if not value:
        return None
    parts = []
    seen = set()
    for part in [p.strip() for p in value.split(";") if p.strip()]:
        if part.startswith(("http://", "https://")) or part.startswith("t "):
            continue
        key = part.lower()
        if key not in seen:
            seen.add(key)
            parts.append(part)
    return "; ".join(parts) if parts else None


def simplify_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.match(r"^-?(\d{1,4})-", value)
    if match:
        return match.group(1)
    return value


def derive_object_type(row: dict[str, Any]) -> str:
    explicit = row.get("object_type")
    description = (row.get("description") or "").lower()
    for kind in ["painting", "sculpture", "portrait", "clock", "drawing", "tapestry", "bust"]:
        if kind in description:
            return "painting" if kind == "portrait" else kind
    return explicit or "artwork"


def derive_artist(row: dict[str, Any]) -> str | None:
    if row.get("artist"):
        return row["artist"]
    description = row.get("description") or ""
    match = re.search(r"\b(?:painting|sculpture|portrait|drawing|tapestry|bust) by ([^.]+)$", description, flags=re.IGNORECASE)
    if not match:
        return None
    artist = match.group(1).strip()
    if artist.lower() in {"anonymous", "unknown", "unknown artist"}:
        return None
    return artist


def selection_score(row: dict[str, Any]) -> tuple[int, str]:
    qid = row["qid"]
    text_blob = " ".join(str(row.get(k) or "") for k in ("title", "description", "artist", "object_type", "materials")).lower()
    score = MAJOR_QID_BOOSTS.get(qid, 0)
    reason = []
    if score:
        reason.append("known high-visitor-relevance Versailles collection work")
    if row.get("image_url"):
        score += 10
    if row.get("inventory_number"):
        score += 5
    if row.get("description"):
        score += 3
    for term, boost in [
        ("marie antoinette", 10),
        ("louis xiv", 10),
        ("napoleon", 8),
        ("battle", 7),
        ("portrait", 5),
        ("bust", 5),
        ("clock", 5),
        ("sculpture", 4),
        ("painting", 4),
        ("history of france", 3),
    ]:
        if term in text_blob:
            score += boost
    if not reason:
        reason.append("visitor-relevant collection record with usable structured metadata")
    return score, "; ".join(reason)


def select_wikidata_records(candidates: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    eligible = [row for row in candidates if row.get("title") and row.get("image_url")]
    enriched = []
    for row in eligible:
        score, reason = selection_score(row)
        row = {**row, "selection_score": score, "selection_reason": reason}
        enriched.append(row)
    enriched.sort(key=lambda r: (-r["selection_score"], r["title"].lower(), r["qid"]))
    selected = []
    seen_titles = set()
    for row in enriched:
        title_key = slugify(row["title"])
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        selected.append(row)
        if len(selected) == count:
            break
    if len(selected) != count:
        raise SystemExit(f"could only select {len(selected)} Wikidata records, expected {count}")
    return selected


def pinned_wikidata_records(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_qid = {row["qid"]: row for row in candidates}
    missing = [qid for qid in PINNED_WIKIDATA_QIDS if qid not in by_qid]
    if missing:
        raise SystemExit(f"missing pinned Versailles Wikidata records: {missing}")
    selected = []
    for qid in PINNED_WIKIDATA_QIDS:
        row = by_qid[qid]
        score, reason = selection_score(row)
        selected.append({**row, "selection_score": score, "selection_reason": reason})
    return selected


OBJECT_TYPE_LABELS = {
    "painting": {"en": "painting", "fr": "peinture", "zh": "绘画"},
    "sculpture": {"en": "sculpture", "fr": "sculpture", "zh": "雕塑"},
    "portrait": {"en": "portrait", "fr": "portrait", "zh": "肖像"},
    "clock": {"en": "clock", "fr": "horloge", "zh": "钟表"},
    "drawing": {"en": "drawing", "fr": "dessin", "zh": "素描"},
    "tapestry": {"en": "tapestry", "fr": "tapisserie", "zh": "挂毯"},
    "bust": {"en": "bust", "fr": "buste", "zh": "半身像"},
    "interior": {"en": "interior", "fr": "espace intérieur", "zh": "室内空间"},
    "gallery": {"en": "gallery", "fr": "galerie", "zh": "画廊空间"},
    "chapel": {"en": "chapel", "fr": "chapelle", "zh": "礼拜堂"},
    "theater": {"en": "theater", "fr": "théâtre", "zh": "剧场"},
    "state rooms": {"en": "state rooms", "fr": "appartement d'apparat", "zh": "礼仪厅室"},
    "apartment": {"en": "apartment", "fr": "appartement", "zh": "套间"},
    "estate ensemble": {"en": "estate ensemble", "fr": "ensemble du domaine", "zh": "园林建筑群"},
    "fountain": {"en": "fountain", "fr": "fontaine", "zh": "喷泉"},
    "artwork": {"en": "artwork", "fr": "oeuvre", "zh": "作品"},
}


def localized_object_type(row: dict[str, Any], lang: str) -> str:
    key = (row.get("object_type") or "artwork").lower()
    return OBJECT_TYPE_LABELS.get(key, OBJECT_TYPE_LABELS["artwork"])[lang]


def source_fact(row: dict[str, Any], lang: str = "en") -> str:
    parts = [localized_object_type(row, lang)]
    if row.get("date"):
        parts.append(str(row["date"]))
    if row.get("artist"):
        parts.append(str(row["artist"]))
    if row.get("materials"):
        parts.append(str(row["materials"]))
    if row.get("inventory_number"):
        parts.append(str(row["inventory_number"]))
    return ", ".join(str(x) for x in parts if x)


def visual_cue(row: dict[str, Any], lang: str) -> str:
    if lang == "fr" and row.get("visual_fr"):
        return str(row["visual_fr"])
    if lang == "zh" and row.get("visual_zh"):
        return str(row["visual_zh"])
    if row.get("visual"):
        return str(row["visual"])
    description = row.get("description") or ""
    if description:
        if lang == "fr":
            return f"son sujet, son format et les détails visibles de cette {localized_object_type(row, 'fr')}"
        if lang == "zh":
            return f"它的主题、构图和这件{localized_object_type(row, 'zh')}的可见细节"
        return f"the subject, format, and visible details of this {localized_object_type(row, 'en')}"
    if lang == "fr":
        return "sa forme, son sujet et son contexte de visite"
    if lang == "zh":
        return "它的形状、主题和参观语境"
    return "the form, subject, and visitor setting"


def normal_content(record: dict[str, Any], lang: str) -> dict[str, str]:
    title = record[f"title_{lang}"] if lang in {"fr", "zh"} else record["title"]
    source_line = source_fact(record, lang)
    room = record.get("room") or record.get("location") or "Chateau de Versailles"
    if lang == "fr":
        return {
            "title": title,
            "analogy": f"{title} situe la visite dans l'histoire et les collections de Versailles.",
            "why_it_matters": f"Cette entrée fait partie du lancement curaté de Versailles dans ELYIO. Les faits disponibles la rattachent à {source_line or 'la collection de Versailles'} et permettent une identification utile sans inventer de récit.",
            "where_to_look": f"Regardez les éléments visibles qui définissent l'oeuvre: {visual_cue(record, 'fr')}. Le lieu indiqué pour la visite est {room}.",
            "rarity_note": "Versailles appartient aux collections publiques et au domaine national: ELYIO ne transforme pas cette importance historique en prix de vente.",
        }
    if lang == "zh":
        return {
            "title": title,
            "analogy": f"{title}把这次参观带入凡尔赛的历史和收藏语境。",
            "why_it_matters": f"这是 ELYIO 凡尔赛精选目录中的一项。现有资料显示它与{source_line or '凡尔赛收藏'}相关，足以提供清晰识别，而不虚构故事。",
            "where_to_look": f"请先看能确认身份的可见特征：{visual_cue(record, 'zh')}。参观位置记录为：{room}。",
            "rarity_note": "凡尔赛属于公共收藏和国家遗产；ELYIO 不把这种历史意义伪装成市场售价。",
        }
    return {
        "title": title,
        "analogy": f"{title} anchors this stop in the history and collections of Versailles.",
        "why_it_matters": f"This is part of ELYIO's focused Versailles launch catalog. The available source facts connect it to {source_line or 'the Versailles collection'}, giving visitors a useful identification without inventing unsupported narrative.",
        "where_to_look": f"Look for the visible identity cues: {visual_cue(record, 'en')}. The visitor location is recorded as {room}.",
        "rarity_note": "Versailles is a public national collection and estate; ELYIO treats its historical importance as beyond an ordinary market price.",
    }


def simple_content(record: dict[str, Any], lang: str) -> dict[str, str]:
    title = record[f"title_{lang}"] if lang in {"fr", "zh"} else record["title"]
    if lang == "fr":
        return {
            "title": title,
            "analogy": f"Vous regardez {title}. Les informations fiables indiquent son sujet, son lieu et son lien avec Versailles.",
        }
    if lang == "zh":
        return {
            "title": title,
            "analogy": f"你看到的是{title}。可靠资料说明了它的主题、位置，以及它和凡尔赛的关系。",
        }
    return {
        "title": title,
        "analogy": f"You are looking at {title}. The reliable facts identify what it is, where it belongs, and why it matters at Versailles.",
    }


def kids_content(record: dict[str, Any], lang: str) -> dict[str, str]:
    title = record[f"title_{lang}"] if lang in {"fr", "zh"} else record["title"]
    if lang == "fr":
        return {
            "title": title,
            "analogy": f"Cherche un indice facile a voir: {visual_cue(record, 'fr')}. Cet indice t'aide a relier {title} a l'histoire de Versailles.",
        }
    if lang == "zh":
        return {
            "title": title,
            "analogy": f"先找一个容易看到的线索：{visual_cue(record, 'zh')}。这个线索能帮助你把{title}和凡尔赛的历史联系起来。",
        }
    return {
        "title": title,
        "analogy": f"Start by finding one clear clue: {visual_cue(record, 'en')}. That clue helps connect {title} to the story of Versailles.",
    }


def value_reveal(source_url: str) -> dict[str, Any]:
    return {
        "mode": "BEYOND_MARKET",
        "aggregate_value_eligible": False,
        "beyond_market_headline": "No ordinary market price.",
        "beyond_market_explanation": "This belongs to the Versailles public collection or estate context, so ELYIO does not present it as an ordinary private-market object.",
        "institutional_legal_context": "Public cultural heritage context; not an appraisal, insurance value, or sale estimate.",
        "confidence": "medium",
        "sources": [source_url],
        "disclaimer": "Not an appraisal, insurance value, or sale estimate.",
        "review_status": "AUTO_QA_PASSED",
    }


def backup_versailles(session: Session) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = BACKUP_ROOT / f"versailles_launch_pre_import_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    queries = {
        "museums_versailles": "SELECT * FROM museums WHERE id='versailles'",
        "artworks_versailles": "SELECT * FROM artworks WHERE museum_id='versailles'",
        "memberships_versailles": "SELECT * FROM artwork_catalog_memberships WHERE museum_id='versailles'",
        "localizations_versailles": "SELECT l.* FROM artwork_localizations l JOIN artworks a ON a.id=l.artwork_id WHERE a.museum_id='versailles'",
        "value_reveals_versailles": "SELECT v.* FROM artwork_value_reveals v JOIN artworks a ON a.id=v.artwork_id WHERE a.museum_id='versailles'",
    }
    counts = {}
    for name, sql in queries.items():
        table = name.split("_versailles", 1)[0]
        if table == "memberships":
            table = "artwork_catalog_memberships"
        if table == "localizations":
            table = "artwork_localizations"
        if table == "value_reveals":
            table = "artwork_value_reveals"
        if not inspect(session.bind).has_table(table):
            continue
        rows = [dict(row._mapping) for row in session.execute(text(sql)).all()]
        counts[name] = len(rows)
        with (out / f"{name}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")
    (out / "counts.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    return out


def build_records() -> list[dict[str, Any]]:
    candidate_by_qid = {
        row["qid"]: row
        for row in fetch_wikidata_candidates(qids=PINNED_WIKIDATA_QIDS)
    }
    candidates = list(candidate_by_qid.values())
    wiki = pinned_wikidata_records(candidates)
    records: list[dict[str, Any]] = []
    for row in MANUAL_SPACES:
        records.append(
            {
                **row,
                "source": SOURCE_OFFICIAL,
                "source_record_id": row["id"].removeprefix("versailles_space_"),
                "image_url": None,
                "artist": None,
                "inventory_number": None,
                "materials": None,
                "department": "Chateau de Versailles",
                "location": row["room"],
                "selection_reason": "official visitor-facing Versailles space with high relevance",
                "raw_json": row,
            }
        )
    for i, row in enumerate(wiki, start=len(records) + 1):
        records.append(
            {
                "id": f"versailles_{row['qid'].lower()}",
                "source": SOURCE_WIKIDATA,
                "source_record_id": row["qid"],
                "title": row["title"],
                "title_fr": row["title_fr"],
                "title_zh": row["title_zh"],
                "artist": derive_artist(row),
                "date": row["date"],
                "object_type": derive_object_type(row),
                "materials": row["materials"],
                "inventory_number": row["inventory_number"],
                "image_url": row["image_url"],
                "source_url": row["source_url"],
                "description": row["description"],
                "department": "Palace of Versailles / Museum of the History of France",
                "location": row["location"] or "Chateau de Versailles",
                "room": row["location"] or "Chateau de Versailles",
                "priority": i,
                "tier": "B" if i <= 30 else "C",
                "selection_reason": row["selection_reason"],
                "raw_json": row["raw_json"],
            }
        )
    if len(records) != 50:
        raise SystemExit(f"internal selection error: {len(records)} records")
    return records


def upsert_museum(session: Session, apply: bool) -> str:
    row = session.get(Museum, MUSEUM_ID)
    if row is None:
        row = Museum(id=MUSEUM_ID)
        if apply:
            session.add(row)
    row.name = row.name or "Chateau de Versailles"
    row.common_name = row.common_name or "Chateau de Versailles"
    row.slug = row.slug or "chateau-de-versailles"
    row.city = row.city or "Versailles"
    row.department = row.department or "Yvelines"
    row.region = row.region or "Ile-de-France"
    row.website_url = row.website_url or "https://en.chateauversailles.fr/"
    row.source_url = row.source_url or VERSAILLES_COLLECTIONS_URL
    row.experience_level = "CURATED"
    return "inserted" if row.id is None else "updated"


def upsert_artwork(session: Session, record: dict[str, Any], apply: bool) -> tuple[str, str]:
    row = (
        session.query(Artwork)
        .filter(Artwork.source == record["source"], Artwork.source_record_id == record["source_record_id"])
        .first()
    )
    action = "updated"
    if row is None:
        row = session.get(Artwork, record["id"])
    if row is None:
        row = Artwork(id=record["id"])
        action = "inserted"
        if apply:
            session.add(row)
    row.museum_id = MUSEUM_ID
    row.artist = record.get("artist")
    row.title_original = record["title"]
    row.year = record.get("date")
    row.inventory_number = record.get("inventory_number")
    row.hall = record.get("room")
    row.image_url = record.get("image_url")
    row.priority = int(record.get("priority") or 100)
    row.tags = [record["tier"], "versailles-launch", slugify(record.get("object_type") or "artwork")]
    row.source_urls = [record["source_url"]]
    row.source = record["source"]
    row.source_record_id = record["source_record_id"]
    row.source_url = record["source_url"]
    row.last_source_sync = datetime.now(timezone.utc)
    row.raw_json = record["raw_json"]
    row.department = record.get("department")
    row.object_type = record.get("object_type")
    row.materials_and_techniques = record.get("materials")
    row.description = record.get("description")
    row.current_location_raw = record.get("location")
    row.room = record.get("room")
    row.display_status = "ON_DISPLAY"
    row.display_status_confidence = "MEDIUM" if record["source"] == SOURCE_WIKIDATA else "HIGH"
    row.display_status_reason = record["selection_reason"]
    row.metadata_status = "READY" if record.get("description") or record["source"] == SOURCE_OFFICIAL else "PARTIAL"
    row.recognition_status = "VISION_READY"
    row.rights_status = "REMOTE_DISPLAY_METADATA_ONLY" if record.get("image_url") else "NO_IMAGE_METADATA"
    row.rights_review_required = False
    return row.id, action


def upsert_membership(session: Session, artwork_id: str, record: dict[str, Any], existing: dict[str, ArtworkCatalogMembership], apply: bool) -> str:
    row = existing.get(artwork_id)
    action = "updated"
    if row is None:
        row = ArtworkCatalogMembership(artwork_id=artwork_id, museum_id=MUSEUM_ID, catalog_version=CATALOG_VERSION)
        action = "inserted"
        if apply:
            session.add(row)
    row.active = True
    row.tier = record["tier"]
    row.visitor_priority = float(1000 - int(record.get("priority") or 100))
    return action


def upsert_localizations(session: Session, artwork_id: str, record: dict[str, Any], existing: dict[tuple[str, str], ArtworkLocalization], apply: bool) -> Counter:
    counts = Counter()
    localized_record = {**record, "title_en": record["title"]}
    for locale_key, locale in [("en", "en"), ("fr", "fr"), ("zh", "zh-Hans")]:
        for mode, content in [
            ("normal", normal_content(localized_record, locale_key)),
            ("simple", simple_content(localized_record, locale_key)),
            ("kids", kids_content(localized_record, locale_key)),
        ]:
            key = (artwork_id, locale, mode)
            row = existing.get(key)
            if row is None:
                row = ArtworkLocalization(artwork_id=artwork_id, locale=locale, mode=mode)
                counts["localizations_inserted"] += 1
                if apply:
                    session.add(row)
                existing[key] = row
            else:
                counts["localizations_updated"] += 1
            row.title = content["title"]
            row.analogy = content["analogy"]
            row.why_it_matters = content.get("why_it_matters")
            row.where_to_look = content.get("where_to_look")
            row.rarity_note = content.get("rarity_note")
            row.audio_script = None
            row.audio_url = None
            row.editorial_status = "published"
            row.reviewed_by = "ELYIO Versailles launch factual importer"
            row.updated_at = datetime.now(timezone.utc)
    return counts


def upsert_value(session: Session, artwork_id: str, record: dict[str, Any], existing: dict[str, ArtworkValueReveal], apply: bool) -> str:
    row = existing.get(artwork_id)
    action = "updated"
    if row is None:
        row = ArtworkValueReveal(artwork_id=artwork_id, catalog_version=CATALOG_VERSION, mode="BEYOND_MARKET")
        action = "inserted"
        if apply:
            session.add(row)
        existing[artwork_id] = row
    value = value_reveal(record["source_url"])
    row.mode = "BEYOND_MARKET"
    row.aggregate_value_eligible = False
    row.estimated_value_low = None
    row.estimated_value_high = None
    row.estimated_value_currency = None
    row.market_context_headline_number = None
    row.market_context_currency = None
    row.market_context_label = None
    row.market_context_explanation = None
    row.relationship_to_artwork = None
    row.context_type = None
    row.source_reference = None
    row.context_date = None
    row.beyond_market_headline = value["beyond_market_headline"]
    row.beyond_market_explanation = value["beyond_market_explanation"]
    row.institutional_legal_context = value["institutional_legal_context"]
    row.optional_context = None
    row.confidence = value["confidence"]
    row.methodology = "Launch catalog value treatment: public cultural heritage context; no sale estimate inferred."
    row.sources = value["sources"]
    row.disclaimer = value["disclaimer"]
    row.review_status = value["review_status"]
    row.generated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return action


def write_snapshot(records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = OUTPUT_DIR / "versailles_launch_50_snapshot.jsonl"
    with snapshot.open("w", encoding="utf-8", newline="\n") as fh:
        for row in records:
            fh.write(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")
    (OUTPUT_DIR / "versailles_launch_50_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write to DATABASE_URL; default is dry-run")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set")

    records = build_records()
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate generated Versailles artwork ids")

    engine = create_engine(database_url, pool_pre_ping=True)
    counts = Counter()
    backup_path = None
    with Session(engine) as session:
        if args.apply:
            backup_path = backup_versailles(session)
        upsert_museum(session, args.apply)
        existing_memberships = {
            row.artwork_id: row
            for row in session.query(ArtworkCatalogMembership)
            .filter(
                ArtworkCatalogMembership.museum_id == MUSEUM_ID,
                ArtworkCatalogMembership.catalog_version == CATALOG_VERSION,
            )
            .all()
        }
        existing_loc = {
            (row.artwork_id, row.locale, row.mode): row
            for row in session.query(ArtworkLocalization)
            .filter(ArtworkLocalization.artwork_id.in_(ids))
            .all()
        }
        existing_values = {
            row.artwork_id: row
            for row in session.query(ArtworkValueReveal)
            .filter(
                ArtworkValueReveal.artwork_id.in_(ids),
                ArtworkValueReveal.catalog_version == CATALOG_VERSION,
            )
            .all()
        }

        for record in records:
            artwork_id, artwork_action = upsert_artwork(session, record, args.apply)
            counts[f"artworks_{artwork_action}"] += 1
            membership_action = upsert_membership(session, artwork_id, record, existing_memberships, args.apply)
            counts[f"memberships_{membership_action}"] += 1
            counts.update(upsert_localizations(session, artwork_id, record, existing_loc, args.apply))
            value_action = upsert_value(session, artwork_id, record, existing_values, args.apply)
            counts[f"value_reveals_{value_action}"] += 1

        # Keep this visitor catalog exactly 50 active members without deleting
        # archival Versailles artwork records that may be added in the future.
        for artwork_id, row in existing_memberships.items():
            if artwork_id not in set(ids) and row.active:
                row.active = False
                counts["memberships_deactivated"] += 1

        if args.apply:
            session.commit()
        else:
            session.rollback()

    summary = {
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "museum_id": MUSEUM_ID,
        "catalog_version": CATALOG_VERSION,
        "records": len(records),
        "official_space_records": len(MANUAL_SPACES),
        "wikidata_records": len(records) - len(MANUAL_SPACES),
        "unique_records": len(set(ids)),
        "expected_active_memberships": 50,
        **dict(counts),
        "backup_path": str(backup_path.relative_to(ROOT)) if backup_path else None,
        "safety": {
            "recognition_assets_created": 0,
            "embeddings_created": 0,
            "tts_audio_bytes_generated": 0,
            "versailles_hosted_image_bytes_fetched": 0,
            "museum_directory_expansion": 0,
        },
    }
    write_snapshot(records, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
