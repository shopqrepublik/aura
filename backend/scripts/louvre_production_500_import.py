#!/usr/bin/env python3
"""Import the frozen Louvre Visitor 500 Layer-1 catalog into production DB.

Idempotent and local-data-only:
  * no Louvre metadata fetches
  * no Louvre image-byte fetches
  * no external image downloads
  * no embeddings
  * RecognitionAsset rows are metadata-only references to already-approved
    Commons assets from the frozen manifest.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, inspect
from sqlalchemy.orm import Session


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT / ".env")

from app.models import (  # noqa: E402
    Artwork,
    ArtworkCatalogMembership,
    LouvreImageReference,
    Museum,
    RecognitionAsset,
)


CATALOG_VERSION = "2026-08-11-v1"
CATALOG_PATH = ROOT / "exports" / "louvre" / "louvre_visitor_500_final.jsonl"
COMMONS_PATH = ROOT / "exports" / "louvre" / "louvre_wikimedia_asset_manifest_final.jsonl"
RAW_DIR = ROOT / "backend" / "data" / "louvre" / "raw"
NORM_DIR = ROOT / "backend" / "data" / "louvre" / "normalized"
BACKUP_ROOT = ROOT / "backups"

EXPECTED_FINAL = 500
EXPECTED_CURRENT_SEED = 261
EXPECTED_REMAINING = 277


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")


def require_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not set")
    return url


def load_normalized(ark: str) -> dict[str, Any]:
    path = NORM_DIR / f"{ark}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_raw(ark: str) -> dict[str, Any] | None:
    path = RAW_DIR / f"{ark}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def backup_tables(session: Session) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = BACKUP_ROOT / f"louvre_500_pre_import_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    tables = [
        ("museums", "SELECT * FROM museums"),
        ("artworks", "SELECT * FROM artworks WHERE museum_id IN ('louvre','orsay','orangerie')"),
        ("louvre_image_references", "SELECT * FROM louvre_image_references"),
        ("recognition_assets", "SELECT * FROM recognition_assets"),
        ("artwork_embeddings", "SELECT * FROM artwork_embeddings"),
        ("artwork_localizations", "SELECT * FROM artwork_localizations"),
        ("artwork_value_reveals", "SELECT * FROM artwork_value_reveals"),
        ("artwork_catalog_memberships", "SELECT * FROM artwork_catalog_memberships"),
    ]
    from sqlalchemy import text

    counts = {}
    for name, sql in tables:
        if not inspect(session.bind).has_table(name):
            continue
        rows = [dict(row._mapping) for row in session.execute(text(sql)).all()]
        write_jsonl(out / f"{name}.jsonl", rows)
        counts[name] = len(rows)
    (out / "counts.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    return out


def artist_from(record: dict[str, Any], norm: dict[str, Any]) -> str | None:
    if record.get("artist"):
        return record["artist"]
    labels = norm.get("creator_labels") or []
    if labels:
        return next((x for x in labels if x not in {"France", "Italie", "Pays-Bas"}), None)
    return None


def copy_artwork_fields(row: Artwork, record: dict[str, Any], norm: dict[str, Any], raw: dict[str, Any] | None, has_asset: bool) -> None:
    ark = record["ark_id"]
    row.museum_id = "louvre"
    row.artist = artist_from(record, norm)
    row.title_original = record["title"]
    row.title_complement = norm.get("title_complement")
    row.year = norm.get("display_date_created") or record.get("date_display")
    row.inventory_number = record.get("inventory_number") or norm.get("inventory_number")
    row.hall = record.get("room") or norm.get("room")
    row.technique = norm.get("materials_and_techniques")
    row.dimensions = norm.get("dimensions_display") or norm.get("dimensions_raw")
    # Do not store Louvre/RMN image URLs in image_url; verifier must only use
    # RecognitionAsset-approved external references.
    row.image_url = None
    row.priority = max(1, 500 - int(float(record.get("visitor_priority_score") or 0)))
    row.tags = [
        record.get("visitor_tier"),
        record.get("department"),
        norm.get("object_type") or record.get("object_type"),
        record.get("room"),
    ]
    row.tags = [x for x in row.tags if x]
    row.source_urls = [record["source_url"]]
    row.source = "louvre"
    row.source_record_id = ark
    row.source_url = record["source_url"]
    row.last_source_sync = datetime.now(timezone.utc)
    row.raw_json = raw
    row.department = record.get("department") or norm.get("department")
    row.collection = norm.get("collection") or norm.get("department")
    row.object_type = norm.get("object_type") or (norm.get("object_types") or [None])[0]
    row.materials_and_techniques = norm.get("materials_and_techniques")
    row.description = norm.get("description")
    row.provenance = norm.get("provenance")
    row.object_history = norm.get("object_history")
    row.historical_context = norm.get("historical_context")
    row.current_location_raw = record.get("current_location") or norm.get("current_location_raw")
    row.room = record.get("room") or norm.get("room")
    row.creator_wikidata_qid = norm.get("creator_wikidata_qid")
    row.creator_raw = norm.get("creator_raw") or norm.get("creator_labels")
    row.creator_labels = norm.get("creator_labels")
    row.display_status = "ON_DISPLAY"
    row.display_status_confidence = record.get("display_status_confidence") or norm.get("display_status_confidence")
    row.display_status_reason = norm.get("display_status_reason")
    row.metadata_status = record.get("metadata_status") or norm.get("metadata_status")
    row.recognition_status = "VISION_PLUS_ASSET" if has_asset else "VISION_READY"
    row.rights_status = record.get("rights_status") or "UNKNOWN"
    row.rights_review_required = row.rights_status != "APPROVED"


def upsert_louvre_image_references(session: Session, artwork_id: str, norm: dict[str, Any]) -> tuple[int, int]:
    refs = norm.get("image_references") or []
    existing = {
        (r.url_image, r.position): r
        for r in session.query(LouvreImageReference).filter(LouvreImageReference.artwork_id == artwork_id).all()
    }
    inserted = updated = 0
    for ref in refs:
        url = ref.get("url_image")
        if not url:
            continue
        key = (url, ref.get("position"))
        row = existing.get(key)
        if row is None:
            row = LouvreImageReference(artwork_id=artwork_id, url_image=url, position=ref.get("position"))
            session.add(row)
            inserted += 1
        else:
            updated += 1
        row.url_thumbnail = ref.get("url_thumbnail")
        row.image_copyright = ref.get("image_copyright")
        row.image_credit = ref.get("image_credit")
        row.rights_status = ref.get("rights_status")
        row.rights_review_required = True
        row.rights_reason = ref.get("rights_reason")
        row.image_source = "louvre_collections"
        row.image_type = ref.get("image_type")
        row.fetched = False
    return inserted, updated


def rights_eligible(asset: dict[str, Any]) -> bool:
    if asset.get("rights_status") != "APPROVED":
        return False
    license_name = (asset.get("license") or "").lower()
    return any(token in license_name for token in ["public domain", "cc0", "cc by", "cc-by"])


def upsert_recognition_asset(session: Session, artwork_id: str, asset: dict[str, Any]) -> tuple[int, int]:
    wikimedia_file = asset.get("wikimedia_file")
    source_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{wikimedia_file}" if wikimedia_file else asset.get("direct_media_url") or asset.get("wikimedia_page_url")
    if not source_url or not rights_eligible(asset):
        return 0, 0
    row = (
        session.query(RecognitionAsset)
        .filter(RecognitionAsset.artwork_id == artwork_id, RecognitionAsset.source == "wikimedia_commons")
        .order_by(RecognitionAsset.updated_at.desc())
        .first()
    )
    inserted = updated = 0
    if row is None:
        row = RecognitionAsset(artwork_id=artwork_id, source="wikimedia_commons", source_url=source_url)
        session.add(row)
        inserted = 1
    else:
        updated = 1
    row.source_url = source_url
    row.license = asset.get("license")
    row.attribution = asset.get("attribution")
    row.rights_status = "public_domain" if (asset.get("license") or "").lower() in {"public domain", "cc0"} else "cc_licensed"
    row.ai_tdm_eligible = True
    row.embedding_eligible = True
    row.local_storage_status = "not_fetched"
    row.updated_at = datetime.now(timezone.utc)
    return inserted, updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    catalog = read_jsonl(CATALOG_PATH)
    commons = {row["ark_id"]: row for row in read_jsonl(COMMONS_PATH)}
    if len(catalog) != EXPECTED_FINAL or len({r["ark_id"] for r in catalog}) != EXPECTED_FINAL:
        raise SystemExit("frozen catalog is not exactly 500 unique ARKs")
    if any(r.get("display_status") != "ON_DISPLAY" for r in catalog):
        raise SystemExit("frozen catalog contains non-ON_DISPLAY rows")

    engine = create_engine(require_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        before_counts = dict(
            session.query(Artwork.museum_id, func.count(Artwork.id)).group_by(Artwork.museum_id).all()
        )
        backup_path = backup_tables(session) if args.apply else None
        museum = session.get(Museum, "louvre")
        if museum is None:
            museum = Museum(id="louvre", name="Musée du Louvre", lat=48.8606, lng=2.3376, geofence_radius_m=350)
            if args.apply:
                session.add(museum)

        existing_louvre = {
            row.source_record_id: row
            for row in session.query(Artwork).filter(Artwork.museum_id == "louvre").all()
            if row.source_record_id
        }
        frozen_ids = {row["ark_id"] for row in catalog}
        production_ids = set(existing_louvre)
        production_extra = sorted(production_ids - frozen_ids)
        frozen_missing = sorted(frozen_ids - production_ids)
        new_rows = updates = 0
        image_inserted = image_updated = 0
        asset_inserted = asset_updated = 0
        membership_inserted = membership_updated = 0
        missing_norm = []
        for record in catalog:
            ark = record["ark_id"]
            norm = load_normalized(ark)
            raw = load_raw(ark)
            if not norm:
                missing_norm.append(ark)
                continue
            asset = commons.get(ark) or {}
            has_asset = rights_eligible(asset)
            row = existing_louvre.get(ark)
            if row is None:
                row = Artwork(id=ark)
                new_rows += 1
            else:
                updates += 1
            copy_artwork_fields(row, record, norm, raw, has_asset)
            if args.apply:
                session.merge(row)
                session.flush()
                ins, upd = upsert_louvre_image_references(session, row.id, norm)
                image_inserted += ins
                image_updated += upd
                ins, upd = upsert_recognition_asset(session, row.id, asset)
                asset_inserted += ins
                asset_updated += upd
                membership = (
                    session.query(ArtworkCatalogMembership)
                    .filter(
                        ArtworkCatalogMembership.artwork_id == row.id,
                        ArtworkCatalogMembership.catalog_version == CATALOG_VERSION,
                    )
                    .first()
                )
                if membership is None:
                    membership = ArtworkCatalogMembership(artwork_id=row.id, museum_id="louvre", catalog_version=CATALOG_VERSION)
                    session.add(membership)
                    membership_inserted += 1
                else:
                    membership_updated += 1
                membership.museum_id = "louvre"
                membership.active = True
                membership.tier = record.get("visitor_tier")
                membership.visitor_priority = float(record.get("visitor_priority_score") or 0)

        if missing_norm:
            raise SystemExit(f"missing local normalized records for frozen catalog: {missing_norm[:10]} total={len(missing_norm)}")

        if not args.apply:
            session.rollback()
        else:
            session.commit()

        after_counts = dict(
            session.query(Artwork.museum_id, func.count(Artwork.id)).group_by(Artwork.museum_id).all()
        )
        louvre_status = Counter(
            status for status, _count in session.query(Artwork.recognition_status, func.count(Artwork.id)).filter(Artwork.museum_id == "louvre").group_by(Artwork.recognition_status).all()
            for _ in range(_count)
        )
        report = {
            "mode": "APPLY" if args.apply else "DRY_RUN",
            "backup_path": str(backup_path.relative_to(ROOT)) if backup_path else None,
            "catalog_version": CATALOG_VERSION,
            "before_artworks_by_museum": before_counts,
            "after_artworks_by_museum": after_counts,
            "frozen_production_overlap": len(production_ids & frozen_ids),
            "production_extra_not_in_frozen": len(production_extra),
            "frozen_missing_from_production": len(frozen_missing),
            "production_extra_sample": production_extra[:20],
            "frozen_missing_sample": frozen_missing[:20],
            "expected_seed_before": EXPECTED_CURRENT_SEED,
            "expected_new_frozen_artworks": EXPECTED_REMAINING,
            "expected_louvre_artworks_after": len(production_ids | frozen_ids),
            "expected_active_memberships": EXPECTED_FINAL,
            "new_rows": new_rows,
            "updates": updates,
            "extra_preserved_artworks": len(production_extra),
            "louvre_image_references_inserted": image_inserted,
            "louvre_image_references_updated": image_updated,
            "recognition_assets_inserted": asset_inserted,
            "recognition_assets_updated": asset_updated,
            "catalog_memberships_inserted": membership_inserted,
            "catalog_memberships_updated": membership_updated,
            "approved_commons_assets_in_manifest": sum(1 for row in commons.values() if rights_eligible(row)),
            "louvre_recognition_status_distribution": dict(louvre_status),
            "image_bytes_fetched": 0,
            "embeddings_created": 0,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
