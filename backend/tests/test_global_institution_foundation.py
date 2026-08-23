import hashlib
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.catalog import (
    InstitutionNotReadyError,
    get_institution_runtime_config,
    get_recognition_candidates,
)
from backend.app.models import (
    Artwork,
    ArtworkCatalogMembership,
    Base,
    Country,
    Institution,
    InstitutionProfile,
)
from backend.scripts.migrate import (
    BASELINE_ID,
    Migration,
    applied_migrations,
    apply_pending,
    baseline,
)


class InstitutionConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def test_country_institution_and_profile_lookup(self):
        with self.Session() as db:
            db.add(Country(code="GB", name="United Kingdom", default_locale="en", default_timezone="Europe/London"))
            db.add(Institution(id="test-gallery", name="Test Gallery", country_code="GB", city="London", timezone="Europe/London", default_locale="en", supported_locales=["en"], active=True))
            db.add(InstitutionProfile(institution_id="test-gallery", candidate_universe="NONE", recognition_policy="UNCATALOGED_ONLY", supported_modes=["normal"]))
            db.commit()
            config = get_institution_runtime_config(db, "test-gallery")
            self.assertEqual(config.display_name, "Test Gallery")
            self.assertEqual(config.candidate_universe, "NONE")
            self.assertEqual(db.get(Institution, "test-gallery").country_code, "GB")

    def test_unknown_institution_fails_closed(self):
        with self.Session() as db:
            with self.assertRaisesRegex(InstitutionNotReadyError, "institution_not_ready"):
                get_recognition_candidates(db, "does-not-exist")

    def test_unconfigured_institution_does_not_fall_back_to_all_artworks(self):
        with self.Session() as db:
            db.add(Country(code="FR", name="France"))
            db.add(Institution(id="configured", name="Configured", country_code="FR", active=True))
            db.add(InstitutionProfile(institution_id="configured", candidate_universe="NONE", recognition_policy="UNCATALOGED_ONLY"))
            db.add(Institution(id="other", name="Other", country_code="FR", active=True))
            db.add(Artwork(id="other-work", museum_id="other", title_original="Other Work"))
            db.commit()
            self.assertEqual(get_recognition_candidates(db, "configured"), [])

    def test_louvre_active_catalog_behavior_and_asset_quarantine_are_data_driven(self):
        with self.Session() as db:
            db.add(Country(code="FR", name="France"))
            db.add(Institution(id="louvre", name="Musée du Louvre", country_code="FR", active=True))
            db.add(InstitutionProfile(
                institution_id="louvre",
                visitor_catalog_version="v1",
                candidate_universe="ACTIVE_CATALOG",
                recognition_policy="TOP_N_METADATA",
                allow_recognition_asset_substitution=False,
            ))
            db.add_all([
                Artwork(id="active", museum_id="louvre", title_original="Active", image_url="https://example.test/presentation.jpg"),
                Artwork(id="inactive", museum_id="louvre", title_original="Inactive"),
            ])
            db.add(ArtworkCatalogMembership(artwork_id="active", museum_id="louvre", catalog_version="v1", active=True))
            db.commit()
            config = get_institution_runtime_config(db, "louvre")
            candidates = get_recognition_candidates(db, "louvre")
            self.assertEqual(config.recognition_policy, "TOP_N_METADATA")
            self.assertFalse(config.allow_recognition_asset_substitution)
            self.assertEqual([row["id"] for row in candidates], ["active"])

    def test_active_catalog_with_no_rows_fails_closed(self):
        with self.Session() as db:
            db.add(Country(code="FR", name="France"))
            db.add(Institution(id="empty", name="Empty", country_code="FR", active=True))
            db.add(InstitutionProfile(institution_id="empty", visitor_catalog_version="v1", candidate_universe="ACTIVE_CATALOG", recognition_policy="TOP_N_METADATA"))
            db.commit()
            with self.assertRaisesRegex(InstitutionNotReadyError, "active catalog is empty"):
                get_recognition_candidates(db, "empty")


class MigrationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        with self.engine.begin() as connection:
            for table in ("museums", "artworks", "artwork_catalog_memberships", "product_events", "admin_sessions", "admin_login_attempts"):
                connection.execute(text(f"CREATE TABLE {table} (id VARCHAR PRIMARY KEY)"))
        baseline_sql = "-- validated baseline; no DDL"
        second_sql = "CREATE TABLE migration_test (id VARCHAR PRIMARY KEY)"
        self.migrations = [
            Migration(BASELINE_ID, Path("baseline.sql"), hashlib.sha256(baseline_sql.encode()).hexdigest(), baseline_sql),
            Migration("0002_test", Path("test.sql"), hashlib.sha256(second_sql.encode()).hexdigest(), second_sql),
        ]

    def test_baseline_is_validation_only_and_idempotent(self):
        baseline(self.engine, self.migrations)
        baseline(self.engine, self.migrations)
        applied = applied_migrations(self.engine)
        self.assertEqual(set(applied), {BASELINE_ID})

    def test_ordered_apply_records_ledger_and_attempt(self):
        baseline(self.engine, self.migrations)
        self.assertEqual(apply_pending(self.engine, self.migrations), ["0002_test"])
        self.assertEqual(apply_pending(self.engine, self.migrations), [])
        with self.engine.connect() as connection:
            status = connection.execute(text("SELECT status FROM schema_migration_attempts WHERE migration_id='0002_test'")).scalar_one()
        self.assertEqual(status, "APPLIED")

    def test_failure_is_visible_and_not_marked_applied(self):
        baseline(self.engine, self.migrations)
        bad_sql = "CREATE TABLE broken ("
        bad = Migration("0002_bad", Path("bad.sql"), hashlib.sha256(bad_sql.encode()).hexdigest(), bad_sql)
        with self.assertRaises(Exception):
            apply_pending(self.engine, [self.migrations[0], bad])
        with self.engine.connect() as connection:
            status = connection.execute(text("SELECT status FROM schema_migration_attempts WHERE migration_id='0002_bad'")).scalar_one()
        self.assertEqual(status, "FAILED")
        self.assertNotIn("0002_bad", applied_migrations(self.engine))


if __name__ == "__main__":
    unittest.main()
