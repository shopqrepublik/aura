#!/usr/bin/env python3
"""Hybrid lexical + semantic retrieval recall benchmark for Louvre Visitor 500."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT / ".env")

from app.catalog import get_recognition_candidates  # noqa: E402
from app.main import _tokens, rank_catalog_candidates  # noqa: E402


OUT = ROOT / "exports" / "louvre" / "recognition_benchmark"
SEARCH = ROOT / "exports" / "louvre" / "recognition_search"
DEFAULT_RESULTS = OUT / "louvre_local_benchmark_results_2026-08-12T113731+0000.jsonl"
INDEX = SEARCH / "louvre_recognition_search_index.jsonl"
QUERY_CACHE = SEARCH / "louvre_query_embedding_cache.jsonl"
EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


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


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def embed_queries(texts: list[str]) -> dict[str, list[float]]:
    cache_rows = read_jsonl(QUERY_CACHE)
    cache = {
        row["query_text"]: row["embedding"]
        for row in cache_rows
        if row.get("embedding_model") == EMBEDDING_MODEL
    }
    missing = [text for text in texts if text and text not in cache]
    if missing:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        for start in range(0, len(missing), 100):
            batch = missing[start:start + 100]
            resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch, encoding_format="float")
            for text, item in zip(batch, resp.data):
                cache[text] = item.embedding
                cache_rows.append({
                    "query_text": text,
                    "embedding_model": EMBEDDING_MODEL,
                    "embedding": item.embedding,
                    "embedded_at": datetime.now(timezone.utc).isoformat(),
                })
    write_jsonl(QUERY_CACHE, cache_rows)
    return cache


def minmax_scores(rows: list[tuple[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    vals = [score for _id, score in rows]
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {_id: 0.0 for _id, _score in rows}
    return {_id: (score - lo) / (hi - lo) for _id, score in rows}


def combined_rank(vision: dict, candidates: list[dict], index_rows: list[dict], query_embedding: list[float], limit: int) -> list[dict]:
    lexical = rank_catalog_candidates(vision, candidates, limit=len(candidates))
    lexical_raw = [(row["candidate"]["id"], row["score"]) for row in lexical]
    lexical_norm = minmax_scores(lexical_raw)

    semantic_raw = [(row["artwork_id"], cosine(query_embedding, row["embedding"])) for row in index_rows]
    semantic_norm = minmax_scores(semantic_raw)
    query_tokens = _tokens(query_text(vision))
    index_tokens = {row["artwork_id"]: _tokens(row.get("document") or "") for row in index_rows}
    df: dict[str, int] = {}
    for tokens in index_tokens.values():
        for token in tokens:
            df[token] = df.get(token, 0) + 1

    def doc_overlap(artwork_id: str) -> float:
        if not query_tokens:
            return 0.0
        weighted = [
            (token, math.log((len(index_rows) + 1) / (df.get(token, 0) + 1)) + 1.0)
            for token in query_tokens
        ]
        weighted.sort(key=lambda item: item[1], reverse=True)
        weighted = weighted[:16]
        denom = sum(weight for _token, weight in weighted)
        if denom <= 0:
            return 0.0
        tokens = index_tokens.get(artwork_id, set())
        return sum(weight for token, weight in weighted if token in tokens) / denom

    doc_lexical_raw = [(row["artwork_id"], doc_overlap(row["artwork_id"])) for row in index_rows]
    doc_lexical_norm = minmax_scores(doc_lexical_raw)
    candidate_by_id = {candidate["id"]: candidate for candidate in candidates}
    lexical_by_id = {row["candidate"]["id"]: row for row in lexical}
    rows = []
    for artwork_id in candidate_by_id:
        lex = lexical_norm.get(artwork_id, 0.0)
        sem = semantic_norm.get(artwork_id, 0.0)
        doclex = doc_lexical_norm.get(artwork_id, 0.0)
        # Semantic retrieval carries candidate recall for anonymous/decorative
        # objects; lexical still protects explicit labels/titles/OCR.
        score = 0.58 * sem + 0.20 * doclex + 0.16 * lex
        if lexical_by_id.get(artwork_id, {}).get("signals", {}).get("ocr_score", 0) > 0:
            score += 0.08
        if lexical_by_id.get(artwork_id, {}).get("signals", {}).get("title_score", 0) >= 0.9:
            score += 0.06
        rows.append({
            "candidate": candidate_by_id[artwork_id],
            "score": round(score, 5),
            "signals": {
                "semantic_score": round(semantic_norm.get(artwork_id, 0.0), 4),
                "semantic_raw": round(dict(semantic_raw).get(artwork_id, 0.0), 4),
                "doc_lexical_score": round(doclex, 4),
                "lexical_score": round(lexical_norm.get(artwork_id, 0.0), 4),
                **(lexical_by_id.get(artwork_id, {}).get("signals") or {}),
            },
        })
    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:limit]


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    counts = Counter()
    for row in rows:
        pos = row.get("rank_position")
        for n in [1, 3, 5, 10, 20]:
            if pos is not None and pos <= n:
                counts[f"top{n}"] += 1
    return {
        "total": total,
        **{f"top{n}_recall": counts[f"top{n}"] / total if total else 0 for n in [1, 3, 5, 10, 20]},
        "top_counts": {f"top{n}": counts[f"top{n}"] for n in [1, 3, 5, 10, 20]},
        "misses_top20": sum(1 for row in rows if row.get("rank_position") is None or row["rank_position"] > 20),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--variant", default="pristine")
    parser.add_argument("--mode", default="hybrid_stage2")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if not INDEX.exists():
        raise SystemExit(f"missing search index: {INDEX}. Run louvre_build_recognition_search_index.py --apply first")
    result_rows = [
        row for row in read_jsonl(Path(args.results))
        if row.get("mode") == args.mode and row.get("variant") == args.variant and row.get("vision")
    ]
    index_rows = read_jsonl(INDEX)
    texts = [query_text(row["vision"]) for row in result_rows]
    query_embeddings = embed_queries(sorted(set(texts)))
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as session:
        candidates = get_recognition_candidates(session, "louvre")

    out_rows = []
    for row, text in zip(result_rows, texts):
        ranked = combined_rank(row["vision"], candidates, index_rows, query_embeddings[text], args.limit)
        pos = None
        for idx, item in enumerate(ranked, 1):
            if item["candidate"]["id"] == row["artwork_id"]:
                pos = idx
                break
        out_rows.append({
            "artwork_id": row["artwork_id"],
            "artwork_ark": row.get("artwork_ark"),
            "expected_title": row.get("expected_title"),
            "department": row.get("department"),
            "tier": row.get("tier"),
            "variant": row.get("variant"),
            "query_text": text,
            "rank_position": pos,
            "top_candidates": [
                {
                    "rank": idx,
                    "artwork_id": item["candidate"]["id"],
                    "title": item["candidate"].get("title"),
                    "department": item["candidate"].get("department"),
                    "score": item.get("score"),
                    "signals": item.get("signals"),
                }
                for idx, item in enumerate(ranked, 1)
            ],
        })

    slug = now_slug()
    detail_path = OUT / f"louvre_semantic_retrieval_recall_{slug}.jsonl"
    summary_path = OUT / f"louvre_semantic_retrieval_recall_summary_{slug}.json"
    write_jsonl(detail_path, out_rows)
    summary = summarize(out_rows)
    summary.update({
        "input_results": str(Path(args.results)),
        "index_path": str(INDEX),
        "embedding_model": EMBEDDING_MODEL,
        "detail_path": str(detail_path.relative_to(ROOT)),
    })
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
