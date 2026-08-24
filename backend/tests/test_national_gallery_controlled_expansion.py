import json
import unittest
from pathlib import Path

from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend/data/onboarding/national_gallery_london"


class NationalGalleryControlledExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection = json.loads((DATA / "controlled_catalog_500_v1.json").read_text(encoding="utf-8"))
        cls.readiness = json.loads((DATA / "controlled_catalog_500_recognition_readiness_v1.json").read_text(encoding="utf-8"))
        cls.baseline = list(NationalGalleryLondonAdapter(DATA / "pre_eminent_review_snapshot_2026-08-23.json").records())

    def test_selection_preserves_170_and_has_exactly_500_unique_records(self):
        rows = self.selection["records"]
        selected = {row["provider_record_id"] for row in rows}
        baseline = {row.provider_record_id for row in self.baseline}
        self.assertEqual(len(rows), 500)
        self.assertEqual(len(selected), 500)
        self.assertTrue(baseline.issubset(selected))
        self.assertEqual(sum(not row["baseline_170"] for row in rows), 330)

    def test_selection_has_intended_media_and_metadata_mix(self):
        summary = self.selection["summary"]
        self.assertEqual(summary["new_with_image_media"], 330)
        self.assertEqual(summary["new_metadata_only"], 0)
        self.assertGreaterEqual(summary["unique_artists"], 300)
        self.assertGreaterEqual(len(summary["visual_proxies"]), 5)

    def test_adapter_filter_is_exact_and_deterministic(self):
        selected = {row["provider_record_id"] for row in self.selection["records"]}
        adapter = NationalGalleryLondonAdapter(DATA / "source_snapshot_2026-08-23.json", provider_record_ids=selected)
        first = [row.provider_record_id for row in adapter.records()]
        second = [row.provider_record_id for row in adapter.records()]
        self.assertEqual(first, second)
        self.assertEqual(set(first), selected)
        self.assertEqual(len(first), 500)

    def test_readiness_is_complete_without_fabricated_assets(self):
        summary = self.readiness["summary"]
        self.assertEqual(summary, {"total": 500, "vision_plus_asset": 500, "vision_ready": 0, "not_ready": 0})
        self.assertEqual(len(self.readiness["records"]), 500)
        self.assertEqual({row["provider_record_id"] for row in self.readiness["records"]}, {row["provider_record_id"] for row in self.selection["records"]})


if __name__ == "__main__":
    unittest.main()
