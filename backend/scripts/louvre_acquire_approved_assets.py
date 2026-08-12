#!/usr/bin/env python3
"""Acquire approved Louvre recognition assets into a controlled local cache.

This is a rights-safe acquisition job, not a benchmark. It fetches only
RecognitionAsset rows that are already APPROVED/eligible in production data,
never Louvre/RMN URLs, and stops immediately on HTTP 429.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "exports" / "louvre" / "recognition_assets"
CACHE = OUT / "cache"
MANIFEST = OUT / "louvre_approved_asset_acquisition_manifest.jsonl"
CHECKPOINT = OUT / "louvre_approved_asset_acquisition_checkpoint.json"
UA = "ELYIO-Louvre-approved-asset-acquisition/1.0 (contact: rights@elyio.co)"
MAX_BYTES = 30 * 1024 * 1024


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_thumbnail_url(url: str, width: int = 1024) -> str:
    parsed = urllib.parse.urlsplit(url)
    if "Special:FilePath" not in parsed.path:
        return url
    safe_path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/:")
    query = dict(urllib.parse.parse_qsl(parsed.query))
    query["width"] = str(width)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, safe_path, urllib.parse.urlencode(query), parsed.fragment))


def is_allowed_source(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return parsed.hostname in {"commons.wikimedia.org", "upload.wikimedia.org"}


def fetch_once(url: str) -> tuple[bytes, dict]:
    req = urllib.request.Request(safe_thumbnail_url(url), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_BYTES:
            raise RuntimeError(f"asset exceeds max byte limit: {content_length}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise RuntimeError("asset exceeded max byte limit during read")
            chunks.append(chunk)
        return b"".join(chunks), dict(resp.headers)


def normalize_image(data: bytes, out_path: Path) -> tuple[int, int]:
    import io

    img = Image.open(io.BytesIO(data))
    img.draft("RGB", (1024, 1024))
    img = img.convert("RGB")
    img.thumbnail((1024, 1024), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="JPEG", quality=88, optimize=True)
    return img.size


def load_rows(limit: int | None) -> list[dict]:
    load_dotenv(ROOT / ".env")
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                text(
                    """
                    select
                      a.id as artwork_id,
                      a.source_record_id as ark_id,
                      a.title_original,
                      a.artist,
                      a.department,
                      a.room,
                      ra.id as asset_id,
                      ra.source,
                      ra.source_url,
                      ra.license,
                      ra.attribution,
                      ra.rights_status,
                      ra.ai_tdm_eligible,
                      ra.embedding_eligible,
                      ra.local_storage_status
                    from artworks a
                    join artwork_catalog_memberships m on m.artwork_id=a.id
                    join recognition_assets ra on ra.artwork_id=a.id
                    where m.museum_id='louvre'
                      and m.catalog_version='2026-08-11-v1'
                      and m.active=true
                      and ra.ai_tdm_eligible=true
                      and ra.embedding_eligible=true
                      and ra.rights_status in ('public_domain','cc_licensed')
                    order by m.visitor_priority desc nulls last, a.id asc
                    """
                )
            ).mappings()
        ]
    return rows[:limit] if limit else rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--delay", type=float, default=8.0)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = load_rows(args.limit)
    planned = []
    acquired = []
    skipped = []
    stopped = None

    for i, row in enumerate(rows, 1):
        if not row["source_url"] or not is_allowed_source(row["source_url"]):
            skipped.append({"ark_id": row["ark_id"], "asset_id": row["asset_id"], "reason": "source_not_allowed"})
            continue
        out_path = CACHE / f"{row['artwork_id']}.jpg"
        planned_row = {
            **row,
            "cache_path": str(out_path.relative_to(ROOT)),
            "fixture_hash": None,
            "acquired_at": None,
            "status": "PLANNED",
        }
        if out_path.exists():
            digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
            planned_row.update({"fixture_hash": digest, "status": "CACHED"})
            acquired.append(planned_row)
            continue
        planned.append(planned_row)
        if not args.apply:
            continue

        try:
            data, headers = fetch_once(row["source_url"])
            w, h = normalize_image(data, out_path)
            digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
            acquired_row = {
                **planned_row,
                "status": "ACQUIRED",
                "fixture_hash": digest,
                "source_bytes_sha256": sha256_bytes(data),
                "width": w,
                "height": h,
                "acquired_at": now(),
                "response_content_type": headers.get("Content-Type"),
            }
            acquired.append(acquired_row)
            with MANIFEST.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(acquired_row, ensure_ascii=False, separators=(",", ":")) + "\n")
            CHECKPOINT.write_text(json.dumps({"last_index": i, "last_ark": row["ark_id"], "updated_at": now()}, indent=2), encoding="utf-8")
            time.sleep(args.delay)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                stopped = {"reason": "HTTP_429", "ark_id": row["ark_id"], "retry_after": retry_after, "stopped_at": now()}
                break
            skipped.append({"ark_id": row["ark_id"], "asset_id": row["asset_id"], "reason": f"HTTP_{exc.code}"})
        except Exception as exc:
            skipped.append({"ark_id": row["ark_id"], "asset_id": row["asset_id"], "reason": f"{type(exc).__name__}: {exc}"})

    plan_path = OUT / "louvre_approved_asset_acquisition_plan.jsonl"
    with plan_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in [*acquired, *planned]:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    summary = {
        "mode": "APPLY" if args.apply else "PLAN_ONLY",
        "eligible_assets": len(rows),
        "already_cached_or_acquired": len(acquired),
        "planned_not_fetched": len(planned),
        "skipped": len(skipped),
        "stopped": stopped,
        "cache_dir": str(CACHE.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "plan": str(plan_path.relative_to(ROOT)),
        "louvre_image_bytes_fetched": 0,
    }
    (OUT / "louvre_approved_asset_acquisition_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
