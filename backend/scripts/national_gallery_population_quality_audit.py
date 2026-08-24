"""Compare normalized metadata/reference quality for baseline and additions."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from PIL import Image

try:
    from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
except ModuleNotFoundError:
    from app.adapters.national_gallery_london import NationalGalleryLondonAdapter

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True); parser.add_argument("--selection", required=True)
    parser.add_argument("--manifest", action="append", required=True); parser.add_argument("--out", required=True)
    args = parser.parse_args()
    selection = json.loads(Path(args.selection).read_text(encoding="utf-8"))["records"]
    groups = {
        str(row["provider_record_id"]): (
            "ORIGINAL_170" if row["baseline_170"] else
            "WORKS_171_500" if row.get("prior_controlled") else
            "NEW_501_1000"
        )
        for row in selection
    }
    normalized = {row.provider_record_id: row for row in NationalGalleryLondonAdapter(args.snapshot, provider_record_ids=set(groups)).records()}
    media = {}
    for manifest in args.manifest:
        for row in json.loads(Path(manifest).read_text(encoding="utf-8"))["records"]:
            if row.get("status") == "READY" and row["provider_record_id"] in groups: media[row["provider_record_id"]] = row
    report = {}
    for name in ("ORIGINAL_170", "WORKS_171_500", "NEW_501_1000"):
        ids = [provider_id for provider_id, group in groups.items() if group == name]
        rows = [normalized[provider_id] for provider_id in ids]
        dimensions = []
        for provider_id in ids:
            with Image.open(ROOT / media[provider_id]["files"]["reference"]["path"]) as image:
                dimensions.append(image.size)
        def count(field): return sum(bool(getattr(row, field, None)) for row in rows)
        report[name] = {
            "records": len(rows), "title": count("title_original"), "artist": count("creator_display"),
            "date": count("date_display"), "description": count("description"), "object_type": count("object_type"),
            "department": count("department"), "accession": count("institution_record_id"),
            "source_url": count("source_url"), "media": len(dimensions),
            "median_width": statistics.median(width for width, _height in dimensions),
            "median_height": statistics.median(height for _width, height in dimensions),
            "portrait_assets": sum(height > width for width, height in dimensions),
            "landscape_assets": sum(width > height for width, height in dimensions),
            "square_assets": sum(width == height for width, height in dimensions),
            "low_resolution": sum(width < 400 or height < 300 or width * height < 180_000 for width, height in dimensions),
        }
    output = Path(args.out); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__": main()
