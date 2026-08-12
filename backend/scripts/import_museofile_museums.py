from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT.parent / ".env")

from app.db import SessionLocal  # noqa: E402
from app.models import Museum  # noqa: E402

DATASET_API = "https://culture.opendatasoft.com/api/explore/v2.1/catalog/datasets/musees-de-france-base-museofile/records"
DATASET_PAGE = "https://culture.opendatasoft.com/explore/dataset/musees-de-france-base-museofile/"
SOURCE_NAME = "museofile"

CANONICAL_ID_BY_MUSEOFILE = {
    "M5031": "louvre",
    "M5060": "orsay",
    "M5030": "orangerie",
    "M5077": "versailles",
}

CURATED_IDS = {"louvre", "orsay", "orangerie"}

DISPLAY_NAME_OVERRIDES = {
    "louvre": "Musée du Louvre",
    "orsay": "Musée d'Orsay",
    "orangerie": "Musée de l'Orangerie",
    "versailles": "Château de Versailles",
    "museofile_m5044": "Musée Rodin",
    "museofile_m5043": "Musée Picasso Paris",
    "museofile_m5055": "Musée du quai Branly - Jacques Chirac",
    "museofile_m1111": "Petit Palais",
    "museofile_m1104": "Musée Carnavalet",
    "museofile_m5025": "Musée de l'Armée",
    "museofile_m5005": "Musée Guimet",
    "museofile_m5003": "Musée de Cluny",
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-") or "museum"


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def museum_id_for(row: dict[str, Any]) -> str:
    ident = row["identifiant"]
    if ident in CANONICAL_ID_BY_MUSEOFILE:
        return CANONICAL_ID_BY_MUSEOFILE[ident]
    return f"museofile_{ident.lower()}"


def display_name_for(museum_id: str, official_name: str) -> str:
    if museum_id in DISPLAY_NAME_OVERRIDES:
        return DISPLAY_NAME_OVERRIDES[museum_id]
    return official_name[:1].upper() + official_name[1:] if official_name else museum_id


def notable_terms(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("artiste", "personnage_phare", "themes", "categorie"):
        raw = row.get(key)
        if not raw:
            continue
        if isinstance(raw, list):
            values.extend(str(x).strip() for x in raw if str(x).strip())
        else:
            values.extend(part.strip() for part in re.split(r"[;,]", str(raw)) if part.strip())
    return values[:80]


def fetch_records(limit: int = 100) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = 0
    total = None
    while total is None or offset < total:
        params = urlencode({"limit": limit, "offset": offset})
        req = Request(f"{DATASET_API}?{params}", headers={"User-Agent": "ELYIO museum directory importer (contact: elyio.co)"})
        with urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        total = int(payload["total_count"])
        batch = payload["results"]
        records.extend(batch)
        offset += len(batch)
        if not batch:
            break
    return records


def upsert_records(records: list[dict[str, Any]], apply: bool) -> dict[str, int]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    db = SessionLocal()
    stats = {"records": len(records), "inserted": 0, "updated": 0, "curated": 0, "ai_guide": 0}
    try:
        existing_by_id = {row.id: row for row in db.query(Museum).all()}
        for record in records:
            mid = museum_id_for(record)
            museum = existing_by_id.get(mid)
            if museum is None:
                museum = Museum(id=mid)
                stats["inserted"] += 1
                if apply:
                    db.add(museum)
            else:
                stats["updated"] += 1

            coords = record.get("coordonnees") or {}
            official_name = record.get("nom_officiel") or record.get("identifiant")
            display_name = display_name_for(mid, official_name)
            experience = "CURATED" if mid in CURATED_IDS else "AI_GUIDE"
            if experience == "CURATED":
                stats["curated"] += 1
            else:
                stats["ai_guide"] += 1

            museum.name = display_name
            museum.lat = coords.get("lat")
            museum.lng = coords.get("lon")
            museum.geofence_radius_m = 180 if str(record.get("ville") or "").lower() == "paris" else 220
            museum.external_source = SOURCE_NAME
            museum.external_id = record.get("identifiant")
            museum.slug = slugify(display_name)
            museum.common_name = official_name
            museum.city = record.get("ville")
            museum.department = record.get("departement")
            museum.region = record.get("region")
            museum.address = " ".join(str(x).strip() for x in [record.get("adresse"), record.get("lieu")] if x).strip() or None
            museum.postal_code = record.get("code_postal")
            museum.website_url = normalize_url(record.get("url"))
            museum.collection_categories = record.get("domaine_thematique") or []
            museum.notable_terms = notable_terms(record)
            museum.source_url = DATASET_PAGE
            museum.source_updated_at = parse_date(record.get("date_de_mise_a_jour"))
            museum.raw_json = record
            museum.experience_level = experience

        if apply:
            db.commit()
            # Keep existing curated IDs marked CURATED even if a future source
            # page changes naming; this is intentionally idempotent.
            db.execute(text("update museums set experience_level = 'CURATED' where id in ('louvre','orsay','orangerie')"))
            db.commit()
        else:
            db.rollback()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write to DATABASE_URL; default is dry-run")
    parser.add_argument("--output", default="exports/museofile_museums_snapshot.jsonl")
    args = parser.parse_args()

    records = fetch_records()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    stats = upsert_records(records, apply=args.apply)
    paris = sum(1 for r in records if r.get("departement") == "Paris")
    idf = sum(1 for r in records if r.get("region") == "Ile-de-France")
    print(json.dumps({**stats, "paris": paris, "ile_de_france": idf, "source": DATASET_API, "snapshot": str(output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
