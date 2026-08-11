from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .models import Artwork, ArtworkEstimate, ArtworkValueReveal


class CatalogUnavailableError(RuntimeError):
    """Raised when the DB-backed catalog cannot be queried."""


def estimate_to_value_reveal(estimate: Optional[ArtworkEstimate]) -> Optional[dict]:
    if estimate is None:
        return None
    return {
        "mode": "ESTIMATED_VALUE",
        "aggregate_value_eligible": True,
        "estimated_value": {
            "low": estimate.estimate_low_eur_m,
            "high": estimate.estimate_high_eur_m,
            "currency": "EUR",
            "confidence": estimate.estimate_confidence,
            "as_of_date": estimate.updated_at.date().isoformat() if estimate.updated_at else None,
            "methodology": estimate.estimate_logic,
            "disclaimer": None,
        },
    }


def explicit_value_reveal_to_dict(row: Optional[ArtworkValueReveal]) -> Optional[dict]:
    if row is None:
        return None
    if row.mode == "ESTIMATED_VALUE":
        if row.estimated_value_low is None or row.estimated_value_high is None:
            return None
        return {
            "mode": "ESTIMATED_VALUE",
            "aggregate_value_eligible": row.aggregate_value_eligible,
            "estimated_value": {
                "low": row.estimated_value_low,
                "high": row.estimated_value_high,
                "currency": row.estimated_value_currency or "EUR",
                "confidence": row.confidence,
                "as_of_date": row.context_date,
                "methodology": row.methodology,
                "disclaimer": row.disclaimer,
            },
            "review_status": row.review_status,
            "catalog_version": row.catalog_version,
            "sources": row.sources or [],
        }
    if row.mode == "MARKET_CONTEXT":
        return {
            "mode": "MARKET_CONTEXT",
            "aggregate_value_eligible": False,
            "market_context": {
                "headline_number": row.market_context_headline_number,
                "currency": row.market_context_currency,
                "label": row.market_context_label or "market context",
                "explanation": row.market_context_explanation or "",
                "relationship_to_artwork": row.relationship_to_artwork or "",
                "context_type": row.context_type or "MARKET_CONTEXT",
                "source_reference": row.source_reference,
                "date": row.context_date,
                "confidence": row.confidence,
                "disclaimer": row.disclaimer,
            },
            "review_status": row.review_status,
            "catalog_version": row.catalog_version,
            "sources": row.sources or [],
        }
    if row.mode == "BEYOND_MARKET":
        return {
            "mode": "BEYOND_MARKET",
            "aggregate_value_eligible": False,
            "beyond_market": {
                "headline": row.beyond_market_headline or "No ordinary market price.",
                "explanation": row.beyond_market_explanation or "",
                "institutional_legal_context": row.institutional_legal_context,
                "optional_context": row.optional_context,
                "disclaimer": row.disclaimer,
                "confidence": row.confidence,
            },
            "review_status": row.review_status,
            "catalog_version": row.catalog_version,
            "sources": row.sources or [],
        }
    return None


def aggregate_eligible_value(artwork: dict) -> Optional[dict]:
    reveal = artwork.get("value_reveal")
    if reveal:
        if reveal.get("mode") != "ESTIMATED_VALUE" or reveal.get("aggregate_value_eligible") is not True:
            return None
        estimated = reveal.get("estimated_value") or {}
        if estimated.get("low") is None or estimated.get("high") is None:
            return None
        return estimated
    if artwork.get("estimate_low") is None or artwork.get("estimate_high") is None:
        return None
    return {"low": artwork["estimate_low"], "high": artwork["estimate_high"], "currency": "EUR"}


def artwork_to_catalog_dict(
    artwork: Artwork,
    estimate: Optional[ArtworkEstimate] = None,
    value_reveal: Optional[ArtworkValueReveal] = None,
) -> dict:
    """Return the legacy DEMO_ARTWORKS-shaped dict used by recognition/UI APIs."""
    reveal = explicit_value_reveal_to_dict(value_reveal) or estimate_to_value_reveal(estimate)
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
        "value_reveal": reveal,
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


def _value_reveal_by_artwork_id(db: Session, artwork_ids: Iterable[str]) -> dict[str, ArtworkValueReveal]:
    ids = list(artwork_ids)
    if not ids:
        return {}
    if db.bind is None or not inspect(db.bind).has_table("artwork_value_reveals"):
        return {}
    rows = (
        db.query(ArtworkValueReveal)
        .filter(ArtworkValueReveal.artwork_id.in_(ids))
        .order_by(ArtworkValueReveal.artwork_id.asc(), ArtworkValueReveal.updated_at.desc())
        .all()
    )
    by_id: dict[str, ArtworkValueReveal] = {}
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
        value_reveals = _value_reveal_by_artwork_id(db, [row.id for row in rows])
        return [artwork_to_catalog_dict(row, estimates.get(row.id), value_reveals.get(row.id)) for row in rows]
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog lookup failed for museum_id={museum_id!r}: {exc}") from exc


def get_catalog_artwork(db: Session, artwork_id: str) -> Optional[dict]:
    try:
        row = db.get(Artwork, artwork_id)
        if row is None:
            return None
        estimate = _estimate_by_artwork_id(db, [row.id]).get(row.id)
        value_reveal = _value_reveal_by_artwork_id(db, [row.id]).get(row.id)
        return artwork_to_catalog_dict(row, estimate, value_reveal)
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
        value_reveals = _value_reveal_by_artwork_id(db, [row.id for row in rows])
        return [artwork_to_catalog_dict(row, estimates.get(row.id), value_reveals.get(row.id)) for row in rows]
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog artwork list lookup failed for museum_id={museum_id!r}: {exc}") from exc


def count_catalog_artworks(db: Session, museum_id: str) -> int:
    if not museum_id:
        return 0
    try:
        return db.query(Artwork).filter(Artwork.museum_id == museum_id).count()
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog count failed for museum_id={museum_id!r}: {exc}") from exc
