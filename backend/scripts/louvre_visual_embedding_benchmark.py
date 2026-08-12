#!/usr/bin/env python3
"""Offline visual embedding benchmark for Louvre recognition retrieval.

Benchmark execution uses only local files:
  * cached VERIFIED RecognitionAsset images
  * existing local benchmark query images
  * cached DINOv2 model
  * cached text/query embeddings from previous metadata retrieval work

No external image/network calls are made during retrieval.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "exports" / "louvre" / "recognition_assets"
BENCH = ROOT / "exports" / "louvre" / "recognition_benchmark"
SEARCH = ROOT / "exports" / "louvre" / "recognition_search"
AUDIT = ASSETS / "louvre_recognition_asset_identity_audit.jsonl"
INTEGRITY = BENCH / "louvre_benchmark_integrity_audit.jsonl"
RESULTS = BENCH / "louvre_local_benchmark_results_2026-08-12T113731+0000.jsonl"
TEXT_INDEX = SEARCH / "louvre_recognition_search_index.jsonl"
QUERY_CACHE = SEARCH / "louvre_query_embedding_cache.jsonl"
OUT_DIR = BENCH / "visual_embedding"
MODEL_ID = "facebook/dinov2-small"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def now_slug() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(":", "")


def normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n else v


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def image_embedding(path: Path, processor, model) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    inputs = processor(images=img, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    if getattr(outputs, "pooler_output", None) is not None:
        vec = outputs.pooler_output[0].detach().cpu().numpy()
    else:
        vec = outputs.last_hidden_state[:, 0, :][0].detach().cpu().numpy()
    return normalize(vec.astype("float32"))


def query_text(vision: dict) -> str:
    parts = [
        vision.get("visual_search_description"),
        vision.get("likely_title") or vision.get("title"),
        vision.get("likely_artist") or vision.get("artist"),
        vision.get("object_category") or vision.get("object_type"),
        vision.get("period_guess"),
        vision.get("material_guess"),
        vision.get("depicted_subject"),
        *(vision.get("dominant_visual_features") or []),
        *(vision.get("distinctive_features") or []),
        *(vision.get("inscriptions_visible") or []),
    ]
    return " ; ".join(str(x).strip() for x in parts if x)


def text_score_lookup() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    text_refs = {
        row["artwork_id"]: normalize(np.array(row["embedding"], dtype="float32"))
        for row in read_jsonl(TEXT_INDEX)
    }
    queries = {
        row["query_text"]: normalize(np.array(row["embedding"], dtype="float32"))
        for row in read_jsonl(QUERY_CACHE)
    }
    return text_refs, queries


def minmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def rank(scores: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def summarize(rows: list[dict], prefix: str = "") -> dict:
    total = len(rows)
    out = {"total": total}
    for n in [1, 3, 5, 20]:
        hit = sum(1 for row in rows if row.get(f"{prefix}rank_position") is not None and row[f"{prefix}rank_position"] <= n)
        out[f"top{n}_recall"] = hit / total if total else 0
        out[f"top{n}_count"] = hit
    return out


def by_group(rows: list[dict], key: str, rank_field: str) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[row.get(key) or "UNKNOWN"].append(row)
    return {k: summarize(v, prefix=rank_field.replace("rank_position", "")) for k, v in sorted(groups.items())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL_ID)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = {r["artwork_id"]: r for r in read_jsonl(AUDIT)}
    integrity = {r["artwork_id"]: r for r in read_jsonl(INTEGRITY)}
    benchmark_rows = [
        r for r in read_jsonl(RESULTS)
        if r.get("mode") == "hybrid_stage2" and r.get("variant") == "pristine" and r.get("vision") and not r.get("error")
    ]
    verified_refs = {
        ark: ROOT / row["local_cached_asset_path"]
        for ark, row in audit.items()
        if row.get("identity_status") == "VERIFIED" and row.get("local_cached_asset_path") and (ROOT / row["local_cached_asset_path"]).exists()
    }
    eligible_rows = [
        row for row in benchmark_rows
        if integrity.get(row["artwork_id"], {}).get("eligible_for_visual_reference_benchmark")
    ]

    processor = AutoImageProcessor.from_pretrained(args.model, local_files_only=True)
    model = AutoModel.from_pretrained(args.model, local_files_only=True)
    model.eval()

    ref_embeddings = {}
    for ark, path in sorted(verified_refs.items()):
        ref_embeddings[ark] = image_embedding(path, processor, model)
    query_embeddings = {}
    for row in eligible_rows:
        query_embeddings[row["artwork_id"]] = image_embedding(ROOT / row["input_path"], processor, model)

    text_refs, text_queries = text_score_lookup()
    detail_rows = []
    weights = [(1.0, 0.0), (0.9, 0.1), (0.8, 0.2), (0.7, 0.3)]
    for row in benchmark_rows:
        ark = row["artwork_id"]
        eligible = row in eligible_rows
        visual_scores = {}
        if eligible:
            visual_scores = {ref_ark: cosine(query_embeddings[ark], emb) for ref_ark, emb in ref_embeddings.items()}
        qtext = query_text(row["vision"])
        text_query = text_queries.get(qtext)
        metadata_scores = {}
        if text_query is not None:
            metadata_scores = {ref_ark: cosine(text_query, text_refs[ref_ark]) for ref_ark in ref_embeddings if ref_ark in text_refs}
        visual_norm = minmax(visual_scores)
        metadata_norm = minmax(metadata_scores)

        def pos_for(ranked):
            for idx, (candidate, _score) in enumerate(ranked, 1):
                if candidate == ark:
                    return idx
            return None

        visual_ranked = rank(visual_norm) if visual_norm else []
        metadata_ranked = rank(metadata_norm) if metadata_norm else []
        fused = {}
        for vw, mw in weights:
            for ref_ark in set(visual_norm) | set(metadata_norm):
                fused[ref_ark] = vw * visual_norm.get(ref_ark, 0.0) + mw * metadata_norm.get(ref_ark, 0.0)
            row_key = f"fused_{int(vw*100)}_{int(mw*100)}_"
            fused_ranked = rank(fused)
            detail = {
                "artwork_id": ark,
                "expected_title": row.get("expected_title"),
                "department": row.get("department"),
                "tier": row.get("tier"),
                "asset_identity_status": audit.get(ark, {}).get("identity_status", "NO_AUDITED_ASSET"),
                "benchmark_integrity_category": integrity.get(ark, {}).get("benchmark_integrity_category"),
                "eligible_visual_row": eligible,
                "configuration": f"visual_{vw:.1f}_metadata_{mw:.1f}",
                "rank_position": pos_for(fused_ranked),
                "top5": [
                    {
                        "artwork_id": cid,
                        "score": round(score, 6),
                        "visual_score": round(visual_norm.get(cid, 0.0), 6),
                        "metadata_score": round(metadata_norm.get(cid, 0.0), 6),
                    }
                    for cid, score in fused_ranked[:5]
                ],
            }
            detail_rows.append(detail)
        detail_rows.append({
            "artwork_id": ark,
            "expected_title": row.get("expected_title"),
            "department": row.get("department"),
            "tier": row.get("tier"),
            "asset_identity_status": audit.get(ark, {}).get("identity_status", "NO_AUDITED_ASSET"),
            "benchmark_integrity_category": integrity.get(ark, {}).get("benchmark_integrity_category"),
            "eligible_visual_row": eligible,
            "configuration": "metadata_only_verified_ref_corpus",
            "rank_position": pos_for(metadata_ranked),
            "top5": [{"artwork_id": cid, "score": round(score, 6)} for cid, score in metadata_ranked[:5]],
        })
        detail_rows.append({
            "artwork_id": ark,
            "expected_title": row.get("expected_title"),
            "department": row.get("department"),
            "tier": row.get("tier"),
            "asset_identity_status": audit.get(ark, {}).get("identity_status", "NO_AUDITED_ASSET"),
            "benchmark_integrity_category": integrity.get(ark, {}).get("benchmark_integrity_category"),
            "eligible_visual_row": eligible,
            "configuration": "visual_only_verified_ref_corpus",
            "rank_position": pos_for(visual_ranked),
            "top5": [{"artwork_id": cid, "score": round(score, 6)} for cid, score in visual_ranked[:5]],
        })

    slug = now_slug()
    detail_path = OUT_DIR / f"louvre_visual_embedding_benchmark_{slug}.jsonl"
    write_jsonl(detail_path, detail_rows)
    configs = sorted({r["configuration"] for r in detail_rows})
    summary = {
        "model": args.model,
        "verified_cached_reference_count": len(ref_embeddings),
        "original_valid_pristine_rows": len(benchmark_rows),
        "eligible_visual_rows": len(eligible_rows),
        "independent_query_rows": sum(1 for r in integrity.values() if r.get("independent_query")),
        "same_source_derivative_rows": sum(1 for r in integrity.values() if r.get("benchmark_integrity_category") == "same-source derivative"),
        "configurations": {},
        "detail_path": str(detail_path.relative_to(ROOT)),
        "network_during_benchmark": 0,
        "louvre_image_bytes_fetched": 0,
    }
    for cfg in configs:
        cfg_rows_all = [r for r in detail_rows if r["configuration"] == cfg]
        cfg_rows_eligible = [r for r in cfg_rows_all if r["eligible_visual_row"]]
        summary["configurations"][cfg] = {
            "original_denominator": summarize(cfg_rows_all),
            "eligible_visual_subset": summarize(cfg_rows_eligible),
        }
    # Failure rows for strongest config. Top-5 is the gate metric, but ties
    # should prefer better Top-3/Top-1 and configurations that actually use
    # visual evidence.
    def config_key(cfg: str):
        eligible = summary["configurations"][cfg]["eligible_visual_subset"]
        uses_visual = 0 if cfg.startswith("metadata_only") else 1
        return (
            eligible["top5_recall"],
            eligible["top3_recall"],
            eligible["top1_recall"],
            uses_visual,
        )

    best_cfg = max(configs, key=config_key)
    failures = [
        {
            **r,
            "likely_failure_category": (
                "missing verified reference" if r["asset_identity_status"] != "VERIFIED"
                else "benchmark leakage/problem" if r["benchmark_integrity_category"] != "same-source derivative"
                else "visual model / reference similarity failure"
            ),
        }
        for r in detail_rows
        if r["configuration"] == best_cfg and (r.get("rank_position") is None or r["rank_position"] > 5)
    ]
    failure_path = OUT_DIR / f"louvre_visual_embedding_failures_{slug}.jsonl"
    write_jsonl(failure_path, failures)
    summary["best_configuration"] = best_cfg
    summary["failure_path"] = str(failure_path.relative_to(ROOT))
    summary_path = OUT_DIR / f"louvre_visual_embedding_benchmark_summary_{slug}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
