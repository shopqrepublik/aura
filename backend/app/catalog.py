from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .models import (
    Artwork,
    ArtworkCatalogMembership,
    ArtworkEstimate,
    ArtworkValueReveal,
    Institution,
    InstitutionProfile,
    RecognitionAsset,
)


class CatalogUnavailableError(RuntimeError):
    """Raised when the DB-backed catalog cannot be queried."""


class InstitutionNotReadyError(CatalogUnavailableError):
    """Controlled fail-closed state for missing/invalid institution config."""


@dataclass(frozen=True)
class InstitutionRuntimeConfig:
    institution_id: str
    display_name: str
    visitor_catalog_version: Optional[str]
    candidate_universe: str
    recognition_policy: str
    supported_modes: tuple[str, ...]
    max_candidates: int
    confidence_auto: float
    confidence_review: float
    fuzzy_candidate_threshold: float
    prompt_context: Optional[str]
    allow_recognition_asset_substitution: bool


VALID_CANDIDATE_UNIVERSES = {"ACTIVE_CATALOG", "INSTITUTION_ARTWORKS", "NONE"}
VALID_RECOGNITION_POLICIES = {"TOP_N_METADATA", "ASSET_VERIFY", "UNCATALOGED_ONLY", "NOT_READY"}


def _has_membership_table(db: Session) -> bool:
    return db.bind is not None and inspect(db.bind).has_table("artwork_catalog_memberships")


def get_institution_runtime_config(db: Session, institution_id: str) -> InstitutionRuntimeConfig:
    if not institution_id:
        raise InstitutionNotReadyError("institution_not_ready: institution identifier is required")
    institution = db.get(Institution, institution_id)
    profile = db.get(InstitutionProfile, institution_id)
    if institution is None or not institution.active:
        raise InstitutionNotReadyError(f"institution_not_ready: unknown or inactive institution {institution_id!r}")
    if profile is None or not profile.active:
        raise InstitutionNotReadyError(f"institution_not_ready: no active profile for institution {institution_id!r}")
    if profile.candidate_universe not in VALID_CANDIDATE_UNIVERSES:
        raise InstitutionNotReadyError(f"institution_not_ready: invalid candidate universe for {institution_id!r}")
    if profile.recognition_policy not in VALID_RECOGNITION_POLICIES:
        raise InstitutionNotReadyError(f"institution_not_ready: invalid recognition policy for {institution_id!r}")
    if profile.candidate_universe == "ACTIVE_CATALOG" and not profile.visitor_catalog_version:
        raise InstitutionNotReadyError(f"institution_not_ready: active catalog version missing for {institution_id!r}")
    valid_pairings = {
        "ACTIVE_CATALOG": {"TOP_N_METADATA", "ASSET_VERIFY"},
        "INSTITUTION_ARTWORKS": {"TOP_N_METADATA", "ASSET_VERIFY"},
        "NONE": {"UNCATALOGED_ONLY"},
    }
    if profile.recognition_policy not in valid_pairings[profile.candidate_universe]:
        raise InstitutionNotReadyError(f"institution_not_ready: incompatible candidate universe and policy for {institution_id!r}")
    if profile.recognition_policy == "NOT_READY":
        raise InstitutionNotReadyError(f"institution_not_ready: recognition disabled for {institution_id!r}")
    return InstitutionRuntimeConfig(
        institution_id=institution.id,
        display_name=institution.common_name or institution.name,
        visitor_catalog_version=profile.visitor_catalog_version,
        candidate_universe=profile.candidate_universe,
        recognition_policy=profile.recognition_policy,
        supported_modes=tuple(profile.supported_modes or []),
        max_candidates=max(1, int(profile.max_candidates or 5)),
        confidence_auto=float(profile.confidence_auto),
        confidence_review=float(profile.confidence_review),
        fuzzy_candidate_threshold=float(profile.fuzzy_candidate_threshold),
        prompt_context=profile.prompt_context,
        allow_recognition_asset_substitution=bool(profile.allow_recognition_asset_substitution),
    )


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
                "content_policy_code": row.content_policy_code,
                "institutional_legal_context_localizations": row.institutional_legal_context_localizations or {},
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
    recognition_asset: Optional[RecognitionAsset] = None,
    allow_recognition_asset_substitution: bool = True,
) -> dict:
    """Return the legacy DEMO_ARTWORKS-shaped dict used by recognition/UI APIs."""
    reveal = explicit_value_reveal_to_dict(value_reveal) or estimate_to_value_reveal(estimate)
    recognition_image_url = artwork.image_url
    recognition_asset_id = None
    if (
        recognition_asset is not None
        and recognition_asset.embedding_eligible
        and allow_recognition_asset_substitution
    ):
        recognition_image_url = recognition_asset.source_url
        recognition_asset_id = recognition_asset.id
    return {
        "id": artwork.id,
        "museum_id": artwork.museum_id,
        "artist": artwork.artist,
        "title": artwork.title_original,
        "year": artwork.year,
        "hall": artwork.hall or artwork.room,
        "inventory_number": artwork.inventory_number,
        "image_url": recognition_image_url,
        "recognition_asset_id": recognition_asset_id,
        "visual_descriptor": recognition_asset.visual_descriptor if recognition_asset is not None else None,
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
        "object_type": artwork.object_type,
        "materials_and_techniques": artwork.materials_and_techniques,
        "dimensions": artwork.dimensions,
        "description": artwork.description,
        "provenance": artwork.provenance,
        "object_history": artwork.object_history,
        "historical_context": artwork.historical_context,
        "current_location_raw": artwork.current_location_raw,
        "room": artwork.room,
        "creator_raw": artwork.creator_raw,
        "creator_labels": artwork.creator_labels,
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


def _recognition_asset_by_artwork_id(db: Session, artwork_ids: Iterable[str]) -> dict[str, RecognitionAsset]:
    ids = list(artwork_ids)
    if not ids:
        return {}
    if db.bind is None or not inspect(db.bind).has_table("recognition_assets"):
        return {}
    rows = (
        db.query(RecognitionAsset)
        .filter(
            RecognitionAsset.artwork_id.in_(ids),
            RecognitionAsset.embedding_eligible.is_(True),
            RecognitionAsset.ai_tdm_eligible.is_(True),
        )
        .order_by(RecognitionAsset.artwork_id.asc(), RecognitionAsset.updated_at.desc())
        .all()
    )
    by_id: dict[str, RecognitionAsset] = {}
    for row in rows:
        by_id.setdefault(row.artwork_id, row)
    return by_id


def get_recognition_candidates(
    db: Session,
    museum_id: str,
    catalog_version: Optional[str] = None,
    runtime_config: Optional[InstitutionRuntimeConfig] = None,
) -> list[dict]:
    try:
        config = runtime_config or get_institution_runtime_config(db, museum_id)
        if catalog_version and catalog_version != config.visitor_catalog_version:
            raise InstitutionNotReadyError(f"institution_not_ready: requested catalog version is not active for {museum_id!r}")
        if config.candidate_universe == "NONE":
            return []
        if config.candidate_universe == "ACTIVE_CATALOG":
            if not _has_membership_table(db):
                raise InstitutionNotReadyError(f"institution_not_ready: catalog membership table missing for {museum_id!r}")
            version = config.visitor_catalog_version
            rows = (
                db.query(Artwork)
                .join(ArtworkCatalogMembership, ArtworkCatalogMembership.artwork_id == Artwork.id)
                .filter(
                    Artwork.museum_id == museum_id,
                    ArtworkCatalogMembership.museum_id == museum_id,
                    ArtworkCatalogMembership.catalog_version == version,
                    ArtworkCatalogMembership.active.is_(True),
                )
                .order_by(ArtworkCatalogMembership.visitor_priority.desc().nullslast(), Artwork.priority.asc().nullslast(), Artwork.id.asc())
                .all()
            )
            if not rows:
                raise InstitutionNotReadyError(f"institution_not_ready: active catalog is empty for {museum_id!r}")
        elif config.candidate_universe == "INSTITUTION_ARTWORKS":
            rows = (
                db.query(Artwork)
                .filter(Artwork.museum_id == museum_id)
                .order_by(Artwork.priority.asc().nullslast(), Artwork.id.asc())
                .all()
            )
        else:
            raise InstitutionNotReadyError(f"institution_not_ready: candidate universe disabled for {museum_id!r}")
        estimates = _estimate_by_artwork_id(db, [row.id for row in rows])
        value_reveals = _value_reveal_by_artwork_id(db, [row.id for row in rows])
        recognition_assets = _recognition_asset_by_artwork_id(db, [row.id for row in rows])
        return [
            artwork_to_catalog_dict(
                row,
                estimates.get(row.id),
                value_reveals.get(row.id),
                recognition_assets.get(row.id),
                config.allow_recognition_asset_substitution,
            )
            for row in rows
        ]
    except InstitutionNotReadyError:
        raise
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog lookup failed for museum_id={museum_id!r}: {exc}") from exc


def get_global_recognition_candidates(db: Session, limit: int = 3000) -> list[dict]:
    """Return a bounded global catalog index for unknown-museum reconciliation.

    This is metadata reconciliation after open visual identification, not a
    model prompt candidate list. The bound covers the current multi-institution
    catalog while keeping the shortlist sent to verification small.
    """
    rows = db.query(Artwork).order_by(Artwork.priority.asc().nullslast(), Artwork.id.asc()).limit(limit).all()
    estimates = _estimate_by_artwork_id(db, [row.id for row in rows])
    value_reveals = _value_reveal_by_artwork_id(db, [row.id for row in rows])
    recognition_assets = _recognition_asset_by_artwork_id(db, [row.id for row in rows])
    return [artwork_to_catalog_dict(row, estimates.get(row.id), value_reveals.get(row.id), recognition_assets.get(row.id), False) for row in rows]


def get_catalog_artwork(db: Session, artwork_id: str) -> Optional[dict]:
    try:
        row = db.get(Artwork, artwork_id)
        if row is None:
            return None
        estimate = _estimate_by_artwork_id(db, [row.id]).get(row.id)
        value_reveal = _value_reveal_by_artwork_id(db, [row.id]).get(row.id)
        recognition_asset = _recognition_asset_by_artwork_id(db, [row.id]).get(row.id)
        profile = db.get(InstitutionProfile, row.museum_id)
        allow_substitution = bool(profile and profile.active and profile.allow_recognition_asset_substitution)
        return artwork_to_catalog_dict(row, estimate, value_reveal, recognition_asset, allow_substitution)
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog artwork lookup failed for artwork_id={artwork_id!r}: {exc}") from exc


def get_catalog_artworks_by_ids(db: Session, museum_id: str, artwork_ids: Iterable[str], catalog_version: Optional[str] = None) -> list[dict]:
    ids = list(artwork_ids)
    if not museum_id or not ids:
        return []
    try:
        config = get_institution_runtime_config(db, museum_id)
        if config.candidate_universe == "NONE":
            return []
        if config.candidate_universe == "ACTIVE_CATALOG":
            version = config.visitor_catalog_version
            rows = (
                db.query(Artwork)
                .join(ArtworkCatalogMembership, ArtworkCatalogMembership.artwork_id == Artwork.id)
                .filter(
                    Artwork.museum_id == museum_id,
                    Artwork.id.in_(ids),
                    ArtworkCatalogMembership.museum_id == museum_id,
                    ArtworkCatalogMembership.catalog_version == version,
                    ArtworkCatalogMembership.active.is_(True),
                )
                .order_by(ArtworkCatalogMembership.visitor_priority.desc().nullslast(), Artwork.priority.asc().nullslast(), Artwork.id.asc())
                .all()
            )
        elif config.candidate_universe == "INSTITUTION_ARTWORKS":
            rows = (
                db.query(Artwork)
                .filter(Artwork.museum_id == museum_id, Artwork.id.in_(ids))
                .order_by(Artwork.priority.asc().nullslast(), Artwork.id.asc())
                .all()
            )
        else:
            raise InstitutionNotReadyError(f"institution_not_ready: candidate universe disabled for {museum_id!r}")
        estimates = _estimate_by_artwork_id(db, [row.id for row in rows])
        value_reveals = _value_reveal_by_artwork_id(db, [row.id for row in rows])
        recognition_assets = _recognition_asset_by_artwork_id(db, [row.id for row in rows])
        return [artwork_to_catalog_dict(row, estimates.get(row.id), value_reveals.get(row.id), recognition_assets.get(row.id), config.allow_recognition_asset_substitution) for row in rows]
    except InstitutionNotReadyError:
        raise
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog artwork list lookup failed for museum_id={museum_id!r}: {exc}") from exc


def count_catalog_artworks(db: Session, museum_id: str, catalog_version: Optional[str] = None) -> int:
    if not museum_id:
        return 0
    try:
        config = get_institution_runtime_config(db, museum_id)
        if config.candidate_universe == "NONE":
            return 0
        if config.candidate_universe == "ACTIVE_CATALOG":
            version = config.visitor_catalog_version
            return (
                db.query(ArtworkCatalogMembership)
                .filter(
                    ArtworkCatalogMembership.museum_id == museum_id,
                    ArtworkCatalogMembership.catalog_version == version,
                    ArtworkCatalogMembership.active.is_(True),
                )
                .count()
            )
        if config.candidate_universe == "INSTITUTION_ARTWORKS":
            return db.query(Artwork).filter(Artwork.museum_id == museum_id).count()
        raise InstitutionNotReadyError(f"institution_not_ready: candidate universe disabled for {museum_id!r}")
    except InstitutionNotReadyError:
        raise
    except Exception as exc:
        raise CatalogUnavailableError(f"catalog count failed for museum_id={museum_id!r}: {exc}") from exc
