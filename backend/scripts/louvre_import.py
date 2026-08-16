# -*- coding: utf-8 -*-
"""Resumable, bounded importer for Louvre Collections (collections.louvre.fr)
Layer-1 metadata -- see docs/louvre-source-audit.md (Phase 0) and
docs/louvre-schema.md (Phase 1) for the full rationale.

HARD RULE, enforced by construction, not just by convention: this script
never issues a request to any Louvre *image* URL. It reads image[] entries
out of the JSON payload it already has in hand (bundled with the record's
own metadata response) and writes them as LouvreImageReference-shaped
records -- metadata only, url strings, never fetched bytes. See
docs/louvre-source-audit.md SS12-13 for why (ADAGP's explicit AI/TDM
prohibition; robots.txt's named block on Anthropic/Claude bots on image
files).

Stages, each resumable independently via the checkpoint file:
  1. discover  -- parse the sitemap index + one sub-sitemap, extract unique
                   ARK ids in document order.
  2. fetch     -- one record at a time (concurrency=1), retry with backoff
                   on transient errors, hard-stop (not retry) on 403.
  3. raw store -- write raw/{arkId}.json immediately on success, before any
                   normalization -- normalization bugs can never corrupt or
                   lose the raw archive.
  4. normalize -- extract fields, classify along THREE INDEPENDENT
                   dimensions (display_status / metadata_status /
                   recognition_status -- an object can be ON_DISPLAY +
                   READY metadata + NEEDS_ASSET all at once, these are
                   never collapsed into one enum), write
                   normalized/{arkId}.json.

Usage (from repo root):
    venv/Scripts/python.exe backend/scripts/louvre_import.py --limit 100
    venv/Scripts/python.exe backend/scripts/louvre_import.py --limit 1000
(safe to re-run with a higher --limit; already-processed ARK ids are
skipped via the checkpoint file, never re-fetched or double-counted)
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "backend", "data", "louvre")
RAW_DIR = os.path.join(DATA_DIR, "raw")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")
ERRORS_PATH = os.path.join(DATA_DIR, "errors", "errors.jsonl")
CHECKPOINT_PATH = os.path.join(DATA_DIR, "checkpoints", "checkpoint.json")
DISCOVERED_ARKS_PATH = os.path.join(DATA_DIR, "checkpoints", "discovered_arks.json")

UA = "AURA-MVP-backend/1.0 (contact: repo owner; research/museum-app project)"
SITEMAP_INDEX = "https://collections.louvre.fr/sitemap.xml"
COURTESY_DELAY_S = 1.5
MAX_ATTEMPTS = 4

# NOTE: an earlier version of this script had a coarse ADAGP-named-artist
# substring heuristic here, used to set an authoritative "restricted"
# classification. Removed per explicit product decision -- guessing rights
# status from a creator-name substring match is not evidence. Rights
# analysis is now a separate future pipeline; see classify_image_rights()
# below for what this script actually asserts (conservatively) instead.


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)


def fetch_with_retry(url):
    """Retries transient errors with backoff. A 403 is treated as an
    explicit access-control signal, not a transient failure -- raised
    immediately so the caller can hard-stop the whole run, per the
    project's own "don't bypass access controls" rule."""
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with http_get(url) as resp:
                return resp.read(), resp.status
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise PermissionError(f"403 from {url} -- treating as explicit access-control signal, not retrying")
            last_err = f"HTTP {e.code}: {e.reason}"
            if e.code == 404:
                return None, 404  # permanent, not transient -- don't retry
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"{type(e).__name__}: {e}"
        wait = 5 * attempt
        print(f"    retry {attempt}/{MAX_ATTEMPTS} after: {last_err} (waiting {wait}s)")
        time.sleep(wait)
    raise RuntimeError(f"failed after {MAX_ATTEMPTS} attempts: {last_err}")


def discover_ark_ids(min_count):
    """Parses the sitemap index, then as many sub-sitemaps as needed to
    reach min_count unique ARK ids, in document order. Cached to disk so
    repeated runs (100 -> 1000) don't re-parse the sitemap every time."""
    if os.path.exists(DISCOVERED_ARKS_PATH):
        with open(DISCOVERED_ARKS_PATH, encoding="utf-8") as f:
            cached = json.load(f)
        if len(cached) >= min_count:
            return cached

    print("Discovering ARK ids from sitemap...")
    index_body, _ = fetch_with_retry(SITEMAP_INDEX)
    sub_sitemaps = re.findall(r"<loc>([^<]+)</loc>", index_body.decode("utf-8"))
    print(f"  sitemap index lists {len(sub_sitemaps)} sub-sitemaps")

    seen = set()
    ordered_ids = []
    for sub_url in sub_sitemaps:
        if len(ordered_ids) >= min_count:
            break
        print(f"  parsing {sub_url} ...")
        body, _ = fetch_with_retry(sub_url)
        for m in re.finditer(r"https://collections\.louvre\.fr/(?:en/)?ark:/53355/(cl\d+)", body.decode("utf-8")):
            ark_id = m.group(1)
            if ark_id not in seen:
                seen.add(ark_id)
                ordered_ids.append(ark_id)
        time.sleep(COURTESY_DELAY_S)

    with open(DISCOVERED_ARKS_PATH, "w", encoding="utf-8") as f:
        json.dump(ordered_ids, f)
    print(f"  discovered {len(ordered_ids)} unique ARK ids")
    return ordered_ids


def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"done": [], "failed": {}}


def save_checkpoint(cp):
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(cp, f, indent=2)


def log_error(ark_id, status, message):
    os.makedirs(os.path.dirname(ERRORS_PATH), exist_ok=True)
    with open(ERRORS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ark_id": ark_id, "status": status, "error": message}) + "\n")


# --- Normalization -------------------------------------------------------
# Three INDEPENDENT classification dimensions, per explicit product decision
# after reviewing the first test import -- an object must be able to be
# ON_DISPLAY + READY metadata + NEEDS_ASSET simultaneously, so these are
# computed and stored as three separate fields, never collapsed into one
# enum the way the original recognition_readiness draft did.

RESERVE_PATTERN = re.compile(r"r[ée]serve", re.IGNORECASE)
ATELIER_PATTERN = re.compile(r"atelier", re.IGNORECASE)
NOT_DISPLAYED_PATTERN = re.compile(r"non\s+expos", re.IGNORECASE)
ROOM_PATTERN = re.compile(r"\b(salle|aile)\b", re.IGNORECASE)


def classify_display_status(current_location, room):
    """Returns (display_status, confidence, reason). display_status is one
    of ON_DISPLAY / NOT_ON_DISPLAY / UNKNOWN -- confidence/reason are kept
    as supplementary evidence, not folded away, since "empty currentLocation"
    and "currentLocation present but unrecognized" (e.g. on long-term loan
    to a different museum entirely -- a real case found in the first test
    batch) are both UNKNOWN but for genuinely different reasons worth being
    able to tell apart later."""
    cl = (current_location or "").strip()
    if not cl:
        return "UNKNOWN", "UNKNOWN", "currentLocation is empty -- no data at all"
    if NOT_DISPLAYED_PATTERN.search(cl):
        return "NOT_ON_DISPLAY", "HIGH", f"currentLocation explicitly says not on display: {cl!r}"
    if RESERVE_PATTERN.search(cl):
        return "NOT_ON_DISPLAY", "HIGH", f"currentLocation matches reserve/storage pattern: {cl!r}"
    if ATELIER_PATTERN.search(cl):
        return "NOT_ON_DISPLAY", "MEDIUM", f"currentLocation matches workshop pattern (not a public gallery): {cl!r}"
    if ROOM_PATTERN.search(cl) and (room or "").strip():
        return "ON_DISPLAY", "HIGH", f"currentLocation matches a real room/wing pattern with room populated: {cl!r} / room={room!r}"
    return "UNKNOWN", "LOW", f"currentLocation present but unrecognized pattern (e.g. possibly on loan elsewhere), not guessed either way: {cl!r}"


def classify_metadata_status(title, creator_labels, date_display, department, dimensions_display):
    has_title = bool((title or "").strip())
    has_creator = bool(creator_labels)
    has_date = bool((date_display or "").strip())
    has_other = bool((department or "").strip()) or bool((dimensions_display or "").strip())
    if not has_title and not has_creator and not has_date:
        return "INSUFFICIENT"
    if has_title and has_creator and has_date:
        return "READY"
    if has_title and (has_creator or has_date or has_other):
        return "PARTIAL"
    return "INSUFFICIENT"


def classify_image_rights(image_copyright):
    """Deliberately NOT a creator-name/ADAGP substring heuristic (removed --
    that was a guess, not evidence). Reads only what the source record
    literally states. Every Louvre-sourced image reference gets
    rights_review_required=True in this phase, full stop -- none of them
    have been cleared for recognition/AI-TDM use by any actual rights
    pipeline yet, so there is nothing to conditionally relax here."""
    if image_copyright:
        return "museum_asserted_copyright", True, f"Louvre/GrandPalaisRmn asserts photographic copyright: {image_copyright!r}. Not evaluated for reuse/AI-TDM eligibility -- treat as unresolved pending a separate rights-review pipeline."
    return "unknown", True, "No copyright string present on this image entry. Absence of a copyright string is not evidence of public-domain status -- treat as unresolved, not as clear."


def classify_recognition_status(metadata_status, has_image_reference, any_rights_restricted_evidence):
    """READY is intentionally unreachable from this function -- it only
    applies once an actual RecognitionAsset row exists, and this importer
    never creates one (see docs/louvre-schema.md). RIGHTS_RESTRICTED is
    reserved for cases with actual source evidence of restriction (e.g. a
    real, verified ADAGP-repertory match) -- not asserted here at all in
    this phase, since no such verified evidence source is wired up yet;
    kept as a real path in the enum but deliberately not producable by this
    heuristic-free classifier."""
    if any_rights_restricted_evidence:
        return "RIGHTS_RESTRICTED"
    if metadata_status == "INSUFFICIENT":
        return "NO_USABLE_ASSET"
    # NEEDS_ASSET regardless of whether Louvre happens to have published a
    # photo -- a Louvre-hosted image reference is never itself a usable
    # recognition asset in this architecture (see RecognitionAsset vs
    # LouvreImageReference separation), so "Louvre has a photo" does not
    # change this outcome.
    return "NEEDS_ASSET"


def normalize_record(raw):
    creators = raw.get("creator") or []
    creator_labels = [c.get("label") for c in creators if c.get("label")]
    creator_wikidata = next((c.get("wikidata") for c in creators if c.get("wikidata")), None)

    object_numbers = raw.get("objectNumber") or []
    inv = object_numbers[0].get("value") if object_numbers else None

    dims = raw.get("dimension") or []
    dim_str = "; ".join(d.get("displayDimension", "") for d in dims if d.get("displayDimension"))
    department = raw.get("collection")

    images = raw.get("image") or []
    image_references = []
    any_rights_restricted_evidence = False  # never set True by this heuristic-free classifier -- see classify_recognition_status
    for im in images:
        rights_status, review_required, rights_reason = classify_image_rights(im.get("copyright"))
        image_references.append({
            "url_image": im.get("urlImage"),
            "url_thumbnail": im.get("urlThumbnail"),
            "image_copyright": im.get("copyright"),
            "image_type": im.get("type"),
            "position": im.get("position"),
            "fetched": False,
            "rights_status": rights_status,
            "rights_review_required": review_required,
            "rights_reason": rights_reason,
        })

    current_location = raw.get("currentLocation")
    room = raw.get("room")
    display_status, display_confidence, display_reason = classify_display_status(current_location, room)

    metadata_status = classify_metadata_status(
        raw.get("title"), creator_labels, raw.get("displayDateCreated"), department, dim_str,
    )
    recognition_status = classify_recognition_status(
        metadata_status, bool(images), any_rights_restricted_evidence,
    )

    return {
        "source": "louvre_collections",
        "source_record_id": raw.get("arkId"),
        "source_url": raw.get("url"),
        "title": raw.get("title"),
        "title_complement": raw.get("titleComplement"),
        "creator_labels": creator_labels,
        "creator_wikidata_qid": creator_wikidata,
        "display_date_created": raw.get("displayDateCreated"),
        "date_created": raw.get("dateCreated"),
        "inventory_number": inv,
        "department": department,
        "object_types": [d.get("value") for d in (raw.get("denominationTitle") or [])],
        "dimensions_display": dim_str,
        "materials_and_techniques": raw.get("materialsAndTechniques"),
        "description": raw.get("description"),
        "provenance": raw.get("provenance"),
        "object_history": raw.get("objectHistory"),
        "place_of_discovery": raw.get("placeOfDiscovery"),
        "bibliography_count": len(raw.get("bibliography") or []),
        "current_location_raw": current_location,
        "room": room,
        "display_status": display_status,
        "display_status_confidence": display_confidence,
        "display_status_reason": display_reason,
        "metadata_status": metadata_status,
        "recognition_status": recognition_status,
        "image_count": len(images),
        "image_references": image_references,
    }


def run(limit, stride=1, extra_ark_ids=None, sample_file=None):
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(NORMALIZED_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)

    if sample_file:
        # Proper stratified census sample (see louvre_stratified_sample.py)
        # built from the full ark_index.jsonl -- covers every sitemap and
        # beginning/middle/end positions within each, not sequential.
        with open(sample_file, encoding="utf-8") as f:
            all_ids = json.load(f)
        ark_ids = all_ids[:limit] if limit else all_ids
        print(f"Using stratified sample file: {len(ark_ids)} ARK ids")
    else:
        discovered = discover_ark_ids(limit * stride if stride > 1 else limit)
        if stride > 1:
            # Sequential sitemap order clusters tightly by department/accession
            # batch (confirmed live: the first 20000 ids are almost entirely
            # Egyptian/Byzantine study objects) -- striding across the
            # already-discovered id list gives a materially more representative
            # department mix without fetching additional sub-sitemaps.
            ark_ids = discovered[::stride][:limit]
        else:
            ark_ids = discovered[:limit]
    if extra_ark_ids:
        ark_ids = list(dict.fromkeys(extra_ark_ids)) + [a for a in ark_ids if a not in extra_ark_ids]
    checkpoint = load_checkpoint()
    done = set(checkpoint["done"])
    failed = checkpoint["failed"]

    todo = [a for a in ark_ids if a not in done and a not in failed]
    print(f"\n{len(ark_ids)} target ARK ids, {len(done)} already done, {len(failed)} previously failed, {len(todo)} to fetch now")

    for i, ark_id in enumerate(todo, 1):
        raw_path = os.path.join(RAW_DIR, f"{ark_id}.json")
        try:
            if not os.path.exists(raw_path):
                url = f"https://collections.louvre.fr/ark:/53355/{ark_id}.json"
                body, status = fetch_with_retry(url)
                if status == 404:
                    failed[ark_id] = "404"
                    log_error(ark_id, 404, "record not found")
                    print(f"[{i}/{len(todo)}] {ark_id}: 404, skipping")
                    continue
                with open(raw_path, "wb") as f:
                    f.write(body)
                time.sleep(COURTESY_DELAY_S)
            with open(raw_path, encoding="utf-8") as f:
                raw = json.load(f)
            normalized = normalize_record(raw)
            with open(os.path.join(NORMALIZED_DIR, f"{ark_id}.json"), "w", encoding="utf-8") as f:
                json.dump(normalized, f, ensure_ascii=False, indent=2)
            done.add(ark_id)
            print(f"[{i}/{len(todo)}] {ark_id}: OK -- {normalized['title']!r} | display={normalized['display_status']} ({normalized['display_status_confidence']}) | metadata={normalized['metadata_status']} | recognition={normalized['recognition_status']}")
        except PermissionError as e:
            print(f"\nHARD STOP: {e}")
            checkpoint["done"] = sorted(done)
            checkpoint["failed"] = failed
            save_checkpoint(checkpoint)
            raise SystemExit(1)
        except Exception as e:
            failed[ark_id] = f"{type(e).__name__}: {e}"
            log_error(ark_id, None, str(e))
            print(f"[{i}/{len(todo)}] {ark_id}: FAILED permanently -- {e}")

        if i % 25 == 0:
            checkpoint["done"] = sorted(done)
            checkpoint["failed"] = failed
            save_checkpoint(checkpoint)

    checkpoint["done"] = sorted(done)
    checkpoint["failed"] = failed
    save_checkpoint(checkpoint)
    print(f"\nDone. {len(done)} succeeded total, {len(failed)} failed total (see {ERRORS_PATH}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--extra", type=str, default="", help="comma-separated ARK ids to always include first")
    parser.add_argument("--sample-file", type=str, default=None, help="JSON list of ARK ids from louvre_stratified_sample.py")
    args = parser.parse_args()
    extra = [a.strip() for a in args.extra.split(",") if a.strip()]
    run(args.limit, stride=args.stride, extra_ark_ids=extra, sample_file=args.sample_file)
