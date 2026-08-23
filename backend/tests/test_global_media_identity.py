import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.app.international import get_institution_international_config, normalize_locale, validate_currency
from backend.app.models import (
    Artwork, ArtworkLocalization, Base, Country, CulturalObject,
    Institution, InstitutionHolding, MediaAsset, SourceProvider, SourceRecord,
)
from backend.app.source_adapter import AdapterMediaRecord, AdapterObjectRecord


class GlobalIdentityMediaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def seed_institution(self, db, code="FR", institution_id="museum", timezone_name="Europe/Paris", locale="fr", currency="EUR"):
        db.add(Country(code=code, name=code, default_locale=locale, default_timezone=timezone_name, default_currency=currency))
        db.add(Institution(id=institution_id, name=institution_id, country_code=code, city="City", timezone=timezone_name, default_locale=locale, supported_locales=[locale], display_currency=currency))

    def test_same_title_is_not_identity_and_localization_does_not_create_object(self):
        with self.Session() as db:
            self.seed_institution(db)
            one = CulturalObject(id="object:one", canonical_title="Untitled")
            two = CulturalObject(id="object:two", canonical_title="Untitled")
            db.add_all([one, two])
            db.add_all([
                InstitutionHolding(id="holding:one", cultural_object_id=one.id, institution_id="museum", institution_record_id="INV-1"),
                InstitutionHolding(id="holding:two", cultural_object_id=two.id, institution_id="museum", institution_record_id="INV-2"),
            ])
            db.add_all([
                Artwork(id="legacy-one", museum_id="museum", cultural_object_id=one.id, institution_holding_id="holding:one", title_original="Untitled", artist="Same Artist"),
                Artwork(id="legacy-two", museum_id="museum", cultural_object_id=two.id, institution_holding_id="holding:two", title_original="Untitled", artist="Same Artist"),
            ])
            db.add(ArtworkLocalization(artwork_id="legacy-one", locale="en-GB", mode="normal", title="A translated title"))
            db.commit()
            self.assertEqual(db.query(CulturalObject).count(), 2)
            self.assertEqual(db.get(Artwork, "legacy-one").cultural_object_id, "object:one")

    def test_provider_record_identity_is_unique_and_preserves_legacy_artwork_id(self):
        with self.Session() as db:
            self.seed_institution(db)
            db.add(SourceProvider(id="provider", name="Provider"))
            db.add(CulturalObject(id="object:legacy-id"))
            db.add(InstitutionHolding(id="holding:legacy-id", cultural_object_id="object:legacy-id", institution_id="museum", institution_record_id="P-1"))
            db.add(Artwork(id="legacy-id", museum_id="museum", cultural_object_id="object:legacy-id", institution_holding_id="holding:legacy-id", title_original="Work"))
            db.add(SourceRecord(id="source:1", provider_id="provider", provider_record_id="P-1", cultural_object_id="object:legacy-id", institution_holding_id="holding:legacy-id", institution_id="museum"))
            db.commit()
            self.assertEqual(db.get(Artwork, "legacy-id").id, "legacy-id")
            db.add(SourceRecord(id="source:duplicate", provider_id="provider", provider_record_id="P-1", cultural_object_id="object:legacy-id"))
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_media_purposes_rights_and_eligibility_are_independent(self):
        with self.Session() as db:
            self.seed_institution(db)
            db.add(SourceProvider(id="commons", name="Commons"))
            db.add(CulturalObject(id="object:media"))
            db.add(InstitutionHolding(id="holding:media", cultural_object_id="object:media", institution_id="museum", institution_record_id="M-1"))
            db.add(Artwork(id="media", museum_id="museum", cultural_object_id="object:media", institution_holding_id="holding:media", title_original="Media"))
            original = MediaAsset(id="media:source", cultural_object_id="object:media", artwork_id="media", provider_id="commons", purpose="SOURCE_ORIGINAL", original_url="https://example.test/a.jpg", rights_status="UNKNOWN", verification_state="UNKNOWN", presentation_eligible=None, recognition_eligible=False)
            presentation = MediaAsset(id="media:presentation", cultural_object_id="object:media", artwork_id="media", provider_id="commons", purpose="PRESENTATION", original_url="https://example.test/p.jpg", rights_status="LICENSED", verification_state="DECLARED_BY_SOURCE", presentation_eligible=True, recognition_eligible=False)
            recognition = MediaAsset(id="media:recognition", cultural_object_id="object:media", artwork_id="media", provider_id="commons", purpose="RECOGNITION_ASSET", original_url="https://example.test/r.jpg", rights_status="LICENSED", verification_state="VERIFIED", presentation_eligible=False, recognition_eligible=True)
            derivative = MediaAsset(id="media:derivative", cultural_object_id="object:media", artwork_id="media", provider_id="commons", purpose="DERIVATIVE", original_url="https://example.test/d.jpg", derivative_of_id="media:source", derivative_spec={"width": 512})
            db.add_all([original, presentation, recognition, derivative])
            db.commit()
            self.assertEqual(db.get(MediaAsset, "media:source").rights_status, "UNKNOWN")
            self.assertFalse(db.get(MediaAsset, "media:presentation").recognition_eligible)
            self.assertTrue(db.get(MediaAsset, "media:recognition").recognition_eligible)
            self.assertEqual(db.get(MediaAsset, "media:derivative").derivative_of_id, "media:source")

    def test_france_and_hypothetical_uk_configuration_are_generic(self):
        with self.Session() as db:
            self.seed_institution(db)
            self.seed_institution(db, "GB", "london-test", "Europe/London", "en-GB", "GBP")
            db.commit()
            fr = get_institution_international_config(db, "museum")
            gb = get_institution_international_config(db, "london-test")
            self.assertEqual((fr.timezone, fr.display_currency), ("Europe/Paris", "EUR"))
            self.assertEqual((gb.timezone, gb.default_locale, gb.display_currency), ("Europe/London", "en-GB", "GBP"))
            self.assertEqual(normalize_locale("zh-hans"), "zh-Hans")
            self.assertEqual(validate_currency("gbp"), "GBP")

    def test_source_adapter_contract_carries_identity_language_and_media_policy(self):
        record = AdapterObjectRecord(
            provider_id="example-provider",
            provider_record_id="object-123",
            institution_id="gallery",
            source_url="https://provider.example/objects/123",
            source_language="en-GB",
            title_original="A Work",
            institution_record_id="NG-123",
            media=(AdapterMediaRecord(
                provider_asset_id="image-1",
                original_url="https://provider.example/images/1.jpg",
                purpose="REFERENCE",
                rights_status="UNKNOWN",
                presentation_eligible=True,
                recognition_eligible=False,
            ),),
        )
        self.assertEqual(record.institution_id, "gallery")
        self.assertEqual(record.source_language, "en-GB")
        self.assertTrue(record.media[0].presentation_eligible)
        self.assertFalse(record.media[0].recognition_eligible)


if __name__ == "__main__":
    unittest.main()
