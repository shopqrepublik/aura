"""Run National Gallery Phase 1 entirely in an isolated in-memory database."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
from backend.app.ingestion import apply_plan, build_plan, readiness_report
from backend.app.international import get_institution_international_config, get_value_output_policy
from backend.app.models import Artwork, ArtworkCatalogMembership, Base, Country, CulturalObject, IngestionRun, Institution, InstitutionHolding, InstitutionProfile, MediaAsset, MediaAssetAssociation, SourceProvider, SourceRecord


def seed(db, config: dict) -> None:
    country, institution, profile, provider = (config[key] for key in ("country", "institution", "profile", "provider"))
    db.add(Country(code=country["code"], name=country["name"], default_locale=country["default_locale"], default_timezone=country["default_timezone"], default_currency=country["default_currency"], active=True))
    db.add(Institution(id=institution["id"], slug=institution["slug"], name=institution["name"], country_code=country["code"], city=institution["city"], timezone=institution["timezone"], default_locale=institution["default_locale"], supported_locales=institution["supported_locales"], display_currency=institution["display_currency"], content_policy=institution["content_policy"], experience_level="AI_GUIDE", active=True))
    db.add(InstitutionProfile(institution_id=institution["id"], candidate_universe=profile["candidate_universe"], recognition_policy=profile["recognition_policy"], active=True))
    db.add(SourceProvider(id=provider["id"], name="National Gallery, London", provider_type="MUSEUM", base_url=provider["endpoint"], adapter_key=provider["adapter_key"], adapter_config={"institution_ids": [institution["id"]]}, active=True))
    db.commit()


def entity_counts(db) -> dict:
    return {name: db.query(model).count() for name, model in (("cultural_objects", CulturalObject), ("holdings", InstitutionHolding), ("source_records", SourceRecord), ("artworks", Artwork), ("media_assets", MediaAsset), ("media_associations", MediaAssetAssociation), ("active_memberships", ArtworkCatalogMembership))}


def main() -> None:
    parser = argparse.ArgumentParser(description="National Gallery Phase 1 isolated validation")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--config", default="backend/data/onboarding/national_gallery_london/config.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    adapter = NationalGalleryLondonAdapter(args.snapshot)
    records = tuple(adapter.records())
    ids = [row.provider_record_id for row in records]
    discovery = {
        "source_records_discoverable": adapter.snapshot["snapshot"]["source_total"]["value"], "records_retrieved": len(records),
        "unique_provider_ids": len(set(ids)), "duplicate_provider_ids": len(ids)-len(set(ids)),
        "with_accession": sum(bool(r.institution_record_id) for r in records), "with_artist": sum(bool(r.creator_display) for r in records),
        "with_title": sum(bool(r.title_original) for r in records), "with_dates": sum(bool(r.date_display) for r in records),
        "with_source_url": sum(bool(r.source_url) for r in records), "with_media": sum(bool(r.media) for r in records),
        "media_references": sum(len(r.media) for r in records),
        "with_explicit_rights": sum(bool((h.get("_source",{}).get("legal") or {}).get("rights")) for h in adapter.snapshot["records"]),
        "incomplete_rights": sum(not bool((h.get("_source",{}).get("legal") or {}).get("rights")) for h in adapter.snapshot["records"]),
        "malformed": sum(not r.provider_record_id or not r.title_original for r in records),
    }
    engine=create_engine("sqlite+pysqlite:///:memory:"); Base.metadata.create_all(engine); Session=sessionmaker(bind=engine)
    with Session() as db:
        seed(db, config); before=entity_counts(db)
        dry=build_plan(db, adapter, config["institution"]["id"], mode="DRY_RUN"); after_dry=entity_counts(db)
        run_one=apply_plan(db, dry, operator_id="isolated-phase1"); after_first=entity_counts(db)
        repeat=build_plan(db, adapter, config["institution"]["id"], mode="RECONCILE", include_missing=True)
        run_two=apply_plan(db, repeat, operator_id="isolated-phase1"); after_second=entity_counts(db)
        intl=get_institution_international_config(db, config["institution"]["id"]); value=get_value_output_policy(intl)
        result={"environment":"isolated_in_memory_sqlite","production_mutations":0,"source_snapshot":adapter.source_snapshot(),"discovery":discovery,"dry_run":dry.summary,"dry_run_zero_mutation":before==after_dry,"plan_actions":dict(Counter(r.action for r in dry.records)),"plan_risks":dict(Counter(r.risk for r in dry.records)),"first_apply_run":run_one,"repeat_apply_run":run_two,"first_apply_counts":after_first,"repeat_apply_counts":after_second,"repeat_apply_idempotent":after_first==after_second,"reconcile_actions":dict(Counter(r.action for r in repeat.records)),"readiness":readiness_report(db, config["institution"]["id"]),"international":{"country":intl.country_code,"timezone":intl.timezone,"locale":intl.default_locale,"currency":intl.display_currency},"value_engine":{"enabled":value.enabled,"engine_currency":value.engine_currency,"display_currency":value.display_currency},"ingestion_runs":db.query(IngestionRun).count()}
    engine.dispose(); print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
