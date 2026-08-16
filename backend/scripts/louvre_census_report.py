# -*- coding: utf-8 -*-
"""Final census report -- uses ONLY the proper stratified sample (every
sitemap x beginning/middle/end positions), not the earlier ad-hoc
100-sequential + ~1000-stride batches from the first test pass, which don't
meet the stratification requirement and would bias department-level
statistics if included."""
import json
import os
from collections import Counter, defaultdict

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")
ARK_INDEX_PATH = os.path.join(DATA_DIR, "checkpoints", "ark_index.jsonl")
SAMPLE_PATH = os.path.join(DATA_DIR, "checkpoints", "stratified_sample.json")
CHECKPOINT_PATH = os.path.join(DATA_DIR, "checkpoints", "checkpoint.json")

NAMED_DEPARTMENTS = [
    "Département des Peintures",
    "Département des Sculptures du Moyen Age, de la Renaissance et des temps modernes",
    "Département des Antiquités égyptiennes",
    "Département des Antiquités grecques, étrusques et romaines",
    "Département des Antiquités orientales",
    "Département des Objets d'art du Moyen Age, de la Renaissance et des temps modernes",
    "Département des Arts de l'Islam",
    "Département des Arts graphiques",
    "Département des Arts de Byzance et des chrétientés en Orient",
]

LANDMARKS = {
    "cl010062370": "Mona Lisa",
    "cl010277627": "Venus de Milo",
    "cl010252531": "Winged Victory of Samothrace",
}


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


def print_stats_block(label, stats):
    n = stats["sample_count"]
    print(f"\n--- {label} (n={n}) ---")
    for k, v in stats.items():
        if k == "sample_count":
            continue
        pct = f" ({100*v/n:.0f}%)" if n else ""
        print(f"  {k:<28} {v:5d}{pct}")


def main():
    with open(SAMPLE_PATH, encoding="utf-8") as f:
        sample_ids = set(json.load(f))
    sample_ids |= set(LANDMARKS.keys())

    records = []
    missing = []
    for ark_id in sample_ids:
        path = os.path.join(NORMALIZED_DIR, f"{ark_id}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                records.append(json.load(f))
        else:
            missing.append(ark_id)

    total = len(records)
    print(f"=== LOUVRE STRATIFIED CENSUS REPORT ===")
    print(f"Stratified sample target: {len(sample_ids)} ARK ids")
    print(f"Successfully normalized: {total}")
    print(f"Missing/failed (permanent 404s): {len(missing)} -- {missing}")

    dupes = total - len({r['source_record_id'] for r in records})
    print(f"Duplicate source ids: {dupes}")

    print("\n=== GLOBAL ===")
    print_stats_block("ALL SAMPLED RECORDS", dept_stats(records))

    print("\n\n=== BY DEPARTMENT (named departments from the census spec) ===")
    by_dept = defaultdict(list)
    for r in records:
        by_dept[r.get("department") or "(none)"].append(r)

    for dept in NAMED_DEPARTMENTS:
        if dept in by_dept:
            print_stats_block(dept, dept_stats(by_dept[dept]))
        else:
            print(f"\n--- {dept} --- NOT REPRESENTED IN THIS SAMPLE")

    other_depts = {k: v for k, v in by_dept.items() if k not in NAMED_DEPARTMENTS}
    if other_depts:
        print("\n\n=== OTHER DEPARTMENTS FOUND (not in the named list) ===")
        for dept, recs in sorted(other_depts.items(), key=lambda kv: -len(kv[1])):
            print(f"  [{len(recs):5d}] {dept}")

    # --- Landmark validation ---
    print("\n\n=== LANDMARK VALIDATION ===")
    for ark_id, name in LANDMARKS.items():
        r = next((r for r in records if r["source_record_id"] == ark_id), None)
        if r:
            print(f"  {name} ({ark_id}): title={r['title']!r} | display={r['display_status']} | dept={r['department']}")
        else:
            print(f"  {name} ({ark_id}): NOT FOUND in normalized records")

    # --- Full-collection extrapolation ---
    with open(ARK_INDEX_PATH, encoding="utf-8") as f:
        total_collection = sum(1 for _ in f)

    on_display_rate = sum(1 for r in records if r.get("display_status") == "ON_DISPLAY") / total if total else 0
    on_display_with_room_rate = sum(1 for r in records if r.get("display_status") == "ON_DISPLAY" and r.get("room")) / total if total else 0
    qid_rate = sum(1 for r in records if r.get("creator_wikidata_qid")) / total if total else 0
    metadata_ready_rate = sum(1 for r in records if r.get("metadata_status") == "READY") / total if total else 0
    visitor_relevant_rate = sum(1 for r in records if r.get("display_status") == "ON_DISPLAY" and r.get("metadata_status") in ("READY", "PARTIAL")) / total if total else 0

    paintings = by_dept.get("Département des Peintures", [])
    paintings_on_display_rate = (sum(1 for r in paintings if r.get("display_status") == "ON_DISPLAY") / len(paintings)) if paintings else None
    sculptures = by_dept.get("Département des Sculptures du Moyen Age, de la Renaissance et des temps modernes", [])
    sculptures_on_display_rate = (sum(1 for r in sculptures if r.get("display_status") == "ON_DISPLAY") / len(sculptures)) if sculptures else None

    print("\n\n=== FULL-COLLECTION EXTRAPOLATION ===")
    print(f"total_louvre_records (exact, from full ARK index): {total_collection}")
    print(f"estimated_on_display_objects: {round(total_collection * on_display_rate):,} ({100*on_display_rate:.1f}% sample rate)")
    print(f"estimated_on_display_with_room: {round(total_collection * on_display_with_room_rate):,} ({100*on_display_with_room_rate:.1f}% sample rate)")
    if paintings_on_display_rate is not None:
        dept_share = len(paintings) / total
        est_dept_total = round(total_collection * dept_share)
        print(f"estimated_paintings_dept_total: ~{est_dept_total:,} (dept is {100*dept_share:.1f}% of sample)")
        print(f"estimated_paintings_on_display: ~{round(est_dept_total * paintings_on_display_rate):,} ({100*paintings_on_display_rate:.1f}% of sampled paintings on display)")
    if sculptures_on_display_rate is not None:
        dept_share = len(sculptures) / total
        est_dept_total = round(total_collection * dept_share)
        print(f"estimated_sculptures_dept_total: ~{est_dept_total:,} (dept is {100*dept_share:.1f}% of sample)")
        print(f"estimated_sculptures_on_display: ~{round(est_dept_total * sculptures_on_display_rate):,} ({100*sculptures_on_display_rate:.1f}% of sampled sculptures on display)")
    print(f"estimated_visitor_relevant_dataset_size (on_display AND metadata READY/PARTIAL): {round(total_collection * visitor_relevant_rate):,} ({100*visitor_relevant_rate:.1f}% sample rate)")
    print(f"estimated_creator_wikidata_qid_coverage (blended, skewed by dept mix): {round(total_collection * qid_rate):,} records ({100*qid_rate:.1f}%)")
    print(f"estimated_recognition_asset_gap: ~{total_collection:,} (100% -- zero RecognitionAsset rows exist anywhere; this is the size of the gap, not a sample-derived estimate)")

    print("\n\n=== QID COVERAGE BY DEPARTMENT ===")
    for dept in NAMED_DEPARTMENTS:
        recs = by_dept.get(dept, [])
        if recs:
            qid_n = sum(1 for r in recs if r.get("creator_wikidata_qid"))
            print(f"  {dept}: {qid_n}/{len(recs)} ({100*qid_n/len(recs):.0f}%)")


if __name__ == "__main__":
    main()
