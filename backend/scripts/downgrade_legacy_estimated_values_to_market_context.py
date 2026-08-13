from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text


TARGET_MUSEUM_IDS = ("orsay", "orangerie")
TARGET_SQL = """
    SELECT
        v.id AS value_reveal_id,
        v.artwork_id,
        a.museum_id,
        a.title_original,
        a.artist,
        v.catalog_version,
        v.mode,
        v.aggregate_value_eligible,
        v.estimated_value_low,
        v.estimated_value_high,
        v.estimated_value_currency,
        v.confidence,
        v.methodology,
        v.disclaimer,
        v.sources,
        v.source_reference,
        v.context_date
    FROM artwork_value_reveals v
    JOIN artworks a ON a.id = v.artwork_id
    WHERE a.museum_id = ANY(:museum_ids)
      AND v.mode = 'ESTIMATED_VALUE'
    ORDER BY a.museum_id, a.id
"""

MARKET_CONTEXT_EXPLANATION = (
    "Comparable auction evidence gives a sense of the market around this artist or category. "
    "It is not a sale estimate for this museum-owned work."
)
MARKET_CONTEXT_DISCLAIMER = "Market context only; not an appraisal, insurance value, or sale estimate."
MARKET_CONTEXT_SOURCE_REFERENCE = "Legacy ELYIO comparable-market methodology; reclassified from estimated value after provenance audit."


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    return value


def backup_rows(rows: list[dict[str, Any]], backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / "legacy_estimated_value_rows_before.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(to_jsonable(row), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reclassify legacy Orsay/Orangerie comparable-market ranges from ESTIMATED_VALUE to MARKET_CONTEXT."
    )
    parser.add_argument("--apply", action="store_true", help="Apply production DB updates. Without this, only dry-runs.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--backup-dir", default=None)
    args = parser.parse_args()

    load_env(Path(args.env_file))
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    engine = create_engine(database_url)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(args.backup_dir or f"backups/legacy_value_provenance_downgrade_{timestamp}")

    with engine.begin() as conn:
        rows = [dict(row._mapping) for row in conn.execute(text(TARGET_SQL), {"museum_ids": list(TARGET_MUSEUM_IDS)})]
        backup_path = backup_rows(rows, backup_dir)

        by_museum: dict[str, int] = {}
        for row in rows:
            by_museum[row["museum_id"]] = by_museum.get(row["museum_id"], 0) + 1

        print(json.dumps({
            "apply": args.apply,
            "target_rows": len(rows),
            "by_museum": by_museum,
            "backup_path": str(backup_path),
            "new_mode": "MARKET_CONTEXT",
            "new_aggregate_value_eligible": False,
        }, ensure_ascii=False, sort_keys=True))

        if not args.apply:
            return

        update_sql = text("""
            UPDATE artwork_value_reveals
            SET
                mode = 'MARKET_CONTEXT',
                aggregate_value_eligible = FALSE,
                estimated_value_low = NULL,
                estimated_value_high = NULL,
                estimated_value_currency = NULL,
                market_context_headline_number = CAST(:headline_number AS jsonb),
                market_context_currency = 'EUR_MILLION',
                market_context_label = 'Comparable market context',
                market_context_explanation = :explanation,
                relationship_to_artwork = :relationship,
                context_type = 'COMPARABLE_MARKET_CONTEXT',
                source_reference = :source_reference,
                context_date = COALESCE(context_date, :context_date),
                confidence = COALESCE(confidence, 'medium'),
                disclaimer = :disclaimer,
                updated_at = NOW()
            WHERE id = :value_reveal_id
        """)

        changed = 0
        for row in rows:
            low = to_jsonable(row["estimated_value_low"])
            high = to_jsonable(row["estimated_value_high"])
            result = conn.execute(update_sql, {
                "value_reveal_id": row["value_reveal_id"],
                "headline_number": json.dumps({"low": low, "high": high}, sort_keys=True),
                "explanation": MARKET_CONTEXT_EXPLANATION,
                "relationship": row["methodology"] or "",
                "source_reference": MARKET_CONTEXT_SOURCE_REFERENCE,
                "context_date": datetime.now(timezone.utc).date().isoformat(),
                "disclaimer": MARKET_CONTEXT_DISCLAIMER,
            })
            changed += result.rowcount or 0

        remaining = conn.execute(text("""
            SELECT a.museum_id, v.mode, COUNT(*) AS count
            FROM artwork_value_reveals v
            JOIN artworks a ON a.id = v.artwork_id
            WHERE a.museum_id = ANY(:museum_ids)
            GROUP BY a.museum_id, v.mode
            ORDER BY a.museum_id, v.mode
        """), {"museum_ids": list(TARGET_MUSEUM_IDS)}).fetchall()

        print(json.dumps({
            "updated_rows": changed,
            "post_counts": [dict(row._mapping) for row in remaining],
        }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
