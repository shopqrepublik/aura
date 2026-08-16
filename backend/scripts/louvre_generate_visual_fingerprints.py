#!/usr/bin/env python3
"""Generate evidence-supported visual fingerprints from Louvre text metadata.

This does not use or fetch images. The model receives only existing recognition
search document text and must extract concise observable descriptors. Output is
reviewable local metadata for retrieval, not visitor editorial copy.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT / ".env")


SEARCH = ROOT / "exports" / "louvre" / "recognition_search"
DOCS = SEARCH / "louvre_recognition_search_documents.jsonl"
OUT = SEARCH / "louvre_visual_fingerprints.jsonl"
MODEL = os.environ.get("OPENAI_RECOGNITION_TEXT_MODEL", os.environ.get("OPENAI_RECOGNITION_MODEL", "gpt-4o"))
VERSION = "louvre_visual_fingerprint_v0.1"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def compact_doc(row: dict) -> dict:
    text = row["document"]
    if len(text) > 6000:
        text = text[:6000].rsplit(" ", 1)[0]
    return {
        "artwork_id": row["artwork_id"],
        "title": row.get("title"),
        "artist": row.get("artist"),
        "department": row.get("department"),
        "metadata": text,
    }


def generate_batch(client, batch: list[dict]) -> list[dict]:
    system_prompt = (
        "You create recognition search fingerprints for a museum app. "
        "Use ONLY the provided metadata. Do not infer unseen colors, pose, or "
        "details unless supported by the metadata. Translate useful French "
        "museum terms into concise English search language. For sparse records, "
        "return a sparse but honest fingerprint. Respond as one JSON object: "
        '{"items":[{"artwork_id":"...","visual_fingerprint":"short phrase",'
        '"object_terms":["..."],"material_terms":["..."],"subject_terms":["..."],'
        '"distinctive_terms":["..."],"inscription_terms":["..."],"evidence_level":"RICH|SPARSE"}]}'
    )
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=3500,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps({"items": [compact_doc(row) for row in batch]}, ensure_ascii=False)},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    items = data.get("items") or []
    by_id = {item.get("artwork_id"): item for item in items}
    output = []
    for row in batch:
        item = by_id.get(row["artwork_id"]) or {}
        output.append({
            "artwork_id": row["artwork_id"],
            "catalog_version": row.get("catalog_version"),
            "fingerprint_version": VERSION,
            "model": MODEL,
            "visual_fingerprint": item.get("visual_fingerprint") or row.get("visual_fingerprint") or "",
            "object_terms": item.get("object_terms") or [],
            "material_terms": item.get("material_terms") or [],
            "subject_terms": item.get("subject_terms") or [],
            "distinctive_terms": item.get("distinctive_terms") or [],
            "inscription_terms": item.get("inscription_terms") or [],
            "evidence_level": item.get("evidence_level") or "SPARSE",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    docs = read_jsonl(DOCS)
    if args.limit:
        docs = docs[:args.limit]
    existing = read_jsonl(OUT) if args.resume else []
    done = {row["artwork_id"] for row in existing}
    pending = [row for row in docs if row["artwork_id"] not in done]
    if not args.apply:
        print(json.dumps({"mode": "PLAN_ONLY", "documents": len(docs), "pending": len(pending), "model": MODEL}, indent=2))
        return
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    rows = list(existing)
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start:start + args.batch_size]
        rows.extend(generate_batch(client, batch))
        write_jsonl(OUT, rows)
        print(json.dumps({"fingerprints": len(rows), "total": len(docs), "model": MODEL}))
        time.sleep(0.25)
    manifest = {
        "fingerprint_version": VERSION,
        "model": MODEL,
        "documents": len(docs),
        "fingerprints": len(rows),
        "output": str(OUT.relative_to(ROOT)),
        "image_bytes_used": 0,
        "louvre_image_bytes_fetched": 0,
    }
    (SEARCH / "louvre_visual_fingerprints_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
