"""
Dry-run/apply importer for the current trusted DEMO_ARTWORKS runtime catalog.

Default is dry-run. Use --apply only after catalog_schema_migration.sql has
been reviewed/applied and the production-write approval has been granted.
"""
import argparse
import os
import sys
from datetime import datetime, timezone

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.normpath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

load_dotenv(os.path.join(REPO_ROOT, ".env"))

from app.main import DEMO_ARTWORKS  # noqa: E402
from app.models import Artwork, ArtworkEstimate, Museum  # noqa: E402

EXPECTED_COUNTS = {"orsay": 101, "orangerie": 15}
SOURCE = "demo_artworks"


def _require_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set (check .env)")
    return database_url


def _validate_demo_catalog() -> None:
    counts: dict[str, int] = {}
    ids = set()
    duplicates = []
    for row in DEMO_ARTWORKS:
        counts[row["museum_id"]] = counts.get(row["museum_id"], 0) + 1
        if row["id"] in ids:
            duplicates.append(row["id"])
        ids.add(row["id"])
    if duplicates:
        raise SystemExit(f"duplicate DEMO_ARTWORKS ids: {duplicates}")
    if counts != EXPECTED_COUNTS:
        raise SystemExit(f"unexpected DEMO_ARTWORKS counts: expected {EXPECTED_COUNTS}, found {counts}")


def _copy_artwork_fields(target: Artwork, source: dict) -> None:
    target.museum_id = source["museum_id"]
    target.artist = source.get("artist")
    target.title_original = source["title"]
    target.year = source.get("year")
    target.inventory_number = source.get("inventory_number")
    target.hall = source.get("hall")
    target.image_url = source.get("image_url")
    target.priority = source.get("priority", 100)
    target.tags = source.get("tags") or []
    target.source_urls = source.get("source_urls") or []
    target.source = SOURCE
    target.source_record_id = source["id"]
    target.source_url = source.get("source_urls", [None])[0] if source.get("source_urls") else None
    target.last_source_sync = datetime.now(timezone.utc)
    target.raw_json = source
    target.display_status = "ON_DISPLAY"
    target.metadata_status = "READY"
    target.recognition_status = "READY"


def _upsert_estimate(session: Session, artwork_id: str, source: dict) -> None:
    low = source.get("estimate_low")
    high = source.get("estimate_high")
    if low is None or high is None:
        return
    row = session.query(ArtworkEstimate).filter(ArtworkEstimate.artwork_id == artwork_id).first()
    if row is None:
        session.add(
            ArtworkEstimate(
                artwork_id=artwork_id,
                estimate_low_eur_m=low,
                estimate_high_eur_m=high,
                estimate_confidence="low",
            )
        )
        return
    row.estimate_low_eur_m = low
    row.estimate_high_eur_m = high
    if row.estimate_confidence is None:
        row.estimate_confidence = "low"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes; default is dry-run")
    args = parser.parse_args()

    _validate_demo_catalog()
    engine = create_engine(_require_database_url())

    with Session(engine) as session:
        missing_museums = sorted({a["museum_id"] for a in DEMO_ARTWORKS} - {m.id for m in session.query(Museum).all()})
        if missing_museums:
            raise SystemExit(f"missing required museum rows: {missing_museums}")

        existing_ids = {row.id for row in session.query(Artwork.id).all()}
        new_rows = [a for a in DEMO_ARTWORKS if a["id"] not in existing_ids]
        updates = [a for a in DEMO_ARTWORKS if a["id"] in existing_ids]

        print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
        print(f"source={SOURCE}")
        print(f"expected_counts={EXPECTED_COUNTS}")
        print(f"demo_total={len(DEMO_ARTWORKS)}")
        print(f"new={len(new_rows)}")
        print(f"would_update={len(updates)}")

        if not args.apply:
            session.rollback()
            return

        for source in DEMO_ARTWORKS:
            row = session.get(Artwork, source["id"])
            if row is None:
                row = Artwork(id=source["id"])
                session.add(row)
            _copy_artwork_fields(row, source)
            _upsert_estimate(session, source["id"], source)

        session.commit()

    print("done")


if __name__ == "__main__":
    main()
