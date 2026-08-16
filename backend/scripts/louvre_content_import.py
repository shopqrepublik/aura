#!/usr/bin/env python3
"""Idempotently import approved Louvre content candidates into production tables.

Scope:
  * artwork_localizations
  * artwork_value_reveals

No Layer-1 artwork facts are overwritten. No audio bytes, RecognitionAssets,
embeddings, catalog membership changes, or Louvre image bytes are created.
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
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT / ".env")

from app.models import Artwork, ArtworkLocalization, ArtworkValueReveal  # noqa: E402


CATALOG_VERSION = "2026-08-11-v1"
CONTENT = ROOT / "exports" / "louvre" / "content"
PHASE2D = CONTENT / "phase2d"
BACKUP_ROOT = ROOT / "backups"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")


def backup_tables(session: Session) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = BACKUP_ROOT / f"louvre_content_pre_import_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    tables = [
        ("artwork_localizations", "SELECT * FROM artwork_localizations"),
        ("artwork_value_reveals", "SELECT * FROM artwork_value_reveals"),
        ("artworks_louvre", "SELECT id,museum_id,source,source_record_id,title_original FROM artworks WHERE museum_id='louvre'"),
    ]
    counts = {}
    for name, sql in tables:
        table_name = name.split("_louvre", 1)[0]
        if table_name != "artworks" and not inspect(session.bind).has_table(table_name):
            continue
        rows = [dict(row._mapping) for row in session.execute(text(sql)).all()]
        write_jsonl(out / f"{name}.jsonl", rows)
        counts[name] = len(rows)
    (out / "counts.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    return out


def content_status(record: dict[str, Any]) -> str:
    if record.get("golden_version"):
        return "reviewed"
    if record.get("review_status") == "AUTO_QA_PASSED":
        return "draft"
    return "draft"


def title_for(record: dict[str, Any], lang: str, content: dict[str, Any]) -> str | None:
    identity = record.get("identity") or {}
    loc = identity.get("title_localization") or record.get("title_localization") or {}
    if isinstance(loc, dict):
        if lang == "zh-Hans":
            return loc.get("zh-Hans") or loc.get("zh_hans") or content.get("title")
        return loc.get(lang) or content.get("title")
    return content.get("title") or identity.get("title")


def join_list(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return "\n".join(str(x) for x in value if x)
    return str(value)


def rarity_note(content: dict[str, Any]) -> str | None:
    parts = []
    for label, key in [("Context", "time_context"), ("Story", "story"), ("Significance", "rarity_significance")]:
        if content.get(key):
            parts.append(f"{label}: {content[key]}")
    return "\n\n".join(parts) if parts else None


def upsert_localization(session: Session, record: dict[str, Any], lang: str, mode: str, content: dict[str, Any], existing: dict[tuple[str, str, str], ArtworkLocalization]) -> tuple[str, int, int]:
    key = (record["artwork_id"], lang, mode)
    row = existing.get(key)
    inserted = updated = 0
    if row is None:
        row = ArtworkLocalization(artwork_id=record["artwork_id"], locale=lang, mode=mode)
        session.add(row)
        existing[key] = row
        inserted = 1
    else:
        updated = 1
    row.title = title_for(record, lang, content)
    if mode == "normal":
        row.analogy = content.get("hook")
        row.why_it_matters = join_list(content.get("why_it_matters"))
        row.where_to_look = join_list(content.get("what_to_notice"))
        row.rarity_note = rarity_note(content)
        row.audio_script = content.get("audio_script")
    elif mode == "simple":
        row.analogy = content.get("simple_mode")
        row.why_it_matters = None
        row.where_to_look = None
        row.rarity_note = None
        row.audio_script = content.get("audio_script")
    elif mode == "kids":
        row.analogy = content.get("kids_mode")
        row.why_it_matters = None
        row.where_to_look = None
        row.rarity_note = None
        row.audio_script = content.get("audio_script")
    row.editorial_status = content_status(record)
    row.updated_at = datetime.now(timezone.utc)
    return f"{lang}:{mode}", inserted, updated


def normalize_value_reveal(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("value_reveal") or {}
    mode = value.get("mode")
    out: dict[str, Any] = {
        "mode": mode,
        "aggregate_value_eligible": bool(value.get("aggregate_value_eligible")),
        "confidence": value.get("confidence"),
        "sources": value.get("sources"),
        "disclaimer": value.get("disclaimer"),
    }
    if mode == "ESTIMATED_VALUE":
        est = value.get("estimated_value") or value
        out.update({
            "estimated_value_low": est.get("low") or est.get("value_low"),
            "estimated_value_high": est.get("high") or est.get("value_high"),
            "estimated_value_currency": est.get("currency"),
            "methodology": est.get("methodology") or value.get("methodology"),
            "context_date": est.get("as_of_date") or value.get("as_of_date"),
        })
    elif mode == "MARKET_CONTEXT":
        ctx = value.get("market_context") or value
        out.update({
            "market_context_headline_number": ctx.get("headline_number"),
            "market_context_currency": ctx.get("currency"),
            "market_context_label": ctx.get("label") or value.get("label_en"),
            "market_context_explanation": ctx.get("explanation") or value.get("explanation_en"),
            "relationship_to_artwork": ctx.get("relationship_to_artwork"),
            "context_type": ctx.get("context_type"),
            "source_reference": ctx.get("source_reference"),
            "context_date": ctx.get("date"),
            "methodology": value.get("methodology"),
        })
    elif mode == "BEYOND_MARKET":
        bm = value.get("beyond_market") or value
        optional = bm.get("optional_context") or value.get("optional_numeric_context")
        out.update({
            "beyond_market_headline": bm.get("headline") or value.get("headline"),
            "beyond_market_explanation": bm.get("explanation") or value.get("explanation_en"),
            "institutional_legal_context": bm.get("institutional_legal_context") or value.get("institutional_legal_context"),
            "optional_context": json.dumps(optional, ensure_ascii=False, separators=(",", ":")) if isinstance(optional, dict) else optional,
        })
    return out


def upsert_value_reveal(session: Session, record: dict[str, Any], existing: dict[tuple[str, str], ArtworkValueReveal]) -> tuple[int, int]:
    value = normalize_value_reveal(record)
    if value.get("mode") not in {"ESTIMATED_VALUE", "MARKET_CONTEXT", "BEYOND_MARKET"}:
        return 0, 0
    key = (record["artwork_id"], CATALOG_VERSION)
    row = existing.get(key)
    inserted = updated = 0
    if row is None:
        row = ArtworkValueReveal(artwork_id=record["artwork_id"], catalog_version=CATALOG_VERSION, mode=value["mode"])
        session.add(row)
        existing[key] = row
        inserted = 1
    else:
        updated = 1
    row.mode = value["mode"]
    row.aggregate_value_eligible = value.get("mode") == "ESTIMATED_VALUE" and value.get("aggregate_value_eligible") is True
    row.estimated_value_low = value.get("estimated_value_low")
    row.estimated_value_high = value.get("estimated_value_high")
    row.estimated_value_currency = value.get("estimated_value_currency")
    row.market_context_headline_number = value.get("market_context_headline_number")
    row.market_context_currency = value.get("market_context_currency")
    row.market_context_label = value.get("market_context_label")
    row.market_context_explanation = value.get("market_context_explanation")
    row.relationship_to_artwork = value.get("relationship_to_artwork")
    row.context_type = value.get("context_type")
    row.source_reference = value.get("source_reference")
    row.context_date = value.get("context_date")
    row.beyond_market_headline = value.get("beyond_market_headline")
    row.beyond_market_explanation = value.get("beyond_market_explanation")
    row.institutional_legal_context = value.get("institutional_legal_context")
    row.optional_context = value.get("optional_context")
    row.confidence = value.get("confidence")
    row.methodology = value.get("methodology")
    row.sources = value.get("sources") or []
    row.disclaimer = value.get("disclaimer") or "Not an appraisal, insurance value, or sale estimate."
    row.review_status = "NEEDS_HUMAN_REVIEW" if not record.get("golden_version") and record.get("visitor_tier") == "B" else "DRAFT"
    row.generated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return inserted, updated


def records_to_import(include_batches: list[str]) -> list[dict[str, Any]]:
    rows = read_jsonl(CONTENT / "louvre_golden20_final.jsonl")
    for batch in include_batches:
        rows.extend(read_jsonl(PHASE2D / batch / "artworks.jsonl"))
    seen = set()
    unique = []
    for row in rows:
        if row["artwork_id"] in seen:
            raise SystemExit(f"duplicate content artwork_id {row['artwork_id']}")
        seen.add(row["artwork_id"])
        unique.append(row)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", default="batch001,batch002")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set")
    batches = [x.strip() for x in args.batches.split(",") if x.strip()]
    records = records_to_import(batches)
    engine = create_engine(database_url)
    counts = Counter()
    missing = []
    with Session(engine) as session:
        record_ids = [r["artwork_id"] for r in records]
        artwork_ids = {row.id for row in session.query(Artwork.id).filter(Artwork.id.in_(record_ids)).all()}
        missing = [r["artwork_id"] for r in records if r["artwork_id"] not in artwork_ids]
        if missing:
            raise SystemExit(f"missing production artworks: {missing[:10]} ({len(missing)})")
        existing_loc_rows = (
            session.query(ArtworkLocalization)
            .filter(ArtworkLocalization.artwork_id.in_(record_ids))
            .all()
        )
        existing_localizations = {
            (row.artwork_id, row.locale, row.mode): row
            for row in existing_loc_rows
        }
        existing_value_rows = (
            session.query(ArtworkValueReveal)
            .filter(
                ArtworkValueReveal.artwork_id.in_(record_ids),
                ArtworkValueReveal.catalog_version == CATALOG_VERSION,
            )
            .all()
        )
        existing_values = {
            (row.artwork_id, row.catalog_version): row
            for row in existing_value_rows
        }
        backup_path = None
        if args.apply:
            backup_path = backup_tables(session)
        for record in records:
            for lang, content in (record.get("content") or {}).items():
                if lang not in {"en", "fr", "zh-Hans"}:
                    continue
                for mode in ["normal", "simple", "kids"]:
                    _key, ins, upd = upsert_localization(session, record, lang, mode, content, existing_localizations)
                    counts["localizations_inserted"] += ins
                    counts["localizations_updated"] += upd
            ins, upd = upsert_value_reveal(session, record, existing_values)
            counts["value_reveals_inserted"] += ins
            counts["value_reveals_updated"] += upd
        if args.apply:
            session.commit()
        else:
            session.rollback()
    summary = {
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "catalog_version": CATALOG_VERSION,
        "records": len(records),
        "batches": batches,
        "missing_artworks": len(missing),
        **dict(counts),
        "expected_localization_rows": len(records) * 3 * 3,
        "production_writes_committed": bool(args.apply),
        "backup_path": str(backup_path.relative_to(ROOT)) if args.apply and backup_path else None,
        "safety": {
            "layer1_artwork_fact_updates": 0,
            "catalog_membership_changes": 0,
            "recognition_assets_created": 0,
            "embeddings_created": 0,
            "tts_audio_bytes_generated": 0,
            "louvre_image_bytes_fetched": 0,
        },
    }
    out = CONTENT / "louvre_content_import_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
