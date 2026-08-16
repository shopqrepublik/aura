#!/usr/bin/env python3
"""Measure Louvre candidate-retrieval recall from captured Stage1 outputs.

This is intentionally cheaper than a full recognition benchmark: it reuses
previously captured OpenAI Stage1 visual evidence, reruns the local DB
candidate ranker against the active Louvre Visitor 500, and reports whether
the expected artwork reaches top-N before Stage2.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT / ".env")

from app.catalog import get_recognition_candidates  # noqa: E402
from app.main import rank_catalog_candidates  # noqa: E402


OUT = ROOT / "exports" / "louvre" / "recognition_benchmark"
DEFAULT_RESULTS = OUT / "louvre_local_benchmark_results_2026-08-12T113731+0000.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def now_slug() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(":", "")


def rank_position(expected_id: str, ranked: list[dict]) -> int | None:
    for idx, row in enumerate(ranked, 1):
        candidate = row.get("candidate") or {}
        if candidate.get("id") == expected_id:
            return idx
    return None


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    by_department: dict[str, Counter] = defaultdict(Counter)
    by_tier: dict[str, Counter] = defaultdict(Counter)
    counters = Counter()
    for row in rows:
        pos = row.get("rank_position")
        for n in [1, 3, 5, 10, 20]:
            if pos is not None and pos <= n:
                counters[f"top{n}"] += 1
        by_department[row.get("department") or "UNKNOWN"]["total"] += 1
        by_tier[row.get("tier") or "UNKNOWN"]["total"] += 1
        for n in [1, 3, 5, 10, 20]:
            if pos is not None and pos <= n:
                by_department[row.get("department") or "UNKNOWN"][f"top{n}"] += 1
                by_tier[row.get("tier") or "UNKNOWN"][f"top{n}"] += 1
    return {
        "total": total,
        **{
            f"top{n}_recall": counters[f"top{n}"] / total if total else 0
            for n in [1, 3, 5, 10, 20]
        },
        "top_counts": {f"top{n}": counters[f"top{n}"] for n in [1, 3, 5, 10, 20]},
        "misses_top20": sum(1 for row in rows if row.get("rank_position") is None or row["rank_position"] > 20),
        "by_department": {
            key: {
                **dict(counter),
                **{
                    f"top{n}_recall": counter[f"top{n}"] / counter["total"] if counter["total"] else 0
                    for n in [1, 3, 5, 10, 20]
                },
            }
            for key, counter in sorted(by_department.items())
        },
        "by_tier": {
            key: {
                **dict(counter),
                **{
                    f"top{n}_recall": counter[f"top{n}"] / counter["total"] if counter["total"] else 0
                    for n in [1, 3, 5, 10, 20]
                },
            }
            for key, counter in sorted(by_tier.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--variant", default="pristine")
    parser.add_argument("--mode", default="hybrid_stage2")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set")

    result_rows = [
        row for row in read_jsonl(Path(args.results))
        if row.get("mode") == args.mode and row.get("variant") == args.variant and row.get("vision")
    ]
    engine = create_engine(database_url)
    with Session(engine) as session:
        candidates = get_recognition_candidates(session, "louvre")

    out_rows = []
    for row in result_rows:
        ranked = rank_catalog_candidates(row["vision"], candidates, limit=args.limit)
        pos = rank_position(row["artwork_id"], ranked)
        out_rows.append({
            "artwork_id": row["artwork_id"],
            "artwork_ark": row.get("artwork_ark"),
            "expected_title": row.get("expected_title"),
            "department": row.get("department"),
            "tier": row.get("tier"),
            "variant": row.get("variant"),
            "rank_position": pos,
            "top_candidates": [
                {
                    "rank": idx,
                    "artwork_id": item["candidate"]["id"],
                    "title": item["candidate"].get("title"),
                    "department": item["candidate"].get("department"),
                    "score": item.get("score"),
                    "signals": item.get("signals"),
                }
                for idx, item in enumerate(ranked, 1)
            ],
            "stage1": row["vision"],
        })

    OUT.mkdir(parents=True, exist_ok=True)
    slug = now_slug()
    detail_path = OUT / f"louvre_retrieval_recall_{slug}.jsonl"
    summary_path = OUT / f"louvre_retrieval_recall_summary_{slug}.json"
    with detail_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    summary = summarize(out_rows)
    summary.update({
        "input_results": str(Path(args.results)),
        "variant": args.variant,
        "mode": args.mode,
        "limit": args.limit,
        "detail_path": str(detail_path.relative_to(ROOT)),
    })
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
