import unittest
from unittest.mock import patch

from backend.app.catalog import InstitutionRuntimeConfig
from backend.app.main import recognize_with_vision


class RecognitionConfirmationSemanticsTests(unittest.TestCase):
    def test_asset_verifier_confirmation_cannot_become_auto_acceptance(self):
        candidate = {
            "id": "artwork:test", "museum_id": "test", "title": "Test Work",
            "artist": "Test Artist", "year": "1900", "image_url": "https://example.org/reference.jpg",
            "recognition_asset_id": "asset:test", "visual_descriptor": {"version": "elyio-lowfreq-rgb-v1", "values": [0.0]},
        }
        ranked = {"candidate": candidate, "score": 1.0, "signals": {}}
        config = InstitutionRuntimeConfig(
            institution_id="test", display_name="Test", visitor_catalog_version="test-v1",
            candidate_universe="ACTIVE_CATALOG", recognition_policy="ASSET_VERIFY",
            supported_modes=("normal",), max_candidates=5, confidence_auto=.92,
            confidence_review=.82, fuzzy_candidate_threshold=.55,
            prompt_context="Test institution", allow_recognition_asset_substitution=True,
        )
        with patch("backend.app.main.recognize_open", return_value={
            "recognized": True, "artist": "Test Artist", "title": "Test Work", "confidence": .99,
        }), patch("backend.app.main.rank_catalog_candidates", return_value=[ranked]), patch(
            "backend.app.main.rank_visual_candidates", return_value=[]
        ), patch("backend.app.main._reference_verification_allowed", return_value=True), patch(
            "backend.app.main.visual_verify_reference_candidates", return_value={
                "decision": "NEEDS_CONFIRMATION", "chosen_id": "artwork:test", "confidence": .99,
            }
        ):
            result = recognize_with_vision("aW1hZ2U=", "test", None, [candidate], institution_config=config)
        self.assertEqual(result["artwork_id"], "artwork:test")
        self.assertGreaterEqual(result["confidence"], config.confidence_review)
        self.assertLess(result["confidence"], config.confidence_auto)
        self.assertEqual(result["stage2_verifier"]["decision"], "NEEDS_CONFIRMATION")

    def test_same_artist_metadata_seed_conflict_requires_confirmation(self):
        chosen = {
            "id": "artwork:isaiah", "museum_id": "test", "title": "Isaiah", "artist": "Same Artist",
            "year": "1300", "image_url": "https://example.org/isaiah.jpg", "recognition_asset_id": "asset:isaiah",
            "visual_descriptor": {"version": "elyio-lowfreq-rgb-v1", "values": [0.0]},
        }
        competitor = {
            "id": "artwork:moses", "museum_id": "test", "title": "Moses", "artist": "Same Artist",
            "year": "1300", "image_url": "https://example.org/moses.jpg", "recognition_asset_id": "asset:moses",
            "visual_descriptor": {"version": "elyio-lowfreq-rgb-v1", "values": [0.1]},
        }
        ranked = [
            {"candidate": chosen, "score": .8, "signals": {}},
            {"candidate": competitor, "score": .4, "signals": {"visual_retrieval_rank": 1}},
        ]
        config = InstitutionRuntimeConfig(
            institution_id="test", display_name="Test", visitor_catalog_version="test-v1",
            candidate_universe="ACTIVE_CATALOG", recognition_policy="ASSET_VERIFY",
            supported_modes=("normal",), max_candidates=5, confidence_auto=.92,
            confidence_review=.82, fuzzy_candidate_threshold=.55,
            prompt_context="Test institution", allow_recognition_asset_substitution=True,
        )
        with patch("backend.app.main.recognize_open", return_value={
            "recognized": True, "artist": "Same Artist", "title": "Isaiah", "confidence": .99,
        }), patch("backend.app.main.rank_catalog_candidates", return_value=ranked), patch(
            "backend.app.main.rank_visual_candidates", return_value=[]
        ), patch("backend.app.main._reference_verification_allowed", return_value=True), patch(
            "backend.app.main.visual_verify_reference_candidates", return_value={
                "decision": "MATCH", "chosen_id": "artwork:isaiah", "confidence": .95,
            }
        ):
            result = recognize_with_vision("aW1hZ2U=", "test", None, [chosen, competitor], institution_config=config)
        self.assertEqual(result["artwork_id"], "artwork:isaiah")
        self.assertEqual(result["stage2_verifier"]["decision"], "NEEDS_CONFIRMATION")
        self.assertGreaterEqual(result["confidence"], config.confidence_review)
        self.assertLess(result["confidence"], config.confidence_auto)


if __name__ == "__main__":
    unittest.main()
