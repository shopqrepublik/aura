from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from .models import Artwork, ArtworkEstimate


class CatalogUnavailableError(RuntimeError):
    """Raised when the DB-backed catalog cannot be queried."""


def artwork_to_catalog_dict(artwork: Artwork, estimate: Optional[ArtworkEstimate] = None) -> dict:
    """Return the legacy DEMO_ARTWORKS-shaped dict used by recognition/UI APIs."""
    return {
        "id": artwork.id,
        "museum_id": artwork.museum_id,
        "artist": artwork.artist,
        "title": artwork.title_original,
        "year": artwork.year,
        "hall": artwork.hall or artwork.room,
        "inventory_number": artwork.inventory_number,
        "image_url": artwork.image_url,
        "priority": artwork.priority,
        "tags": artwork.tags or [],
        "source_urls": artwork.source_urls or [],
        "estimate_low": estimate.estimate_low_eur_m if estimate else None,
        "estimate_high": estimate.estimate_high_eur_m if estimate else None,
        "needs_editorial_review": estimate.reviewed_by is None if estimate else True,
        "source": artwork.source,
        "source_record_id": artwork.source_record_id,
        "source_url": artwork.source_url,
        "department": artwork.department,
        "display_status": artwork.display_status,
        "metadata_status": artwork.metadata_status,
        "recognition_status": artwork.recognition_status,
        "rights_status": artwork.rights_status,
        "rights_review_required": artwork.rights_review_required,
    }


def _estimate_by_artwork_id(db: Session, artwork_ids: Iterable[str]) -> dict[str, ArtworkEstimate]:
    ids = list(artwork_ids)
    if not ids:
        return {}
    rows = (
        db.query(ArtworkEstimate)
        .filter(ArtworkEstimate.artwork_id.in_(ids))
        .order_by(ArtworkEstimate.artwork_id.asc(), ArtworkEstimate.updated_at.desc())
        .all()
    )
    by_id: dict[str, ArtworkEstimate] = {}
    for row in rows:
        by_id.setdefault(row.artwork_id, row)
    return by_id


def get_recognition_candidates(db: Session, museum_id: str) -> list[dict]:
    if not museum_id:
        return []
    try:
        rows = (
            db.query(Artwork)
            .filter(Artwork.museum_id == museum_id)
            .order_by(Artwork.priority.asc().nullslast(), Artwork.id.asc())
            .all()
        )
        estimates = _estimate_by_artwork_id(db, [row.id for row in rows])
        return [artwork_to_catalog_dict(row, estimates.get(row.id)) for row in rows]
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog lookup failed for museum_id={museum_id!r}: {exc}") from exc


def get_catalog_artwork(db: Session, artwork_id: str) -> Optional[dict]:
    try:
        row = db.get(Artwork, artwork_id)
        if row is None:
            return None
        estimate = _estimate_by_artwork_id(db, [row.id]).get(row.id)
        return artwork_to_catalog_dict(row, estimate)
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog artwork lookup failed for artwork_id={artwork_id!r}: {exc}") from exc


def get_catalog_artworks_by_ids(db: Session, museum_id: str, artwork_ids: Iterable[str]) -> list[dict]:
    ids = list(artwork_ids)
    if not museum_id or not ids:
        return []
    try:
        rows = (
            db.query(Artwork)
            .filter(Artwork.museum_id == museum_id, Artwork.id.in_(ids))
            .order_by(Artwork.priority.asc().nullslast(), Artwork.id.asc())
            .all()
        )
        estimates = _estimate_by_artwork_id(db, [row.id for row in rows])
        return [artwork_to_catalog_dict(row, estimates.get(row.id)) for row in rows]
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog artwork list lookup failed for museum_id={museum_id!r}: {exc}") from exc


def count_catalog_artworks(db: Session, museum_id: str) -> int:
    if not museum_id:
        return 0
    try:
        return db.query(Artwork).filter(Artwork.museum_id == museum_id).count()
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog count failed for museum_id={museum_id!r}: {exc}") from exc
