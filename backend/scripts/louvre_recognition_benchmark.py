#!/usr/bin/env python3
"""Commons-only Louvre recognition benchmark.

Uses existing approved RecognitionAsset URLs as legally permitted test inputs.
No Louvre-hosted image bytes are fetched. Calls the deployed production
/v1/recognize endpoint so results exercise the runtime OpenAI + DB path.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "exports" / "louvre" / "recognition_benchmark"
UA = "ELYIO-Louvre-recognition-benchmark/1.0"


def thumbnail_url(url: str, width: int = 768) -> str:
    parsed = urllib.parse.urlsplit(url)
    if "Special:FilePath" not in parsed.path:
        return url
    safe_path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/:")
    query = dict(urllib.parse.parse_qsl(parsed.query))
    query["width"] = str(width)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, safe_path, urllib.parse.urlencode(query), parsed.fragment))


def fetch_b64(url: str) -> str:
    req = urllib.request.Request(thumbnail_url(url), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
    return base64.b64encode(data).decode("ascii")


def post_recognize(api_url: str, image_b64: str) -> tuple[dict, float]:
    body = json.dumps({"image_base64": image_b64, "museum_id": "louvre", "locale": "en"}).encode("utf-8")
    req = urllib.request.Request(
        api_url.rstrip("/") + "/v1/recognize",
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload, time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--api-url", default="https://api.elyio.co")
    parser.add_argument("--apply", action="store_true", help="actually call production recognition; default only writes plan")
    parser.add_argument("--allow-remote-wikimedia", action="store_true", help="deprecated escape hatch; prefer louvre_local_recognition_benchmark.py")
    args = parser.parse_args()

    if args.apply and not args.allow_remote_wikimedia:
        raise SystemExit(
            "BENCHMARK_INVALID_NETWORK_CONTAMINATED: this benchmark depends on live Wikimedia. "
            "Use backend/scripts/louvre_acquire_approved_assets.py followed by "
            "backend/scripts/louvre_local_recognition_benchmark.py instead."
        )

    load_dotenv(ROOT / ".env")
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                text(
                    """
                    select a.id, a.source_record_id, a.title_original, a.artist, ra.source_url
                    from artworks a
                    join artwork_catalog_memberships m on m.artwork_id=a.id
                    join recognition_assets ra on ra.artwork_id=a.id
                    where m.museum_id='louvre'
                      and m.catalog_version='2026-08-11-v1'
                      and m.active=true
                      and ra.embedding_eligible=true
                      and ra.ai_tdm_eligible=true
                    order by m.visitor_priority desc nulls last, a.id asc
                    limit :limit
                    """
                ),
                {"limit": args.limit},
            ).mappings()
        ]

    OUT.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    plan_path = OUT / f"louvre_commons_benchmark_plan_{generated_at.replace(':','')}.jsonl"
    with plan_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    if not args.apply:
        print(json.dumps({"mode": "PLAN_ONLY", "planned": len(rows), "plan_path": str(plan_path.relative_to(ROOT))}, indent=2))
        return

    results = []
    for i, row in enumerate(rows, 1):
        try:
            image_b64 = fetch_b64(row["source_url"])
            payload, latency = post_recognize(args.api_url, image_b64)
            top = payload.get("artwork_id")
            top3 = [top] + [x for x in payload.get("alternatives", []) if x != top]
            result = {
                "expected_ark": row["source_record_id"],
                "expected_id": row["id"],
                "title": row["title_original"],
                "status": payload.get("status"),
                "top1": top,
                "top3": top3[:3],
                "confidence": payload.get("confidence"),
                "recognition_mode": payload.get("recognition_mode"),
                "latency_s": round(latency, 3),
                "top1_correct": top == row["id"],
                "top3_correct": row["id"] in top3[:3],
            }
        except Exception as exc:
            result = {
                "expected_ark": row["source_record_id"],
                "expected_id": row["id"],
                "title": row["title_original"],
                "error": f"{type(exc).__name__}: {exc}",
                "top1_correct": False,
                "top3_correct": False,
            }
        results.append(result)
        print(json.dumps({"i": i, "of": len(rows), **result}, ensure_ascii=False))

    result_path = OUT / f"louvre_commons_benchmark_results_{generated_at.replace(':','')}.jsonl"
    with result_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    latencies = sorted(r["latency_s"] for r in results if "latency_s" in r)
    summary = {
        "mode": "APPLY",
        "api_url": args.api_url,
        "total": len(results),
        "top1_accuracy": sum(1 for r in results if r["top1_correct"]) / len(results) if results else 0,
        "top3_accuracy": sum(1 for r in results if r["top3_correct"]) / len(results) if results else 0,
        "errors": sum(1 for r in results if "error" in r),
        "median_latency_s": latencies[len(latencies) // 2] if latencies else None,
        "p95_latency_s": latencies[int(len(latencies) * 0.95) - 1] if latencies else None,
        "result_path": str(result_path.relative_to(ROOT)),
        "louvre_image_bytes_fetched": 0,
    }
    (OUT / f"louvre_commons_benchmark_summary_{generated_at.replace(':','')}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
