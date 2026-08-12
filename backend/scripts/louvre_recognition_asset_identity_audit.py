#!/usr/bin/env python3
"""Audit Louvre RecognitionAsset identity integrity.

Rights approval is not enough for recognition. This script classifies existing
Louvre asset mappings into:
  * VERIFIED
  * QUARANTINED_MISMATCH
  * UNRESOLVED

No files are deleted. No production tables are changed.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT / ".env")

ASSET_DIR = ROOT / "exports" / "louvre" / "recognition_assets"
CACHE = ASSET_DIR / "cache"
FINAL_CATALOG = ROOT / "exports" / "louvre" / "louvre_visitor_500_final.jsonl"
FINAL_MANIFEST = ROOT / "exports" / "louvre" / "louvre_wikimedia_asset_manifest_final.jsonl"
ACQUIRED = ASSET_DIR / "louvre_approved_asset_acquisition_manifest.jsonl"
OUT_JSONL = ASSET_DIR / "louvre_recognition_asset_identity_audit.jsonl"
OUT_CSV = ASSET_DIR / "louvre_recognition_asset_identity_audit.csv"
UA = "ELYIO-Louvre-recognition-asset-identity-audit/1.0"

LANDMARK_QIDS = {
    "cl010062370": "Q12418",
    "cl010252531": "Q157322",
    "cl010277627": "Q185981",
    "cl010059199": "Q212616",
    "cl010064382": "Q185255",
    "cl010091976": "Q743870",
    "cl010065720": "Q179900",
    "cl010065566": "Q431397",
    "cl010062239": "Q188880",
    "cl010065872": "Q194173",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def norm(text: str | None) -> str:
    if not text:
        return ""
    text = urllib.parse.unquote(str(text)).replace("_", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.lower()
    try:
        import unicodedata
        text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    except Exception:
        pass
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def tokens(text: str | None) -> set[str]:
    stop = {"the", "and", "with", "from", "de", "la", "le", "les", "des", "dit", "dite", "a", "of", "in", "au", "du", "un", "une", "by", "jpg", "png", "jpeg"}
    return {t for t in norm(text).split() if len(t) >= 3 and t not in stop}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def http_json(url: str, params: dict[str, str]) -> dict:
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wikidata_entities(qids: list[str]) -> dict[str, dict]:
    out = {}
    qids = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        data = http_json("https://www.wikidata.org/w/api.php", {
            "action": "wbgetentities",
            "ids": "|".join(chunk),
            "props": "claims|labels|descriptions",
            "languages": "en|fr",
            "format": "json",
        })
        out.update(data.get("entities") or {})
        time.sleep(0.2)
    return out


def claim_strings(entity: dict, prop: str) -> list[str]:
    vals = []
    for claim in entity.get("claims", {}).get(prop, []) or []:
        value = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(value, str):
            vals.append(value)
    return vals


def claim_qids(entity: dict, prop: str) -> list[str]:
    vals = []
    for claim in entity.get("claims", {}).get(prop, []) or []:
        value = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(value, dict) and value.get("numeric-id"):
            vals.append("Q" + str(value["numeric-id"]))
    return vals


def entity_label(entity: dict) -> str:
    labels = entity.get("labels") or {}
    return (labels.get("en") or labels.get("fr") or {}).get("value") or ""


def filename_from_url(url: str | None) -> str:
    if not url:
        return ""
    return urllib.parse.unquote(url.rsplit("/", 1)[-1]).split("?", 1)[0]


def local_cache_path(ark: str) -> str | None:
    path = CACHE / f"{ark}.jpg"
    return str(path.relative_to(ROOT)) if path.exists() else None


def classify(row: dict, catalog: dict, acquired_by_ark: dict, entity: dict | None) -> dict:
    ark = row["ark_id"]
    cat_title = catalog.get("title") or row.get("title")
    cat_artist = catalog.get("artist") or row.get("artist")
    filename = row.get("wikimedia_file") or filename_from_url((acquired_by_ark.get(ark) or {}).get("source_url")) or filename_from_url(row.get("wikimedia_page_url"))
    qid = row.get("wikidata_item_qid")
    label = entity_label(entity or {})
    invs = set(claim_strings(entity or {}, "P217"))
    images = set(claim_strings(entity or {}, "P18"))
    collections = set(claim_qids(entity or {}, "P195"))
    locations = set(claim_qids(entity or {}, "P276"))
    creators = set(claim_qids(entity or {}, "P170"))
    row_inv = {x for x in [catalog.get("inventory_number"), row.get("inventory_number")] if x}
    cat_terms = tokens(" ".join(str(x) for x in [cat_title, cat_artist, catalog.get("department"), catalog.get("object_type")] if x))
    source_terms = tokens(" ".join(str(x) for x in [label, filename, row.get("attribution")] if x))
    title_terms = tokens(cat_title)
    label_file_terms = tokens(" ".join([label, filename]))
    token_overlap = jaccard(cat_terms, source_terms)
    title_overlap = jaccard(title_terms, label_file_terms)
    inv_match = bool(invs and row_inv and invs.intersection(row_inv))
    louvre_linked = "Q19675" in collections or "Q19675" in locations
    p18_match = bool(filename and any(norm(filename) == norm(img) for img in images))
    landmark_qid_match = LANDMARK_QIDS.get(ark) == qid

    reasons = []
    status = "UNRESOLVED"
    if landmark_qid_match and p18_match:
        status = "VERIFIED"
        reasons.append("curated landmark Wikidata QID and P18 file agree")
    elif inv_match and louvre_linked and p18_match and (title_overlap >= 0.22 or token_overlap >= 0.18):
        status = "VERIFIED"
        reasons.append("Wikidata P217 inventory + Louvre collection/location + P18 file + title/metadata agreement")
    elif inv_match and p18_match and (title_overlap >= 0.35 or token_overlap >= 0.28):
        status = "VERIFIED"
        reasons.append("Wikidata P217 inventory + P18 file + strong title/metadata agreement")
    else:
        mismatch_signals = []
        if row.get("match_method") == "wikidata_p217_inventory_exact" and not louvre_linked:
            mismatch_signals.append("old P217 match lacks Louvre collection/location constraint")
        if qid and not inv_match and row_inv:
            mismatch_signals.append("Wikidata P217 does not match catalog inventory")
        if qid and not p18_match and filename:
            mismatch_signals.append("manifest file is not the Wikidata P18 file")
        if title_overlap < 0.08 and token_overlap < 0.08:
            mismatch_signals.append("source title/filename/attribution disagree with catalog identity")
        if len(mismatch_signals) >= 2:
            status = "QUARANTINED_MISMATCH"
            reasons.extend(mismatch_signals)
        else:
            reasons.append("insufficient strong identity evidence")

    return {
        "artwork_id": ark,
        "catalog_title": cat_title,
        "catalog_artist": cat_artist,
        "object_type": catalog.get("object_type"),
        "source_provider": "wikimedia_commons",
        "source_page": row.get("wikimedia_page_url") or (acquired_by_ark.get(ark) or {}).get("source_url"),
        "source_identifier": qid,
        "source_filename": filename,
        "local_cached_asset_path": local_cache_path(ark),
        "rights_status": row.get("rights_status") or (acquired_by_ark.get(ark) or {}).get("rights_status"),
        "license": row.get("license") or (acquired_by_ark.get(ark) or {}).get("license"),
        "match_method": row.get("match_method"),
        "wikidata_label": label,
        "wikidata_inventory": ";".join(sorted(invs)),
        "wikidata_p18": ";".join(sorted(images)),
        "wikidata_louvre_linked": louvre_linked,
        "identity_evidence": "; ".join(reasons),
        "identity_status": status,
        "token_overlap": round(token_overlap, 4),
        "title_overlap": round(title_overlap, 4),
    }


def main() -> None:
    catalog = {r["ark_id"]: r for r in read_jsonl(FINAL_CATALOG)}
    manifest = [r for r in read_jsonl(FINAL_MANIFEST) if r.get("rights_status") == "APPROVED"]
    acquired = {r["ark_id"]: r for r in read_jsonl(ACQUIRED)}
    qids = [r.get("wikidata_item_qid") for r in manifest if r.get("wikidata_item_qid")]
    entities = wikidata_entities(qids)
    rows = []
    for row in manifest:
        ark = row["ark_id"]
        rows.append(classify(row, catalog.get(ark, {}), acquired, entities.get(row.get("wikidata_item_qid"))))
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    fields = list(rows[0].keys()) if rows else []
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "assets_audited": len(rows),
        "status_counts": dict(Counter(r["identity_status"] for r in rows)),
        "jsonl": str(OUT_JSONL.relative_to(ROOT)),
        "csv": str(OUT_CSV.relative_to(ROOT)),
        "root_cause": "Original SPARQL inventory matcher accepted Wikidata P217 matches without constraining the item to Louvre collection/location and without post-validating title/creator/object agreement; inventory-like identifiers can collide across unrelated works.",
        "production_rows_modified": 0,
        "assets_deleted": 0,
    }
    (ASSET_DIR / "louvre_recognition_asset_identity_audit_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
