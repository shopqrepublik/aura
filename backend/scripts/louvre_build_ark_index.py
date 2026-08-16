# -*- coding: utf-8 -*-
"""Enumeration-only pass over all 26 official Louvre Collections sitemaps.
Fetches the 26 sub-sitemap XML files (NOT the ~500k individual record
.json endpoints -- see docs/louvre-source-audit.md §9), extracts every
unique ARK id, and writes a durable index. This is the complete-collection
enumeration step; nothing here fetches per-record metadata.

Output: backend/data/louvre/checkpoints/ark_index.jsonl, one JSON object
per unique ARK id: {ark_id, source_url, sitemap_id, position_in_sitemap,
ark_prefix, discovered_at}.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre")
ARK_INDEX_PATH = os.path.join(DATA_DIR, "checkpoints", "ark_index.jsonl")

UA = "AURA-MVP-backend/1.0 (contact: repo owner; research/museum-app project)"
SITEMAP_INDEX = "https://collections.louvre.fr/sitemap.xml"
COURTESY_DELAY_S = 1.0
MAX_ATTEMPTS = 4

ARK_LINE_PATTERN = re.compile(r"https://collections\.louvre\.fr/(?:en/)?ark:/53355/(cl\d+)")


def fetch_with_retry(url):
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise PermissionError(f"403 from {url} -- explicit access-control signal, stopping")
            last_err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"{type(e).__name__}: {e}"
        wait = 5 * attempt
        print(f"    retry {attempt}/{MAX_ATTEMPTS} after {last_err}, waiting {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"failed after {MAX_ATTEMPTS} attempts: {last_err}")


def main():
    os.makedirs(os.path.dirname(ARK_INDEX_PATH), exist_ok=True)

    print("Fetching sitemap index...")
    index_body = fetch_with_retry(SITEMAP_INDEX)
    sub_sitemaps = re.findall(r"<loc>([^<]+)</loc>", index_body.decode("utf-8"))
    print(f"  {len(sub_sitemaps)} sub-sitemaps listed")

    seen_global = set()
    total_raw_matches = 0
    now = datetime.now(timezone.utc).isoformat()

    with open(ARK_INDEX_PATH, "w", encoding="utf-8") as out:
        for sitemap_id, sub_url in enumerate(sub_sitemaps):
            print(f"[{sitemap_id + 1}/{len(sub_sitemaps)}] fetching {sub_url} ...")
            body = fetch_with_retry(sub_url).decode("utf-8")
            seen_in_this_file = set()
            position = 0
            for m in ARK_LINE_PATTERN.finditer(body):
                ark_id = m.group(1)
                total_raw_matches += 1
                if ark_id in seen_in_this_file:
                    continue  # dedupe fr/en/hreflang duplicates within this sub-sitemap
                seen_in_this_file.add(ark_id)
                if ark_id in seen_global:
                    continue  # cross-sub-sitemap duplicate, if any -- keep first occurrence only
                seen_global.add(ark_id)
                record = {
                    "ark_id": ark_id,
                    "source_url": f"https://collections.louvre.fr/ark:/53355/{ark_id}",
                    "sitemap_id": sitemap_id,
                    "position_in_sitemap": position,
                    "ark_prefix": ark_id[:4],  # e.g. "cl01", "cl02"
                    "discovered_at": now,
                }
                out.write(json.dumps(record) + "\n")
                position += 1
            print(f"    {len(seen_in_this_file)} unique ARK ids in this sub-sitemap ({len(seen_global)} unique total so far)")
            time.sleep(COURTESY_DELAY_S)

    print(f"\nDone. {len(seen_global)} unique ARK ids across {len(sub_sitemaps)} sub-sitemaps "
          f"({total_raw_matches} raw href matches before dedup).")
    print(f"Index written to {ARK_INDEX_PATH}")


if __name__ == "__main__":
    main()
