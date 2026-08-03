# -*- coding: utf-8 -*-
"""
Pre-fetches and caches every catalog work's reference image to
backend/.reference_cache/, so the first real scan of each work doesn't pay
for a live Wikimedia Commons download inside visual_verify_single_candidate().

Run once after deploy / whenever DEMO_ARTWORKS changes:
    python backend/scripts/warm_reference_cache.py

Sequential with a small delay between requests — Wikimedia Commons rate-limits
concurrent/rapid bot traffic (HTTP 429) hard enough that fetching all ~100
images concurrently on first real traffic reliably trips it (this happened
during testing). A cold cache is not just slower, it can outright fail scans.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.main import DEMO_ARTWORKS, REFERENCE_CACHE_DIR, _fetch_reference_image_b64

if __name__ == "__main__":
    os.makedirs(REFERENCE_CACHE_DIR, exist_ok=True)
    total = len(DEMO_ARTWORKS)
    for i, artwork in enumerate(DEMO_ARTWORKS, 1):
        cache_path = os.path.join(REFERENCE_CACHE_DIR, f'{artwork["id"]}.jpg')
        if os.path.exists(cache_path):
            print(f"[{i}/{total}] {artwork['id']} already cached, skip")
            continue
        print(f"[{i}/{total}] {artwork['id']} downloading...")
        _fetch_reference_image_b64(artwork)
        time.sleep(1.2)  # be polite to Commons — see module docstring
    print("done")
