# -*- coding: utf-8 -*-
"""Build a metadata-only Louvre visitor-500 candidate export.

This is a discovery/export script only. It never writes production DB rows,
never fetches Louvre image URLs, and never downloads Wikimedia image bytes.

Inputs:
  - backend/data/louvre/checkpoints/on_display_enum_progress.json
  - backend/data/louvre/raw/*.json
  - backend/data/louvre/normalized/*.json
  - exports/louvre/louvre_on_display_sample.csv

Optional network:
  - targeted official Louvre JSON metadata for ARKs already discovered by the
    Louvre Palais location list-view workflow, only until 500 ON_DISPLAY records
    are available locally.
  - Wikidata/Commons metadata APIs for image-license discovery.
"""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

import louvre_import


REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre")
RAW_DIR = os.path.join(DATA_DIR, "raw")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")
CHECKPOINT_DIR = os.path.join(DATA_DIR, "checkpoints")
EXPORT_DIR = os.path.join(REPO_ROOT, "exports", "louvre")

PALACE_PROGRESS_PATH = os.path.join(CHECKPOINT_DIR, "on_display_enum_progress.json")
PROD_261_PATH = os.path.join(EXPORT_DIR, "louvre_on_display_sample.csv")
FETCH_LOG_PATH = os.path.join(EXPORT_DIR, "louvre_visitor_500_new_fetches.jsonl")
VISITOR_JSONL = os.path.join(EXPORT_DIR, "louvre_visitor_500_candidates.jsonl")
VISITOR_CSV = os.path.join(EXPORT_DIR, "louvre_visitor_500_candidates.csv")
ASSET_JSONL = os.path.join(EXPORT_DIR, "louvre_wikimedia_asset_manifest.jsonl")
ASSET_CSV = os.path.join(EXPORT_DIR, "louvre_wikimedia_asset_manifest.csv")

TARGET = 500
COURTESY_DELAY_S = louvre_import.COURTESY_DELAY_S
HTTP_UA = "AURA-MVP-backend/1.0 (metadata-only Louvre visitor-500 discovery)"

LANDMARKS = {
    "cl010062370": "Mona Lisa",
    "cl010277627": "Venus de Milo",
    "cl010252531": "Winged Victory of Samothrace",
}

LANDMARK_WIKIDATA = {
    "cl010062370": "Q12418",
    "cl010277627": "Q151952",
    "cl010252531": "Q216402",
}

MAJOR_TERMS = [
    ("joconde", "landmark masterpiece"),
    ("mona lisa", "landmark masterpiece"),
    ("vénus de milo", "landmark masterpiece"),
    ("venus de milo", "landmark masterpiece"),
    ("victoire de samothrace", "landmark masterpiece"),
    ("samothrace", "landmark masterpiece"),
    ("liberté guidant le peuple", "major painting"),
    ("radeau de la méduse", "major painting"),
    ("sacre de l'empereur napoléon", "major painting"),
    ("noces de cana", "major painting"),
    ("grande odalisque", "major painting"),
    ("serment des horaces", "major painting"),
    ("sabines", "major painting"),
    ("sardanapale", "major painting"),
    ("dentellière", "major painting"),
    ("hammurabi", "major ancient object"),
    ("scribe", "major ancient object"),
    ("taureau", "major ancient object"),
    ("lamassu", "major ancient object"),
    ("marly", "prominent sculpture court"),
    ("marley", "prominent sculpture court"),
    ("psyché", "prominent sculpture"),
    ("psyche", "prominent sculpture"),
]

DEPARTMENT_TARGETS = {
    "Département des Peintures": 95,
    "Département des Sculptures du Moyen Age, de la Renaissance et des temps modernes": 55,
    "Département des Antiquités grecques, étrusques et romaines": 70,
    "Département des Antiquités égyptiennes": 90,
    "Département des Antiquités orientales": 65,
    "Département des Objets d'art du Moyen Age, de la Renaissance et des temps modernes": 75,
    "Département des Arts de l'Islam": 30,
    "Département des Arts de Byzance et des chrétientés en Orient": 10,
}

VISITOR_FIELDS = [
    "ark_id",
    "inventory_number",
    "title",
    "artist",
    "creator_wikidata_qid",
    "department",
    "object_type",
    "room",
    "current_location",
    "source_url",
    "display_status",
    "metadata_status",
    "visitor_priority_score",
    "selection_reason",
    "already_in_production_261",
]

ASSET_FIELDS = [
    "ark_id",
    "inventory_number",
    "title",
    "artist",
    "wikidata_item_qid",
    "wikimedia_file",
    "wikimedia_page_url",
    "direct_media_url",
    "license",
    "license_url",
    "attribution",
    "match_method",
    "match_confidence",
    "rights_status",
    "rights_reason",
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_production_seed_ids():
    ids = set()
    with open(PROD_261_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ids.add(row["ark_id"])
    return ids


def load_palais_candidates():
    data = load_json(PALACE_PROGRESS_PATH)
    return list(dict.fromkeys(data.get("ark_ids") or []))


def load_normalized_records():
    records = {}
    for name in os.listdir(NORMALIZED_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(NORMALIZED_DIR, name)
        r = load_json(path)
        ark_id = r.get("source_record_id") or r.get("ark_id") or name[:-5]
        records[ark_id] = r
    return records


def fetch_and_normalize_missing_palais(records, palais_ids, target=TARGET):
    """Fetch official Louvre JSON metadata only until enough ON_DISPLAY rows exist."""
    fetched = 0
    os.makedirs(EXPORT_DIR, exist_ok=True)
    on_display = {a for a, r in records.items() if r.get("display_status") == "ON_DISPLAY"}
    if len(on_display) >= target:
        return fetched

    with open(FETCH_LOG_PATH, "a", encoding="utf-8") as log:
        for ark_id in palais_ids:
            if len(on_display) >= target:
                break
            if ark_id in records:
                continue

            raw_path = os.path.join(RAW_DIR, f"{ark_id}.json")
            norm_path = os.path.join(NORMALIZED_DIR, f"{ark_id}.json")
            if os.path.exists(raw_path):
                raw = load_json(raw_path)
            else:
                url = f"https://collections.louvre.fr/ark:/53355/{ark_id}.json"
                body, status = louvre_import.fetch_with_retry(url)
                if status == 404:
                    log.write(json.dumps({"ark_id": ark_id, "status": 404}, ensure_ascii=False) + "\n")
                    log.flush()
                    continue
                with open(raw_path, "wb") as f:
                    f.write(body)
                raw = json.loads(body.decode("utf-8"))
                fetched += 1
                log.write(json.dumps({"ark_id": ark_id, "status": status, "url": url}, ensure_ascii=False) + "\n")
                log.flush()
                time.sleep(COURTESY_DELAY_S)

            normalized = louvre_import.normalize_record(raw)
            write_json(norm_path, normalized)
            records[ark_id] = normalized
            if normalized.get("display_status") == "ON_DISPLAY":
                on_display.add(ark_id)
            print(
                f"[louvre fetch {fetched}] {ark_id}: display={normalized.get('display_status')} "
                f"local_on_display={len(on_display)}",
                flush=True,
            )
    return fetched


def first_text(value):
    if isinstance(value, list):
        return next((str(v) for v in value if v), None)
    return value


def creator_label(record):
    labels = record.get("creator_labels") or []
    return labels[0] if labels else None


def object_type(record):
    vals = record.get("object_types") or []
    return vals[0] if vals else None


def inventory_values_from_raw(ark_id, normalized):
    values = []
    raw_path = os.path.join(RAW_DIR, f"{ark_id}.json")
    if os.path.exists(raw_path):
        try:
            raw = load_json(raw_path)
            for n in raw.get("objectNumber") or []:
                v = n.get("value")
                if v:
                    values.append(v)
        except Exception:
            pass
    inv = normalized.get("inventory_number")
    if inv:
        values.insert(0, inv)
    seen = set()
    return [v for v in values if not (v in seen or seen.add(v))]


def score_record(ark_id, record, production_seed):
    title = (record.get("title") or "").strip()
    haystack = " ".join([
        title,
        record.get("title_complement") or "",
        creator_label(record) or "",
        record.get("department") or "",
        record.get("room") or "",
        record.get("current_location_raw") or "",
        object_type(record) or "",
    ]).lower()
    score = 50.0
    reasons = ["confirmed ON_DISPLAY by existing Louvre classifier"]
    if ark_id in LANDMARKS:
        score += 100
        reasons.append(LANDMARKS[ark_id])
    if ark_id in production_seed:
        score += 12
        reasons.append("retained from production 261 seed set")
    if record.get("metadata_status") == "READY":
        score += 10
        reasons.append("READY metadata")
    elif record.get("metadata_status") == "PARTIAL":
        score += 4
        reasons.append("PARTIAL metadata")
    if record.get("room"):
        score += 8
        reasons.append("specific public room evidence")
    if record.get("image_count", 0):
        score += min(8, int(record.get("image_count", 0)) * 2)
        reasons.append("Louvre image reference metadata exists")
    if creator_label(record):
        score += 6
        reasons.append("creator label present")
    if record.get("creator_wikidata_qid"):
        score += 6
        reasons.append("creator Wikidata QID present")
    if record.get("inventory_number"):
        score += 5
        reasons.append("inventory number present")
    for term, reason in MAJOR_TERMS:
        if term in haystack:
            score += 30
            reasons.append(reason)
            break
    dept = record.get("department") or ""
    if dept in DEPARTMENT_TARGETS:
        score += 5
        reasons.append("major visitor department")
    # Penalize generic untitled fragments when not in the seed set.
    if ark_id not in production_seed and title.lower() in {"fragment", "vase", "coupe", "statue", "statuette"}:
        score -= 8
        reasons.append("generic title")
    return round(score, 2), "; ".join(dict.fromkeys(reasons))


def select_visitor_catalog(records, production_seed, target=TARGET):
    on_display = {
        ark: r for ark, r in records.items()
        if r.get("display_status") == "ON_DISPLAY" and r.get("title") and r.get("room")
    }
    scored = []
    for ark, record in on_display.items():
        score, reason = score_record(ark, record, production_seed)
        scored.append((ark, record, score, reason))

    selected = {}
    for ark in sorted((a for a in production_seed if a in on_display)):
        r = on_display[ark]
        score, reason = score_record(ark, r, production_seed)
        selected[ark] = (r, score, reason)

    by_dept = defaultdict(list)
    for ark, record, score, reason in scored:
        if ark in selected:
            continue
        by_dept[record.get("department") or "(none)"].append((ark, record, score, reason))
    for dept in by_dept:
        by_dept[dept].sort(key=lambda x: (-x[2], x[0]))

    # Add high-scoring records per major department first, then fill globally.
    for dept, quota in DEPARTMENT_TARGETS.items():
        desired = max(0, min(quota, len(by_dept.get(dept, []))))
        current = sum(1 for r, _, _ in selected.values() if r.get("department") == dept)
        for item in by_dept.get(dept, [])[: max(0, desired - current)]:
            if len(selected) >= target:
                break
            selected[item[0]] = (item[1], item[2], item[3])
        if len(selected) >= target:
            break

    if len(selected) < target:
        for ark, record, score, reason in sorted(scored, key=lambda x: (-x[2], x[0])):
            if len(selected) >= target:
                break
            selected.setdefault(ark, (record, score, reason))

    rows = []
    for ark, (record, score, reason) in selected.items():
        rows.append({
            "ark_id": ark,
            "inventory_number": record.get("inventory_number"),
            "title": record.get("title"),
            "artist": creator_label(record),
            "creator_wikidata_qid": record.get("creator_wikidata_qid"),
            "department": record.get("department"),
            "object_type": object_type(record),
            "room": record.get("room"),
            "current_location": record.get("current_location_raw"),
            "source_url": record.get("source_url"),
            "display_status": record.get("display_status"),
            "metadata_status": record.get("metadata_status"),
            "visitor_priority_score": score,
            "selection_reason": reason,
            "already_in_production_261": ark in production_seed,
            "_inventory_values": inventory_values_from_raw(ark, record),
        })
    rows.sort(key=lambda r: (-float(r["visitor_priority_score"]), r["ark_id"]))
    return rows[:target]


def compact_csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_jsonl(path, rows, fields_to_drop=None):
    fields_to_drop = set(fields_to_drop or [])
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            out = {k: v for k, v in row.items() if k not in fields_to_drop}
            f.write(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: compact_csv_value(row.get(k)) for k in fields})


def http_json(url, params=None, retries=3, method="GET"):
    if params:
        encoded_params = urllib.parse.urlencode(params).encode("utf-8")
    else:
        encoded_params = None
    if params and method == "GET":
        url = url + "?" + urllib.parse.urlencode(params)
        encoded_params = None
    last_err = None
    for attempt in range(1, retries + 1):
        headers = {"User-Agent": HTTP_UA, "Accept": "application/json"}
        if method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=encoded_params, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and attempt < retries:
                retry_after = e.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else 65
                print(f"[metadata rate limit] HTTP 429, waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
        except Exception as e:
            last_err = e
            time.sleep(2 * attempt)
    raise RuntimeError(f"metadata request failed after {retries} attempts: {last_err}")


def sparql_inventory_matches(rows):
    inv_to_arks = defaultdict(list)
    for row in rows:
        for inv in row.get("_inventory_values") or []:
            if inv:
                inv_to_arks[inv].append(row["ark_id"])
    matches = defaultdict(list)
    inventories = list(inv_to_arks.keys())
    endpoint = "https://query.wikidata.org/sparql"
    for i in range(0, len(inventories), 900):
        chunk = inventories[i:i + 900]
        values = " ".join(json.dumps(v, ensure_ascii=False) for v in chunk)
        query = f"""
SELECT ?item ?inventory ?image WHERE {{
  VALUES ?inventory {{ {values} }}
  ?item wdt:P217 ?inventory .
  OPTIONAL {{ ?item wdt:P195 ?collection. }}
  OPTIONAL {{ ?item wdt:P276 ?location. }}
  OPTIONAL {{ ?item wdt:P18 ?image. }}
}}
"""
        data = http_json(endpoint, {"query": query, "format": "json"}, method="POST")
        for b in data.get("results", {}).get("bindings", []):
            inv = b.get("inventory", {}).get("value")
            collection = b.get("collection", {}).get("value", "").rsplit("/", 1)[-1]
            location = b.get("location", {}).get("value", "").rsplit("/", 1)[-1]
            if collection != "Q19675" and location != "Q19675":
                continue
            for ark in inv_to_arks.get(inv, []):
                matches[ark].append({
                    "wikidata_item_qid": b.get("item", {}).get("value", "").rsplit("/", 1)[-1],
                    "wikidata_label": None,
                    "inventory": inv,
                    "image": b.get("image", {}).get("value"),
                    "creator": None,
                    "match_method": "wikidata_p217_inventory_exact",
                    "match_confidence": 0.9,
                })
        print(f"[wikidata inventory] {min(i+900, len(inventories))}/{len(inventories)} inventories", flush=True)
        if i + 900 < len(inventories):
            time.sleep(65)
    return matches


def commons_filename_from_url(url):
    if not url:
        return None
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    return name.replace(" ", "_")


def commons_imageinfo(filename):
    if not filename:
        return None
    title = "File:" + filename
    data = http_json("https://commons.wikimedia.org/w/api.php", {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "format": "json",
    })
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    infos = page.get("imageinfo") or []
    return infos[0] if infos else None


def commons_batch_imageinfo(filenames):
    out = {}
    unique = [f for f in dict.fromkeys(filenames) if f]
    for i in range(0, len(unique), 40):
        chunk = unique[i:i + 40]
        titles = "|".join("File:" + name for name in chunk)
        try:
            data = http_json("https://commons.wikimedia.org/w/api.php", {
                "action": "query",
                "titles": titles,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "format": "json",
            })
        except Exception as e:
            print(f"[commons batch skipped] {i + 1}-{i + len(chunk)}: {e}", flush=True)
            continue
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            title = page.get("title", "")
            filename = title[5:] if title.startswith("File:") else title
            infos = page.get("imageinfo") or []
            if infos:
                out[filename.replace(" ", "_")] = infos[0]
        print(f"[commons batch] {min(i + 40, len(unique))}/{len(unique)} files", flush=True)
        time.sleep(0.2)
    return out


def claim_entity_ids(entity, prop):
    ids = []
    for claim in entity.get("claims", {}).get(prop, []) or []:
        snak = claim.get("mainsnak") or {}
        value = (snak.get("datavalue") or {}).get("value")
        if isinstance(value, dict) and "numeric-id" in value:
            ids.append("Q" + str(value["numeric-id"]))
    return ids


def claim_strings(entity, prop):
    vals = []
    for claim in entity.get("claims", {}).get(prop, []) or []:
        snak = claim.get("mainsnak") or {}
        value = (snak.get("datavalue") or {}).get("value")
        if isinstance(value, str):
            vals.append(value)
    return vals


def wikidata_entities(qids):
    if not qids:
        return {}
    data = http_json("https://www.wikidata.org/w/api.php", {
        "action": "wbgetentities",
        "ids": "|".join(qids),
        "props": "claims|labels|descriptions",
        "languages": "en|fr",
        "format": "json",
    })
    return data.get("entities", {})


def wikidata_search_title(row):
    title = row.get("title") or ""
    searches = []
    if row["ark_id"] in LANDMARKS:
        searches.append(LANDMARKS[row["ark_id"]])
    if title:
        searches.append(title)
        # The Mona Lisa source title is long; search the common embedded name too.
        for term, _ in MAJOR_TERMS:
            if term in title.lower():
                searches.append(term)
    seen = set()
    search_terms = [s for s in searches if not (s in seen or seen.add(s))]
    qids = []
    for term in search_terms[:3]:
        data = http_json("https://www.wikidata.org/w/api.php", {
            "action": "wbsearchentities",
            "search": term,
            "language": "en",
            "format": "json",
            "limit": 7,
        })
        for hit in data.get("search", []) or []:
            qid = hit.get("id")
            if qid and qid not in qids:
                qids.append(qid)
        if qids:
            break
        time.sleep(0.1)
    entities = wikidata_entities(qids[:10])
    return entities


def image_match_from_entity(row, qid, entity, method_hint):
    collections = claim_entity_ids(entity, "P195")
    locations = claim_entity_ids(entity, "P276")
    invs = set(claim_strings(entity, "P217"))
    row_invs = set(row.get("_inventory_values") or [])
    if (
        qid != LANDMARK_WIKIDATA.get(row["ark_id"])
        and "Q19675" not in collections
        and "Q19675" not in locations
        and not (invs and row_invs and invs.intersection(row_invs))
    ):
        return None
    images = claim_strings(entity, "P18")
    if not images:
        return None
    creators = set(claim_entity_ids(entity, "P170"))
    creator_qid = row.get("creator_wikidata_qid")

    label = None
    labels = entity.get("labels") or {}
    if "en" in labels:
        label = labels["en"].get("value")
    elif "fr" in labels:
        label = labels["fr"].get("value")

    confidence = 0.78
    method = "wikidata_title_collection_louvre"
    reasons = ["Wikidata entity is in collection Louvre"]
    if qid == LANDMARK_WIKIDATA.get(row["ark_id"]):
        confidence = 0.98
        method = "curated_landmark_wikidata_qid"
        reasons.append("curated landmark QID")
    elif invs and row_invs and invs.intersection(row_invs):
        confidence = 0.95
        method = "wikidata_title_then_p217_inventory_exact_p195_louvre"
        reasons.append("inventory number agrees")
    elif creator_qid and creator_qid in creators:
        confidence = 0.88
        method = "wikidata_title_creator_p195_louvre"
        reasons.append("creator QID agrees")
    elif method_hint:
        reasons.append(method_hint)

    return {
        "wikidata_item_qid": qid,
        "wikidata_label": label,
        "inventory": next(iter(invs), None),
        "image": "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(images[0].replace(" ", "_")),
        "creator": None,
        "match_method": method,
        "match_confidence": confidence,
        "match_reason": "; ".join(reasons),
    }


def fallback_wikidata_match(row):
    qid = LANDMARK_WIKIDATA.get(row["ark_id"])
    if qid:
        entities = wikidata_entities([qid])
        entity = entities.get(qid)
        if entity:
            match = image_match_from_entity(row, qid, entity, "landmark")
            if match:
                return match

    entities = wikidata_search_title(row)
    valid = []
    for cand_qid, entity in entities.items():
        match = image_match_from_entity(row, cand_qid, entity, None)
        if match:
            valid.append(match)
    valid.sort(key=lambda m: -m["match_confidence"])
    if valid:
        return valid[0]
    return None


def clean_meta_value(meta, key):
    val = (meta or {}).get(key, {})
    if isinstance(val, dict):
        return val.get("value")
    return val


def classify_commons_rights(meta):
    license_short = (clean_meta_value(meta, "LicenseShortName") or "").strip()
    license_url = clean_meta_value(meta, "LicenseUrl")
    usage_terms = (clean_meta_value(meta, "UsageTerms") or "").strip()
    copyrighted = (clean_meta_value(meta, "Copyrighted") or "").strip().lower()
    restrictions = (clean_meta_value(meta, "Restrictions") or "").strip().lower()
    hay = " ".join([license_short, usage_terms, copyrighted, restrictions]).lower()

    if any(term in hay for term in ["noncommercial", "non-commercial", "no derivatives", "no derivative"]):
        return "REJECTED", f"Commons metadata indicates incompatible restriction: {license_short or usage_terms}"
    approved_terms = ["public domain", "cc0", "cc by", "cc-by", "cc by-sa", "cc-by-sa", "pd-art"]
    if any(term in hay for term in approved_terms) and license_url:
        return "APPROVED", f"Commons license metadata is clear: {license_short or usage_terms}"
    if copyrighted == "false" and (license_short or usage_terms):
        return "APPROVED", f"Commons marks file as not copyrighted with license: {license_short or usage_terms}"
    return "REVIEW_REQUIRED", f"Commons rights metadata is ambiguous: license={license_short!r}, usage={usage_terms!r}, copyrighted={copyrighted!r}"


def build_asset_manifest(rows):
    matches = sparql_inventory_matches(rows)
    chosen_by_ark = {}
    for idx, row in enumerate(rows, 1):
        candidates = sorted(matches.get(row["ark_id"], []), key=lambda m: -m["match_confidence"])
        chosen = next((m for m in candidates if m.get("image")), candidates[0] if candidates else None)
        if (not chosen or not chosen.get("image")) and row["ark_id"] in LANDMARK_WIKIDATA:
            try:
                chosen = fallback_wikidata_match(row)
            except Exception as e:
                print(f"[wikidata fallback skipped] {row['ark_id']}: {e}", flush=True)
        chosen_by_ark[row["ark_id"]] = chosen

    filenames = [
        commons_filename_from_url(chosen.get("image"))
        for chosen in chosen_by_ark.values()
        if chosen and chosen.get("image")
    ]
    commons_infos = commons_batch_imageinfo(filenames)

    manifest = []
    for idx, row in enumerate(rows, 1):
        chosen = chosen_by_ark.get(row["ark_id"])
        if not chosen or not chosen.get("image"):
            manifest.append({
                "ark_id": row["ark_id"],
                "inventory_number": row.get("inventory_number"),
                "title": row.get("title"),
                "artist": row.get("artist"),
                "wikidata_item_qid": chosen.get("wikidata_item_qid") if chosen else None,
                "wikimedia_file": None,
                "wikimedia_page_url": None,
                "direct_media_url": None,
                "license": None,
                "license_url": None,
                "attribution": None,
                "match_method": chosen.get("match_method") if chosen else "no_verified_inventory_match",
                "match_confidence": chosen.get("match_confidence") if chosen else 0.0,
                "rights_status": "NO_ASSET_FOUND",
                "rights_reason": "No Wikimedia Commons P18 image found through exact Louvre inventory-number match.",
            })
            continue
        filename = commons_filename_from_url(chosen.get("image"))
        info = commons_infos.get(filename)
        meta = (info or {}).get("extmetadata") or {}
        rights_status, rights_reason = classify_commons_rights(meta)
        if rights_status == "APPROVED" and float(chosen.get("match_confidence") or 0) < 0.85:
            rights_status = "REVIEW_REQUIRED"
            rights_reason = "Rights metadata is reusable, but the artwork match is below the approval-confidence threshold."
        manifest.append({
            "ark_id": row["ark_id"],
            "inventory_number": row.get("inventory_number"),
            "title": row.get("title"),
            "artist": row.get("artist"),
            "wikidata_item_qid": chosen.get("wikidata_item_qid"),
            "wikimedia_file": filename,
            "wikimedia_page_url": (info or {}).get("descriptionurl"),
            "direct_media_url": (info or {}).get("url"),
            "license": clean_meta_value(meta, "LicenseShortName") or clean_meta_value(meta, "UsageTerms"),
            "license_url": clean_meta_value(meta, "LicenseUrl"),
            "attribution": clean_meta_value(meta, "Attribution") or clean_meta_value(meta, "Artist") or clean_meta_value(meta, "Credit"),
            "match_method": chosen.get("match_method"),
            "match_confidence": chosen.get("match_confidence"),
            "rights_status": rights_status,
            "rights_reason": rights_reason,
        })
        print(f"[commons] {idx}/{len(rows)} {row['ark_id']} {rights_status}", flush=True)
        time.sleep(0.2)
    return manifest


def validate_outputs(visitor_rows, manifest, fetched_count):
    counts = {
        "visitor_total": len(visitor_rows),
        "visitor_unique_ark": len({r["ark_id"] for r in visitor_rows}),
        "visitor_on_display_bad": sum(1 for r in visitor_rows if r["display_status"] != "ON_DISPLAY"),
        "production_seed_retained": sum(1 for r in visitor_rows if r["already_in_production_261"]),
        "production_seed_excluded": len(load_production_seed_ids()) - sum(1 for r in visitor_rows if r["already_in_production_261"]),
        "new_json_records_fetched": fetched_count,
        "manifest_total": len(manifest),
        "manifest_unique_ark": len({r["ark_id"] for r in manifest}),
        "departments": Counter(r["department"] or "(none)" for r in visitor_rows),
        "metadata": Counter(r["metadata_status"] or "(none)" for r in visitor_rows),
        "rights": Counter(r["rights_status"] or "(none)" for r in manifest),
        "high_confidence_matches": sum(1 for r in manifest if float(r.get("match_confidence") or 0) >= 0.9 and r.get("wikimedia_file")),
        "landmarks": {},
    }
    visitor_by_ark = {r["ark_id"]: r for r in visitor_rows}
    manifest_by_ark = {r["ark_id"]: r for r in manifest}
    for ark, name in LANDMARKS.items():
        counts["landmarks"][ark] = {
            "name": name,
            "in_visitor_500": ark in visitor_by_ark,
            "rights_status": manifest_by_ark.get(ark, {}).get("rights_status"),
            "wikimedia_file": manifest_by_ark.get(ark, {}).get("wikimedia_file"),
        }
    return counts


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    production_seed = load_production_seed_ids()
    palais_ids = load_palais_candidates()
    records = load_normalized_records()
    before_on_display = sum(1 for r in records.values() if r.get("display_status") == "ON_DISPLAY")
    fetched_count = fetch_and_normalize_missing_palais(records, palais_ids, TARGET)
    after_on_display = sum(1 for r in records.values() if r.get("display_status") == "ON_DISPLAY")
    visitor_rows = select_visitor_catalog(records, production_seed, TARGET)
    manifest = build_asset_manifest(visitor_rows)

    write_jsonl(VISITOR_JSONL, visitor_rows, fields_to_drop={"_inventory_values"})
    write_csv(VISITOR_CSV, visitor_rows, VISITOR_FIELDS)
    write_jsonl(ASSET_JSONL, manifest)
    write_csv(ASSET_CSV, manifest, ASSET_FIELDS)

    counts = validate_outputs(visitor_rows, manifest, fetched_count)
    counts["before_local_on_display"] = before_on_display
    counts["after_local_on_display"] = after_on_display
    print(json.dumps(counts, ensure_ascii=False, indent=2, default=dict), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
