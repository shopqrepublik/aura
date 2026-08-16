# -*- coding: utf-8 -*-
"""Validation statistics over the current backend/data/louvre/ import
state -- reads only what louvre_import.py already produced, no network
calls. Produces both global and per-department breakdowns (see
docs/louvre-schema.md and the census report)."""
import glob
import json
import os
from collections import Counter, defaultdict

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")
ERRORS_PATH = os.path.join(DATA_DIR, "errors", "errors.jsonl")
CHECKPOINT_PATH = os.path.join(DATA_DIR, "checkpoints", "checkpoint.json")

# Exact official names, confirmed live from the Louvre site's own advanced-
# search "Collection" dropdown (not guessed) -- "Objets d'art" in particular
# has a longer official name than the obvious guess.
NAMED_DEPARTMENTS = [
    "Département des Peintures",
    "Département des Sculptures du Moyen Age, de la Renaissance et des temps modernes",
    "Département des Antiquités égyptiennes",
    "Département des Antiquités grecques, étrusques et romaines",
    "Département des Antiquités orientales",
    "Département des Objets d'art du Moyen Age, de la Renaissance et des temps modernes",
    "Département des Arts de l'Islam",
    "Département des Arts graphiques",
    "Département des Arts de Byzance et des chrétientés en Orient",  # large in our samples, not in the original named list but real
]


def load_all():
    records = []
    for path in glob.glob(os.path.join(NORMALIZED_DIR, "*.json")):
        with open(path, encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def dept_stats(records):
    n = len(records)
    with_image_ref = sum(1 for r in records if r.get("image_count", 0) > 0)
    with_copyright = sum(1 for r in records if any(im.get("image_copyright") for im in r.get("image_references", [])))
    return {
        "sample_count": n,
        "on_display": sum(1 for r in records if r.get("display_status") == "ON_DISPLAY"),
        "not_on_display": sum(1 for r in records if r.get("display_status") == "NOT_ON_DISPLAY"),
        "unknown_display": sum(1 for r in records if r.get("display_status") == "UNKNOWN"),
        "with_room": sum(1 for r in records if r.get("room")),
        "with_creator": sum(1 for r in records if r.get("creator_labels")),
        "with_creator_wikidata_qid": sum(1 for r in records if r.get("creator_wikidata_qid")),
        "with_image_reference": with_image_ref,
        "with_image_copyright": with_copyright,
        "metadata_ready": sum(1 for r in records if r.get("metadata_status") == "READY"),
        "metadata_partial": sum(1 for r in records if r.get("metadata_status") == "PARTIAL"),
        "metadata_insufficient": sum(1 for r in records if r.get("metadata_status") == "INSUFFICIENT"),
        "needs_recognition_asset": sum(1 for r in records if r.get("recognition_status") == "NEEDS_ASSET"),
        "no_usable_asset": sum(1 for r in records if r.get("recognition_status") == "NO_USABLE_ASSET"),
    }


def print_stats_block(label, stats, total_for_pct=None):
    n = stats["sample_count"]
    denom = total_for_pct or n
    print(f"\n--- {label} (n={n}) ---")
    for k, v in stats.items():
        if k == "sample_count":
            continue
        pct = f" ({100*v/denom:.0f}%)" if denom else ""
        print(f"  {k:<28} {v:5d}{pct}")


def main():
    records = load_all()
    total = len(records)

    with open(CHECKPOINT_PATH, encoding="utf-8") as f:
        cp = json.load(f)
    failed_count = len(cp.get("failed", {}))

    errors = []
    if os.path.exists(ERRORS_PATH):
        with open(ERRORS_PATH, encoding="utf-8") as f:
            errors = [json.loads(line) for line in f if line.strip()]

    ids = [r["source_record_id"] for r in records]
    dupes = total - len(set(ids))

    print(f"=== Louvre import validation: {total} normalized records ===\n")
    print(f"successfully imported : {total}")
    print(f"failed                : {failed_count}  (errors logged: {len(errors)})")
    print(f"duplicate source ids  : {dupes}")

    print("\n=== GLOBAL ===")
    print_stats_block("ALL RECORDS", dept_stats(records))

    print("\n\n=== BY DEPARTMENT (named departments from the census spec) ===")
    by_dept = defaultdict(list)
    for r in records:
        by_dept[r.get("department") or "(none)"].append(r)

    for dept in NAMED_DEPARTMENTS:
        if dept in by_dept:
            print_stats_block(dept, dept_stats(by_dept[dept]), total_for_pct=len(by_dept[dept]))
        else:
            print(f"\n--- {dept} --- NOT REPRESENTED IN THIS SAMPLE")

    other_depts = {k: v for k, v in by_dept.items() if k not in NAMED_DEPARTMENTS}
    if other_depts:
        print("\n\n=== OTHER DEPARTMENTS FOUND (not in the named list) ===")
        for dept, recs in sorted(other_depts.items(), key=lambda kv: -len(kv[1])):
            print(f"  [{len(recs):5d}] {dept}")

    dept_counter = Counter(r.get("department") or "(none)" for r in records)
    print("\n\n=== all departments by count ===")
    for k, v in dept_counter.most_common(30):
        print(f"  [{v:5d}] {k}")

    if errors:
        print(f"\n\nerrors sample (up to 10 of {len(errors)}):")
        for e in errors[:10]:
            print(" ", e)


if __name__ == "__main__":
    main()
