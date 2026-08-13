#!/usr/bin/env python3
"""Import the second Paris curated museum wave.

Scope:
- Guimet, Cluny, Carnavalet, Petit Palais Paris, and Musee de l'Armee.
- 30 pinned Wikidata collection records per museum.

This importer is idempotent and additive. It does not create RecognitionAssets,
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

from app.models import Artwork, ArtworkCatalogMembership, ArtworkLocalization, ArtworkValueReveal, Museum  # noqa: E402


CATALOG_VERSION = "2026-08-14-v1"
OUTPUT_DIR = ROOT / "exports" / "paris_curated_wave2"
BACKUP_ROOT = ROOT / "backups"
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "ELYIO Paris curated wave 2 importer (https://elyio.co)"


MUSEUM_CONFIGS: dict[str, dict[str, Any]] = {
    "guimet": {
        "museum_id": "museofile_m5005",
        "display_name": "Musée national des arts asiatiques - Guimet",
        "source": "wikidata_guimet",
        "collection_qid": "Q860994",
        "department": "Musée Guimet collection",
        "room": "Musée Guimet",
        "source_url": "https://www.wikidata.org/wiki/Q860994",
        "pinned_qids": [
            "Q27062092", "Q5948124", "Q112111667", "Q124094529", "Q28531311",
            "Q60389988", "Q4281022", "Q46127483", "Q46136544", "Q44279153",
            "Q47300513", "Q43131839", "Q43133338", "Q43133859", "Q43134286",
            "Q43378697", "Q42899460", "Q131544891", "Q137781333", "Q138329530",
            "Q28529549", "Q45990805", "Q46104973", "Q46022071", "Q46091970",
            "Q138330501", "Q138349695", "Q43124373", "Q43125584", "Q33083137",
        ],
    },
    "cluny": {
        "museum_id": "museofile_m5003",
        "display_name": "Musée de Cluny - Musée national du Moyen Âge",
        "source": "wikidata_cluny",
        "collection_qid": "Q1124095",
        "department": "Musée de Cluny collection",
        "room": "Musée de Cluny",
        "source_url": "https://www.wikidata.org/wiki/Q1124095",
        "pinned_qids": [
            "Q2289754", "Q1394918", "Q430222", "Q684453", "Q5147745",
            "Q9584283", "Q114902064", "Q115672885", "Q124960630", "Q140707798",
            "Q64138504", "Q65953484", "Q138317176", "Q134393721", "Q134390789",
            "Q136297784", "Q18156247", "Q18156272", "Q18156273", "Q18156279",
            "Q18156282", "Q18156280", "Q20983808", "Q110817696", "Q6049877",
            "Q137603834", "Q137453059", "Q137643388", "Q25396229", "Q14528677",
        ],
    },
    "carnavalet": {
        "museum_id": "museofile_m1104",
        "display_name": "Musée Carnavalet - Histoire de Paris",
        "source": "wikidata_carnavalet",
        "collection_qid": "Q640447",
        "department": "Musée Carnavalet collection",
        "room": "Musée Carnavalet",
        "source_url": "https://www.wikidata.org/wiki/Q640447",
        "pinned_qids": [
            "Q20087570", "Q1799047", "Q113988382", "Q16467705", "Q2902543",
            "Q97051722", "Q16931464", "Q18084769", "Q18783414", "Q19595326",
            "Q104370760", "Q104370142", "Q104373108", "Q104371543", "Q105356817",
            "Q104356159", "Q97069933", "Q97028411", "Q104369361", "Q104372522",
            "Q104372703", "Q104370980", "Q104371244", "Q97060914", "Q104370119",
            "Q18676922", "Q18783418", "Q18783422", "Q19370812", "Q19595331",
        ],
    },
    "petit_palais": {
        "museum_id": "museofile_m1111",
        "display_name": "Petit Palais - Musée des Beaux-Arts de la Ville de Paris",
        "source": "wikidata_petit_palais",
        "collection_qid": "Q59546080",
        "department": "Petit Palais collection",
        "room": "Petit Palais",
        "source_url": "https://www.wikidata.org/wiki/Q59546080",
        "pinned_qids": [
            "Q326503", "Q1293985", "Q3210841", "Q48651005", "Q3210835",
            "Q3399375", "Q18578022", "Q19820361", "Q80112683", "Q2842423",
            "Q3612977", "Q3944464", "Q12837243", "Q15877748", "Q17353184",
            "Q25396225", "Q61677254", "Q7936304", "Q104443853", "Q104443881",
            "Q104444964", "Q16969091", "Q3842460", "Q47154163", "Q104444971",
            "Q104445064", "Q104445070", "Q19753116", "Q137900389", "Q21558298",
        ],
    },
    "armee": {
        "museum_id": "museofile_m5025",
        "display_name": "Musée de l'Armée",
        "source": "wikidata_armee",
        "collection_qid": "Q1996069",
        "department": "Musée de l'Armée collection",
        "room": "Musée de l'Armée",
        "source_url": "https://www.wikidata.org/wiki/Q1996069",
        "pinned_qids": [
            "Q1282840", "Q720483", "Q3589378", "Q47528216", "Q3561686",
            "Q120355686", "Q121061617", "Q130458021", "Q111306290", "Q121077338",
            "Q30107050", "Q106654904", "Q30115013", "Q117024764", "Q130481897",
            "Q112294939", "Q112294948", "Q30106396", "Q30106701", "Q56259960",
            "Q56760585", "Q112181242", "Q30132293", "Q56599085", "Q111281500",
            "Q112181621", "Q111333162", "Q29994981", "Q56605490", "Q88862654",
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


def sparql_request(query: str) -> dict[str, Any]:
    url = f"{WIKIDATA_ENDPOINT}?{urlencode({'query': query, 'format': 'json'})}"
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(8 * (attempt + 1))
    raise RuntimeError(f"Wikidata query failed: {last_error}")


def fetch_wikidata_records(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    qids = config["pinned_qids"]
    subject_clause = "VALUES ?item { " + " ".join(f"wd:{qid}" for qid in qids) + " }"
    query = f"""
SELECT ?item ?itemLabel ?itemDescription ?labelFr ?labelZh
       (SAMPLE(?image0) AS ?image)
       (SAMPLE(?date0) AS ?date)
       (SAMPLE(?inventory0) AS ?inventory)
       (SAMPLE(?creatorLabel0) AS ?creatorLabel)
       (SAMPLE(?typeLabel0) AS ?typeLabel)
WHERE {{
  {subject_clause}
  ?item wdt:P195 wd:{config["collection_qid"]} .
  OPTIONAL {{ ?item wdt:P18 ?image0. }}
  OPTIONAL {{ ?item wdt:P571|wdt:P577|wdt:P585 ?date0. }}
  OPTIONAL {{ ?item wdt:P217 ?inventory0. }}
  OPTIONAL {{ ?item wdt:P170 ?creator. ?creator rdfs:label ?creatorLabel0 FILTER(LANG(?creatorLabel0) = "en") }}
  OPTIONAL {{ ?item wdt:P31 ?type. ?type rdfs:label ?typeLabel0 FILTER(LANG(?typeLabel0) = "en") }}
  OPTIONAL {{ ?item rdfs:label ?labelFr FILTER(LANG(?labelFr) = "fr") }}
  OPTIONAL {{ ?item rdfs:label ?labelZh FILTER(LANG(?labelZh) = "zh") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr,zh". }}
}}
GROUP BY ?item ?itemLabel ?itemDescription ?labelFr ?labelZh
"""
    payload = sparql_request(query)
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
            "artist": binding.get("creatorLabel", {}).get("value"),
            "date": simplify_date(binding.get("date", {}).get("value")),
            "inventory_number": binding.get("inventory", {}).get("value"),
            "image_url": image,
            "object_type": binding.get("typeLabel", {}).get("value"),
            "raw_json": {k: v.get("value") for k, v in binding.items()},
        }
    missing = [qid for qid in qids if qid not in rows]
    if missing:
        raise RuntimeError(f"{config['display_name']} pinned records missing from source query: {missing}")
    return rows


def source_fact(record: dict[str, Any], lang: str) -> str:
    pieces = []
    if record.get("artist"):
        pieces.append(record["artist"])
    if record.get("date"):
        pieces.append(record["date"])
    if record.get("object_type"):
        pieces.append(record["object_type"])
    if record.get("inventory_number"):
        pieces.append(
            f"inventory {record['inventory_number']}" if lang == "en"
            else f"inventaire {record['inventory_number']}" if lang == "fr"
            else f"藏品编号 {record['inventory_number']}"
        )
    return ", ".join(pieces)


def visual_cue(record: dict[str, Any], lang: str) -> str:
    title = record.get(f"title_{lang}") if lang in {"fr", "zh"} else record.get("title")
    parts = [title, record.get("object_type"), record.get("description")]
    if lang == "zh":
        return "、".join([p for p in parts if p])[:190]
    return ", ".join([p for p in parts if p])[:270]


def content(config: dict[str, Any], record: dict[str, Any], lang: str, mode: str) -> dict[str, str]:
    title = record.get(f"title_{lang}") if lang in {"fr", "zh"} else record["title"]
    museum = config["display_name"]
    fact = source_fact(record, lang)
    cue = visual_cue(record, lang)
    if lang == "fr":
        if mode == "kids":
            return {
                "title": title,
                "analogy": f"Choisis un détail visible sur {title} et regarde comment il aide à reconnaître l'objet.",
                "why_it_matters": f"Ce détail te relie à une vraie pièce conservée par {museum}.",
                "where_to_look": f"Cherche: {cue}.",
                "rarity_note": "ELYIO explique l'objet comme patrimoine public, sans inventer de prix.",
            }
        if mode == "simple":
            return {
                "title": title,
                "analogy": f"Vous regardez {title}.",
                "why_it_matters": f"Les données disponibles l'associent directement à {museum}. {fact}",
                "where_to_look": f"Commencez par ces indices: {cue}.",
                "rarity_note": "Ce n'est pas présenté comme un objet à vendre.",
            }
        return {
            "title": title,
            "analogy": f"{title} fait partie du lancement curaté ELYIO pour {museum}.",
            "why_it_matters": f"Cette entrée a été retenue parce que des données publiques la relient directement à la collection de {museum}. {fact} donne une identité fiable sans ajouter de récit non sourcé.",
            "where_to_look": f"Regardez d'abord les indices visibles: {cue}. Ils aident à relier l'objet réel à la fiche de source.",
            "rarity_note": "La valeur est traitée comme contexte patrimonial public, pas comme estimation de vente.",
        }
    if lang == "zh":
        if mode == "kids":
            return {
                "title": title,
                "analogy": f"在{title}上找一个看得见的线索，看看它怎样帮助你认出这件作品。",
                "why_it_matters": f"这个线索把你看到的东西和{museum}的一件真实馆藏联系起来。",
                "where_to_look": f"请寻找：{cue}。",
                "rarity_note": "ELYIO 把它作为公共文化遗产来解释，不编造价格。",
            }
        if mode == "simple":
            return {
                "title": title,
                "analogy": f"你正在看的是{title}。",
                "why_it_matters": f"现有资料把它明确连接到{museum}的收藏。{fact}",
                "where_to_look": f"先看这些线索：{cue}。",
                "rarity_note": "这里不会把它说成可出售的商品。",
            }
        return {
            "title": title,
            "analogy": f"{title}属于 ELYIO 为{museum}推出的精选目录。",
            "why_it_matters": f"这条记录被纳入，是因为公开资料把它直接连接到{museum}的收藏。{fact}提供可靠身份，不添加没有来源的故事。",
            "where_to_look": f"先看这些可见线索：{cue}。这些线索帮助你把眼前对象和来源记录对应起来。",
            "rarity_note": "价值部分按公共文化遗产语境处理，而不是出售估价。",
        }
    if mode == "kids":
        return {
            "title": title,
            "analogy": f"Pick one visible clue on {title} and see how it helps identify the object.",
            "why_it_matters": f"That clue connects what you see to a real object in the {museum} collection.",
            "where_to_look": f"Look for: {cue}.",
            "rarity_note": "ELYIO explains it as public heritage, without inventing a price.",
        }
    if mode == "simple":
        return {
            "title": title,
            "analogy": f"You are looking at {title}.",
            "why_it_matters": f"The available facts connect it directly to the {museum} collection. {fact}",
            "where_to_look": f"Start with these clues: {cue}.",
            "rarity_note": "This is not presented as an object for sale.",
        }
    return {
        "title": title,
        "analogy": f"{title} is part of ELYIO's curated launch catalog for {museum}.",
        "why_it_matters": f"This record is included because public data connects it directly to the {museum} collection. {fact} gives the visitor a reliable identity without adding unsupported story.",
        "where_to_look": f"Start with the visible cues: {cue}. These details connect what you are seeing to the source record.",
        "rarity_note": "The value reveal treats this as public heritage context, not as a sale estimate.",
    }


def build_records(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = fetch_wikidata_records(config)
    records = []
    prefix = slugify(config["display_name"])
    for idx, qid in enumerate(config["pinned_qids"], start=1):
        row = rows[qid]
        records.append({
            "id": f"{prefix}_{qid.lower()}",
            "source": config["source"],
            "source_record_id": qid,
            "title": row["title"],
            "title_fr": row["title_fr"],
            "title_zh": row["title_zh"],
            "artist": row["artist"],
            "date": row["date"],
            "object_type": row["object_type"] or "artwork",
            "inventory_number": row["inventory_number"],
            "image_url": row["image_url"],
            "source_url": row["source_url"],
            "description": row["description"],
            "department": config["department"],
            "room": config["room"],
            "priority": idx,
            "tier": "A" if idx <= 5 else "B" if idx <= 20 else "C",
            "selection_reason": f"pinned {config['display_name']} launch-catalog record from Wikidata collection membership",
            "raw_json": row["raw_json"],
        })
    return records


def load_snapshot(key: str) -> list[dict[str, Any]] | None:
    path = OUTPUT_DIR / f"{key}_launch_snapshot.jsonl"
    if not path.exists():
        return None
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_snapshots(records_by_museum: dict[str, list[dict[str, Any]]], summary: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, records in records_by_museum.items():
        with (OUTPUT_DIR / f"{key}_launch_snapshot.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in records:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str) + "\n")
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def backup(session: Session, museum_ids: list[str]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = BACKUP_ROOT / f"paris_curated_wave2_pre_import_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    queries = {
        "museums": "SELECT * FROM museums WHERE id = ANY(:museum_ids)",
        "artworks": "SELECT * FROM artworks WHERE museum_id = ANY(:museum_ids)",
        "memberships": "SELECT * FROM artwork_catalog_memberships WHERE museum_id = ANY(:museum_ids)",
        "localizations": "SELECT l.* FROM artwork_localizations l JOIN artworks a ON a.id=l.artwork_id WHERE a.museum_id = ANY(:museum_ids)",
        "value_reveals": "SELECT v.* FROM artwork_value_reveals v JOIN artworks a ON a.id=v.artwork_id WHERE a.museum_id = ANY(:museum_ids)",
    }
    counts = {}
    for name, sql in queries.items():
        table = {"museums": "museums", "artworks": "artworks", "memberships": "artwork_catalog_memberships", "localizations": "artwork_localizations", "value_reveals": "artwork_value_reveals"}[name]
        if not inspect(session.bind).has_table(table):
            continue
        rows = [dict(row._mapping) for row in session.execute(text(sql), {"museum_ids": museum_ids}).all()]
        counts[name] = len(rows)
        with (out / f"{name}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")
    (out / "counts.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    return out


def upsert_museum(session: Session, config: dict[str, Any], apply: bool) -> None:
    row = session.get(Museum, config["museum_id"])
    if row is None:
        raise RuntimeError(f"missing Muséofile museum row {config['museum_id']} for {config['display_name']}")
    row.experience_level = "CURATED"
    row.source_url = row.source_url or config["source_url"]


def upsert_artwork(session: Session, config: dict[str, Any], record: dict[str, Any], apply: bool) -> tuple[str, str]:
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
    row.technique = None
    row.dimensions = None
    row.image_url = record.get("image_url")
    row.priority = record["priority"]
    row.tags = [record["tier"], "paris-curated-wave2", slugify(record.get("object_type") or "artwork")]
    row.source_urls = [record["source_url"]]
    row.source = record["source"]
    row.source_record_id = record["source_record_id"]
    row.source_url = record["source_url"]
    row.last_source_sync = datetime.now(timezone.utc)
    row.raw_json = record["raw_json"]
    row.department = record["department"]
    row.object_type = record["object_type"]
    row.description = record.get("description")
    row.current_location_raw = record["room"]
    row.room = record["room"]
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
    row.visitor_priority = float(1000 - record["priority"])
    return action


def upsert_localizations(session: Session, config: dict[str, Any], artwork_id: str, record: dict[str, Any], existing: dict[tuple[str, str], ArtworkLocalization], apply: bool) -> Counter:
    counts = Counter()
    for lang_key, locale in [("en", "en"), ("fr", "fr"), ("zh", "zh-Hans")]:
        for mode in ["normal", "simple", "kids"]:
            payload = content(config, record, lang_key, mode)
            key = (artwork_id, locale, mode)
            row = existing.get(key)
            if row is None:
                row = ArtworkLocalization(artwork_id=artwork_id, locale=locale, mode=mode)
                existing[key] = row
                counts["localizations_inserted"] += 1
                if apply:
                    session.add(row)
            else:
                counts["localizations_updated"] += 1
            row.title = payload["title"]
            row.analogy = payload["analogy"]
            row.why_it_matters = payload["why_it_matters"]
            row.where_to_look = payload["where_to_look"]
            row.rarity_note = payload["rarity_note"]
            row.audio_script = None
            row.audio_url = None
            row.editorial_status = "published"
            row.reviewed_by = "ELYIO Paris curated wave 2 factual importer"
            row.updated_at = datetime.now(timezone.utc)
    return counts


def upsert_value(session: Session, config: dict[str, Any], artwork_id: str, record: dict[str, Any], existing: dict[str, ArtworkValueReveal], apply: bool) -> str:
    row = existing.get(artwork_id)
    action = "updated"
    if row is None:
        row = ArtworkValueReveal(artwork_id=artwork_id, catalog_version=CATALOG_VERSION)
        existing[artwork_id] = row
        action = "inserted"
        if apply:
            session.add(row)
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
    row.beyond_market_headline = "No ordinary market price."
    row.beyond_market_explanation = f"This belongs to the {config['display_name']} public collection context, so ELYIO does not present it as a private-market sale object."
    row.institutional_legal_context = "Public cultural heritage context; not an appraisal, insurance value, or sale estimate."
    row.optional_context = None
    row.confidence = "medium"
    row.methodology = "Launch value treatment: public cultural heritage context; no sale estimate inferred."
    row.sources = [record["source_url"]]
    row.disclaimer = "Not an appraisal, insurance value, or sale estimate."
    row.review_status = "AUTO_QA_PASSED"
    row.generated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return action


def coverage_query(session: Session) -> list[dict[str, Any]]:
    museums = [
        "louvre", "orsay", "orangerie", "versailles", "museofile_m5044", "museofile_m5043", "museofile_m5055",
        "museofile_m5005", "museofile_m5003", "museofile_m1104", "museofile_m1111", "museofile_m5025",
    ]
    rows = session.execute(text("""
        WITH active AS (
          SELECT a.id, a.museum_id
          FROM artworks a
          WHERE a.museum_id = ANY(:museum_ids)
            AND (
              a.museum_id IN ('orsay','orangerie')
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
    """), {"museum_ids": museums}).all()
    return [dict(row._mapping) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--refresh-source", action="store_true")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set")

    records_by_museum = {}
    for key, config in MUSEUM_CONFIGS.items():
        snapshot = None if args.refresh_source else load_snapshot(key)
        records = snapshot or build_records(config)
        if len(records) != 30:
            raise SystemExit(f"{key} expected 30 records, got {len(records)}")
        records_by_museum[key] = records

    engine = create_engine(database_url, pool_pre_ping=True)
    counts = Counter()
    backup_path = None
    with Session(engine, autoflush=args.apply) as session:
        museum_ids = [cfg["museum_id"] for cfg in MUSEUM_CONFIGS.values()]
        if args.apply:
            backup_path = backup(session, museum_ids)
        for key, config in MUSEUM_CONFIGS.items():
            upsert_museum(session, config, args.apply)
            records = records_by_museum[key]
            ids = [row["id"] for row in records]
            memberships = {
                row.artwork_id: row
                for row in session.query(ArtworkCatalogMembership)
                .filter(ArtworkCatalogMembership.museum_id == config["museum_id"], ArtworkCatalogMembership.catalog_version == CATALOG_VERSION)
                .all()
            }
            localizations = {
                (row.artwork_id, row.locale, row.mode): row
                for row in session.query(ArtworkLocalization).filter(ArtworkLocalization.artwork_id.in_(ids)).all()
            }
            values = {
                row.artwork_id: row
                for row in session.query(ArtworkValueReveal)
                .filter(ArtworkValueReveal.artwork_id.in_(ids), ArtworkValueReveal.catalog_version == CATALOG_VERSION)
                .all()
            }
            for record in records:
                artwork_id, artwork_action = upsert_artwork(session, config, record, args.apply)
                counts[f"{key}_artworks_{artwork_action}"] += 1
                membership_action = upsert_membership(session, config, artwork_id, record, memberships, args.apply)
                counts[f"{key}_memberships_{membership_action}"] += 1
                counts.update(upsert_localizations(session, config, artwork_id, record, localizations, args.apply))
                value_action = upsert_value(session, config, artwork_id, record, values, args.apply)
                counts[f"{key}_value_reveals_{value_action}"] += 1
            active_ids = set(ids)
            for artwork_id, row in memberships.items():
                if artwork_id not in active_ids and row.active:
                    row.active = False
                    counts[f"{key}_memberships_deactivated"] += 1
        coverage = coverage_query(session)
        if args.apply:
            session.commit()
        else:
            session.rollback()

    summary = {
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "catalog_version": CATALOG_VERSION,
        "new_museums": {key: len(records) for key, records in records_by_museum.items()},
        "counts": dict(counts),
        "coverage": coverage,
        "backup_path": str(backup_path) if backup_path else None,
    }
    write_snapshots(records_by_museum, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
