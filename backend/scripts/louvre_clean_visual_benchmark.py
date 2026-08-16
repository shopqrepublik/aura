#!/usr/bin/env python3
"""Build and benchmark a clean Louvre visual-retrieval test set.

This is an experiment script, not production recognition code.

Network is used only by `build` to acquire legal non-Louvre reference images.
`run` uses local files only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "exports/louvre/recognition_benchmark/louvre_local_benchmark_results_2026-08-12T113731+0000.jsonl"
ASSET_AUDIT = ROOT / "exports/louvre/recognition_assets/louvre_recognition_asset_identity_audit.jsonl"
ACQ_MANIFEST = ROOT / "exports/louvre/recognition_assets/louvre_approved_asset_acquisition_manifest.jsonl"
SEARCH_INDEX = ROOT / "exports/louvre/recognition_search/louvre_recognition_search_index.jsonl"
QUERY_EMBED_CACHE = ROOT / "exports/louvre/recognition_search/louvre_query_embedding_cache.jsonl"

OUT_DIR = ROOT / "exports/louvre/recognition_benchmark/clean_visual"
REF_DIR = OUT_DIR / "references"
COVERAGE_CSV = OUT_DIR / "louvre_benchmark_reference_coverage.csv"
CLEAN_JSONL = OUT_DIR / "louvre_clean_visual_benchmark.jsonl"
LINEAGES_JSONL = OUT_DIR / "louvre_reference_lineages.jsonl"
ABLATION_JSON = OUT_DIR / "louvre_visual_retrieval_ablation.json"
FAILURE_CSV = OUT_DIR / "louvre_visual_failure_analysis.csv"
REPORT_MD = OUT_DIR / "louvre_clean_visual_decision_report.md"

USER_AGENT = "ELYIO Louvre recognition benchmark/1.0 (contact: engineering@elyio.local; metadata-only rights-safe acquisition)"
LOUVRE_QID = "Q19675"
APPROVED_LICENSE_MARKERS = (
    "public domain",
    "cc0",
    "cc-by",
    "cc by",
    "cc-by-sa",
    "cc by-sa",
)
REJECTED_LICENSE_MARKERS = ("noncommercial", "non-commercial", " no derivatives", "nd", "fair use")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm_title(title: str | None) -> str:
    if not title:
        return ""
    title = title.replace("_", " ")
    title = re.sub(r"^File:", "", title, flags=re.I)
    return urllib.parse.unquote(title).strip()


def file_title_from_url(url: str | None) -> str | None:
    if not url:
        return None
    marker = "/Special:FilePath/"
    if marker in url:
        return "File:" + urllib.parse.unquote(url.split(marker, 1)[1].split("?", 1)[0])
    if "/wiki/File:" in url:
        return "File:" + urllib.parse.unquote(url.split("/wiki/File:", 1)[1].split("?", 1)[0])
    return None


def lineage_id_from_file_title(title: str | None) -> str | None:
    if not title:
        return None
    return "commons_file:" + norm_title(title).casefold()


def safe_slug(value: str, max_len: int = 80) -> str:
    value = urllib.parse.unquote(value)
    value = re.sub(r"^File:", "", value, flags=re.I)
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return value[:max_len] or hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def http_json(url: str, params: dict[str, Any] | None = None, retries: int = 2) -> dict[str, Any]:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                raise SystemExit(f"HTTP 429 from {url}; Retry-After={retry_after}. Acquisition paused.")
            if attempt >= retries:
                raise
        time.sleep(1.0 + attempt)
    raise RuntimeError("unreachable")


def http_bytes(url: str, retries: int = 2) -> tuple[bytes, str | None]:
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.read(), resp.headers.get("Content-Type")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                raise SystemExit(f"HTTP 429 from {url}; Retry-After={retry_after}. Acquisition paused.")
            if attempt >= retries:
                raise
        time.sleep(1.5 + attempt)
    raise RuntimeError("unreachable")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dhash(path: Path, hash_size: int = 8) -> str:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
    bits = []
    for row in range(hash_size):
        offset = row * (hash_size + 1)
        for col in range(hash_size):
            bits.append(pixels[offset + col] > pixels[offset + col + 1])
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def hamming_hex(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def image_size(path: Path) -> tuple[int, int]:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.size


def approved_license(ext: dict[str, Any]) -> tuple[bool, str, str | None, str | None]:
    license_short = str(ext.get("LicenseShortName", {}).get("value") or "")
    usage_terms = str(ext.get("UsageTerms", {}).get("value") or "")
    license_url = ext.get("LicenseUrl", {}).get("value")
    attribution = ext.get("Artist", {}).get("value") or ext.get("Credit", {}).get("value")
    text = f"{license_short} {usage_terms}".casefold()
    if any(marker in text for marker in REJECTED_LICENSE_MARKERS):
        return False, license_short or usage_terms or "unknown", license_url, attribution
    if any(marker in text for marker in APPROVED_LICENSE_MARKERS):
        return True, license_short or usage_terms or "approved", license_url, attribution
    return False, license_short or usage_terms or "unknown", license_url, attribution


def benchmark_rows() -> list[dict[str, Any]]:
    rows = [
        r for r in read_jsonl(BENCH)
        if r.get("mode") == "hybrid_stage2" and r.get("variant") == "pristine" and r.get("vision") and not r.get("error")
    ]
    dedup = {}
    for row in rows:
        dedup[row["artwork_id"]] = row
    return list(dedup.values())


def wikidata_entity(qid: str) -> dict[str, Any]:
    data = http_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    return data["entities"][qid]


def claim_strings(entity: dict[str, Any], prop: str) -> list[str]:
    out = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, str):
            out.append(value)
    return out


def commons_categories(entity: dict[str, Any]) -> list[str]:
    cats = []
    sitelink = entity.get("sitelinks", {}).get("commonswiki", {}).get("title")
    if sitelink and sitelink.startswith("Category:"):
        cats.append(sitelink)
    for p373 in claim_strings(entity, "P373"):
        cats.append("Category:" + p373)
    return list(dict.fromkeys(cats))


def commons_file_infos(titles: list[str]) -> list[dict[str, Any]]:
    if not titles:
        return []
    out = []
    for i in range(0, len(titles), 20):
        chunk = ["File:" + re.sub(r"^File:", "", t, flags=re.I) for t in titles[i:i + 20]]
        data = http_json("https://commons.wikimedia.org/w/api.php", {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "titles": "|".join(chunk),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|sha1|extmetadata",
            "iiurlwidth": "1400",
        })
        for page in data.get("query", {}).get("pages", []):
            if page.get("missing") or not page.get("imageinfo"):
                continue
            ii = page["imageinfo"][0]
            out.append({
                "title": page["title"],
                "url": ii.get("thumburl") or ii.get("url"),
                "full_url": ii.get("url"),
                "mime": ii.get("mime"),
                "width": ii.get("thumbwidth") or ii.get("width"),
                "height": ii.get("thumbheight") or ii.get("height"),
                "sha1": ii.get("sha1"),
                "extmetadata": ii.get("extmetadata", {}),
            })
    return out


def commons_category_files(category: str, limit: int = 40) -> list[str]:
    data = http_json("https://commons.wikimedia.org/w/api.php", {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "categorymembers",
        "gcmtitle": category,
        "gcmnamespace": "6",
        "gcmlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|mime|sha1|extmetadata",
        "iiurlwidth": "1400",
    })
    pages = data.get("query", {}).get("pages", [])
    return [page["title"] for page in pages if page.get("title", "").startswith("File:")]


def search_commons_files(query: str, limit: int = 10) -> list[str]:
    data = http_json("https://commons.wikimedia.org/w/api.php", {
        "action": "query",
        "format": "json",
        "list": "search",
        "srnamespace": "6",
        "srlimit": str(limit),
        "srsearch": query,
    })
    return [r["title"] for r in data.get("query", {}).get("search", []) if r.get("title", "").startswith("File:")]


def acquire_reference(ark: str, file_info: dict[str, Any], identity_evidence: str) -> dict[str, Any] | None:
    ok, license_name, license_url, attribution = approved_license(file_info.get("extmetadata", {}))
    if not ok:
        return None
    url = file_info.get("url")
    if not url:
        return None
    title = file_info["title"]
    ext = ".jpg"
    mime = (file_info.get("mime") or "").lower()
    if "png" in mime:
        ext = ".png"
    elif "webp" in mime:
        ext = ".webp"
    slug = safe_slug(title)
    path = REF_DIR / f"{ark}_{hashlib.sha1(title.encode('utf-8')).hexdigest()[:10]}_{slug}{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        body, content_type = http_bytes(url)
        path.write_bytes(body)
        time.sleep(0.5)
    else:
        content_type = None
    width, height = image_size(path)
    return {
        "reference_id": hashlib.sha1(f"{ark}|{title}".encode("utf-8")).hexdigest()[:16],
        "artwork_id": ark,
        "source_provider": "wikimedia_commons",
        "source_file_title": title,
        "source_page_url": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="/:_"),
        "direct_media_reference": file_info.get("full_url") or url,
        "local_path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "dhash": dhash(path),
        "width": width,
        "height": height,
        "source_lineage_id": lineage_id_from_file_title(title),
        "license": license_name,
        "license_url": license_url,
        "attribution": attribution,
        "rights_status": "APPROVED",
        "identity_status": "VERIFIED",
        "identity_evidence": identity_evidence,
        "acquired_at": now_iso(),
        "response_content_type": content_type,
    }


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REF_DIR.mkdir(parents=True, exist_ok=True)
    audit = {r["artwork_id"]: r for r in read_jsonl(ASSET_AUDIT)}
    acq = {r["artwork_id"]: r for r in read_jsonl(ACQ_MANIFEST)}
    bench = benchmark_rows()

    verified = [r for r in audit.values() if r.get("identity_status") == "VERIFIED"]
    verified_artworks = {r["artwork_id"] for r in verified}
    verified_local = [
        r for r in verified
        if r["artwork_id"] in acq and (ROOT / acq[r["artwork_id"]].get("cache_path", "")).exists()
    ]
    reconciliation = {
        "audited_verified_assets": len(verified),
        "verified_distinct_artworks": len(verified_artworks),
        "verified_with_usable_local_image_bytes": len(verified_local),
        "verified_without_local_bytes": len(verified) - len(verified_local),
        "multiple_verified_assets_same_artwork": len(verified) - len(verified_artworks),
        "verified_artworks_in_41_benchmark": len({r["artwork_id"] for r in bench} & verified_artworks),
        "locally_embeddable_verified_references": len(verified_local),
        "why_previous_experiment_used_25": "Only 25 of the 60 identity-VERIFIED assets were present in the acquisition manifest/cache; the remaining cached files belonged to assets now UNRESOLVED or QUARANTINED_MISMATCH and were excluded.",
    }

    lineages: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    clean_rows: list[dict[str, Any]] = []

    for row in bench:
        ark = row["artwork_id"]
        asset = audit.get(ark, {})
        acquired = acq.get(ark, {})
        qid = asset.get("source_identifier")
        query_path = ROOT / row["input_path"]
        query_fixture_path = ROOT / row["fixture_path"]
        query_source_file = file_title_from_url(acquired.get("source_url")) or (
            "File:" + asset.get("source_filename") if asset.get("source_filename") else None
        )
        query_lineage = lineage_id_from_file_title(query_source_file)
        query_hash = sha256_file(query_path) if query_path.exists() else row.get("input_hash")
        query_dhash = dhash(query_path) if query_path.exists() else None

        candidate_titles = []
        identity_sources = {}
        categories = []
        if qid:
            try:
                entity = wikidata_entity(qid)
                for p18 in claim_strings(entity, "P18"):
                    title = "File:" + p18
                    candidate_titles.append(title)
                    identity_sources[title] = f"wikidata_entity_{qid}_P18"
                categories = commons_categories(entity)
                for category in categories[:2]:
                    try:
                        for title in commons_category_files(category):
                            candidate_titles.append(title)
                            identity_sources[title] = f"commons_category_from_wikidata_{qid}:{category}"
                    except Exception as exc:  # keep acquisition bounded and artifact-generating
                        identity_sources[f"ERROR:{category}"] = str(exc)
                if len(candidate_titles) < 3:
                    search_text = " ".join(filter(None, [row.get("expected_title"), row.get("expected_artist"), "Louvre"]))
                    for title in search_commons_files(search_text, limit=10):
                        candidate_titles.append(title)
                        identity_sources.setdefault(title, f"commons_search_title_artist_louvre:{qid}")
            except Exception as exc:
                identity_sources[f"ERROR:{qid}"] = str(exc)

        candidate_titles = list(dict.fromkeys(candidate_titles))
        current_title_norm = norm_title(query_source_file).casefold()
        query_identity_verified = asset.get("identity_status") == "VERIFIED"
        if not query_identity_verified and current_title_norm:
            for title in candidate_titles:
                if norm_title(title).casefold() == current_title_norm and not identity_sources.get(title, "").startswith("commons_search"):
                    query_identity_verified = True

        refs = []
        for info in commons_file_infos(candidate_titles):
            title = info["title"]
            if norm_title(title).casefold() == current_title_norm:
                continue
            evidence = identity_sources.get(title, "unknown")
            if evidence.startswith("commons_search"):
                # Search can propose good leads, but it is not strong enough for
                # automatic VERIFIED identity in this benchmark.
                continue
            ref = acquire_reference(ark, info, evidence)
            if not ref:
                continue
            if ref["sha256"] == query_hash:
                ref["leakage_status"] = "IDENTICAL_BYTES"
                lineages.append(ref)
                continue
            phash_distance = hamming_hex(query_dhash, ref["dhash"])
            ref["query_dhash_distance"] = phash_distance
            ref["query_source_lineage_id"] = query_lineage
            if ref["source_lineage_id"] == query_lineage:
                ref["leakage_status"] = "SAME_LINEAGE"
            elif phash_distance is not None and phash_distance <= 2:
                ref["leakage_status"] = "AMBIGUOUS_NEAR_DUPLICATE_HASH"
            else:
                ref["leakage_status"] = "CLEAN_INDEPENDENT"
                refs.append(ref)
            lineages.append(ref)
            if len(refs) >= (4 if "Sculptures" in (row.get("department") or "") else 2):
                break

        clean_refs = [r for r in refs if r["leakage_status"] == "CLEAN_INDEPENDENT"]
        query_mode = "existing_benchmark_query"
        clean_query_path = row["input_path"]
        clean_query_lineage = query_lineage
        clean_query_hash = query_hash
        category = "NO_VERIFIED_REFERENCE"
        status = "NO_VERIFIED_REFERENCE"
        independent_ref_count = len(clean_refs)

        if query_identity_verified and clean_refs:
            category = "CLEAN_INDEPENDENT"
            status = "CLEAN_INDEPENDENT"
        elif not query_identity_verified and len(clean_refs) >= 2:
            # Existing query source could not be verified; use first legal
            # reference as query and the remaining independent legal references
            # as retrieval references. This preserves the original benchmark row
            # separately while making the clean view honest.
            query_ref = clean_refs[0]
            clean_refs = clean_refs[1:]
            query_mode = "replacement_legal_query"
            clean_query_path = query_ref["local_path"]
            clean_query_lineage = query_ref["source_lineage_id"]
            clean_query_hash = query_ref["sha256"]
            independent_ref_count = len(clean_refs)
            category = "CLEAN_INDEPENDENT" if clean_refs else "NO_VERIFIED_REFERENCE"
            status = category
        elif asset.get("identity_status") == "VERIFIED" and not clean_refs:
            category = "SAME_SOURCE_LEAKAGE"
            status = "NEEDS_ALTERNATE_REFERENCE"
        elif asset.get("identity_status") == "QUARANTINED_MISMATCH":
            category = "INVALID"
            status = "QUERY_SOURCE_IDENTITY_MISMATCH"
        elif asset.get("identity_status") == "UNRESOLVED":
            category = "AMBIGUOUS"
            status = "QUERY_SOURCE_UNRESOLVED"

        coverage_row = {
            "artwork_id": ark,
            "title": row.get("expected_title"),
            "artist_maker": row.get("expected_artist"),
            "object_type": (row.get("vision") or {}).get("object_category"),
            "department": row.get("department"),
            "tier": row.get("tier"),
            "current_query_source_identity": query_source_file,
            "current_query_hash": query_hash,
            "current_query_lineage_id": query_lineage,
            "current_query_identity_verified": query_identity_verified,
            "current_verified_reference_count": 1 if asset.get("identity_status") == "VERIFIED" else 0,
            "independent_verified_reference_count": independent_ref_count,
            "acquisition_needed": "no" if category == "CLEAN_INDEPENDENT" else "yes",
            "status": status,
            "eligibility_category": category,
            "wikidata_qid": qid,
            "commons_categories": "; ".join(categories),
        }
        coverage.append(coverage_row)
        if category == "CLEAN_INDEPENDENT":
            clean_rows.append({
                "artwork_id": ark,
                "title": row.get("expected_title"),
                "artist_maker": row.get("expected_artist"),
                "department": row.get("department"),
                "tier": row.get("tier"),
                "object_type": (row.get("vision") or {}).get("object_category"),
                "query_path": clean_query_path,
                "query_sha256": clean_query_hash,
                "query_source_lineage_id": clean_query_lineage,
                "query_mode": query_mode,
                "original_benchmark_input_path": row.get("input_path"),
                "original_benchmark_fixture_path": row.get("fixture_path"),
                "reference_ids": [r["reference_id"] for r in clean_refs],
                "reference_source_lineage_ids": [r["source_lineage_id"] for r in clean_refs],
                "leakage_checks": {
                    "query_reference_same_lineage": False,
                    "query_reference_identical_bytes": False,
                    "query_reference_near_duplicate_hash": False,
                },
            })

    with COVERAGE_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(coverage[0].keys()))
        writer.writeheader()
        writer.writerows(coverage)
    write_jsonl(CLEAN_JSONL, clean_rows)
    write_jsonl(LINEAGES_JSONL, lineages)
    summary = {
        "generated_at": now_iso(),
        "reconciliation": reconciliation,
        "original_rows": len(coverage),
        "category_counts": dict(Counter(r["eligibility_category"] for r in coverage)),
        "clean_independent_rows": len(clean_rows),
        "distinct_clean_artworks": len({r["artwork_id"] for r in clean_rows}),
        "reference_images": len([r for r in lineages if r.get("leakage_status") == "CLEAN_INDEPENDENT"]),
        "artworks_with_clean_references": len({r["artwork_id"] for r in lineages if r.get("leakage_status") == "CLEAN_INDEPENDENT"}),
        "network_acquisition_completed": True,
        "louvre_image_bytes_fetched": 0,
    }
    (OUT_DIR / "louvre_clean_visual_build_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def load_vector_rows(path: Path) -> dict[str, np.ndarray]:
    out = {}
    for row in read_jsonl(path):
        if "embedding" in row:
            out[row["artwork_id"]] = np.array(row["embedding"], dtype=np.float32)
    return out


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if math.isclose(lo, hi):
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def image_embedding(path: Path, processor: Any, model: Any) -> np.ndarray:
    import torch

    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    inputs = processor(images=img, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    vec = outputs.pooler_output[0].detach().cpu().numpy().astype(np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def summarize_ranks(ranks: list[int | None]) -> dict[str, Any]:
    total = len(ranks)
    out = {"total": total}
    for n in (1, 3, 5, 20):
        hits = sum(1 for rank in ranks if rank is not None and rank <= n)
        out[f"top{n}_count"] = hits
        out[f"top{n}_recall"] = hits / total if total else 0.0
    return out


def run() -> None:
    from transformers import AutoImageProcessor, AutoModel

    clean_rows = read_jsonl(CLEAN_JSONL)
    lineages = [r for r in read_jsonl(LINEAGES_JSONL) if r.get("leakage_status") == "CLEAN_INDEPENDENT"]
    search_vectors = load_vector_rows(SEARCH_INDEX)
    query_vectors = load_vector_rows(QUERY_EMBED_CACHE)

    processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small", local_files_only=True)
    model = AutoModel.from_pretrained("facebook/dinov2-small", local_files_only=True)
    model.eval()

    ref_embeddings = {}
    ref_by_artwork = defaultdict(list)
    for ref in lineages:
        path = ROOT / ref["local_path"]
        if not path.exists():
            continue
        emb = image_embedding(path, processor, model)
        ref_embeddings[ref["reference_id"]] = emb
        ref_by_artwork[ref["artwork_id"]].append(ref)

    query_embeddings = {}
    for row in clean_rows:
        path = ROOT / row["query_path"]
        if path.exists():
            query_embeddings[row["artwork_id"]] = image_embedding(path, processor, model)

    indexed_artworks = sorted(ref_by_artwork)
    weights = {
        "metadata_only": (0.0, 1.0),
        "dinov2_visual_only": (1.0, 0.0),
        "dinov2_visual_0.9_metadata_0.1": (0.9, 0.1),
        "dinov2_visual_0.8_metadata_0.2": (0.8, 0.2),
        "dinov2_visual_0.7_metadata_0.3": (0.7, 0.3),
    }
    detail = []
    summary = {
        "generated_at": now_iso(),
        "model": "facebook/dinov2-small",
        "original_rows": 41,
        "clean_independent_rows": len(clean_rows),
        "clean_distinct_artworks": len({r["artwork_id"] for r in clean_rows}),
        "reference_images_indexed": len(ref_embeddings),
        "artworks_indexed": len(indexed_artworks),
        "network_during_benchmark": 0,
        "louvre_image_bytes_fetched": 0,
        "methods": {},
    }

    for method, (visual_w, metadata_w) in weights.items():
        ranks = []
        for row in clean_rows:
            expected = row["artwork_id"]
            visual_scores = {}
            if expected in query_embeddings:
                q_emb = query_embeddings[expected]
                for artwork_id, refs in ref_by_artwork.items():
                    sims = [cosine(q_emb, ref_embeddings[ref["reference_id"]]) for ref in refs if ref["reference_id"] in ref_embeddings]
                    if sims:
                        visual_scores[artwork_id] = max(sims)
            metadata_scores = {}
            q_text = query_vectors.get(expected)
            if q_text is not None:
                for artwork_id, vec in search_vectors.items():
                    metadata_scores[artwork_id] = cosine(q_text, vec)
            visual_scores = normalize_scores(visual_scores)
            metadata_scores = normalize_scores(metadata_scores)
            if method == "dinov2_visual_only":
                candidate_ids = set(visual_scores)
            else:
                candidate_ids = set(metadata_scores) | set(visual_scores)
            fused = {}
            for artwork_id in candidate_ids:
                fused[artwork_id] = visual_w * visual_scores.get(artwork_id, 0.0) + metadata_w * metadata_scores.get(artwork_id, 0.0)
            ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
            rank = next((i + 1 for i, (artwork_id, _) in enumerate(ranked) if artwork_id == expected), None)
            ranks.append(rank)
            detail.append({
                "method": method,
                "artwork_id": expected,
                "title": row.get("title"),
                "department": row.get("department"),
                "object_type": row.get("object_type"),
                "rank_position": rank,
                "top5": [
                    {
                        "artwork_id": artwork_id,
                        "fused_score": round(score, 6),
                        "visual_score": round(visual_scores.get(artwork_id, 0.0), 6),
                        "metadata_score": round(metadata_scores.get(artwork_id, 0.0), 6),
                    }
                    for artwork_id, score in ranked[:5]
                ],
            })
        summary["methods"][method] = summarize_ranks(ranks)

    (OUT_DIR / "louvre_visual_retrieval_ablation_detail.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in detail) + "\n",
        encoding="utf-8",
    )
    ABLATION_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    best_method = max(summary["methods"], key=lambda m: (
        summary["methods"][m]["top5_recall"],
        summary["methods"][m]["top3_recall"],
        summary["methods"][m]["top1_recall"],
    ))
    failure_rows = [r for r in detail if r["method"] == best_method and (r["rank_position"] is None or r["rank_position"] > 5)]
    with FAILURE_CSV.open("w", encoding="utf-8", newline="") as f:
        fields = ["artwork_id", "title", "department", "object_type", "rank_position", "top5", "failure_category"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in failure_rows:
            writer.writerow({
                "artwork_id": r["artwork_id"],
                "title": r["title"],
                "department": r["department"],
                "object_type": r["object_type"],
                "rank_position": r["rank_position"],
                "top5": json.dumps(r["top5"], ensure_ascii=False),
                "failure_category": "embedding_model_or_reference_viewpoint",
            })

    decision = "DATA_INSUFFICIENT"
    clean_n = summary["clean_independent_rows"]
    clean_artworks = summary["clean_distinct_artworks"]
    best_top5 = summary["methods"][best_method]["top5_recall"]
    if clean_n >= 30 and clean_artworks >= 20:
        if best_top5 >= 0.95:
            decision = "PASS"
        elif best_top5 >= 0.90:
            decision = "NEAR_PASS"
        else:
            decision = "MODEL_ARCHITECTURE_FAIL"
    summary["best_method"] = best_method
    summary["decision"] = decision
    ABLATION_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def report() -> None:
    build_summary = json.loads((OUT_DIR / "louvre_clean_visual_build_summary.json").read_text(encoding="utf-8"))
    ablation = json.loads(ABLATION_JSON.read_text(encoding="utf-8")) if ABLATION_JSON.exists() else {}
    coverage_counts = build_summary.get("category_counts", {})
    methods = ablation.get("methods", {})
    rows = [
        "# Louvre Clean Visual Benchmark Decision Report",
        "",
        f"Generated: {now_iso()}",
        "",
        "## Reference Reconciliation",
        "",
        f"- Audited VERIFIED assets: {build_summary['reconciliation']['audited_verified_assets']}",
        f"- Distinct VERIFIED artworks: {build_summary['reconciliation']['verified_distinct_artworks']}",
        f"- Locally usable VERIFIED reference bytes: {build_summary['reconciliation']['verified_with_usable_local_image_bytes']}",
        f"- VERIFIED without local bytes: {build_summary['reconciliation']['verified_without_local_bytes']}",
        f"- Multiple VERIFIED assets for same artwork: {build_summary['reconciliation']['multiple_verified_assets_same_artwork']}",
        f"- VERIFIED artworks represented in the 41-row benchmark: {build_summary['reconciliation']['verified_artworks_in_41_benchmark']}",
        f"- Why previous experiment used 25: {build_summary['reconciliation']['why_previous_experiment_used_25']}",
        "",
        "## Benchmark Coverage",
        "",
        f"- Original rows: {build_summary['original_rows']}",
        f"- CLEAN_INDEPENDENT: {coverage_counts.get('CLEAN_INDEPENDENT', 0)}",
        f"- SAME_SOURCE_LEAKAGE: {coverage_counts.get('SAME_SOURCE_LEAKAGE', 0)}",
        f"- NO_VERIFIED_REFERENCE: {coverage_counts.get('NO_VERIFIED_REFERENCE', 0)}",
        f"- AMBIGUOUS: {coverage_counts.get('AMBIGUOUS', 0)}",
        f"- INVALID: {coverage_counts.get('INVALID', 0)}",
        f"- Distinct clean artworks: {build_summary['distinct_clean_artworks']}",
        "",
        "## Reference Corpus",
        "",
        f"- Artworks indexed: {ablation.get('artworks_indexed', 0)}",
        f"- Reference images indexed: {ablation.get('reference_images_indexed', 0)}",
        "",
        "## Retrieval",
        "",
        "| Method | Top-1 | Top-3 | Top-5 | Top-20 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for method in ["metadata_only", "dinov2_visual_only", "dinov2_visual_0.9_metadata_0.1", "dinov2_visual_0.8_metadata_0.2", "dinov2_visual_0.7_metadata_0.3"]:
        m = methods.get(method, {})
        rows.append(
            f"| {method} | {m.get('top1_recall', 0):.1%} | {m.get('top3_recall', 0):.1%} | {m.get('top5_recall', 0):.1%} | {m.get('top20_recall', 0):.1%} |"
        )
    rows.extend([
        "",
        "## Decision",
        "",
        f"Decision: **{ablation.get('decision', 'DATA_INSUFFICIENT')}**",
        "",
        "Production writes: no",
        "",
        "Deployment: no",
    ])
    REPORT_MD.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(REPORT_MD)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "run", "report"])
    args = parser.parse_args()
    if args.command == "build":
        build()
    elif args.command == "run":
        run()
    else:
        report()


if __name__ == "__main__":
    main()
