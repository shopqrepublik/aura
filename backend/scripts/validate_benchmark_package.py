"""Fail-closed integrity validation for the benchmark-only media package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise SystemExit(f"records missing or invalid in {path}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--readiness", required=True, type=Path)
    parser.add_argument("--descriptors", required=True, type=Path)
    args = parser.parse_args()

    manifest_rows = records(args.manifest)
    catalog_rows = records(args.catalog)
    readiness_rows = records(args.readiness)
    descriptor_rows = records(args.descriptors)
    if not (len(catalog_rows) == len(readiness_rows) == len(descriptor_rows) == 2559):
        raise SystemExit(
            f"candidate package count mismatch: catalog={len(catalog_rows)} "
            f"readiness={len(readiness_rows)} descriptors={len(descriptor_rows)}"
        )
    if len(manifest_rows) != 2559:
        raise SystemExit(f"benchmark manifest count mismatch: {len(manifest_rows)}")

    required: dict[str, dict] = {}
    errors: list[str] = []
    for row in manifest_rows:
        if row.get("status") != "READY":
            errors.append(f"{row.get('provider_record_id')}: status={row.get('status')}")
            continue
        for role, metadata in (row.get("files") or {}).items():
            rel = metadata.get("path")
            if not rel or rel in required:
                errors.append(f"duplicate or missing path: {rel!r}")
                continue
            required[rel] = metadata
            path = args.root / rel
            if not path.is_file():
                errors.append(f"missing {role}: {rel}")
                continue
            size, checksum = digest(path)
            if size != metadata.get("bytes") or checksum != metadata.get("sha256"):
                errors.append(f"checksum mismatch {role}: {rel}")

    actual = {
        p.relative_to(args.root).as_posix()
        for p in args.root.glob("benchmark_media/corpus_2559_v1/**/*")
        if p.is_file() and p.name != "manifest.json"
    }
    unexpected = sorted(actual - set(required))
    if unexpected:
        errors.append(f"unexpected files: {unexpected[:5]}" + (" ..." if len(unexpected) > 5 else ""))
    if errors:
        raise SystemExit("benchmark package integrity failed:\n" + "\n".join(errors))
    print(json.dumps({"catalog": 2559, "manifest_records": len(manifest_rows), "fixture_files": len(required), "status": "PASS"}))


if __name__ == "__main__":
    main()
