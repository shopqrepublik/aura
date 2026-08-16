#!/usr/bin/env python3
"""Build recognition search documents and text embeddings for Louvre Visitor 500.

Inputs are local/production-approved metadata only:
  * active DB Louvre Visitor 500 catalog rows
  * approved RecognitionAsset metadata already stored in DB/catalog mapping
  * frozen Wikimedia asset manifest metadata

No Louvre image bytes are fetched. No remote image URLs are opened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT / ".env")

from app.catalog import get_recognition_candidates  # noqa: E402


CATALOG_VERSION = "2026-08-11-v1"
OUT = ROOT / "exports" / "louvre" / "recognition_search"
COMMONS_FINAL = ROOT / "exports" / "louvre" / "louvre_wikimedia_asset_manifest_final.jsonl"
CATALOG_FINAL = ROOT / "exports" / "louvre" / "louvre_visitor_500_final.jsonl"
FINGERPRINTS = OUT / "louvre_visual_fingerprints.jsonl"
EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
INDEX_VERSION = "louvre_recognition_search_v0.1"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def compact(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ; ".join(compact(x) for x in value if x)
    if isinstance(value, dict):
        return " ; ".join(f"{k}: {compact(v)}" for k, v in value.items() if v)
    text = str(value).replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def clip(text: str, limit: int) -> str:
    text = compact(text)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0]


def filename_terms(url: str | None) -> str:
    if not url:
        return ""
    tail = url.rsplit("/", 1)[-1]
    tail = tail.replace("_", " ").replace("%20", " ")
    return re.sub(r"\s+", " ", tail).strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def commons_by_ark() -> dict[str, list[dict]]:
    rows = read_jsonl(COMMONS_FINAL)
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.get("ark_id") or row.get("artwork_id"), []).append(row)
    return grouped


def catalog_by_ark() -> dict[str, dict]:
    return {row["ark_id"]: row for row in read_jsonl(CATALOG_FINAL)}


def fingerprints_by_ark() -> dict[str, dict]:
    return {row["artwork_id"]: row for row in read_jsonl(FINGERPRINTS)}


def build_document(candidate: dict, commons_rows: list[dict], catalog_row: dict | None = None, fingerprint_row: dict | None = None) -> dict:
    catalog_row = catalog_row or {}
    fingerprint_row = fingerprint_row or {}
    ark = candidate["id"]
    title = compact(candidate.get("title"))
    artist = compact(candidate.get("artist") or candidate.get("creator_labels") or candidate.get("creator_raw"))
    fields = {
        "canonical_title": title,
        "creator": artist,
        "object_type": compact(candidate.get("object_type")),
        "period_or_date": compact(candidate.get("year")),
        "materials": compact(candidate.get("materials_and_techniques") or candidate.get("technique")),
        "dimensions": compact(candidate.get("dimensions")),
        "department": compact(candidate.get("department")),
        "room": compact(candidate.get("room") or candidate.get("hall")),
        "location": compact(candidate.get("current_location_raw")),
        "subject_description": clip(candidate.get("description"), 1600),
        "historical_context": clip(candidate.get("historical_context"), 500),
        "object_history": clip(candidate.get("object_history"), 500),
        "provenance": clip(candidate.get("provenance"), 350),
        "inventory_number": compact(candidate.get("inventory_number")),
        "source_record_id": compact(candidate.get("source_record_id") or ark),
        "tags": compact(candidate.get("tags")),
        "visitor_tier": compact(catalog_row.get("visitor_tier")),
        "visitor_priority": compact(catalog_row.get("visitor_priority_score")),
        "selection_reason": clip(catalog_row.get("selection_reason"), 900),
        "recognition_visual_fingerprint": clip(fingerprint_row.get("visual_fingerprint"), 900),
        "recognition_object_terms": compact(fingerprint_row.get("object_terms")),
        "recognition_material_terms": compact(fingerprint_row.get("material_terms")),
        "recognition_subject_terms": compact(fingerprint_row.get("subject_terms")),
        "recognition_distinctive_terms": compact(fingerprint_row.get("distinctive_terms")),
        "recognition_inscription_terms": compact(fingerprint_row.get("inscription_terms")),
        # Asset filenames are deliberately excluded from the search document
        # until asset identity is re-audited. A benchmark pass found several
        # rights-approved Commons files mapped to the wrong Louvre object; that
        # should not contaminate primary retrieval.
        "approved_asset_match_evidence": compact([
            f"{row.get('match_method')} {row.get('match_confidence')} {row.get('rights_status')}"
            for row in commons_rows
            if row.get("rights_status") == "APPROVED"
        ]),
    }
    fingerprint_parts = [
        fields["object_type"],
        fields["materials"],
        fields["subject_description"],
        fields["department"],
        fields["room"],
    ]
    visual_fingerprint = compact(fingerprint_parts)
    search_document = "\n".join(
        f"{key}: {value}" for key, value in fields.items() if value
    )
    search_document += f"\nvisual_fingerprint: {visual_fingerprint}"
    search_document = clip(search_document, 12000)
    return {
        "artwork_id": ark,
        "catalog_version": CATALOG_VERSION,
        "index_version": INDEX_VERSION,
        "title": title,
        "artist": artist or None,
        "department": fields["department"],
        "room": fields["room"],
        "document": search_document,
        "visual_fingerprint": visual_fingerprint,
        "document_hash": sha256_text(search_document),
        "embedding_model": EMBEDDING_MODEL,
    }


def embed_documents(rows: list[dict], batch_size: int) -> list[dict]:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    embedded = []
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        resp = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[row["document"] for row in batch],
            encoding_format="float",
        )
        for row, item in zip(batch, resp.data):
            embedded.append({
                **row,
                "embedding": item.embedding,
                "embedded_at": datetime.now(timezone.utc).isoformat(),
            })
        print(json.dumps({"embedded": len(embedded), "total": len(rows), "model": EMBEDDING_MODEL}))
    return embedded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="call OpenAI embeddings API; default writes documents only")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set")
    engine = create_engine(database_url)
    with Session(engine) as session:
        candidates = get_recognition_candidates(session, "louvre", CATALOG_VERSION)
    if len(candidates) != 500:
        raise SystemExit(f"expected 500 active Louvre candidates, got {len(candidates)}")

    commons = commons_by_ark()
    catalog = catalog_by_ark()
    fingerprints = fingerprints_by_ark()
    docs = [
        build_document(candidate, commons.get(candidate["id"], []), catalog.get(candidate["id"]), fingerprints.get(candidate["id"]))
        for candidate in candidates
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    docs_path = OUT / "louvre_recognition_search_documents.jsonl"
    write_jsonl(docs_path, docs)
    output = {
        "catalog_version": CATALOG_VERSION,
        "index_version": INDEX_VERSION,
        "documents": len(docs),
        "embedding_model": EMBEDDING_MODEL,
        "documents_path": str(docs_path.relative_to(ROOT)),
        "openai_embeddings_called": False,
    }
    if args.apply:
        embedded = embed_documents(docs, args.batch_size)
        embed_path = OUT / "louvre_recognition_search_index.jsonl"
        write_jsonl(embed_path, embedded)
        output.update({
            "openai_embeddings_called": True,
            "embeddings": len(embedded),
            "index_path": str(embed_path.relative_to(ROOT)),
        })
    (OUT / "louvre_recognition_search_manifest.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
