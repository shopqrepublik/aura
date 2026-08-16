# -*- coding: utf-8 -*-
"""Masterpiece closure pass for Louvre visitor 500.

This script only patches the approved v2 catalog with the six verified
Tier-A missing works and removes the lowest-priority Tier-C rows needed to
keep the total at exactly 500.
"""
import csv
import json
import os
import sys
from collections import Counter

import louvre_visitor_500_phase1 as phase1


REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXPORT_DIR = os.path.join(REPO_ROOT, "exports", "louvre")
NORMALIZED_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre", "normalized")

V2_JSONL = os.path.join(EXPORT_DIR, "louvre_visitor_500_v2.jsonl")
V2_ASSET_JSONL = os.path.join(EXPORT_DIR, "louvre_wikimedia_asset_manifest_v2.jsonl")
FINAL_CSV = os.path.join(EXPORT_DIR, "louvre_visitor_500_final.csv")
FINAL_JSONL = os.path.join(EXPORT_DIR, "louvre_visitor_500_final.jsonl")
FINAL_REMOVED_CSV = os.path.join(EXPORT_DIR, "louvre_visitor_500_final_removed.csv")
FINAL_ADDED_CSV = os.path.join(EXPORT_DIR, "louvre_visitor_500_final_added.csv")
FINAL_ASSET_JSONL = os.path.join(EXPORT_DIR, "louvre_wikimedia_asset_manifest_final.jsonl")
FINAL_ASSET_CSV = os.path.join(EXPORT_DIR, "louvre_wikimedia_asset_manifest_final.csv")
CLOSURE_REPORT = os.path.join(EXPORT_DIR, "louvre_masterpiece_closure_report.md")

TARGETS = [
    ("raft", "The Raft of the Medusa", "cl010059199"),
    ("cana", "The Wedding Feast at Cana", "cl010064382"),
    ("psyche", "Psyche Revived by Cupid's Kiss", "cl010091976"),
    ("coronation", "The Coronation of Napoleon", "cl010065720"),
    ("odalisque", "Grande Odalisque", "cl010065566"),
    ("horatii", "Oath of the Horatii", "cl010062239"),
]

REJECTED_ALTS = [
    ("raft_candidate_from_prompt", "cl010064841", "Rejected for the Tier A masterpiece slot: official Louvre JSON identifies this as a small oil sketch/preparatory study (`RF 2229`, description starts `Esquisse`), not the monumental visitor-facing painting. The exact full painting record verified in Phase 1C is `cl010059199` / `INV 4884`."),
    ("horatii_alt_check", "cl010064936", "Rejected: official Louvre JSON title is a different painting, `Saint Jérôme soutenant deux jeunes pendus injustement condamnés`."),
]

FIELDS = [
    "ark_id", "inventory_number", "title", "artist", "department", "room",
    "display_status", "display_status_confidence", "current_location", "source_url",
    "metadata_status", "visitor_tier", "visitor_priority_score",
    "selection_reason", "existing_production", "new_candidate",
    "commons_asset_status", "commons_match_confidence", "commons_file_page",
    "direct_media_reference", "license", "license_url", "attribution",
    "rights_status", "rights_reason", "content_readiness", "recognition_readiness",
]


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_norm(ark):
    path = os.path.join(NORMALIZED_DIR, ark + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def creator(record):
    labels = record.get("creator_labels") or []
    return labels[0] if labels else None


def obj_type(record):
    vals = record.get("object_types") or []
    return vals[0] if vals else None


def row_from_record(ark, record, seed_ids):
    score, reason = phase1.score_record(ark, record, seed_ids)
    return {
        "ark_id": ark,
        "inventory_number": record.get("inventory_number"),
        "title": record.get("title"),
        "artist": creator(record),
        "creator_wikidata_qid": record.get("creator_wikidata_qid"),
        "department": record.get("department"),
        "object_type": obj_type(record),
        "room": record.get("room"),
        "current_location": record.get("current_location_raw"),
        "source_url": record.get("source_url"),
        "display_status": record.get("display_status"),
        "display_status_confidence": record.get("display_status_confidence"),
        "metadata_status": record.get("metadata_status"),
        "visitor_tier": "A",
        "visitor_priority_score": round(score + 180, 2),
        "selection_reason": reason + "; Tier A masterpiece closure; official Louvre JSON verifies ON_DISPLAY",
        "existing_production": ark in seed_ids,
        "new_candidate": ark not in seed_ids,
        "_inventory_values": phase1.inventory_values_from_raw(ark, record),
    }


def enrich_existing_v2_row(row, seed_ids):
    record = load_norm(row["ark_id"])
    if not record:
        return row
    out = dict(row)
    out["display_status_confidence"] = record.get("display_status_confidence")
    out["current_location"] = record.get("current_location_raw")
    out["source_url"] = record.get("source_url")
    out["creator_wikidata_qid"] = record.get("creator_wikidata_qid")
    out["object_type"] = obj_type(record)
    out["_inventory_values"] = phase1.inventory_values_from_raw(row["ark_id"], record)
    out["existing_production"] = row["ark_id"] in seed_ids
    out["new_candidate"] = row["ark_id"] not in seed_ids
    return out


def parse_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).lower() == "true"


def remove_lowest_tier_c(rows, n):
    removable = [
        r for r in rows
        if r.get("visitor_tier") == "C"
        and r.get("department") != "Département des Arts de l'Islam"
    ]
    removable.sort(key=lambda r: (
        float(r.get("visitor_priority_score") or 0),
        1 if r.get("rights_status") == "APPROVED" else 0,
        r.get("ark_id") or "",
    ))
    removed_ids = {r["ark_id"] for r in removable[:n]}
    removed = []
    kept = []
    for r in rows:
        if r["ark_id"] in removed_ids:
            removed.append({
                "ark_id": r["ark_id"],
                "title": r.get("title"),
                "department": r.get("department"),
                "visitor_tier": r.get("visitor_tier"),
                "visitor_priority_score": r.get("visitor_priority_score"),
                "removal_reason": "lowest-priority Tier C row removed to admit verified Tier A masterpiece while preserving total=500",
            })
        else:
            kept.append(r)
    return kept, removed


def enrich_with_assets(rows, assets):
    by_ark = {r["ark_id"]: r for r in assets}
    out = []
    for row in rows:
        a = by_ark.get(row["ark_id"], {})
        rights = a.get("rights_status") or "NO_ASSET_FOUND"
        if rights == "APPROVED":
            recognition = "CANDIDATE_ASSET_APPROVED_NOT_IMPORTED"
        elif rights == "REVIEW_REQUIRED":
            recognition = "ASSET_REVIEW_REQUIRED"
        else:
            recognition = "NEEDS_ASSET"
        out.append({
            "ark_id": row["ark_id"],
            "inventory_number": row.get("inventory_number"),
            "title": row.get("title"),
            "artist": row.get("artist"),
            "department": row.get("department"),
            "room": row.get("room"),
            "display_status": row.get("display_status"),
            "display_status_confidence": row.get("display_status_confidence"),
            "current_location": row.get("current_location"),
            "source_url": row.get("source_url"),
            "metadata_status": row.get("metadata_status"),
            "visitor_tier": row.get("visitor_tier"),
            "visitor_priority_score": row.get("visitor_priority_score"),
            "selection_reason": row.get("selection_reason"),
            "existing_production": parse_bool(row.get("existing_production")),
            "new_candidate": parse_bool(row.get("new_candidate")),
            "commons_asset_status": rights,
            "commons_match_confidence": a.get("match_confidence") or 0,
            "commons_file_page": a.get("wikimedia_page_url"),
            "direct_media_reference": a.get("direct_media_url"),
            "license": a.get("license"),
            "license_url": a.get("license_url"),
            "attribution": a.get("attribution"),
            "rights_status": rights,
            "rights_reason": a.get("rights_reason"),
            "content_readiness": "READY" if row.get("metadata_status") == "READY" else "PARTIAL",
            "recognition_readiness": recognition,
        })
    return out


def write_csv(path, rows, fields):
    phase1.write_csv(path, rows, fields)


def write_report(final_rows, added, removed, assets, closure):
    by_ark = {r["ark_id"]: r for r in final_rows}
    asset_by_ark = {r["ark_id"]: r for r in assets}
    lines = [
        "# Louvre Visitor 500 Masterpiece Closure Report",
        "",
        "Scope: Phase 1C only resolved the six missing Tier A works. No production tables, RecognitionAssets, embeddings, or Louvre image bytes were created.",
        "",
        "## Closure Results",
        "",
        "| Work | Status | ARK | Display | Room | Commons | Rights | Included | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, expected, ark in TARGETS:
        c = closure[ark]
        final = by_ark.get(ark)
        asset = asset_by_ark.get(ark, {})
        lines.append(
            f"| {expected} | {'FOUND' if c['found'] else 'NOT FOUND'} | {ark} | "
            f"{c.get('display_status') or ''} | {c.get('room') or ''} | "
            f"{asset.get('wikimedia_page_url') or ''} | {asset.get('rights_status') or 'NO_ASSET_FOUND'} | "
            f"{'yes' if final else 'no'} | {c.get('reason') or ''} |"
        )
    lines += ["", "## Rebalance", ""]
    lines.append(f"- Added rows: {len(added)}")
    lines.append(f"- Removed rows: {len(removed)}")
    lines.append("- Removed rows are the lowest-priority Tier C entries eligible for replacement; Tier A, Tier B, and Islamic Art coverage were preserved.")
    lines += ["", "## Rejected Alternate ARKs", ""]
    for label, ark, reason in REJECTED_ALTS:
        lines.append(f"- `{ark}` ({label}): {reason}")
    lines += ["", "## Final Validation", ""]
    lines.append(f"- Final rows: {len(final_rows)}")
    lines.append(f"- Unique ARKs: {len({r['ark_id'] for r in final_rows})}")
    lines.append(f"- All ON_DISPLAY: {all(r['display_status'] == 'ON_DISPLAY' for r in final_rows)}")
    lines.append(f"- Rights distribution: {dict(Counter(r['rights_status'] for r in final_rows))}")
    lines.append(f"- Tier distribution: {dict(Counter(r['visitor_tier'] for r in final_rows))}")
    with open(CLOSURE_REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    seed_ids = phase1.load_production_seed_ids()
    v2 = [enrich_existing_v2_row(r, seed_ids) for r in load_jsonl(V2_JSONL)]
    v2_assets = load_jsonl(V2_ASSET_JSONL)
    v2_asset_by_ark = {r["ark_id"]: r for r in v2_assets}
    v2_ids = {r["ark_id"] for r in v2}
    closure = {}
    add_rows = []
    for label, expected, ark in TARGETS:
        record = load_norm(ark)
        found = record is not None and (record.get("title") or "")
        status = record.get("display_status") if record else None
        closure[ark] = {
            "label": label,
            "expected": expected,
            "found": bool(found),
            "ark_id": ark,
            "title": record.get("title") if record else None,
            "artist": creator(record) if record else None,
            "inventory_number": record.get("inventory_number") if record else None,
            "department": record.get("department") if record else None,
            "room": record.get("room") if record else None,
            "current_location": record.get("current_location_raw") if record else None,
            "display_status": status,
            "display_status_confidence": record.get("display_status_confidence") if record else None,
            "metadata_status": record.get("metadata_status") if record else None,
            "source_url": record.get("source_url") if record else None,
            "reason": "official Louvre JSON verifies ON_DISPLAY" if status == "ON_DISPLAY" else "not included because ON_DISPLAY was not verified",
        }
        if status == "ON_DISPLAY" and ark not in v2_ids:
            add_rows.append(row_from_record(ark, record, seed_ids))

    kept, removed = remove_lowest_tier_c(v2, len(add_rows))
    final_source = kept + add_rows
    final_source.sort(key=lambda r: (
        {"A": 0, "B": 1, "C": 2}.get(r.get("visitor_tier"), 9),
        -float(r.get("visitor_priority_score") or 0),
        r["ark_id"],
    ))
    new_assets = phase1.build_asset_manifest(add_rows) if add_rows else []
    new_asset_by_ark = {r["ark_id"]: r for r in new_assets}
    assets = []
    for row in final_source:
        assets.append(new_asset_by_ark.get(row["ark_id"]) or v2_asset_by_ark.get(row["ark_id"]) or {
            "ark_id": row["ark_id"],
            "inventory_number": row.get("inventory_number"),
            "title": row.get("title"),
            "artist": row.get("artist"),
            "wikidata_item_qid": None,
            "wikimedia_file": None,
            "wikimedia_page_url": None,
            "direct_media_url": None,
            "license": None,
            "license_url": None,
            "attribution": None,
            "match_method": "no_verified_match",
            "match_confidence": 0.0,
            "rights_status": "NO_ASSET_FOUND",
            "rights_reason": "No verified Wikimedia Commons asset candidate in prior or closure discovery.",
        })
    final_rows = enrich_with_assets(final_source, assets)

    added = [{
        "ark_id": r["ark_id"],
        "title": r.get("title"),
        "department": r.get("department"),
        "visitor_tier": r.get("visitor_tier"),
        "addition_reason": "verified Tier A masterpiece added in closure pass",
    } for r in add_rows]

    phase1.write_jsonl(FINAL_JSONL, final_rows)
    write_csv(FINAL_CSV, final_rows, FIELDS)
    write_csv(FINAL_REMOVED_CSV, removed, ["ark_id", "title", "department", "visitor_tier", "visitor_priority_score", "removal_reason"])
    write_csv(FINAL_ADDED_CSV, added, ["ark_id", "title", "department", "visitor_tier", "addition_reason"])
    phase1.write_jsonl(FINAL_ASSET_JSONL, assets)
    write_csv(FINAL_ASSET_CSV, assets, phase1.ASSET_FIELDS)
    write_report(final_rows, added, removed, assets, closure)

    print(json.dumps({
        "final_total": len(final_rows),
        "unique_arks": len({r["ark_id"] for r in final_rows}),
        "all_on_display": all(r["display_status"] == "ON_DISPLAY" for r in final_rows),
        "tiers": dict(Counter(r["visitor_tier"] for r in final_rows)),
        "departments": dict(Counter(r["department"] for r in final_rows)),
        "rights": dict(Counter(r["rights_status"] for r in final_rows)),
        "added": added,
        "removed_count": len(removed),
        "closure": closure,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
