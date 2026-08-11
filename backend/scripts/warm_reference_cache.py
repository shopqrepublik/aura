# -*- coding: utf-8 -*-
"""
Pre-fetches and caches every catalog work's reference image to
backend/.reference_cache/, so the first real scan of each work doesn't pay
for a live Wikimedia Commons download inside visual_verify_single_candidate().

Run once after deploy / whenever the DB-backed catalog changes:
    python backend/scripts/warm_reference_cache.py

Sequential with a delay between requests — Wikimedia Commons rate-limits
concurrent/rapid bot traffic (HTTP 429) hard enough that fetching all ~100
images concurrently on first real traffic reliably trips it (this happened
during testing, and again during a Docker-build warm-up sweep — see
_urlopen_with_retry in app/main.py for the backoff-on-429 handling this
script now benefits from too). A cold cache is not just slower, it can
outright fail scans.

Per-artwork fetch failures (rate-limiting that outlasts the retry budget, a
transient network error, one bad URL) are logged and skipped rather than
aborting the whole run — this script is meant to be safe to run as a Docker
build step, where one stubborn image souring the entire image build is far
worse than shipping with a small handful of works still cold (those just
fall back to a live, now-safe-by-construction fetch at request time).
"""
import os
import sys
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.catalog import get_recognition_candidates
from app.db import SessionLocal
from app.main import DEMO_ARTWORKS, REFERENCE_CACHE_DIR, _fetch_reference_image_b64


def _load_db_catalog(museum_ids: list[str]) -> list[dict]:
    if SessionLocal is None:
        raise SystemExit("DATABASE_URL not set; refusing to warm from DEMO_ARTWORKS without --demo-reference")
    with SessionLocal() as session:
        rows: list[dict] = []
        for museum_id in museum_ids:
            rows.extend(get_recognition_candidates(session, museum_id))
        return rows

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--museum-id", action="append")
    parser.add_argument(
        "--demo-reference",
        action="store_true",
        help="warm from DEMO_ARTWORKS instead of the DB catalog; rollback/reference use only",
    )
    args = parser.parse_args()

    museum_ids = args.museum_id or ["orsay", "orangerie"]
    catalog = DEMO_ARTWORKS if args.demo_reference else _load_db_catalog(museum_ids)
    os.makedirs(REFERENCE_CACHE_DIR, exist_ok=True)
    total = len(catalog)
    failed = []
    for i, artwork in enumerate(catalog, 1):
        cache_path = os.path.join(REFERENCE_CACHE_DIR, f'{artwork["id"]}.jpg')
        if os.path.exists(cache_path):
            print(f"[{i}/{total}] {artwork['id']} already cached, skip")
            continue
        print(f"[{i}/{total}] {artwork['id']} downloading...")
        try:
            _fetch_reference_image_b64(artwork)
        except Exception as e:
            print(f"[{i}/{total}] {artwork['id']} FAILED, skipping: {type(e).__name__}: {e}")
            failed.append(artwork["id"])
        time.sleep(2)  # be polite to Commons — see module docstring
    if failed:
        print(f"\ndone, but {len(failed)}/{total} works stayed cold: {failed}")
    else:
        print("\ndone, all works cached")
