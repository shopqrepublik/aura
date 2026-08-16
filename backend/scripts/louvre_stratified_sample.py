# -*- coding: utf-8 -*-
"""Builds a stratified census sample list from the full ark_index.jsonl
(no network calls -- pure local sampling logic). NOT sequential sampling:
covers every sitemap, and within each sitemap covers beginning/middle/end
position-thirds, spread via stride rather than taking the literal first N
of each third.

Usage:
    venv/Scripts/python.exe backend/scripts/louvre_stratified_sample.py --total 5000
Writes backend/data/louvre/checkpoints/stratified_sample.json (ordered list
of ark_ids) for louvre_import.py to consume.
"""
import argparse
import json
import os
from collections import defaultdict

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre")
ARK_INDEX_PATH = os.path.join(DATA_DIR, "checkpoints", "ark_index.jsonl")
OUT_PATH = os.path.join(DATA_DIR, "checkpoints", "stratified_sample.json")


def load_index():
    by_sitemap = defaultdict(list)
    with open(ARK_INDEX_PATH, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            by_sitemap[r["sitemap_id"]].append(r)
    for sid in by_sitemap:
        by_sitemap[sid].sort(key=lambda r: r["position_in_sitemap"])
    return by_sitemap


def stratified_pick(records, n):
    """Splits records into beginning/middle/end thirds, strides evenly
    within each third to reach roughly n/3 picks per third."""
    total = len(records)
    if total == 0 or n <= 0:
        return []
    third = total // 3
    thirds = [records[:third] or records, records[third:2 * third] or records, records[2 * third:] or records]
    per_third = max(1, n // 3)
    picks = []
    for group in thirds:
        if not group:
            continue
        stride = max(1, len(group) // per_third)
        picks.extend(group[::stride][:per_third])
    return picks[:n]


def main(total_target):
    by_sitemap = load_index()
    n_sitemaps = len(by_sitemap)
    per_sitemap = max(1, total_target // n_sitemaps)
    print(f"{n_sitemaps} sitemaps, targeting ~{per_sitemap} records/sitemap for a total of ~{total_target}")

    sample = []
    for sid in sorted(by_sitemap.keys()):
        picks = stratified_pick(by_sitemap[sid], per_sitemap)
        sample.extend(picks)
        print(f"  sitemap {sid}: {len(by_sitemap[sid])} total records -> {len(picks)} sampled")

    ark_ids = [r["ark_id"] for r in sample]

    prefix_counts = defaultdict(int)
    for r in sample:
        prefix_counts[r["ark_prefix"]] += 1

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ark_ids, f)

    print(f"\n{len(ark_ids)} ARK ids sampled across {n_sitemaps} sitemaps.")
    print(f"prefix distribution in sample: {dict(prefix_counts)}")
    print(f"Written to {OUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, default=5000)
    args = parser.parse_args()
    main(args.total)
