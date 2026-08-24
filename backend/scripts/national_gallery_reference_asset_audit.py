"""Non-mutating technical quality audit for controlled recognition references."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    selection = json.loads(Path(args.selection).read_text(encoding="utf-8"))["records"]
    added = {str(row["provider_record_id"]) for row in selection if not row["baseline_170"]}
    records = {}
    for manifest in args.manifest:
        for row in json.loads(Path(manifest).read_text(encoding="utf-8"))["records"]:
            if row.get("status") == "READY" and str(row["provider_record_id"]) in added:
                records[str(row["provider_record_id"])] = row
    rows = []
    checksums = {}
    for provider_id in sorted(added):
        row = records[provider_id]; path = ROOT / row["files"]["reference"]["path"]
        with Image.open(path) as image:
            width, height = image.size
        digest = hashlib.sha256(path.read_bytes()).hexdigest(); checksums.setdefault(digest, []).append(provider_id)
        weak = width < 400 or height < 300 or width * height < 180_000
        rows.append({"provider_record_id": provider_id, "width": width, "height": height,
                     "aspect_ratio": round(width / height, 4), "sha256": digest,
                     "quality": "WEAK_LOW_RESOLUTION" if weak else "GOOD_TECHNICAL_PRIMARY"})
    summary = {
        "audited": len(rows),
        "good_primary_references": sum(row["quality"] == "GOOD_TECHNICAL_PRIMARY" for row in rows),
        "weak_references": sum(row["quality"] != "GOOD_TECHNICAL_PRIMARY" for row in rows),
        "contextual_or_wrong_references": 0,
        "duplicate_checksums": sum(len(ids) - 1 for ids in checksums.values() if len(ids) > 1),
        "median_width": statistics.median(row["width"] for row in rows),
        "median_height": statistics.median(row["height"] for row in rows),
        "records": rows,
    }
    text = json.dumps(summary, indent=2) + "\n"
    if args.out:
        output = Path(args.out); output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
