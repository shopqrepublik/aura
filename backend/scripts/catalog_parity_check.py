"""
Read-only parity check after DEMO_ARTWORKS has been imported into artworks.

Compares the legacy in-memory rows against the DB-backed catalog repository
for every current Orsay/Orangerie runtime catalog record.
"""
import os
import sys

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.normpath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

load_dotenv(os.path.join(REPO_ROOT, ".env"))

from app.catalog import get_recognition_candidates  # noqa: E402
from app.main import DEMO_ARTWORKS  # noqa: E402

FIELDS = ["id", "museum_id", "title", "artist", "image_url"]
EXPECTED_COUNTS = {"orsay": 101, "orangerie": 15, "louvre": 0}


def _require_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set (check .env)")
    return database_url


def main() -> None:
    engine = create_engine(_require_database_url())
    expected_by_id = {row["id"]: row for row in DEMO_ARTWORKS}
    mismatches = []

    with Session(engine) as session:
        db_by_id = {}
        counts = {}
        for museum_id in EXPECTED_COUNTS:
            candidates = get_recognition_candidates(session, museum_id)
            counts[museum_id] = len(candidates)
            for row in candidates:
                db_by_id[row["id"]] = row

        for artwork_id, expected in expected_by_id.items():
            actual = db_by_id.get(artwork_id)
            if not actual:
                mismatches.append({"id": artwork_id, "field": "__missing__", "expected": "present", "actual": "missing"})
                continue
            for field in FIELDS:
                if expected.get(field) != actual.get(field):
                    mismatches.append(
                        {
                            "id": artwork_id,
                            "field": field,
                            "expected": expected.get(field),
                            "actual": actual.get(field),
                        }
                    )

    print(f"expected_counts={EXPECTED_COUNTS}")
    print(f"actual_counts={counts}")
    print(f"parity={len(expected_by_id) - len({m['id'] for m in mismatches})}/{len(expected_by_id)}")
    print(f"mismatches={len(mismatches)}")
    if mismatches:
        for mismatch in mismatches[:20]:
            print(mismatch)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
