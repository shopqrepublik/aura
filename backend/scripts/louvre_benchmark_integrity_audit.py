#!/usr/bin/env python3
"""Audit integrity/leakage of captured Louvre benchmark rows."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "exports" / "louvre" / "recognition_benchmark" / "louvre_local_benchmark_results_2026-08-12T113731+0000.jsonl"
ASSET_AUDIT = ROOT / "exports" / "louvre" / "recognition_assets" / "louvre_recognition_asset_identity_audit.jsonl"
OUT = ROOT / "exports" / "louvre" / "recognition_benchmark" / "louvre_benchmark_integrity_audit.jsonl"
SUMMARY = ROOT / "exports" / "louvre" / "recognition_benchmark" / "louvre_benchmark_integrity_audit_summary.json"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    audit = {r["artwork_id"]: r for r in read_jsonl(ASSET_AUDIT)}
    rows = [
        r for r in read_jsonl(BENCH)
        if r.get("mode") == "hybrid_stage2" and r.get("variant") == "pristine" and r.get("vision") and not r.get("error")
    ]
    out_rows = []
    for row in rows:
        ark = row["artwork_id"]
        asset = audit.get(ark)
        status = (asset or {}).get("identity_status") or "NO_AUDITED_ASSET"
        fixture_path = ROOT / row.get("fixture_path", "")
        input_path = ROOT / row.get("input_path", "")
        identical = fixture_path.exists() and input_path.exists() and fixture_path.read_bytes() == input_path.read_bytes()
        same_source = bool(row.get("fixture_hash") and row.get("variant") == "pristine" and row.get("fixture_path") != row.get("input_path"))
        if status == "VERIFIED" and not identical and same_source:
            category = "same-source derivative"
        elif status == "VERIFIED" and identical:
            category = "same-image leakage"
        elif status != "VERIFIED":
            category = "no verified reference"
        else:
            category = "independent query + verified reference"
        out_rows.append({
            "artwork_id": ark,
            "expected_title": row.get("expected_title"),
            "department": row.get("department"),
            "tier": row.get("tier"),
            "asset_identity_status": status,
            "fixture_path": row.get("fixture_path"),
            "input_path": row.get("input_path"),
            "query_bytes_identical_to_reference": identical,
            "same_source_derivative": same_source,
            "independent_query": category == "independent query + verified reference",
            "benchmark_integrity_category": category,
            "eligible_for_visual_reference_benchmark": status == "VERIFIED" and category in {"same-source derivative", "independent query + verified reference"},
        })
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    summary = {
        "original_valid_pristine_rows": len(out_rows),
        "category_counts": dict(Counter(r["benchmark_integrity_category"] for r in out_rows)),
        "asset_status_counts": dict(Counter(r["asset_identity_status"] for r in out_rows)),
        "eligible_visual_rows": sum(1 for r in out_rows if r["eligible_for_visual_reference_benchmark"]),
        "independent_query_rows": sum(1 for r in out_rows if r["independent_query"]),
        "leakage_warning": "Current local positive benchmark uses same-source derivatives from cached reference assets, not independent museum photos. Use it for retrieval plumbing, not launch accuracy claims.",
        "jsonl": str(OUT.relative_to(ROOT)),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
