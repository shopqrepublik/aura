"""Provision the National Gallery controlled recognition catalog.

APPLY is explicit and idempotent. The institution is active for backend
recognition but remains protected by ``controlled_preview_only``; it is not
returned by the public directory and its artworks are not publicly readable.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:  # repository execution
    from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
    from backend.app.db import SessionLocal
    from backend.app.ingestion import apply_plan, build_plan, stable_id
    from backend.app.models import Artwork, ArtworkCatalogMembership, Base, Country, Institution, InstitutionProfile, MediaAsset, MediaAssetAssociation, RecognitionAsset, SourceProvider
except ModuleNotFoundError:  # Fly image execution from /app
    from app.adapters.national_gallery_london import NationalGalleryLondonAdapter
    from app.db import SessionLocal
    from app.ingestion import apply_plan, build_plan, stable_id
    from app.models import Artwork, ArtworkCatalogMembership, Base, Country, Institution, InstitutionProfile, MediaAsset, MediaAssetAssociation, RecognitionAsset, SourceProvider

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2] if (SCRIPT.parents[2] / "backend").exists() else SCRIPT.parents[1]
BACKEND_ROOT = ROOT / "backend" if (ROOT / "backend").exists() else ROOT
SNAPSHOT = BACKEND_ROOT / "data/onboarding/national_gallery_london/source_snapshot_2026-08-23.json"
SELECTION = BACKEND_ROOT / "data/onboarding/national_gallery_london/controlled_catalog_1000_v1.json"
READINESS = BACKEND_ROOT / "data/onboarding/national_gallery_london/controlled_catalog_1000_recognition_readiness_v1.json"
DESCRIPTORS = BACKEND_ROOT / "data/onboarding/national_gallery_london/controlled_catalog_1000_visual_descriptors_v1.json"
CONFIG = BACKEND_ROOT / "data/onboarding/national_gallery_london/config.json"
INSTITUTION_ID = "national-gallery-london"
PROVIDER_ID = "national_gallery_london"
CATALOG_VERSION = "ng-controlled-1000-v1-retrieval"
CONTROLLED_SIZE = 1000


def selection() -> tuple[list[str], set[str]]:
    rows = json.loads(SELECTION.read_text(encoding="utf-8"))["records"]
    ordered = [str(row["provider_record_id"]) for row in rows]
    if len(ordered) != CONTROLLED_SIZE or len(set(ordered)) != CONTROLLED_SIZE:
        raise RuntimeError(f"controlled selection must contain exactly {CONTROLLED_SIZE} unique provider IDs")
    return ordered, set(ordered)


def selected_adapter(provider_record_ids: set[str] | None = None) -> NationalGalleryLondonAdapter:
    return NationalGalleryLondonAdapter(SNAPSHOT, provider_record_ids=provider_record_ids or selection()[1])


def apply_in_bounded_batches(db, *, operator: str, batch_size: int = 100) -> dict:
    """Apply source records without materializing a 1,000-record raw plan.

    Source ingestion is additive and idempotent; controlled membership/profile
    activation remains a single, separate final step. A failed batch can be
    retried safely and can never expose a partial public catalog.
    """
    ordered, _ = selection()
    summaries: list[dict] = []
    run_ids: list[str] = []
    for offset in range(0, len(ordered), batch_size):
        batch = set(ordered[offset:offset + batch_size])
        adapter = selected_adapter(batch)
        plan = build_plan(db, adapter, INSTITUTION_ID, mode="PLAN")
        summaries.append(plan.summary)
        run_ids.append(apply_plan(db, plan, operator_id=operator))
        db.expunge_all()
        del plan, adapter
        gc.collect()
    totals = {
        key: sum(int(summary.get(key, 0)) for summary in summaries)
        for key in summaries[0]
    } if summaries else {}
    return {"batch_size": batch_size, "batches": len(summaries), "ingestion_run_ids": run_ids, "summary": totals}


def recognition_ready_ids() -> set[str]:
    rows = json.loads(READINESS.read_text(encoding="utf-8"))["records"]
    return {stable_id("artwork", PROVIDER_ID, str(row["provider_record_id"])) for row in rows if row["readiness"] == "VISION_PLUS_ASSET"}


def recognition_descriptors() -> dict[str, dict]:
    rows = json.loads(DESCRIPTORS.read_text(encoding="utf-8"))["records"]
    return {
        stable_id("artwork", PROVIDER_ID, str(row["provider_record_id"])): {
            "version": row["version"],
            "values": row["values"],
            "source_sha256": row["source_sha256"],
        }
        for row in rows
    }


def register(db) -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    country = db.get(Country, "GB")
    if country is None:
        country = Country(code="GB", name="United Kingdom")
        db.add(country)
    country.default_locale = "en-GB"; country.default_timezone = "Europe/London"; country.default_currency = "GBP"; country.active = True
    db.flush()
    institution = db.get(Institution, INSTITUTION_ID)
    if institution is None:
        institution = Institution(id=INSTITUTION_ID, slug=INSTITUTION_ID, name="The National Gallery")
        db.add(institution)
    institution.common_name = "National Gallery"; institution.city = "London"; institution.country_code = "GB"
    institution.timezone = "Europe/London"; institution.default_locale = "en-GB"; institution.supported_locales = ["en-GB"]
    institution.display_currency = "GBP"; institution.experience_level = "CURATED"; institution.active = True
    institution.content_policy = {**(data["institution"].get("content_policy") or {}), "controlled_preview_only": True, "seo_enabled": False}
    db.flush()
    profile = db.get(InstitutionProfile, INSTITUTION_ID)
    if profile is None:
        profile = InstitutionProfile(institution_id=INSTITUTION_ID)
        db.add(profile)
    # Keep the currently active controlled version until the replacement
    # memberships have been applied successfully. Fresh isolated databases
    # can point directly at the target version.
    if not profile.visitor_catalog_version:
        profile.visitor_catalog_version = CATALOG_VERSION
    profile.candidate_universe = "ACTIVE_CATALOG"
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
    db.flush()


def activate_controlled_catalog(db) -> dict:
    ordered_provider_ids, _ = selection()
    plus_asset_ids = recognition_ready_ids()
    descriptors = recognition_descriptors()
    order = {stable_id("artwork", PROVIDER_ID, provider_id): position for position, provider_id in enumerate(ordered_provider_ids)}
    artworks = db.query(Artwork).filter(Artwork.id.in_(tuple(order))).all()
    if len(artworks) != len(order):
        raise RuntimeError(f"selected artwork parity failed: expected {len(order)}, found {len(artworks)}")
    memberships = assets = 0
    # Historical controlled versions remain auditable but are not active
    # candidate universes after this explicit version switch.
    db.query(ArtworkCatalogMembership).filter(
        ArtworkCatalogMembership.museum_id == INSTITUTION_ID,
        ArtworkCatalogMembership.catalog_version != CATALOG_VERSION,
        ArtworkCatalogMembership.active.is_(True),
    ).update({ArtworkCatalogMembership.active: False}, synchronize_session=False)
    for artwork in artworks:
        position = order[artwork.id]
        membership = db.query(ArtworkCatalogMembership).filter_by(artwork_id=artwork.id, catalog_version=CATALOG_VERSION).first()
        if membership is None:
            membership = ArtworkCatalogMembership(artwork_id=artwork.id, museum_id=INSTITUTION_ID, catalog_version=CATALOG_VERSION)
            db.add(membership); memberships += 1
        membership.active = True; membership.tier = "CONTROLLED_PREVIEW"; membership.visitor_priority = float(CONTROLLED_SIZE - position)
        if artwork.id not in plus_asset_ids:
            continue
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
        recognition.visual_descriptor = descriptors.get(artwork.id)
    db.get(InstitutionProfile, INSTITUTION_ID).visitor_catalog_version = CATALOG_VERSION
    db.commit()
    return {"artworks": len(artworks), "memberships_created": memberships, "recognition_assets_created": assets}


def status(db) -> dict:
    selected_ids = tuple(stable_id("artwork", PROVIDER_ID, provider_id) for provider_id in selection()[0])
    asset_artworks = db.query(RecognitionAsset.artwork_id).filter(RecognitionAsset.artwork_id.in_(selected_ids)).distinct().count()
    memberships = db.query(ArtworkCatalogMembership).filter_by(museum_id=INSTITUTION_ID, catalog_version=CATALOG_VERSION, active=True).count()
    return {
        "institution": db.get(Institution, INSTITUTION_ID) is not None,
        "artworks": db.query(Artwork).filter_by(museum_id=INSTITUTION_ID).count(),
        "catalog_version": CATALOG_VERSION,
        "active_controlled_memberships": memberships,
        "recognition_assets": db.query(RecognitionAsset).join(Artwork, Artwork.id == RecognitionAsset.artwork_id).filter(Artwork.museum_id == INSTITUTION_ID).count(),
        "vision_plus_asset": asset_artworks,
        "vision_ready": memberships - asset_artworks,
        "not_ready": 0,
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
            adapter = selected_adapter()
            plan = build_plan(db, adapter, INSTITUTION_ID, mode="PLAN")
            result = {"environment": "isolated_in_memory_sqlite", "production_mutations": 0, "plan": plan.summary, "production_public_activation": False}
        engine.dispose()
    else:
        with SessionLocal() as db:
            if args.mode == "STATUS": result = status(db)
            else:
                register(db)
                db.commit()
                result = {"production_public_activation": False}
                result["ingestion"] = apply_in_bounded_batches(db, operator=args.operator)
                result["controlled_catalog"] = activate_controlled_catalog(db)
                result["status"] = status(db)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__": main()
