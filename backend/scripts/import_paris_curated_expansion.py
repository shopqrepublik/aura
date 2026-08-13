#!/usr/bin/env python3
"""Import the Paris curated expansion.

Scope:
- Backfill curated Orsay/Orangerie content from the legacy approved runtime
  catalog.
- Create focused launch catalogs for Rodin, Picasso Paris, and Quai Branly
  from pinned Wikidata collection records.

This script is idempotent and additive. It does not create RecognitionAssets,
embeddings, TTS audio, or fetch museum-hosted image bytes.
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
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
    ArtworkEstimate,
    ArtworkLocalization,
    ArtworkValueReveal,
    Museum,
)


CATALOG_VERSION = "2026-08-13-v1"
LEGACY_CATALOG_VERSION = "legacy-orsay-orangerie-curated-2026-08-13"
OUTPUT_DIR = ROOT / "exports" / "paris_curated_expansion"
BACKUP_ROOT = ROOT / "backups"
STATIC_ARTWORKS = ROOT / "web" / "lib" / "data" / "artworks.json"
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "ELYIO Paris curated expansion importer (https://elyio.co)"


MUSEUM_CONFIGS: dict[str, dict[str, Any]] = {
    "rodin": {
        "museum_id": "museofile_m5044",
        "name": "Musee Rodin",
        "display_name": "Musée Rodin",
        "source": "wikidata_rodin",
        "collection_qid": "Q650519",
        "department": "Musée Rodin collection",
        "room": "Musée Rodin",
        "source_url": "https://www.wikidata.org/wiki/Q650519",
        "pinned_qids": [
            "Q154571",
            "Q2418237",
            "Q2770535",
            "Q42413554",
            "Q3205060",
            "Q3463880",
            "Q11855751",
            "Q3205458",
            "Q19007127",
            "Q19007225",
            "Q26834197",
            "Q106314799",
            "Q106265262",
            "Q19945289",
            "Q3209848",
            "Q31842466",
            "Q105679701",
            "Q117545302",
            "Q18003128",
            "Q94137842",
            "Q19006977",
            "Q135811327",
            "Q135780151",
            "Q135777143",
            "Q4792194",
            "Q26220257",
            "Q13528770",
            "Q65965438",
            "Q65965466",
            "Q18890731",
        ],
    },
    "picasso": {
        "museum_id": "museofile_m5043",
        "name": "Musee Picasso Paris",
        "display_name": "Musée Picasso Paris",
        "source": "wikidata_picasso_paris",
        "collection_qid": "Q743206",
        "creator_qid": "Q5593",
        "department": "Musée Picasso Paris collection",
        "room": "Musée Picasso Paris",
        "source_url": "https://www.wikidata.org/wiki/Q743206",
        "pinned_qids": [
            "Q2872716",
            "Q133829142",
            "Q133829168",
            "Q3714168",
            "Q3937639",
            "Q133829201",
            "Q3937627",
            "Q495447",
            "Q3207122",
            "Q3224377",
            "Q3715971",
            "Q3715980",
            "Q3794006",
            "Q133828154",
            "Q131443791",
            "Q133865314",
            "Q133462324",
            "Q3698201",
            "Q112678967",
            "Q132973371",
            "Q133829075",
            "Q60550366",
            "Q60453730",
            "Q133288979",
            "Q27184551",
            "Q3337122",
            "Q3898246",
            "Q133249468",
            "Q133283506",
            "Q133283554",
        ],
    },
    "quai_branly": {
        "museum_id": "museofile_m5055",
        "name": "Musee du quai Branly - Jacques Chirac",
        "display_name": "Musée du quai Branly - Jacques Chirac",
        "source": "wikidata_quai_branly",
        "collection_qid": "Q167863",
        "department": "Musée du quai Branly - Jacques Chirac collection",
        "room": "Musée du quai Branly - Jacques Chirac",
        "source_url": "https://www.wikidata.org/wiki/Q167863",
        "pinned_qids": [
            "Q109512724",
            "Q109513136",
            "Q136806650",
            "Q136806719",
            "Q28842788",
            "Q28942332",
            "Q28942362",
            "Q28912441",
            "Q28937297",
            "Q28942383",
            "Q28942677",
            "Q137168029",
            "Q137168030",
            "Q137168031",
            "Q137168032",
            "Q137168033",
            "Q137168034",
            "Q28944159",
            "Q28937343",
            "Q28937211",
            "Q28792186",
            "Q28789939",
            "Q28790115",
            "Q28941751",
            "Q28820342",
            "Q28914394",
            "Q115696367",
            "Q115695445",
            "Q28822856",
            "Q63724183",
        ],
    },
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-") or "record"


def simplify_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.match(r"^-?(\d{1,4})-", value)
    if match:
        return match.group(1)
    return value


def clean_joined(value: str | None) -> str | None:
    if not value:
        return None
    parts: list[str] = []
    seen: set[str] = set()
    for part in [p.strip() for p in value.split(";") if p.strip()]:
        if part.startswith(("http://", "https://")):
            continue
        key = part.lower()
        if key not in seen:
            seen.add(key)
            parts.append(part)
    return "; ".join(parts) if parts else None


def fetch_wikidata_records(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    qids = config["pinned_qids"]
    subject_clause = "VALUES ?item { " + " ".join(f"wd:{qid}" for qid in qids) + " }"
    creator_clause = f"?item wdt:P170 wd:{config['creator_qid']} ." if config.get("creator_qid") else ""
    query = f"""
SELECT ?item ?itemLabel ?itemDescription ?labelFr ?labelZh ?image ?date ?inventory
WHERE {{
  {subject_clause}
  ?item wdt:P195 wd:{config["collection_qid"]} .
  {creator_clause}
  OPTIONAL {{ ?item wdt:P18 ?image. }}
  OPTIONAL {{ ?item wdt:P571|wdt:P577|wdt:P585 ?date. }}
  OPTIONAL {{ ?item wdt:P217 ?inventory. }}
  OPTIONAL {{ ?item rdfs:label ?labelFr FILTER(LANG(?labelFr) = "fr") }}
  OPTIONAL {{ ?item rdfs:label ?labelZh FILTER(LANG(?labelZh) = "zh") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr,zh". }}
}}
ORDER BY ?item
"""
    url = f"{WIKIDATA_ENDPOINT}?{urlencode({'query': query, 'format': 'json'})}"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
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
        raise RuntimeError(f"Wikidata query failed for {config['display_name']}: {last_error}")

    rows: dict[str, dict[str, Any]] = {}
    for binding in payload["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        image = binding.get("image", {}).get("value")
        if image and image.startswith("http://"):
            image = "https://" + image[len("http://") :]
        title = binding.get("itemLabel", {}).get("value") or binding.get("labelFr", {}).get("value") or qid
        rows[qid] = {
            "qid": qid,
            "source_url": f"https://www.wikidata.org/wiki/{qid}",
            "title": title,
            "title_fr": binding.get("labelFr", {}).get("value") or title,
            "title_zh": binding.get("labelZh", {}).get("value") or title,
            "description": binding.get("itemDescription", {}).get("value"),
            "artist": None,
            "date": simplify_date(binding.get("date", {}).get("value")),
            "inventory_number": binding.get("inventory", {}).get("value"),
            "image_url": image,
            "object_type": None,
            "materials": None,
            "location": None,
            "raw_json": {k: v.get("value") for k, v in binding.items()},
        }
    missing = [qid for qid in qids if qid not in rows]
    if missing:
        raise RuntimeError(f"{config['display_name']} pinned records missing from source query: {missing}")
    return rows


def source_fact(record: dict[str, Any], lang: str = "en") -> str:
    artist = record.get("artist")
    object_type = record.get("object_type") or "record"
    date = record.get("date")
    material = record.get("materials")
    inv = record.get("inventory_number")
    parts = []
    if artist:
        parts.append(artist)
    if date:
        parts.append(date)
    if object_type:
        parts.append(object_type)
    if material:
        parts.append(material)
    if inv:
        parts.append(f"inventory {inv}" if lang == "en" else f"inventaire {inv}" if lang == "fr" else f"藏品编号 {inv}")
    return ", ".join(parts)


def visual_cue(record: dict[str, Any], lang: str = "en") -> str:
    title = record.get(f"title_{lang}") if lang in {"fr", "zh"} else record.get("title")
    object_type = record.get("object_type") or ""
    material = record.get("materials") or ""
    description = record.get("description") or ""
    if lang == "fr":
        return ", ".join([p for p in [title, object_type, material, description] if p])[:260]
    if lang == "zh":
        return "、".join([p for p in [title, object_type, material, description] if p])[:180]
    return ", ".join([p for p in [title, object_type, material, description] if p])[:260]


def derive_artist(config: dict[str, Any], row: dict[str, Any]) -> str | None:
    if config.get("creator_qid") == "Q5593":
        return "Pablo Picasso"
    artist = row.get("artist")
    if artist:
        return artist
    description = row.get("description") or ""
    match = re.search(r"\bby ([^,.;]+)", description, flags=re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).strip()
    if value.lower() in {"anonymous", "unknown", "unknown artist"}:
        return None
    return value


def derive_object_type(row: dict[str, Any]) -> str:
    object_type = row.get("object_type")
    if object_type and object_type != "artwork":
        return object_type
    description = (row.get("description") or "").lower()
    for kind in [
        "painting",
        "sculpture",
        "statue",
        "bust",
        "drawing",
        "collage",
        "mask",
        "throne",
        "doll",
        "necklace",
        "bowl",
        "door frame",
        "headrest",
    ]:
        if kind in description:
            return kind
    return object_type or "artwork"


def normal_content(config: dict[str, Any], record: dict[str, Any], lang: str) -> dict[str, str]:
    title = record[f"title_{lang}"] if lang in {"fr", "zh"} else record["title"]
    museum = config["display_name"]
    fact = source_fact(record, lang)
    cue = visual_cue(record, lang)
    if lang == "fr":
        return {
            "title": title,
            "analogy": f"{title} fait partie du lancement curaté ELYIO pour {museum}.",
            "why_it_matters": f"Cette entrée est retenue parce que les données publiques la relient directement à la collection de {museum}. {fact} donne au visiteur une identité fiable sans inventer de récit.",
            "where_to_look": f"Commencez par les indices visibles: {cue}. Ces éléments aident à relier ce que vous voyez à la fiche source.",
            "rarity_note": "ELYIO traite cette oeuvre comme patrimoine public ou collectionnel: aucune estimation de vente n'est inventée.",
        }
    if lang == "zh":
        return {
            "title": title,
            "analogy": f"{title}属于 ELYIO 为{museum}推出的精选目录。",
            "why_it_matters": f"这条记录被纳入，是因为公开结构化资料把它明确连接到{museum}的收藏。{fact}能给参观者一个可靠身份，而不虚构故事。",
            "where_to_look": f"请先看可见的识别线索：{cue}。这些线索帮助你把眼前对象和来源记录对应起来。",
            "rarity_note": "ELYIO 将其作为公共文化遗产或馆藏对象处理；不会编造市场售价。",
        }
    return {
        "title": title,
        "analogy": f"{title} is part of ELYIO's curated launch catalog for {museum}.",
        "why_it_matters": f"This record is included because public structured data connects it directly to the {museum} collection. {fact} gives the visitor a reliable identity without inventing unsupported story.",
        "where_to_look": f"Start with the visible identity cues: {cue}. These details connect what you are seeing to the source record.",
        "rarity_note": "ELYIO treats this as public heritage or collection context; it does not invent a sale estimate.",
    }


def simple_content(config: dict[str, Any], record: dict[str, Any], lang: str) -> dict[str, str]:
    title = record[f"title_{lang}"] if lang in {"fr", "zh"} else record["title"]
    museum = config["display_name"]
    if lang == "fr":
        return {
            "title": title,
            "analogy": f"Vous regardez {title}. Les faits disponibles indiquent son lien avec {museum}.",
            "where_to_look": f"Cherchez d'abord: {visual_cue(record, 'fr')}.",
            "rarity_note": "Ce n'est pas présenté comme un objet à vendre: c'est une oeuvre ou un objet de collection publique.",
        }
    if lang == "zh":
        return {
            "title": title,
            "analogy": f"你看到的是{title}。现有资料说明它和{museum}的收藏有关。",
            "where_to_look": f"先寻找这些线索：{visual_cue(record, 'zh')}。",
            "rarity_note": "这里不会把它说成可出售的商品；它是公共收藏中的作品或物件。",
        }
    return {
        "title": title,
        "analogy": f"You are looking at {title}. The available facts connect it to the {museum} collection.",
        "where_to_look": f"First look for: {visual_cue(record, 'en')}.",
        "rarity_note": "This is not presented as an object for sale; it is part of a public collection context.",
    }


def kids_content(config: dict[str, Any], record: dict[str, Any], lang: str) -> dict[str, str]:
    title = record[f"title_{lang}"] if lang in {"fr", "zh"} else record["title"]
    if lang == "fr":
        return {
            "title": title,
            "analogy": f"Essaie de trouver un indice facile à voir sur {title}.",
            "where_to_look": f"Regarde si tu peux repérer: {visual_cue(record, 'fr')}.",
            "rarity_note": "Cet indice aide ELYIO à expliquer pourquoi cet objet compte dans le musée.",
        }
    if lang == "zh":
        return {
            "title": title,
            "analogy": f"试着在{title}上找到一个容易看到的线索。",
            "where_to_look": f"看看你能不能发现：{visual_cue(record, 'zh')}。",
            "rarity_note": "这个线索能帮助 ELYIO 说明它为什么在博物馆里重要。",
        }
    return {
        "title": title,
        "analogy": f"Try to find one clear clue on {title}.",
        "where_to_look": f"See if you can spot: {visual_cue(record, 'en')}.",
        "rarity_note": "That clue helps ELYIO explain why this object matters in the museum.",
    }


def beyond_market_value(config: dict[str, Any], source_url: str) -> dict[str, Any]:
    museum = config["display_name"]
    return {
        "mode": "BEYOND_MARKET",
        "aggregate_value_eligible": False,
        "beyond_market_headline": "No ordinary market price.",
        "beyond_market_explanation": f"This belongs to the {museum} public collection context, so ELYIO does not present it as a private-market sale object.",
        "institutional_legal_context": "Public cultural heritage context; not an appraisal, insurance value, or sale estimate.",
        "confidence": "medium",
        "sources": [source_url],
        "disclaimer": "Not an appraisal, insurance value, or sale estimate.",
        "review_status": "AUTO_QA_PASSED",
    }


def build_new_museum_records(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = fetch_wikidata_records(config)
    records: list[dict[str, Any]] = []
    for i, qid in enumerate(config["pinned_qids"], start=1):
        row = rows[qid]
        records.append(
            {
                "id": f"{slugify(config['name'])}_{qid.lower()}",
                "source": config["source"],
                "source_record_id": qid,
                "title": row["title"],
                "title_fr": row["title_fr"],
                "title_zh": row["title_zh"],
                "artist": derive_artist(config, row),
                "date": row["date"],
                "object_type": derive_object_type(row),
                "materials": row["materials"],
                "inventory_number": row["inventory_number"],
                "image_url": row["image_url"],
                "source_url": row["source_url"],
                "description": row["description"],
                "department": config["department"],
                "location": row["location"] or config["room"],
                "room": row["location"] or config["room"],
                "priority": i,
                "tier": "A" if i <= 5 else "B" if i <= 20 else "C",
                "selection_reason": f"pinned {config['display_name']} launch-catalog record from Wikidata collection membership",
                "raw_json": row["raw_json"],
            }
        )
    if len(records) != len(config["pinned_qids"]):
        raise RuntimeError(f"{config['display_name']} selected {len(records)} records")
    return records


def normalize_snapshot_record(config: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    row = dict(record)
    row["artist"] = derive_artist(config, row)
    row["object_type"] = derive_object_type(row)
    return row


def load_snapshot_records(key: str, config: dict[str, Any]) -> list[dict[str, Any]] | None:
    path = OUTPUT_DIR / f"{key}_launch_snapshot.jsonl"
    if not path.exists():
        return None
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [normalize_snapshot_record(config, row) for row in records] or None


def load_static_records() -> list[dict[str, Any]]:
    return json.loads(STATIC_ARTWORKS.read_text(encoding="utf-8"))


def localized_value(value: Any, locale: str) -> str | None:
    if isinstance(value, dict):
        return value.get(locale) or value.get("en")
    if isinstance(value, str):
        return value
    return None


def upsert_legacy_localizations(session: Session, records: list[dict[str, Any]], apply: bool) -> Counter:
    counts = Counter()
    ids = [row["id"] for row in records]
    existing = {
        (row.artwork_id, row.locale, row.mode): row
        for row in session.query(ArtworkLocalization).filter(ArtworkLocalization.artwork_id.in_(ids)).all()
    }
    for record in records:
        for locale in ["en", "fr", "zh-Hans"]:
            modes = {
                "normal": {
                    "analogy": localized_value(record.get("accent"), locale),
                    "why_it_matters": localized_value(record.get("why"), locale),
                    "where_to_look": localized_value(record.get("where"), locale),
                    "rarity_note": localized_value(record.get("rarity"), locale),
                    "audio_script": localized_value(record.get("audioScript"), locale),
                    "audio_url": localized_value(record.get("audioUrl"), locale),
                },
                "simple": {
                    "analogy": localized_value(record.get("whySimple") or record.get("why"), locale),
                    "why_it_matters": localized_value(record.get("whySimple") or record.get("why"), locale),
                    "where_to_look": localized_value(record.get("whereSimple") or record.get("where"), locale),
                    "rarity_note": localized_value(record.get("raritySimple") or record.get("rarity"), locale),
                },
                "kids": {
                    "analogy": localized_value(record.get("whyKids") or record.get("whySimple") or record.get("why"), locale),
                    "why_it_matters": localized_value(record.get("whyKids") or record.get("whySimple") or record.get("why"), locale),
                    "where_to_look": localized_value(record.get("whereKids") or record.get("whereSimple") or record.get("where"), locale),
                    "rarity_note": localized_value(record.get("rarityKids") or record.get("raritySimple") or record.get("rarity"), locale),
                },
            }
            for mode, content in modes.items():
                key = (record["id"], locale, mode)
                row = existing.get(key)
                if row is None:
                    row = ArtworkLocalization(artwork_id=record["id"], locale=locale, mode=mode)
                    existing[key] = row
                    counts["legacy_localizations_inserted"] += 1
                    if apply:
                        session.add(row)
                else:
                    counts["legacy_localizations_updated"] += 1
                row.title = localized_value(record.get("title"), locale) or record["id"]
                row.analogy = content.get("analogy")
                row.why_it_matters = content.get("why_it_matters")
                row.where_to_look = content.get("where_to_look")
                row.rarity_note = content.get("rarity_note")
                row.audio_script = content.get("audio_script")
                row.audio_url = content.get("audio_url")
                row.editorial_status = "published"
                row.reviewed_by = "ELYIO legacy curated catalog import"
                row.updated_at = datetime.now(timezone.utc)
    return counts


def upsert_legacy_values(session: Session, records: list[dict[str, Any]], apply: bool) -> Counter:
    counts = Counter()
    ids = [row["id"] for row in records]
    existing_estimates = {row.artwork_id: row for row in session.query(ArtworkEstimate).filter(ArtworkEstimate.artwork_id.in_(ids)).all()}
    existing_reveals = {
        row.artwork_id: row
        for row in session.query(ArtworkValueReveal)
        .filter(ArtworkValueReveal.artwork_id.in_(ids), ArtworkValueReveal.catalog_version == LEGACY_CATALOG_VERSION)
        .all()
    }
    for record in records:
        estimate = record.get("estimate") or {}
        low = estimate.get("low")
        high = estimate.get("high")
        logic = estimate.get("logic")
        est = existing_estimates.get(record["id"])
        if low is not None and high is not None and est is None:
            est = ArtworkEstimate(artwork_id=record["id"])
            existing_estimates[record["id"]] = est
            counts["legacy_estimates_inserted"] += 1
            if apply:
                session.add(est)
        elif low is not None and high is not None and est is not None:
            counts["legacy_estimates_preserved"] += 1
        if est is not None and low is not None and high is not None:
            est.estimate_low_eur_m = float(low)
            est.estimate_high_eur_m = float(high)
            est.estimate_logic = logic
            est.estimate_confidence = "medium"
            est.reviewed_by = est.reviewed_by or "ELYIO legacy curated catalog"
            est.updated_at = datetime.now(timezone.utc)

        reveal = existing_reveals.get(record["id"])
        if reveal is None:
            reveal = ArtworkValueReveal(artwork_id=record["id"], catalog_version=LEGACY_CATALOG_VERSION)
            existing_reveals[record["id"]] = reveal
            counts["legacy_value_reveals_inserted"] += 1
            if apply:
                session.add(reveal)
        else:
            counts["legacy_value_reveals_updated"] += 1
        if low is None or high is None:
            counts["legacy_value_reveals_beyond_market"] += 1
            reveal.mode = "BEYOND_MARKET"
            reveal.aggregate_value_eligible = False
            reveal.estimated_value_low = None
            reveal.estimated_value_high = None
            reveal.estimated_value_currency = None
            reveal.beyond_market_headline = "No responsible market range."
            reveal.beyond_market_explanation = "ELYIO found no defensible market comparable for this specific museum work and does not turn weak context into a price."
            reveal.institutional_legal_context = "Public collection context; not an appraisal, insurance value, or sale estimate."
            reveal.optional_context = None
            reveal.confidence = "medium"
            reveal.methodology = logic
        else:
            reveal.mode = "ESTIMATED_VALUE"
            reveal.aggregate_value_eligible = True
            reveal.estimated_value_low = float(low)
            reveal.estimated_value_high = float(high)
            reveal.estimated_value_currency = "EUR"
            reveal.beyond_market_headline = None
            reveal.beyond_market_explanation = None
            reveal.institutional_legal_context = None
            reveal.optional_context = None
            reveal.confidence = "medium"
            reveal.methodology = logic
        reveal.market_context_headline_number = None
        reveal.market_context_currency = None
        reveal.market_context_label = None
        reveal.market_context_explanation = None
        reveal.relationship_to_artwork = None
        reveal.context_type = None
        reveal.source_reference = None
        reveal.context_date = None
        reveal.sources = [record.get("imageUrl")] if record.get("imageUrl") else []
        reveal.disclaimer = "ELYIO visitor value context; not an appraisal, insurance value, or sale estimate."
        reveal.review_status = "AUTO_QA_PASSED"
        reveal.generated_at = datetime.now(timezone.utc)
        reveal.updated_at = datetime.now(timezone.utc)
    return counts


def upsert_new_museum(session: Session, config: dict[str, Any], apply: bool) -> None:
    row = session.get(Museum, config["museum_id"])
    if row is None:
        row = Museum(id=config["museum_id"], name=config["display_name"])
        if apply:
            session.add(row)
    row.experience_level = "CURATED"
    row.source_url = row.source_url or config["source_url"]


def upsert_new_artwork(session: Session, config: dict[str, Any], record: dict[str, Any], apply: bool) -> tuple[str, str]:
    row = session.query(Artwork).filter(Artwork.source == record["source"], Artwork.source_record_id == record["source_record_id"]).first()
    action = "updated"
    if row is None:
        row = session.get(Artwork, record["id"])
    if row is None:
        row = Artwork(id=record["id"])
        action = "inserted"
        if apply:
            session.add(row)
    row.museum_id = config["museum_id"]
    row.artist = record.get("artist")
    row.title_original = record["title"]
    row.year = record.get("date")
    row.inventory_number = record.get("inventory_number")
    row.hall = record.get("room")
    row.technique = record.get("materials")
    row.image_url = record.get("image_url")
    row.priority = int(record.get("priority") or 100)
    row.tags = [record["tier"], "paris-curated-launch", slugify(record.get("object_type") or "artwork")]
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
    row.display_status_confidence = "MEDIUM"
    row.display_status_reason = record["selection_reason"]
    row.metadata_status = "READY" if record.get("description") else "PARTIAL"
    row.recognition_status = "VISION_READY"
    row.rights_status = "REMOTE_DISPLAY_METADATA_ONLY" if record.get("image_url") else "NO_IMAGE_METADATA"
    row.rights_review_required = False
    return row.id, action


def upsert_membership(session: Session, config: dict[str, Any], artwork_id: str, record: dict[str, Any], existing: dict[str, ArtworkCatalogMembership], apply: bool) -> str:
    row = existing.get(artwork_id)
    action = "updated"
    if row is None:
        row = ArtworkCatalogMembership(artwork_id=artwork_id, museum_id=config["museum_id"], catalog_version=CATALOG_VERSION)
        existing[artwork_id] = row
        action = "inserted"
        if apply:
            session.add(row)
    row.active = True
    row.tier = record["tier"]
    row.visitor_priority = float(1000 - int(record.get("priority") or 100))
    return action


def upsert_new_localizations(session: Session, config: dict[str, Any], artwork_id: str, record: dict[str, Any], existing: dict[tuple[str, str], ArtworkLocalization], apply: bool) -> Counter:
    counts = Counter()
    for lang_key, locale in [("en", "en"), ("fr", "fr"), ("zh", "zh-Hans")]:
        for mode, content in [
            ("normal", normal_content(config, record, lang_key)),
            ("simple", simple_content(config, record, lang_key)),
            ("kids", kids_content(config, record, lang_key)),
        ]:
            key = (artwork_id, locale, mode)
            row = existing.get(key)
            if row is None:
                row = ArtworkLocalization(artwork_id=artwork_id, locale=locale, mode=mode)
                existing[key] = row
                counts["new_localizations_inserted"] += 1
                if apply:
                    session.add(row)
            else:
                counts["new_localizations_updated"] += 1
            row.title = content["title"]
            row.analogy = content["analogy"]
            row.why_it_matters = content.get("why_it_matters")
            row.where_to_look = content.get("where_to_look")
            row.rarity_note = content.get("rarity_note")
            row.audio_script = None
            row.audio_url = None
            row.editorial_status = "published"
            row.reviewed_by = "ELYIO Paris curated expansion factual importer"
            row.updated_at = datetime.now(timezone.utc)
    return counts


def upsert_new_value(session: Session, config: dict[str, Any], artwork_id: str, record: dict[str, Any], existing: dict[str, ArtworkValueReveal], apply: bool) -> str:
    row = existing.get(artwork_id)
    action = "updated"
    if row is None:
        row = ArtworkValueReveal(artwork_id=artwork_id, catalog_version=CATALOG_VERSION)
        existing[artwork_id] = row
        action = "inserted"
        if apply:
            session.add(row)
    value = beyond_market_value(config, record["source_url"])
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
    row.methodology = "Launch value treatment: public cultural heritage context; no sale estimate inferred."
    row.sources = value["sources"]
    row.disclaimer = value["disclaimer"]
    row.review_status = value["review_status"]
    row.generated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return action


def backup(session: Session, target_museum_ids: list[str], legacy_ids: list[str]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = BACKUP_ROOT / f"paris_curated_expansion_pre_import_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    queries = {
        "museums": "SELECT * FROM museums WHERE id = ANY(:museum_ids)",
        "artworks_new_museums": "SELECT * FROM artworks WHERE museum_id = ANY(:museum_ids)",
        "memberships_new_museums": "SELECT * FROM artwork_catalog_memberships WHERE museum_id = ANY(:museum_ids)",
        "legacy_localizations": "SELECT * FROM artwork_localizations WHERE artwork_id = ANY(:legacy_ids)",
        "legacy_estimates": "SELECT * FROM artwork_estimates WHERE artwork_id = ANY(:legacy_ids)",
        "legacy_value_reveals": "SELECT * FROM artwork_value_reveals WHERE artwork_id = ANY(:legacy_ids)",
    }
    counts = {}
    for name, sql in queries.items():
        table = {
            "museums": "museums",
            "artworks_new_museums": "artworks",
            "memberships_new_museums": "artwork_catalog_memberships",
            "legacy_localizations": "artwork_localizations",
            "legacy_estimates": "artwork_estimates",
            "legacy_value_reveals": "artwork_value_reveals",
        }[name]
        if not inspect(session.bind).has_table(table):
            continue
        rows = [
            dict(row._mapping)
            for row in session.execute(text(sql), {"museum_ids": target_museum_ids, "legacy_ids": legacy_ids}).all()
        ]
        counts[name] = len(rows)
        with (out / f"{name}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")
    (out / "counts.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    return out


def write_snapshot(records_by_museum: dict[str, list[dict[str, Any]]], summary: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, records in records_by_museum.items():
        with (OUTPUT_DIR / f"{key}_launch_snapshot.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in records:
                fh.write(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def coverage_query(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            """
            WITH active AS (
              SELECT a.id, a.museum_id
              FROM artworks a
              WHERE a.museum_id IN ('louvre','orsay','orangerie','versailles','museofile_m5044','museofile_m5043','museofile_m5055')
                AND (
                  a.museum_id NOT IN ('louvre','versailles','museofile_m5044','museofile_m5043','museofile_m5055')
                  OR EXISTS (
                    SELECT 1 FROM artwork_catalog_memberships m
                    WHERE m.artwork_id=a.id AND m.museum_id=a.museum_id AND m.active IS TRUE
                  )
                )
            ),
            loc AS (
              SELECT artwork_id, count(*) rows
              FROM artwork_localizations
              WHERE editorial_status='published'
              GROUP BY artwork_id
            )
            SELECT museum_id,
                   count(*) active,
                   count(*) FILTER (WHERE COALESCE(loc.rows,0) >= 9) full_curated,
                   count(*) FILTER (WHERE COALESCE(loc.rows,0) < 9 AND COALESCE(loc.rows,0) > 0) partial_curated,
                   count(*) FILTER (WHERE COALESCE(loc.rows,0) = 0) fallback
            FROM active
            LEFT JOIN loc ON loc.artwork_id=active.id
            GROUP BY museum_id
            ORDER BY museum_id
            """
        )
    ).all()
    return [dict(row._mapping) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write to DATABASE_URL; default is dry-run")
    parser.add_argument("--refresh-source", action="store_true", help="refresh pinned Wikidata metadata instead of reusing local snapshots")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set")

    legacy_records = load_static_records()
    legacy_ids = [row["id"] for row in legacy_records]
    records_by_museum = {}
    for key, config in MUSEUM_CONFIGS.items():
        snapshot = None if args.refresh_source else load_snapshot_records(key, config)
        records_by_museum[key] = snapshot or build_new_museum_records(config)
    for key, records in records_by_museum.items():
        if len(records) != 30:
            raise SystemExit(f"{key} expected 30 records, got {len(records)}")

    engine = create_engine(database_url, pool_pre_ping=True)
    counts = Counter()
    backup_path = None
    with Session(engine, autoflush=args.apply) as session:
        existing_legacy = {row.id: row.museum_id for row in session.query(Artwork).filter(Artwork.id.in_(legacy_ids)).all()}
        if len(existing_legacy) != len(legacy_ids):
            missing = sorted(set(legacy_ids) - set(existing_legacy))
            raise SystemExit(f"legacy Orsay/Orangerie records missing from production: {missing[:10]}")
        for row in legacy_records:
            expected = row.get("museumId") or "orsay"
            if existing_legacy.get(row["id"]) != expected:
                raise SystemExit(f"legacy museum mismatch for {row['id']}: expected {expected}, got {existing_legacy.get(row['id'])}")

        if args.apply:
            backup_path = backup(session, [cfg["museum_id"] for cfg in MUSEUM_CONFIGS.values()], legacy_ids)

        counts.update(upsert_legacy_localizations(session, legacy_records, args.apply))
        counts.update(upsert_legacy_values(session, legacy_records, args.apply))

        for key, config in MUSEUM_CONFIGS.items():
            upsert_new_museum(session, config, args.apply)
            records = records_by_museum[key]
            ids = [row["id"] for row in records]
            existing_memberships = {
                row.artwork_id: row
                for row in session.query(ArtworkCatalogMembership)
                .filter(ArtworkCatalogMembership.museum_id == config["museum_id"], ArtworkCatalogMembership.catalog_version == CATALOG_VERSION)
                .all()
            }
            existing_loc = {
                (row.artwork_id, row.locale, row.mode): row
                for row in session.query(ArtworkLocalization).filter(ArtworkLocalization.artwork_id.in_(ids)).all()
            }
            existing_values = {
                row.artwork_id: row
                for row in session.query(ArtworkValueReveal)
                .filter(ArtworkValueReveal.artwork_id.in_(ids), ArtworkValueReveal.catalog_version == CATALOG_VERSION)
                .all()
            }
            for record in records:
                artwork_id, action = upsert_new_artwork(session, config, record, args.apply)
                counts[f"{key}_artworks_{action}"] += 1
                membership_action = upsert_membership(session, config, artwork_id, record, existing_memberships, args.apply)
                counts[f"{key}_memberships_{membership_action}"] += 1
                counts.update(upsert_new_localizations(session, config, artwork_id, record, existing_loc, args.apply))
                value_action = upsert_new_value(session, config, artwork_id, record, existing_values, args.apply)
                counts[f"{key}_value_reveals_{value_action}"] += 1
            active_ids = set(ids)
            for artwork_id, row in existing_memberships.items():
                if artwork_id not in active_ids and row.active:
                    row.active = False
                    counts[f"{key}_memberships_deactivated"] += 1

        if args.apply:
            session.commit()
        else:
            session.rollback()

    summary = {
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "catalog_version": CATALOG_VERSION,
        "legacy_records": len(legacy_records),
        "new_museums": {key: len(records) for key, records in records_by_museum.items()},
        "counts": dict(counts),
        "backup_path": str(backup_path) if backup_path else None,
    }
    write_snapshot(records_by_museum, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
