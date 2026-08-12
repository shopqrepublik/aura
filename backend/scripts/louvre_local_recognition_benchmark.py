#!/usr/bin/env python3
"""Benchmark Louvre recognition from local approved assets only.

No Wikimedia/Louvre network requests happen here. Inputs are files created by
louvre_acquire_approved_assets.py. The production API may be called, but image
bytes come from the local controlled corpus.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "exports" / "louvre" / "recognition_assets"
CACHE = ASSETS / "cache"
OUT = ROOT / "exports" / "louvre" / "recognition_benchmark"
UA = "ELYIO-Louvre-local-recognition-benchmark/1.0"


def now_slug() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(":", "")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def select_fixtures(limit: int) -> list[dict]:
    rows = read_jsonl(ASSETS / "louvre_approved_asset_acquisition_manifest.jsonl")
    if not rows:
        rows = read_jsonl(ASSETS / "louvre_approved_asset_acquisition_plan.jsonl")
    fixtures = []
    seen_departments = set()
    for row in rows:
        path = ROOT / row.get("cache_path", "")
        if not path.exists():
            continue
        item = {
            "artwork_id": row["artwork_id"],
            "artwork_ark": row["ark_id"],
            "museum_id": "louvre",
            "asset_id": row["asset_id"],
            "expected_title": row.get("title_original"),
            "expected_artist": row.get("artist"),
            "department": row.get("department"),
            "room": row.get("room"),
            "license": row.get("license"),
            "fixture_path": str(path.relative_to(ROOT)),
            "fixture_hash": sha256(path),
        }
        if item["department"] not in seen_departments:
            fixtures.insert(0, item)
            seen_departments.add(item["department"])
        else:
            fixtures.append(item)
    return fixtures[:limit]


def create_variants(fixtures: list[dict], variants: list[str]) -> list[dict]:
    variant_dir = OUT / "local_variants"
    variant_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for fixture in fixtures:
        src = ROOT / fixture["fixture_path"]
        img = Image.open(src).convert("RGB")
        for variant in variants:
            out = variant_dir / f"{fixture['artwork_id']}_{variant}.jpg"
            v = img.copy()
            if variant == "crop":
                w, h = v.size
                v = v.crop((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)))
            elif variant == "low_light":
                v = ImageEnhance.Brightness(v).enhance(0.55)
            elif variant == "blur":
                v = v.filter(ImageFilter.GaussianBlur(radius=1.2))
            elif variant == "perspective":
                w, h = v.size
                v = v.rotate(4, resample=Image.Resampling.BICUBIC, expand=True).crop((8, 8, max(9, w - 8), max(9, h - 8)))
            elif variant == "glare":
                overlay = Image.new("RGB", v.size, (255, 255, 255))
                mask = Image.new("L", v.size, 0)
                mw, mh = mask.size
                for x in range(mw):
                    for y in range(mh):
                        if abs((x / max(1, mw)) - (y / max(1, mh))) < 0.045:
                            mask.putpixel((x, y), 75)
                v = Image.composite(overlay, v, mask)
            v.thumbnail((900, 900), Image.LANCZOS)
            v.save(out, format="JPEG", quality=86, optimize=True)
            rows.append({**fixture, "variant": variant, "input_path": str(out.relative_to(ROOT)), "input_hash": sha256(out)})
    return rows


def post_recognize(api_url: str, image_path: Path, mode: str) -> tuple[dict, float]:
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    body = {"image_base64": image_b64, "museum_id": "louvre", "locale": "en"}
    if mode == "vision_metadata_only":
        body["benchmark_mode"] = "vision_metadata_only"
    req = urllib.request.Request(
        api_url.rstrip("/") + "/v1/recognize",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=150) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload, time.perf_counter() - start


def benchmark(api_url: str, rows: list[dict], mode: str) -> list[dict]:
    results = []
    for i, row in enumerate(rows, 1):
        try:
            payload, latency = post_recognize(api_url, ROOT / row["input_path"], mode)
            top = payload.get("artwork_id")
            top3 = [top] + [x for x in payload.get("alternatives", []) if x != top]
            result = {
                **row,
                "mode": mode,
                "status": payload.get("status"),
                "top1": top,
                "top3": top3[:3],
                "confidence": payload.get("confidence"),
                "recognition_mode": payload.get("recognition_mode"),
                "latency_s": round(latency, 3),
                "top1_correct": top == row["artwork_id"],
                "top3_correct": row["artwork_id"] in top3[:3],
            }
        except Exception as exc:
            result = {**row, "mode": mode, "error": f"{type(exc).__name__}: {exc}", "top1_correct": False, "top3_correct": False}
        results.append(result)
        print(json.dumps({"i": i, "of": len(rows), "mode": mode, "ark": row["artwork_ark"], "variant": row["variant"], "ok": result.get("top1_correct"), "error": result.get("error")}, ensure_ascii=False))
    return results


def summarize(results: list[dict]) -> dict:
    total = len(results)
    errors = [r for r in results if "error" in r]
    valid = [r for r in results if "error" not in r]
    latencies = sorted(r["latency_s"] for r in valid if "latency_s" in r)
    by_variant = {}
    for variant in sorted({r["variant"] for r in results}):
        rows = [r for r in results if r["variant"] == variant]
        by_variant[variant] = {
            "total": len(rows),
            "top1": sum(1 for r in rows if r.get("top1_correct")),
            "top3": sum(1 for r in rows if r.get("top3_correct")),
            "top1_accuracy": sum(1 for r in rows if r.get("top1_correct")) / len(rows) if rows else 0,
            "top3_accuracy": sum(1 for r in rows if r.get("top3_correct")) / len(rows) if rows else 0,
        }
    return {
        "total": total,
        "valid": len(valid),
        "errors": len(errors),
        "top1_accuracy": sum(1 for r in results if r.get("top1_correct")) / total if total else 0,
        "top3_accuracy": sum(1 for r in results if r.get("top3_correct")) / total if total else 0,
        "median_latency_s": statistics.median(latencies) if latencies else None,
        "p95_latency_s": latencies[int(len(latencies) * 0.95) - 1] if latencies else None,
        "by_variant": by_variant,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="https://api.elyio.co")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--variants", default="pristine,crop,low_light")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    fixtures = select_fixtures(args.limit)
    variants = [x.strip() for x in args.variants.split(",") if x.strip()]
    rows = create_variants(fixtures, variants) if fixtures else []
    slug = now_slug()
    fixture_path = OUT / f"louvre_local_fixture_manifest_{slug}.jsonl"
    with fixture_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    if not args.apply:
        print(json.dumps({"mode": "PLAN_ONLY", "fixtures": len(fixtures), "inputs": len(rows), "fixture_manifest": str(fixture_path.relative_to(ROOT))}, indent=2))
        return

    results_a = benchmark(args.api_url, rows, "vision_metadata_only")
    results_b = benchmark(args.api_url, rows, "hybrid_stage2")
    result_path = OUT / f"louvre_local_benchmark_results_{slug}.jsonl"
    with result_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in [*results_a, *results_b]:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    summary = {
        "benchmark_status": "VALID_LOCAL_CORPUS",
        "fixtures": len(fixtures),
        "inputs_per_mode": len(rows),
        "vision_metadata_only": summarize(results_a),
        "hybrid_stage2": summarize(results_b),
        "louvre_image_bytes_fetched": 0,
        "wikimedia_runtime_requests": 0,
        "result_path": str(result_path.relative_to(ROOT)),
    }
    (OUT / f"louvre_local_benchmark_summary_{slug}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
