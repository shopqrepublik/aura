"""Build versioned, non-image recognition descriptors from an approved corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from backend.app.visual_retrieval import DESCRIPTOR_VERSION, descriptor_from_image
except ModuleNotFoundError:
    from app.visual_retrieval import DESCRIPTOR_VERSION, descriptor_from_image
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    selected = {
        str(row["provider_record_id"])
        for row in json.loads(Path(args.selection).read_text(encoding="utf-8"))["records"]
    }
    records: dict[str, dict] = {}
    for path in args.manifest:
        for row in json.loads(Path(path).read_text(encoding="utf-8"))["records"]:
            if row.get("status") == "READY" and str(row["provider_record_id"]) in selected:
                records[str(row["provider_record_id"])] = row
    if set(records) != selected:
        raise SystemExit(f"descriptor input parity failed: selected={len(selected)} ready={len(records)}")
    output = []
    for provider_id in sorted(records):
        row = records[provider_id]
        path = ROOT / row["files"]["reference"]["path"]
        with Image.open(path) as image:
            values = descriptor_from_image(image)
        output.append({
            "provider_record_id": provider_id,
            "version": DESCRIPTOR_VERSION,
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "values": values,
        })
    payload = {
        "schema_version": 1,
        "descriptor_version": DESCRIPTOR_VERSION,
        "catalog_version": "ng-controlled-500-v2-retrieval",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": output,
    }
    Path(args.out).write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(output), "descriptor_version": DESCRIPTOR_VERSION}))


if __name__ == "__main__":
    main()
