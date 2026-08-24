"""Run a small non-mutating negative-image safety benchmark."""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import time
from pathlib import Path

from dotenv import load_dotenv

try:
    from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
    from backend.app.main import REFERENCE_CACHE_DIR, recognize_with_vision
    from backend.scripts.national_gallery_recognition_benchmark import candidate, config
except ModuleNotFoundError:
    from app.adapters.national_gallery_london import NationalGalleryLondonAdapter
    from app.main import REFERENCE_CACHE_DIR, recognize_with_vision
    from scripts.national_gallery_recognition_benchmark import candidate, config


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--descriptors", required=True)
    parser.add_argument("--catalog-manifest", action="append", required=True)
    parser.add_argument("--negative-dir", required=True)
    parser.add_argument("--catalog-version", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY required")
    selected = {str(row["provider_record_id"]) for row in json.loads(Path(args.selection).read_text())["records"]}
    media = {}
    for manifest in args.catalog_manifest:
        media.update({str(row["provider_record_id"]): row for row in json.loads(Path(manifest).read_text())["records"] if row.get("status") == "READY"})
    descriptors = {str(row["provider_record_id"]): row for row in json.loads(Path(args.descriptors).read_text())["records"]}
    rows = [row for row in NationalGalleryLondonAdapter(args.snapshot).records() if row.provider_record_id in selected]
    candidates = [candidate(row, media[row.provider_record_id], True, descriptors[row.provider_record_id]) for row in rows]
    Path(REFERENCE_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    for item, row in zip(candidates, rows):
        shutil.copyfile(ROOT / media[row.provider_record_id]["files"]["reference"]["path"], Path(REFERENCE_CACHE_DIR) / f'{item["id"]}.jpg')
    runtime = config("vision_plus_asset", args.catalog_version)
    results = []
    for image_path in sorted(Path(args.negative_dir).glob("*.jpg")):
        started = time.perf_counter()
        result = recognize_with_vision(base64.b64encode(image_path.read_bytes()).decode(), "national-gallery-london", None, candidates, institution_config=runtime)
        results.append({
            "case": image_path.name, "artwork_id": result.get("artwork_id"),
            "confidence": float(result.get("confidence", 0) or 0),
            "fallback": bool(result.get("recognized_but_not_cataloged")),
            "latency_s": time.perf_counter() - started,
        })
    summary = {
        "cases": len(results),
        "false_catalog_matches": sum(bool(row["artwork_id"]) for row in results),
        "confident_false_matches": sum(bool(row["artwork_id"]) and row["confidence"] >= runtime.confidence_auto for row in results),
        "fallback_or_unresolved": sum(not row["artwork_id"] for row in results),
        "results": results,
    }
    output = Path(args.out); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
