"""Provision the National Gallery controlled recognition catalog.

APPLY is explicit and idempotent. The institution is active for backend
recognition but remains protected by ``controlled_preview_only``; it is not
returned by the public directory and its artworks are not publicly readable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
from backend.app.db import SessionLocal
from backend.app.ingestion import apply_plan, build_plan
from backend.app.models import (
    Artwork, ArtworkCatalogMembership, Base, Country, Institution, InstitutionProfile,
    MediaAsset, MediaAssetAssociation, RecognitionAsset, SourceProvider,
)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "backend/data/onboarding/national_gallery_london/pre_eminent_review_snapshot_2026-08-23.json"
CONFIG = ROOT / "backend/data/onboarding/national_gallery_london/config.json"
INSTITUTION_ID = "national-gallery-london"
PROVIDER_ID = "national_gallery_london"
CATALOG_VERSION = "ng-controlled-170-v1"


def register(db) -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    country = db.get(Country, "GB")
    if country is None:
        country = Country(code="GB", name="United Kingdom")
        db.add(country)
    country.default_locale = "en-GB"; country.default_timezone = "Europe/London"; country.default_currency = "GBP"; country.active = True
    institution = db.get(Institution, INSTITUTION_ID)
    if institution is None:
        institution = Institution(id=INSTITUTION_ID, slug=INSTITUTION_ID, name="The National Gallery")
        db.add(institution)
    institution.common_name = "National Gallery"; institution.city = "London"; institution.country_code = "GB"
    institution.timezone = "Europe/London"; institution.default_locale = "en-GB"; institution.supported_locales = ["en-GB"]
    institution.display_currency = "GBP"; institution.experience_level = "CURATED"; institution.active = True
    institution.content_policy = {**(data["institution"].get("content_policy") or {}), "controlled_preview_only": True, "seo_enabled": False}
    profile = db.get(InstitutionProfile, INSTITUTION_ID)
    if profile is None:
        profile = InstitutionProfile(institution_id=INSTITUTION_ID)
        db.add(profile)
    profile.visitor_catalog_version = CATALOG_VERSION; profile.candidate_universe = "ACTIVE_CATALOG"
    profile.recognition_policy = "ASSET_VERIFY"; profile.supported_modes = ["normal", "simple", "kids"]
    profile.max_candidates = 5; profile.confidence_auto = .92; profile.confidence_review = .82
    profile.fuzzy_candidate_threshold = .55; profile.allow_recognition_asset_substitution = True
    profile.prompt_context = "The National Gallery, London. Resolve only against ELYIO's institution-scoped catalog."
    profile.directory_priority = 1000; profile.active = True
    provider = db.get(SourceProvider, PROVIDER_ID)
    if provider is None:
        provider = SourceProvider(id=PROVIDER_ID, name="National Gallery, London", provider_type="MUSEUM")
        db.add(provider)
    provider.base_url = data["provider"]["endpoint"]; provider.adapter_key = "national_gallery_ciim_v1"
    provider.adapter_config = {"institution_ids": [INSTITUTION_ID]}; provider.active = True
    db.commit()


def activate_controlled_catalog(db) -> dict:
    artworks = db.query(Artwork).filter(Artwork.museum_id == INSTITUTION_ID).all()
    memberships = assets = 0
    for position, artwork in enumerate(artworks):
        membership = db.query(ArtworkCatalogMembership).filter_by(artwork_id=artwork.id, catalog_version=CATALOG_VERSION).first()
        if membership is None:
            membership = ArtworkCatalogMembership(artwork_id=artwork.id, museum_id=INSTITUTION_ID, catalog_version=CATALOG_VERSION)
            db.add(membership); memberships += 1
        membership.active = True; membership.tier = "CONTROLLED_PREVIEW"; membership.visitor_priority = float(170 - position)
        association = (
            db.query(MediaAssetAssociation, MediaAsset)
            .join(MediaAsset, MediaAsset.id == MediaAssetAssociation.media_asset_id)
            .filter(
                MediaAssetAssociation.active.is_(True),
                MediaAssetAssociation.institution_holding_id == artwork.institution_holding_id,
                MediaAsset.media_type == "IMAGE",
                MediaAsset.original_url.isnot(None),
            ).order_by(MediaAssetAssociation.position.asc().nullslast()).first()
        )
        if association is None:
            continue
        edge, media = association
        edge.recognition_eligible = True; media.recognition_eligible = True
        recognition_url = f"https://data.ng.ac.uk/iiif/3/{media.provider_asset_id}/full/max/0/default.jpg"
        recognition = db.query(RecognitionAsset).filter_by(artwork_id=artwork.id, source_url=recognition_url).first()
        if recognition is None:
            recognition = RecognitionAsset(artwork_id=artwork.id, source="national_gallery_controlled_preview", source_url=recognition_url)
            db.add(recognition); assets += 1
        recognition.license = media.license_code; recognition.attribution = media.attribution
        recognition.rights_status = (media.rights_status or "unknown").lower()
        recognition.ai_tdm_eligible = True; recognition.embedding_eligible = True
        recognition.local_storage_status = "not_fetched"
    db.commit()
    return {"artworks": len(artworks), "memberships_created": memberships, "recognition_assets_created": assets}


def status(db) -> dict:
    return {
        "institution": db.get(Institution, INSTITUTION_ID) is not None,
        "artworks": db.query(Artwork).filter_by(museum_id=INSTITUTION_ID).count(),
        "active_controlled_memberships": db.query(ArtworkCatalogMembership).filter_by(museum_id=INSTITUTION_ID, catalog_version=CATALOG_VERSION, active=True).count(),
        "recognition_assets": db.query(RecognitionAsset).join(Artwork, Artwork.id == RecognitionAsset.artwork_id).filter(Artwork.museum_id == INSTITUTION_ID).count(),
        "public_selector": False,
        "seo": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("mode", choices=("PLAN", "APPLY", "STATUS")); parser.add_argument("--operator")
    args = parser.parse_args()
    if args.mode == "APPLY" and not args.operator: parser.error("--operator is required for APPLY")
    if args.mode == "PLAN":
        engine = create_engine("sqlite+pysqlite:///:memory:"); Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        with Session() as db:
            register(db)
            adapter = NationalGalleryLondonAdapter(SNAPSHOT)
            plan = build_plan(db, adapter, INSTITUTION_ID, mode="PLAN")
            result = {"environment": "isolated_in_memory_sqlite", "production_mutations": 0, "plan": plan.summary, "production_public_activation": False}
        engine.dispose()
    else:
        with SessionLocal() as db:
            if args.mode == "STATUS": result = status(db)
            else:
                register(db)
                adapter = NationalGalleryLondonAdapter(SNAPSHOT)
                plan = build_plan(db, adapter, INSTITUTION_ID, mode="PLAN")
                result = {"plan": plan.summary, "production_public_activation": False}
                result["ingestion_run_id"] = apply_plan(db, plan, operator_id=args.operator)
                result["controlled_catalog"] = activate_controlled_catalog(db)
                result["status"] = status(db)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__": main()
