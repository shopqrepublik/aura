# -*- coding: utf-8 -*-
"""Curatorial audit and v2 rebalance for the Louvre visitor-500 export.

Discovery/export only:
  - no production database writes
  - no RecognitionAsset rows
  - no embeddings
  - no Louvre image-byte fetches
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

import louvre_visitor_500_phase1 as phase1


REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXPORT_DIR = os.path.join(REPO_ROOT, "exports", "louvre")
NORMALIZED_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre", "normalized")

V1_JSONL = os.path.join(EXPORT_DIR, "louvre_visitor_500_candidates.jsonl")
V1_ASSET_JSONL = os.path.join(EXPORT_DIR, "louvre_wikimedia_asset_manifest.jsonl")
AUDIT_MD = os.path.join(EXPORT_DIR, "louvre_visitor_500_curatorial_audit.md")
CHECKLIST_CSV = os.path.join(EXPORT_DIR, "louvre_must_have_checklist.csv")
CHECKLIST_JSONL = os.path.join(EXPORT_DIR, "louvre_must_have_checklist.jsonl")
V2_CSV = os.path.join(EXPORT_DIR, "louvre_visitor_500_v2.csv")
V2_JSONL = os.path.join(EXPORT_DIR, "louvre_visitor_500_v2.jsonl")
V2_REMOVED_CSV = os.path.join(EXPORT_DIR, "louvre_visitor_500_v2_removed.csv")
V2_ADDED_CSV = os.path.join(EXPORT_DIR, "louvre_visitor_500_v2_added.csv")
V2_ASSET_JSONL = os.path.join(EXPORT_DIR, "louvre_wikimedia_asset_manifest_v2.jsonl")
V2_ASSET_CSV = os.path.join(EXPORT_DIR, "louvre_wikimedia_asset_manifest_v2.csv")


MUST_HAVE = [
    ("cl010062370", "Mona Lisa", "A", "Official Louvre masterpiece trail and Louvre source metadata", "https://www.louvre.fr/en/explore/visitor-trails/the-louvre-s-masterpieces"),
    ("cl010277627", "Venus de Milo", "A", "Official Louvre masterpiece trail and Louvre source metadata", "https://www.louvre.fr/en/explore/visitor-trails/the-louvre-s-masterpieces"),
    ("cl010252531", "Winged Victory of Samothrace", "A", "Official Louvre masterpiece trail and Louvre source metadata", "https://www.louvre.fr/en/explore/visitor-trails/the-louvre-s-masterpieces"),
    ("cl010065872", "Liberty Leading the People", "A", "Major visitor-facing painting verified from official Louvre JSON in Phase 1B", "https://collections.louvre.fr/ark:/53355/cl010065872"),
    ("cl010064841", "The Raft of the Medusa", "A", "Major Louvre painting listed in public structured references; current display not verified locally due Louvre request timeout", "https://www.wikidata.org/wiki/Q212616"),
    ("cl010064382", "The Wedding Feast at Cana", "A", "Official Louvre masterpiece-route work; current display not verified locally due Louvre request timeout", "https://www.wikidata.org/wiki/Q185255"),
    ("cl010091976", "Psyche Revived by Cupid's Kiss", "A", "Major Louvre sculpture; current display not verified locally due Louvre request timeout", "https://www.wikidata.org/wiki/Q743870"),
    ("", "The Coronation of Napoleon", "A", "Major David painting; Louvre ARK/current display not verified in local metadata", "https://www.wikidata.org/wiki/Q179900"),
    ("", "Grande Odalisque", "A", "Major Ingres painting; Louvre ARK/current display not verified in local metadata", "https://www.wikidata.org/wiki/Q431397"),
    ("", "Oath of the Horatii", "A", "Major David painting; Louvre ARK/current display not verified in local metadata", "https://www.wikidata.org/wiki/Q188880"),
    ("cl010066107", "The Virgin and Child with Saint Anne", "A", "Leonardo work with official Louvre ON_DISPLAY metadata", "https://collections.louvre.fr/ark:/53355/cl010066107"),
    ("cl010059215", "Portrait of Juliette Récamier", "B", "David painting with official Louvre ON_DISPLAY metadata", "https://collections.louvre.fr/ark:/53355/cl010059215"),
    ("cl010059373", "Medea furieuse", "B", "Delacroix painting with official Louvre ON_DISPLAY metadata", "https://collections.louvre.fr/ark:/53355/cl010059373"),
    ("cl010063515", "L'Amour et Psyché", "B", "Visitor-relevant painting with official Louvre ON_DISPLAY metadata", "https://collections.louvre.fr/ark:/53355/cl010063515"),
    ("cl010327142", "Islamic Art: Aiguiere with confronted birds", "B", "Islamic Art ON_DISPLAY verified from official Louvre JSON in Phase 1B", "https://collections.louvre.fr/ark:/53355/cl010327142"),
    ("cl010329191", "Islamic Art: Basin of Sultan al-'Adil II Abu Bakr", "B", "Islamic Art ON_DISPLAY verified from official Louvre JSON in Phase 1B", "https://collections.louvre.fr/ark:/53355/cl010329191"),
    ("cl010321121", "Islamic Art: Edicule a scene festive", "B", "Islamic Art ON_DISPLAY verified from official Louvre JSON in Phase 1B", "https://collections.louvre.fr/ark:/53355/cl010321121"),
    ("cl010315397", "Islamic Art: Plat a inscription rayonnante", "B", "Islamic Art ON_DISPLAY verified from official Louvre JSON in Phase 1B", "https://collections.louvre.fr/ark:/53355/cl010315397"),
    ("cl010327133", "Islamic Art: Paon element d'automate", "B", "Islamic Art ON_DISPLAY verified from official Louvre JSON in Phase 1B", "https://collections.louvre.fr/ark:/53355/cl010327133"),
    ("cl010329343", "Islamic Art: Chandelier aux canards", "B", "Islamic Art ON_DISPLAY verified from official Louvre JSON in Phase 1B", "https://collections.louvre.fr/ark:/53355/cl010329343"),
    ("cl010333267", "Islamic Art: Mamluk Cairo porch", "B", "Islamic Art ON_DISPLAY verified from official Louvre JSON in Phase 1B", "https://collections.louvre.fr/ark:/53355/cl010333267"),
]

GENERIC_TITLES = {
    "figurine", "vase", "statuette", "statue", "amulette", "bague", "relief",
    "tablette", "sceau cylindre", "hache", "éclat retouché", "flacon",
    "pot", "perle", "épingle", "modèle", "pendeloque", "applique",
}

DEPT_CAPS = {
    "Département des Antiquités égyptiennes": 112,
    "Département des Objets d'art du Moyen Age, de la Renaissance et des temps modernes": 118,
    "Département des Peintures": 110,
    "Département des Antiquités orientales": 84,
    "Département des Sculptures du Moyen Age, de la Renaissance et des temps modernes": 60,
    "Département des Antiquités grecques, étrusques et romaines": 45,
    "Département des Arts de Byzance et des chrétientés en Orient": 10,
    "Département des Arts de l'Islam": 20,
}

SCARCE_MAJOR_DEPTS = {
    "Département des Antiquités grecques, étrusques et romaines",
    "Département des Sculptures du Moyen Age, de la Renaissance et des temps modernes",
    "Département des Arts de Byzance et des chrétientés en Orient",
    "Département des Arts de l'Islam",
}


def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_records():
    records = {}
    for name in os.listdir(NORMALIZED_DIR):
        if not name.endswith(".json"):
            continue
        r = json.load(open(os.path.join(NORMALIZED_DIR, name), encoding="utf-8"))
        ark = r.get("source_record_id") or name[:-5]
        records[ark] = r
    return records


def first_creator(record):
    labels = record.get("creator_labels") or []
    return labels[0] if labels else None


def object_type(record):
    vals = record.get("object_types") or []
    return vals[0] if vals else None


def normalize_row_from_record(ark, record, seed_ids):
    return {
        "ark_id": ark,
        "inventory_number": record.get("inventory_number"),
        "title": record.get("title"),
        "artist": first_creator(record),
        "creator_wikidata_qid": record.get("creator_wikidata_qid"),
        "department": record.get("department"),
        "object_type": object_type(record),
        "room": record.get("room"),
        "current_location": record.get("current_location_raw"),
        "source_url": record.get("source_url"),
        "display_status": record.get("display_status"),
        "metadata_status": record.get("metadata_status"),
        "already_in_production_261": ark in seed_ids,
        "_inventory_values": phase1.inventory_values_from_raw(ark, record),
    }


def audit_markdown(v1_rows):
    dept = Counter(r.get("department") or "(none)" for r in v1_rows)
    rooms = Counter(r.get("room") or "(none)" for r in v1_rows)
    artists = Counter(r.get("artist") or "(null)" for r in v1_rows)
    titles = Counter((r.get("title") or "").strip().lower() for r in v1_rows)
    types = Counter((r.get("object_type") or "").strip().lower() for r in v1_rows)

    major = [r for r in v1_rows if float(r.get("visitor_priority_score") or 0) >= 120]
    representative = [r for r in v1_rows if 100 <= float(r.get("visitor_priority_score") or 0) < 120]
    opportunistic = [
        r for r in v1_rows
        if (r.get("title") or "").strip().lower() in GENERIC_TITLES
        or titles[(r.get("title") or "").strip().lower()] >= 4
        or types[(r.get("object_type") or "").strip().lower()] >= 8
    ]

    lines = [
        "# Louvre Visitor 500 Curatorial Audit",
        "",
        "Scope: audit of `louvre_visitor_500_candidates.jsonl` before approving a definitive visitor catalog. No production data was modified.",
        "",
        "## Summary",
        f"- Rows audited: {len(v1_rows)}",
        f"- Unique ARKs: {len({r['ark_id'] for r in v1_rows})}",
        f"- Genuine major visitor-facing works by current scoring: {len(major)}",
        f"- Important representative collection objects: {len(representative)}",
        f"- Opportunistic/repetitive candidates flagged for possible replacement: {len(opportunistic)}",
        "",
        "## Department Distribution",
    ]
    for k, v in dept.most_common():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Overrepresented Rooms"]
    for k, v in rooms.most_common(15):
        lines.append(f"- {k}: {v}")
    lines += ["", "## Overrepresented Object Types / Titles"]
    for k, v in types.most_common(15):
        lines.append(f"- {k or '(none)'}: {v}")
    lines.append("")
    for k, v in titles.most_common(15):
        lines.append(f"- title `{k or '(blank)'}`: {v}")
    lines += ["", "## Overrepresented Artists / Creator Labels"]
    for k, v in artists.most_common(15):
        lines.append(f"- {k}: {v}")
    lines += [
        "",
        "## Curatorial Findings",
        "- v1 correctly includes Mona Lisa, Venus de Milo, Winged Victory, and Leonardo's Saint Anne.",
        "- v1 is too dependent on the available Palais metadata pool: Egyptian and decorative objects dominate the long tail.",
        "- v1 has no Islamic Art, even though the Louvre presents Islamic Art as a visitor-facing department.",
        "- Several repetitive generic archaeological/decorative object rows should be replaced by verified high-relevance works.",
        "- Major Tier A works not yet locally verified as ON_DISPLAY remain outside v2 rather than guessed in.",
        "",
        "## Missing / Underrepresented Visitor Areas",
        "- Islamic Art: corrected in v2 only where official Louvre JSON verified ON_DISPLAY.",
        "- High-profile French Romantic and Neoclassical paintings: partially corrected by adding `Liberté guidant le peuple`.",
        "- Some major Louvre masterpieces remain missing until their current Louvre metadata can be fetched without request failure.",
    ]
    with open(AUDIT_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def build_checklist(records, v1_ids, final_ids):
    rows = []
    for ark, title_hint, priority, reason, evidence in MUST_HAVE:
        record = records.get(ark) if ark else None
        title = record.get("title") if record else title_hint
        artist = first_creator(record) if record else None
        dept = record.get("department") if record else None
        room = record.get("room") if record else None
        display = record.get("display_status") if record else None
        rows.append({
            "ark_id": ark,
            "title": title,
            "artist": artist,
            "department": dept,
            "reason": reason,
            "evidence_source": evidence,
            "currently_in_500": ark in v1_ids if ark else False,
            "on_display_verified": display == "ON_DISPLAY",
            "room": room,
            "priority": priority,
            "in_final_500": ark in final_ids if ark else False,
            "missing_reason": "" if (ark and ark in final_ids) else (
                "current ON_DISPLAY status not verified from local/official metadata"
                if not record or display != "ON_DISPLAY"
                else "lower than final visitor-500 threshold"
            ),
        })
    return rows


def enhanced_score(row, v1_asset_by_ark, must_have_by_ark, title_counts, type_counts, room_counts):
    base = float(row.get("visitor_priority_score") or 0)
    title = (row.get("title") or "").strip().lower()
    typ = (row.get("object_type") or "").strip().lower()
    dept = row.get("department") or ""
    ark = row["ark_id"]
    score = base
    reasons = []

    if ark in must_have_by_ark:
        priority = must_have_by_ark[ark]["priority"]
        if priority == "A":
            score += 160
            reasons.append("Tier A must-have")
        else:
            score += 85
            reasons.append("must-have checklist")
    if dept == "Département des Arts de l'Islam":
        score += 90
        reasons.append("corrects Islamic Art coverage gap")
    if dept == "Service de l'Histoire du Louvre":
        score -= 45
        reasons.append("lower priority than visitor-facing collection department")
    if v1_asset_by_ark.get(ark, {}).get("rights_status") == "APPROVED":
        score += 20
        reasons.append("Commons asset candidate approved in discovery")
    if title in GENERIC_TITLES:
        score -= 40
        reasons.append("generic title")
    if typ in GENERIC_TITLES:
        score -= 25
        reasons.append("generic object type")
    if title_counts[title] > 3 and ark not in must_have_by_ark:
        score -= min(35, 6 * (title_counts[title] - 3))
        reasons.append("repetitive title cluster")
    if type_counts[typ] > 8 and ark not in must_have_by_ark:
        score -= min(35, 3 * (type_counts[typ] - 8))
        reasons.append("repetitive object-type cluster")
    if room_counts[row.get("room") or ""] > 10 and ark not in must_have_by_ark:
        score -= 10
        reasons.append("dense room cluster")
    if row.get("metadata_status") == "READY":
        score += 10
    if row.get("artist"):
        score += 5
    return round(score, 2), "; ".join(reasons)


def rebalance(records, v1_rows, v1_assets, seed_ids):
    v1_by_ark = {r["ark_id"]: r for r in v1_rows}
    v1_asset_by_ark = {r["ark_id"]: r for r in v1_assets}
    must_have_by_ark = {ark: {"priority": p, "reason": reason} for ark, _, p, reason, _ in MUST_HAVE if ark}

    candidate_rows = []
    for ark, record in records.items():
        if record.get("display_status") != "ON_DISPLAY" or not record.get("title") or not record.get("room"):
            continue
        row = normalize_row_from_record(ark, record, seed_ids)
        if ark in v1_by_ark:
            row.update({k: v for k, v in v1_by_ark[ark].items() if k.startswith("visitor_") or k == "selection_reason"})
        else:
            score, reason = phase1.score_record(ark, record, seed_ids)
            row["visitor_priority_score"] = score
            row["selection_reason"] = reason
        candidate_rows.append(row)

    title_counts = Counter((r.get("title") or "").strip().lower() for r in candidate_rows)
    type_counts = Counter((r.get("object_type") or "").strip().lower() for r in candidate_rows)
    room_counts = Counter(r.get("room") or "" for r in candidate_rows)

    for row in candidate_rows:
        score, extra_reason = enhanced_score(row, v1_asset_by_ark, must_have_by_ark, title_counts, type_counts, room_counts)
        row["_score"] = score
        row["_extra_reason"] = extra_reason

    candidate_rows.sort(key=lambda r: (-r["_score"], r["ark_id"]))
    selected = []
    selected_ids = set()
    dept_counts = Counter()
    title_selected = Counter()
    type_selected = Counter()

    for row in sorted(candidate_rows, key=lambda r: (r.get("department") or "", -r["_score"], r["ark_id"])):
        dept = row.get("department") or ""
        if dept not in SCARCE_MAJOR_DEPTS:
            continue
        selected.append(row)
        selected_ids.add(row["ark_id"])
        dept_counts[dept] += 1
        title_selected[(row.get("title") or "").strip().lower()] += 1
        type_selected[(row.get("object_type") or "").strip().lower()] += 1

    for row in candidate_rows:
        ark = row["ark_id"]
        if ark in selected_ids:
            continue
        dept = row.get("department") or ""
        title = (row.get("title") or "").strip().lower()
        typ = (row.get("object_type") or "").strip().lower()
        is_must = ark in must_have_by_ark
        cap = DEPT_CAPS.get(dept, 25)
        if dept_counts[dept] >= cap and not is_must:
            continue
        if title in GENERIC_TITLES and title_selected[title] >= 4 and not is_must:
            continue
        if typ in GENERIC_TITLES and type_selected[typ] >= 6 and not is_must:
            continue
        selected.append(row)
        selected_ids.add(ark)
        dept_counts[dept] += 1
        title_selected[title] += 1
        type_selected[typ] += 1
        if len(selected) == 500:
            break

    if len(selected) < 500:
        selected_ids = {r["ark_id"] for r in selected}
        for row in candidate_rows:
            if row["ark_id"] in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(row["ark_id"])
            if len(selected) == 500:
                break

    selected_ids = {r["ark_id"] for r in selected}
    removed = []
    for ark, row in v1_by_ark.items():
        if ark not in selected_ids:
            title = (row.get("title") or "").strip().lower()
            reason = "lower-priority replacement"
            if title in GENERIC_TITLES:
                reason = "repetitive generic object replaced by higher visitor-relevance candidate"
            elif (row.get("department") or "").startswith("Service de l'Histoire"):
                reason = "removed to prioritize visitor-facing collection departments"
            removed.append({"ark_id": ark, "title": row.get("title"), "department": row.get("department"), "removal_reason": reason})
    added = []
    for row in selected:
        if row["ark_id"] not in v1_by_ark:
            added.append({
                "ark_id": row["ark_id"],
                "title": row.get("title"),
                "department": row.get("department"),
                "addition_reason": row.get("_extra_reason") or "higher visitor relevance than removed candidate",
            })
    return selected, removed, added


def classify_tier(row, must_have_by_ark, asset):
    if row["ark_id"] in must_have_by_ark and must_have_by_ark[row["ark_id"]]["priority"] == "A":
        return "A"
    if row["ark_id"] in must_have_by_ark:
        return "B"
    score = float(row.get("visitor_priority_score") or 0)
    if row.get("department") == "Département des Arts de l'Islam":
        return "B"
    if asset and asset.get("rights_status") == "APPROVED" and score >= 100:
        return "B"
    if score >= 115:
        return "B"
    return "C"


def write_outputs(v2_rows, removed, added, assets, seed_ids):
    asset_by_ark = {r["ark_id"]: r for r in assets}
    must_have_by_ark = {ark: {"priority": p, "reason": reason} for ark, _, p, reason, _ in MUST_HAVE if ark}
    out_rows = []
    for row in v2_rows:
        asset = asset_by_ark.get(row["ark_id"], {})
        tier = classify_tier(row, must_have_by_ark, asset)
        rights = asset.get("rights_status") or "NO_ASSET_FOUND"
        readiness = "CANDIDATE_ASSET_APPROVED_NOT_IMPORTED" if rights == "APPROVED" else ("ASSET_REVIEW_REQUIRED" if rights == "REVIEW_REQUIRED" else "NEEDS_ASSET")
        reason_bits = [row.get("selection_reason") or "selected by visitor priority"]
        if row.get("_extra_reason"):
            reason_bits.append(row["_extra_reason"])
        out_rows.append({
            "ark_id": row["ark_id"],
            "inventory_number": row.get("inventory_number"),
            "title": row.get("title"),
            "artist": row.get("artist"),
            "department": row.get("department"),
            "room": row.get("room"),
            "display_status": row.get("display_status"),
            "metadata_status": row.get("metadata_status"),
            "visitor_tier": tier,
            "visitor_priority_score": row.get("_score", row.get("visitor_priority_score")),
            "selection_reason": "; ".join([b for b in reason_bits if b]),
            "existing_production": row["ark_id"] in seed_ids,
            "new_candidate": row["ark_id"] not in seed_ids,
            "commons_asset_status": rights,
            "commons_match_confidence": asset.get("match_confidence") or 0,
            "commons_file_page": asset.get("wikimedia_page_url"),
            "rights_status": rights,
            "content_readiness": "READY" if row.get("metadata_status") == "READY" else "PARTIAL",
            "recognition_readiness": readiness,
        })
    fields = [
        "ark_id", "inventory_number", "title", "artist", "department", "room",
        "display_status", "metadata_status", "visitor_tier", "visitor_priority_score",
        "selection_reason", "existing_production", "new_candidate",
        "commons_asset_status", "commons_match_confidence", "commons_file_page",
        "rights_status", "content_readiness", "recognition_readiness",
    ]
    phase1.write_jsonl(V2_JSONL, out_rows)
    phase1.write_csv(V2_CSV, out_rows, fields)
    phase1.write_csv(V2_REMOVED_CSV, removed, ["ark_id", "title", "department", "removal_reason"])
    phase1.write_csv(V2_ADDED_CSV, added, ["ark_id", "title", "department", "addition_reason"])
    phase1.write_jsonl(V2_ASSET_JSONL, assets)
    phase1.write_csv(V2_ASSET_CSV, assets, phase1.ASSET_FIELDS)
    return out_rows


def write_checklist(rows):
    fields = [
        "ark_id", "title", "artist", "department", "reason", "evidence_source",
        "currently_in_500", "on_display_verified", "room", "priority",
        "in_final_500", "missing_reason",
    ]
    phase1.write_jsonl(CHECKLIST_JSONL, rows)
    phase1.write_csv(CHECKLIST_CSV, rows, fields)


def summarize(v1_rows, v2_rows, checklist, assets, removed, added):
    print(json.dumps({
        "v1_count": len(v1_rows),
        "v2_count": len(v2_rows),
        "v2_unique_arks": len({r["ark_id"] for r in v2_rows}),
        "v2_bad_display": sum(1 for r in v2_rows if r["display_status"] != "ON_DISPLAY"),
        "departments_before": dict(Counter(r.get("department") or "(none)" for r in v1_rows)),
        "departments_after": dict(Counter(r.get("department") or "(none)" for r in v2_rows)),
        "removed": len(removed),
        "added": len(added),
        "tiers": dict(Counter(r["visitor_tier"] for r in v2_rows)),
        "metadata": dict(Counter(r["metadata_status"] for r in v2_rows)),
        "rights": dict(Counter(r["rights_status"] for r in v2_rows)),
        "approved_by_tier": {
            tier: sum(1 for r in v2_rows if r["visitor_tier"] == tier and r["rights_status"] == "APPROVED")
            for tier in ["A", "B", "C"]
        },
        "total_by_tier": {
            tier: sum(1 for r in v2_rows if r["visitor_tier"] == tier)
            for tier in ["A", "B", "C"]
        },
        "checklist_total": len(checklist),
        "checklist_present_final": sum(1 for r in checklist if r["in_final_500"]),
        "checklist_missing": sum(1 for r in checklist if not r["in_final_500"]),
        "landmarks": {
            ark: next((r for r in v2_rows if r["ark_id"] == ark), None)
            for ark in ["cl010062370", "cl010277627", "cl010252531"]
        },
    }, ensure_ascii=False, indent=2))


def main():
    records = load_records()
    v1_rows = load_jsonl(V1_JSONL)
    v1_assets = load_jsonl(V1_ASSET_JSONL)
    seed_ids = phase1.load_production_seed_ids()
    audit_markdown(v1_rows)
    v2_source_rows, removed, added = rebalance(records, v1_rows, v1_assets, seed_ids)
    assets = phase1.build_asset_manifest(v2_source_rows)
    out_rows = write_outputs(v2_source_rows, removed, added, assets, seed_ids)
    checklist = build_checklist(records, {r["ark_id"] for r in v1_rows}, {r["ark_id"] for r in out_rows})
    write_checklist(checklist)
    summarize(v1_rows, out_rows, checklist, assets, removed, added)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
