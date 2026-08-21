import base64
import hashlib
import os
import unittest
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import admin
from backend.app.models import Artwork, ArtworkCatalogMembership, Base, LouvreImageReference, ProductEvent, RecognitionAsset


def make_hash(password: str) -> str:
    salt = b"test-admin-salt"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 1000)
    return "pbkdf2_sha256$1000$" + base64.urlsafe_b64encode(salt).decode().rstrip("=") + "$" + base64.urlsafe_b64encode(digest).decode().rstrip("=")


class AdminPanelTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.old_hash = admin.ADMIN_PASSWORD_HASH
        self.old_email = admin.ADMIN_EMAIL
        admin.ADMIN_PASSWORD_HASH = make_hash("correct-password")
        admin.ADMIN_EMAIL = "admin@example.com"
        app = FastAPI()
        app.include_router(admin.router)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[admin.get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        admin.ADMIN_PASSWORD_HASH = self.old_hash
        admin.ADMIN_EMAIL = self.old_email
        self.engine.dispose()

    def test_password_hash_verification(self):
        encoded = make_hash("secret")
        self.assertTrue(admin.verify_password("secret", encoded))
        self.assertFalse(admin.verify_password("wrong", encoded))

    def test_admin_login_logout_and_api_auth(self):
        self.assertEqual(self.client.get("/v1/admin/me").status_code, 401)
        self.assertEqual(self.client.post("/v1/admin/login", json={"email": "admin@example.com", "password": "bad"}).status_code, 401)
        login = self.client.post("/v1/admin/login", json={"email": "admin@example.com", "password": "correct-password"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/v1/admin/me").status_code, 200)
        self.assertEqual(self.client.post("/v1/admin/logout").status_code, 200)
        self.assertEqual(self.client.get("/v1/admin/me").status_code, 401)

    def test_metric_helpers(self):
        self.assertEqual(admin._confidence_bucket(0.1), "0-0.25")
        self.assertEqual(admin._confidence_bucket(0.9), "0.85+")
        self.assertEqual(admin._percentile([100, 300, 200], 50), 200)
        start, end, prev_start, prev_end, key = admin._period_bounds("7d")
        self.assertEqual(key, "7d")
        self.assertIsNotNone(start)
        self.assertIsNotNone(prev_start)
        self.assertGreater(end - start, timedelta(days=6))

    def test_identityless_server_recognition_is_operational_not_visitor_metric(self):
        db = self.Session()
        now = datetime.now(timezone.utc)
        db.add(ProductEvent(event_id="attempt-1", event_name="recognition_started", occurred_at=now, museum_id="louvre"))
        db.add(ProductEvent(event_id="done-1", event_name="recognition_completed", occurred_at=now, museum_id="louvre", properties={"status": "matched", "confidence": 1.0}))
        db.add(ProductEvent(event_id="attempt-2", event_name="recognition_started", occurred_at=now, museum_id="louvre"))
        db.add(ProductEvent(event_id="fail-1", event_name="recognition_failed", occurred_at=now, museum_id="louvre", properties={"reason": "ai_error"}))
        db.commit()
        metrics = admin._recognition_metrics(db, now - timedelta(minutes=1), now + timedelta(minutes=1))
        db.close()
        self.assertEqual(metrics["attempts"], 0)
        self.assertEqual(metrics["successful"], 0)
        self.assertEqual(metrics["failed"], 0)
        self.assertIsNone(metrics["success_rate"])
        self.assertEqual(metrics["identityless_operational_events"], 4)

    def test_identified_recognition_counts_as_visitor_metric(self):
        db = self.Session()
        now = datetime.now(timezone.utc)
        identity = {"anonymous_id": "anon-1", "session_id": "session-1"}
        db.add(ProductEvent(event_id="attempt-1", event_name="recognition_started", occurred_at=now, museum_id="louvre", **identity))
        db.add(ProductEvent(event_id="done-1", event_name="scan_success", occurred_at=now, museum_id="louvre", artwork_id="work-1", properties={"confidence": 0.9}, **identity))
        db.commit()
        metrics = admin._recognition_metrics(db, now - timedelta(minutes=1), now + timedelta(minutes=1))
        db.close()
        self.assertEqual(metrics["attempts"], 1)
        self.assertEqual(metrics["successful"], 1)
        self.assertEqual(metrics["failed"], 0)
        self.assertEqual(metrics["success_rate"], 100.0)

    def test_internal_test_events_are_excluded_from_founder_metrics(self):
        db = self.Session()
        now = datetime.now(timezone.utc)
        db.add(ProductEvent(
            event_id="internal-app",
            event_name="app_opened",
            occurred_at=now,
            anonymous_id="qa-anon",
            session_id="qa-session",
            properties={"internal_test": True},
        ))
        db.add(ProductEvent(
            event_id="real-app",
            event_name="app_opened",
            occurred_at=now,
            anonymous_id="real-anon",
            session_id="real-session",
            properties={},
        ))
        db.commit()
        active = admin._identity_count(db, now - timedelta(minutes=1), now + timedelta(minutes=1), {"app_opened"})
        sessions = admin._basic_user_metrics(db, now - timedelta(minutes=1), now + timedelta(minutes=1), None, None)["sessions"]
        db.close()
        self.assertEqual(active, 1)
        self.assertEqual(sessions, 1)

    def test_catalog_health_separates_presentation_reference_and_assets(self):
        db = self.Session()
        db.add_all([
            Artwork(id="with-presentation", museum_id="louvre", title_original="With presentation", image_url="https://example.com/a.jpg", recognition_status="VISION_READY"),
            Artwork(id="with-asset", museum_id="louvre", title_original="With asset", recognition_status="VISION_PLUS_ASSET"),
            Artwork(id="with-louvre-ref", museum_id="louvre", title_original="With Louvre ref", recognition_status="VISION_READY"),
            Artwork(id="no-reference", museum_id="louvre", title_original="No reference", recognition_status="VISION_READY"),
        ])
        for artwork_id in ["with-presentation", "with-asset", "with-louvre-ref", "no-reference"]:
            db.add(ArtworkCatalogMembership(artwork_id=artwork_id, museum_id="louvre", catalog_version="test", active=True))
        db.add(RecognitionAsset(artwork_id="with-asset", source="wikimedia_commons", source_url="https://commons.example/work.jpg", local_storage_status="not_fetched"))
        db.add(LouvreImageReference(artwork_id="with-louvre-ref", url_image="https://collections.louvre.example/work.jpg", fetched=False))
        db.commit()
        metrics = admin._catalog_health(db)
        db.close()
        self.assertEqual(metrics["active_visitor_catalog_total"], 4)
        self.assertEqual(metrics["works_with_presentation_images"], 1)
        self.assertEqual(metrics["works_missing_presentation_images"], 3)
        self.assertEqual(metrics["works_with_recognition_assets"], 1)
        self.assertEqual(metrics["works_missing_recognition_assets"], 3)
        self.assertEqual(metrics["works_with_source_or_reference_images"], 3)
        self.assertEqual(metrics["works_missing_any_image_reference"], 1)


if __name__ == "__main__":
    unittest.main()
