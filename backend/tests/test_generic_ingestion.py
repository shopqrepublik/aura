import unittest
from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.ingestion import (
    IngestionConfigurationError, apply_plan, build_plan, readiness_report,
    safe_deactivate_source_record,
)
from backend.app.international import get_institution_international_config, get_value_output_policy
from backend.app.models import (
    Artwork, ArtworkCatalogMembership, Base, Country, CulturalObject,
    CulturalObjectDuplicateReview, IngestionRun, Institution, InstitutionHolding,
    InstitutionProfile, MediaAsset, MediaAssetAssociation, SourceProvider, SourceRecord,
)
from backend.app.source_adapter import AdapterMediaRecord, AdapterObjectRecord


class FixtureAdapter:
    adapter_key = "fixture_v1"
    provider_id = "fixture"

    def __init__(self, rows): self.rows = tuple(rows)
    def records(self): return iter(self.rows)
    def source_snapshot(self): return "fixture:snapshot-1"


class GenericIngestionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            db.add(Country(code="FR", name="France", default_locale="fr", default_timezone="Europe/Paris", default_currency="EUR"))
            db.add(Institution(id="museum", name="Museum", country_code="FR", city="City", timezone="Europe/Paris", default_locale="fr", supported_locales=["fr", "en"], display_currency="EUR"))
            db.add(InstitutionProfile(institution_id="museum", candidate_universe="ACTIVE_VISITOR_CATALOG", recognition_policy="VISION_TWO_STAGE"))
            db.add(SourceProvider(id="fixture", name="Fixture", adapter_key="fixture_v1", adapter_config={"institution_ids": ["museum"]}))
            db.commit()

    def row(self, record_id="one", title="Work", accession="INV-1", rights="UNKNOWN", verification="UNKNOWN"):
        return AdapterObjectRecord(
            provider_id="fixture", provider_record_id=record_id, institution_id="museum",
            source_url=f"https://source.test/{record_id}", source_language="en",
            title_original=title, title_locale="en", creator_display="Artist",
            institution_record_id=accession, retrieved_at=datetime.now(timezone.utc),
            media=(AdapterMediaRecord(
                provider_asset_id=f"image-{record_id}", original_url=f"https://source.test/{record_id}.jpg",
                purpose="REFERENCE", rights_status=rights, verification_state=verification,
                presentation_eligible=True, recognition_eligible=True,
            ),),
        )

    def counts(self, db):
        return tuple(db.query(model).count() for model in (CulturalObject, InstitutionHolding, Artwork, SourceRecord, MediaAsset, MediaAssetAssociation, ArtworkCatalogMembership))

    def test_dry_run_plan_has_zero_mutation_and_reports_provenance(self):
        with self.Session() as db:
            before = self.counts(db)
            plan = build_plan(db, FixtureAdapter([self.row()]), "museum", mode="DRY_RUN")
            self.assertEqual(before, self.counts(db))
            self.assertEqual(plan.summary["new_objects"], 1)
            self.assertGreater(plan.summary["provenance_issues"], 0)

    def test_apply_is_idempotent_and_never_activates_catalog(self):
        with self.Session() as db:
            adapter = FixtureAdapter([self.row()])
            first = apply_plan(db, build_plan(db, adapter, "museum"), operator_id="test")
            entity_counts = self.counts(db)
            second = apply_plan(db, build_plan(db, adapter, "museum"), operator_id="test")
            self.assertNotEqual(first, second)
            self.assertEqual(entity_counts, self.counts(db))
            self.assertEqual(db.query(IngestionRun).count(), 2)
            self.assertEqual(db.query(ArtworkCatalogMembership).count(), 0)

    def test_source_update_and_duplicate_source_batch(self):
        with self.Session() as db:
            apply_plan(db, build_plan(db, FixtureAdapter([self.row()]), "museum"), operator_id="test")
            changed = build_plan(db, FixtureAdapter([self.row(title="Materially changed")]), "museum")
            self.assertEqual(changed.records[0].action, "UPDATE")
            self.assertEqual(changed.records[0].risk, "REVIEW_RECOMMENDED")
            duplicate = build_plan(db, FixtureAdapter([self.row(), self.row()]), "museum")
            self.assertEqual(duplicate.records[1].action, "INVALID")

    def test_weak_duplicate_is_suggested_never_merged(self):
        with self.Session() as db:
            apply_plan(db, build_plan(db, FixtureAdapter([self.row("one", accession="INV-1")]), "museum"), operator_id="test")
            plan = build_plan(db, FixtureAdapter([self.row("two", accession="INV-2")]), "museum")
            self.assertEqual(plan.records[0].action, "POSSIBLE_DUPLICATE")
            apply_plan(db, plan, operator_id="test")
            self.assertEqual(db.query(CulturalObject).count(), 2)
            self.assertEqual(db.query(CulturalObjectDuplicateReview).count(), 1)

    def test_rights_gates_and_safe_deactivation(self):
        with self.Session() as db:
            rows = [self.row("unknown"), self.row("declared", accession="INV-2", rights="LICENSED", verification="DECLARED_BY_SOURCE"), self.row("restricted", accession="INV-3", rights="RESTRICTED", verification="RESTRICTED")]
            apply_plan(db, build_plan(db, FixtureAdapter(rows), "museum"), operator_id="test")
            assets = {m.verification_state: m for m in db.query(MediaAsset).all()}
            self.assertIsNone(assets["UNKNOWN"].presentation_eligible)
            self.assertFalse(assets["DECLARED_BY_SOURCE"].recognition_eligible)
            self.assertFalse(assets["RESTRICTED"].presentation_eligible)
            source = db.query(SourceRecord).filter(SourceRecord.provider_record_id == "unknown").one()
            result = safe_deactivate_source_record(db, source.id, operator_id="test")
            self.assertFalse(source.active)
            self.assertEqual(result["media_disabled"], 1)

    def test_fail_closed_target_and_currency_safety(self):
        with self.Session() as db:
            bad = replace(self.row(), institution_id="missing")
            with self.assertRaises(IngestionConfigurationError):
                build_plan(db, FixtureAdapter([bad]), "missing")
            db.add(Country(code="GB", name="United Kingdom", default_locale="en-GB", default_timezone="Europe/London", default_currency="GBP"))
            db.add(Institution(id="national-gallery-paper", name="National Gallery", country_code="GB", city="London", timezone="Europe/London", default_locale="en-GB", supported_locales=["en-GB"], display_currency="GBP"))
            db.commit()
            policy = get_value_output_policy(get_institution_international_config(db, "national-gallery-paper"))
            self.assertFalse(policy.enabled)
            self.assertEqual(policy.engine_currency, "EUR")
            self.assertEqual(policy.display_currency, "GBP")

    def test_shared_media_is_one_entity_with_exact_relationship_edges(self):
        shared = AdapterMediaRecord(
            provider_asset_id="shared-video", original_url="https://source.test/shared.mp4",
            purpose="REFERENCE", media_type="VIDEO", rights_status="LICENSED",
            verification_state="DECLARED_BY_SOURCE", presentation_eligible=None,
            recognition_eligible=False, association_scope="HOLDING",
            association_role="CONTEXTUAL", source_relationship_key="shared-video-edge",
        )
        rows = []
        for index, name in enumerate(("A", "B", "C"), 1):
            specific = AdapterMediaRecord(
                provider_asset_id=f"image-{name}", original_url=f"https://source.test/{name}.jpg",
                purpose="REFERENCE", media_type="IMAGE", rights_status="UNKNOWN",
                verification_state="UNKNOWN", recognition_eligible=False,
                association_scope="HOLDING", association_role="REFERENCE",
                source_relationship_key=f"image-{name}-edge",
            )
            rows.append(replace(self.row(name, title=f"Object {name}", accession=f"INV-{index}"), media=(shared, specific)))
        with self.Session() as db:
            adapter = FixtureAdapter(rows)
            plan = build_plan(db, adapter, "museum", mode="DRY_RUN")
            self.assertEqual(plan.summary["unique_media_assets"], 4)
            self.assertEqual(plan.summary["media_relationship_edges"], 6)
            apply_plan(db, plan, operator_id="test")
            self.assertEqual(db.query(MediaAsset).count(), 4)
            self.assertEqual(db.query(MediaAssetAssociation).count(), 6)
            video = db.query(MediaAsset).filter(MediaAsset.provider_asset_id == "shared-video").one()
            edges = db.query(MediaAssetAssociation).filter(MediaAssetAssociation.media_asset_id == video.id).all()
            self.assertEqual(len(edges), 3)
            self.assertTrue(all(edge.relationship_role == "CONTEXTUAL" for edge in edges))
            self.assertTrue(all(edge.recognition_eligible is False for edge in edges))
            apply_plan(db, build_plan(db, adapter, "museum"), operator_id="test")
            self.assertEqual(db.query(MediaAsset).count(), 4)
            self.assertEqual(db.query(MediaAssetAssociation).count(), 6)

    def test_deactivating_one_source_preserves_shared_asset_and_other_edges(self):
        shared = AdapterMediaRecord(provider_asset_id="shared", original_url="https://source.test/shared.mp4", media_type="VIDEO", purpose="REFERENCE", verification_state="DECLARED_BY_SOURCE", rights_status="LICENSED", association_scope="HOLDING", association_role="CONTEXTUAL", source_relationship_key="shared")
        rows = [replace(self.row("one", accession="INV-1"), media=(shared,)), replace(self.row("two", accession="INV-2", title="Other"), media=(shared,))]
        with self.Session() as db:
            apply_plan(db, build_plan(db, FixtureAdapter(rows), "museum"), operator_id="test")
            source = db.query(SourceRecord).filter(SourceRecord.provider_record_id == "one").one()
            result = safe_deactivate_source_record(db, source.id, operator_id="test")
            self.assertEqual(result["media_associations_disabled"], 1)
            self.assertEqual(db.query(MediaAsset).count(), 1)
            self.assertEqual(db.query(MediaAssetAssociation).filter(MediaAssetAssociation.active.is_(True)).count(), 1)


if __name__ == "__main__":
    unittest.main()
