import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import admin, main
from backend.app.auth import get_optional_current_user
from backend.app.models import (
    AnalyticsIdentityLink,
    Artwork,
    Base,
    Country,
    InstitutionProfile,
    Museum,
    ProductEvent,
    RecognitionAttempt,
    UncatalogedSighting,
    User,
)


def event_payload(**overrides):
    payload = {
        "schema_version": 2,
        "event_id": str(uuid.uuid4()),
        "event_name": "app_opened",
        "client_occurred_at": datetime.now(timezone.utc).isoformat(),
        "anonymous_id": "10000000-0000-4000-8000-000000000001",
        "session_id": "20000000-0000-4000-8000-000000000001",
        "properties": {},
    }
    payload.update(overrides)
    return payload


class EventTrustSecurityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            db.add(Country(code="FR", name="France"))
            db.add(Museum(id="louvre", name="Louvre", country_code="FR", active=True))
            db.add(Artwork(id="known-work", museum_id="louvre", title_original="Known"))
            db.commit()
        self.old_qa = admin.ANALYTICS_QA_TOKEN
        self.old_limit = admin.EVENT_RATE_LIMIT_PER_MINUTE
        admin.ANALYTICS_QA_TOKEN = "test-qa-secret"
        admin.EVENT_RATE_LIMIT_PER_MINUTE = 120
        admin._event_rate_buckets.clear()
        app = FastAPI()
        app.include_router(admin.router)

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[admin.get_db] = override_db
        app.dependency_overrides[get_optional_current_user] = lambda: None
        self.app = app
        self.client = TestClient(app)

    def tearDown(self):
        admin.ANALYTICS_QA_TOKEN = self.old_qa
        admin.EVENT_RATE_LIMIT_PER_MINUTE = self.old_limit
        admin._event_rate_buckets.clear()
        self.engine.dispose()

    def latest(self):
        with self.Session() as db:
            return db.query(ProductEvent).order_by(ProductEvent.created_at.desc()).first()

    def test_public_user_id_spoof_is_rejected(self):
        response = self.client.post("/v1/events", json=event_payload(user_id=str(uuid.uuid4())))
        self.assertEqual(response.status_code, 400)

    def test_public_internal_test_spoof_is_stripped(self):
        response = self.client.post("/v1/events", json=event_payload(properties={"internal_test": True}))
        self.assertEqual(response.status_code, 200)
        row = self.latest()
        self.assertFalse(row.internal_test)
        self.assertNotIn("internal_test", row.properties)

    def test_qa_header_creates_server_trusted_internal_event(self):
        response = self.client.post("/v1/events", json=event_payload(), headers={"X-ELYIO-QA-Token": "test-qa-secret"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.latest().internal_test)

    def test_client_cannot_backdate_canonical_timestamp(self):
        old = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        before = datetime.now(timezone.utc) - timedelta(seconds=2)
        response = self.client.post("/v1/events", json=event_payload(client_occurred_at=old))
        self.assertEqual(response.status_code, 200)
        row = self.latest()
        self.assertGreaterEqual(row.occurred_at.replace(tzinfo=timezone.utc), before)
        self.assertIsNone(row.client_occurred_at)

    def test_unknown_event_and_malformed_ids_are_rejected(self):
        self.assertEqual(self.client.post("/v1/events", json=event_payload(event_name="invented_conversion")).status_code, 422)
        self.assertEqual(self.client.post("/v1/events", json=event_payload(anonymous_id="<script>bad</script>")).status_code, 422)
        self.assertEqual(self.client.post("/v1/events", json=event_payload(session_id="not-a-uuid")).status_code, 422)

    def test_oversized_properties_are_rejected(self):
        response = self.client.post("/v1/events", json=event_payload(properties={"blob": "x" * 9000}))
        self.assertEqual(response.status_code, 422)

    def test_invalid_dimensions_do_not_enter_analytics(self):
        self.assertEqual(self.client.post("/v1/events", json=event_payload(event_name="museum_selected", museum_id="fake-museum")).status_code, 422)
        self.assertEqual(self.client.post("/v1/events", json=event_payload(event_name="scan_success", museum_id="louvre", artwork_id="fake-work")).status_code, 422)
        with self.Session() as db:
            self.assertEqual(db.query(ProductEvent).count(), 0)

    def test_authenticated_user_is_derived_and_identity_linked(self):
        user = User(id=uuid.UUID("30000000-0000-4000-8000-000000000001"), email="test@example.com")
        self.app.dependency_overrides[get_optional_current_user] = lambda: user
        response = self.client.post("/v1/events", json=event_payload())
        self.assertEqual(response.status_code, 200)
        with self.Session() as db:
            row = db.query(ProductEvent).one()
            link = db.get(AnalyticsIdentityLink, event_payload()["anonymous_id"])
            self.assertEqual(row.user_id, str(user.id))
            self.assertEqual(link.user_id, str(user.id))

    def test_duplicate_event_id_is_idempotent(self):
        payload = event_payload()
        self.assertTrue(self.client.post("/v1/events", json=payload).json()["stored"])
        duplicate = self.client.post("/v1/events", json=payload).json()
        self.assertFalse(duplicate["stored"])
        self.assertTrue(duplicate["duplicate"])

    def test_rate_limit_is_enforced(self):
        admin.EVENT_RATE_LIMIT_PER_MINUTE = 2
        self.assertEqual(self.client.post("/v1/events", json=event_payload()).status_code, 200)
        self.assertEqual(self.client.post("/v1/events", json=event_payload()).status_code, 200)
        self.assertEqual(self.client.post("/v1/events", json=event_payload()).status_code, 429)


class AnalyticsCorrectnessTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_attempt(self, db, attempt_id, identity, when, outcome, session=None, internal=False, user=None):
        db.add(RecognitionAttempt(
            recognition_attempt_id=attempt_id,
            anonymous_id=identity,
            user_id=user,
            session_id=session,
            institution_id="louvre",
            completed_at=when,
            terminal_outcome=outcome,
            internal_test=internal,
        ))

    def test_one_attempt_one_outcome_companion_events_do_not_double_count(self):
        now = datetime.now(timezone.utc)
        identity = "40000000-0000-4000-8000-000000000001"
        with self.Session() as db:
            self.add_attempt(db, "a1", identity, now, "success")
            for name in ("recognition_completed", "scan_success", "catalog_match"):
                db.add(ProductEvent(event_id=str(uuid.uuid4()), event_name=name, occurred_at=now, schema_version=2, business_eligible=True, internal_test=False, anonymous_id=identity, recognition_attempt_id="a1"))
            self.add_attempt(db, "a2", identity, now, "no_match")
            db.commit()
            metrics = admin._recognition_metrics(db, now - timedelta(minutes=1), now + timedelta(minutes=1))
            self.assertEqual(metrics["attempts"], 2)
            self.assertEqual(metrics["successful"], 1)
            self.assertEqual(metrics["failed"], 1)

    def test_activation_identity_link_sessions_returning_and_retention(self):
        now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
        anon = "50000000-0000-4000-8000-000000000001"
        user = "60000000-0000-4000-8000-000000000001"
        with self.Session() as db:
            db.add(AnalyticsIdentityLink(anonymous_id=anon, user_id=user))
            self.add_attempt(db, "d0", anon, now - timedelta(days=30), "success", "70000000-0000-4000-8000-000000000001")
            self.add_attempt(db, "d1", anon, now - timedelta(days=29), "no_match", "70000000-0000-4000-8000-000000000002")
            self.add_attempt(db, "d7", anon, now - timedelta(days=23), "success", "70000000-0000-4000-8000-000000000003", user=user)
            self.add_attempt(db, "d30", anon, now, "success", "70000000-0000-4000-8000-000000000004", user=user)
            self.add_attempt(db, "qa", "80000000-0000-4000-8000-000000000001", now, "success", internal=True)
            db.commit()
            self.assertEqual(admin._activated_identity_count(db, now - timedelta(days=31), now + timedelta(seconds=1)), 1)
            self.assertEqual(admin._returning_user_count(db, now - timedelta(days=1), now + timedelta(seconds=1)), 1)
            retention = admin._retention(db)
            self.assertEqual(retention["d1"], 100.0)
            self.assertEqual(retention["d7"], 100.0)
            self.assertEqual(retention["d30"], 100.0)
            users = admin._basic_user_metrics(db, now - timedelta(days=31), now + timedelta(seconds=1), None, None)
            self.assertEqual(users["active_users"]["value"], 1)
            self.assertEqual(users["sessions"], 4)

    def test_legacy_events_are_not_promoted_to_business_metrics(self):
        now = datetime.now(timezone.utc)
        with self.Session() as db:
            db.add(ProductEvent(
                event_id=str(uuid.uuid4()), event_name="scan_success", occurred_at=now,
                anonymous_id="51000000-0000-4000-8000-000000000001",
                trust_level="LEGACY_UNVERIFIED", business_eligible=None, internal_test=None,
            ))
            db.commit()
            users = admin._basic_user_metrics(db, now - timedelta(minutes=1), now + timedelta(minutes=1), None, None)
            self.assertEqual(users["active_users"]["value"], 0)
            self.assertEqual(users["activated_users"], 0)


class RecognitionAttemptEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            db.add(Country(code="FR", name="France"))
            db.add(Museum(id="louvre", name="Louvre", country_code="FR", active=True))
            db.add(Museum(id="configured-ai-guide", name="Configured AI Guide", country_code="FR", active=True, experience_level="AI_GUIDE"))
            db.add(InstitutionProfile(institution_id="louvre", candidate_universe="INSTITUTION_ARTWORKS", recognition_policy="ASSET_VERIFY"))
            db.add(InstitutionProfile(institution_id="configured-ai-guide", candidate_universe="NONE", recognition_policy="UNCATALOGED_ONLY"))
            db.add(Artwork(id="known-work", museum_id="louvre", title_original="Known"))
            db.commit()

        def override_db():
            with self.Session() as db:
                yield db

        main.app.dependency_overrides[main.get_db] = override_db
        main.app.dependency_overrides[get_optional_current_user] = lambda: None
        self.old_key = main.OPENAI_API_KEY
        self.old_recognize = main.recognize_with_vision
        main.OPENAI_API_KEY = "test-key"
        self.calls = 0

        def fake_recognition(*_args, **_kwargs):
            self.calls += 1
            return {"artwork_id": "known-work", "confidence": 0.99, "alternatives": [], "recognition_mode": "VISION_READY"}

        main.recognize_with_vision = fake_recognition
        self.client = TestClient(main.app)

    def tearDown(self):
        main.OPENAI_API_KEY = self.old_key
        main.recognize_with_vision = self.old_recognize
        main.app.dependency_overrides.clear()
        self.engine.dispose()

    def test_attempt_id_propagates_and_retry_is_idempotent(self):
        attempt_id = "90000000-0000-4000-8000-000000000001"
        payload = {
            "image_base64": "AA==",
            "museum_id": "louvre",
            "locale": "en",
            "recognition_attempt_id": attempt_id,
            "anonymous_id": "90000000-0000-4000-8000-000000000002",
            "session_id": "90000000-0000-4000-8000-000000000003",
        }
        first = self.client.post("/v1/recognize", json=payload)
        second = self.client.post("/v1/recognize", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["recognition_attempt_id"], attempt_id)
        self.assertEqual(second.json()["recognition_attempt_id"], attempt_id)
        self.assertEqual(self.calls, 1)
        with self.Session() as db:
            rows = db.query(RecognitionAttempt).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].terminal_outcome, "success")
            self.assertEqual(rows[0].engine_outcome, "CATALOG_CANDIDATE_MATCHED")
            self.assertEqual(rows[0].visitor_resolution, "AUTO_ACCEPTED")
            self.assertEqual(rows[0].artwork_id, "known-work")

    def test_event_body_over_limit_is_rejected_before_ingestion(self):
        response = self.client.post(
            "/v1/events",
            content=b'{"padding":"' + (b"x" * (admin.EVENT_BODY_MAX_BYTES + 1)) + b'"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 413)

    def test_confirmation_required_is_engine_success_but_distinct_visitor_resolution(self):
        main.recognize_with_vision = lambda *_args, **_kwargs: {
            "artwork_id": "known-work", "confidence": 0.85,
            "alternatives": [], "recognition_mode": "VISION_READY",
        }
        attempt_id = "91000000-0000-4000-8000-000000000001"
        response = self.client.post("/v1/recognize", json={
            "image_base64": "AA==", "museum_id": "louvre", "locale": "en",
            "recognition_attempt_id": attempt_id,
            "anonymous_id": "91000000-0000-4000-8000-000000000002",
            "session_id": "91000000-0000-4000-8000-000000000003",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "needs_confirmation")
        with self.Session() as db:
            row = db.get(RecognitionAttempt, attempt_id)
            self.assertEqual(row.terminal_outcome, "success")
            self.assertEqual(row.engine_outcome, "CATALOG_CANDIDATE_MATCHED")
            self.assertEqual(row.visitor_resolution, "CONFIRMATION_REQUIRED")

    def test_configured_institution_keeps_truthful_uncataloged_ai_fallback(self):
        main.recognize_with_vision = lambda *_args, **_kwargs: {
            "artwork_id": None, "confidence": 0.78, "alternatives": [],
            "recognized_but_not_cataloged": {"artist": "Unknown Artist", "title": "Uncataloged Work"},
            "recognition_mode": "AI_UNCATALOGED",
        }
        attempt_id = "92000000-0000-4000-8000-000000000001"
        anonymous_id = "92000000-0000-4000-8000-000000000002"
        session_id = "92000000-0000-4000-8000-000000000003"
        response = self.client.post("/v1/recognize", json={
            "image_base64": "AA==", "museum_id": "configured-ai-guide", "locale": "en",
            "recognition_attempt_id": attempt_id, "anonymous_id": anonymous_id, "session_id": session_id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "no_match")
        self.assertEqual(response.json()["recognized_but_not_cataloged"]["title"], "Uncataloged Work")
        with self.Session() as db:
            row = db.get(RecognitionAttempt, attempt_id)
            self.assertEqual(row.terminal_outcome, "uncataloged_result")
            self.assertEqual(row.engine_outcome, "UNCATALOGED_IDENTIFIED")
            self.assertEqual(row.visitor_resolution, "GENERATED_RESULT")
            self.assertEqual(row.institution_id, "configured-ai-guide")
            self.assertEqual(row.anonymous_id, anonymous_id)
            self.assertEqual(row.session_id, session_id)
            sighting = db.query(UncatalogedSighting).filter(UncatalogedSighting.museum_id == "configured-ai-guide").one()
            self.assertEqual(sighting.count, 1)


if __name__ == "__main__":
    unittest.main()
