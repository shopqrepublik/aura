import json
import unittest
from unittest.mock import patch
from pathlib import Path

from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
from backend.scripts.national_gallery_controlled_preview import apply_in_bounded_batches


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend/data/onboarding/national_gallery_london"


class NationalGalleryControlledExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection = json.loads((DATA / "controlled_catalog_500_v1.json").read_text(encoding="utf-8"))
        cls.readiness = json.loads((DATA / "controlled_catalog_500_recognition_readiness_v1.json").read_text(encoding="utf-8"))
        cls.baseline = list(NationalGalleryLondonAdapter(DATA / "pre_eminent_review_snapshot_2026-08-23.json").records())
        cls.selection_1000 = json.loads((DATA / "controlled_catalog_1000_v1.json").read_text(encoding="utf-8"))
        cls.readiness_1000 = json.loads((DATA / "controlled_catalog_1000_recognition_readiness_v1.json").read_text(encoding="utf-8"))
        cls.selection_2000 = json.loads((DATA / "controlled_catalog_2000_v1.json").read_text(encoding="utf-8"))
        cls.readiness_2000 = json.loads((DATA / "controlled_catalog_2000_recognition_readiness_v1.json").read_text(encoding="utf-8"))

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

    def test_1000_selection_preserves_every_controlled_500_identity(self):
        old = {row["provider_record_id"] for row in self.selection["records"]}
        new_rows = self.selection_1000["records"]
        new = {row["provider_record_id"] for row in new_rows}
        self.assertEqual(len(new_rows), 1000)
        self.assertEqual(len(new), 1000)
        self.assertTrue(old.issubset(new))
        self.assertEqual(sum(not row["prior_controlled"] for row in new_rows), 500)
        self.assertGreaterEqual(self.selection_1000["summary"]["unique_artists"], 600)

    def test_1000_readiness_is_exact(self):
        self.assertEqual(self.readiness_1000["summary"], {
            "total": 1000, "vision_plus_asset": 1000,
            "vision_ready": 0, "not_ready": 0,
        })
        self.assertEqual(
            {row["provider_record_id"] for row in self.readiness_1000["records"]},
            {row["provider_record_id"] for row in self.selection_1000["records"]},
        )

    def test_2000_selection_preserves_every_controlled_1000_identity(self):
        old = {row["provider_record_id"] for row in self.selection_1000["records"]}
        rows = self.selection_2000["records"]
        selected = {row["provider_record_id"] for row in rows}
        self.assertEqual(len(rows), 2000)
        self.assertEqual(len(selected), 2000)
        self.assertTrue(old.issubset(selected))
        self.assertEqual(sum(not row["prior_controlled"] for row in rows), 1000)
        self.assertEqual(self.selection_2000["summary"]["new_with_image_media"], 1000)
        self.assertEqual(self.selection_2000["summary"]["new_metadata_only"], 0)

    def test_2000_readiness_is_exact(self):
        self.assertEqual(self.readiness_2000["summary"], {
            "total": 2000, "vision_plus_asset": 2000,
            "vision_ready": 0, "not_ready": 0,
        })
        self.assertEqual(
            {row["provider_record_id"] for row in self.readiness_2000["records"]},
            {row["provider_record_id"] for row in self.selection_2000["records"]},
        )

    def test_controlled_apply_is_bounded_before_activation(self):
        class FakePlan:
            summary = {"records_inspected": 100, "new_objects": 100}
        with patch("backend.scripts.national_gallery_controlled_preview.selection", return_value=(list(map(str, range(1000))), set())), patch(
            "backend.scripts.national_gallery_controlled_preview.selected_adapter", return_value=object()
        ) as adapter, patch(
            "backend.scripts.national_gallery_controlled_preview.build_plan", return_value=FakePlan()
        ), patch(
            "backend.scripts.national_gallery_controlled_preview.apply_plan", side_effect=[f"run-{i}" for i in range(10)]
        ) as apply:
            class DB:
                def expunge_all(self): pass
            result = apply_in_bounded_batches(DB(), operator="test", batch_size=100)
        self.assertEqual(result["batches"], 10)
        self.assertEqual(result["summary"]["records_inspected"], 1000)
        self.assertEqual(adapter.call_count, 10)
        self.assertEqual(apply.call_count, 10)

    def test_single_batch_operator_mode_is_retryable(self):
        class FakePlan:
            summary = {"records_inspected": 100}
        with patch("backend.scripts.national_gallery_controlled_preview.selection", return_value=(list(map(str, range(1000))), set())), patch(
            "backend.scripts.national_gallery_controlled_preview.selected_adapter", return_value=object()
        ) as adapter, patch(
            "backend.scripts.national_gallery_controlled_preview.build_plan", return_value=FakePlan()
        ), patch(
            "backend.scripts.national_gallery_controlled_preview.apply_plan", return_value="run-one"
        ) as apply:
            class DB:
                def expunge_all(self): pass
            result = apply_in_bounded_batches(DB(), operator="test", batch_index=7)
        self.assertEqual(result["batches"], 1)
        self.assertEqual(result["summary"]["records_inspected"], 100)
        self.assertEqual(adapter.call_count, 1)
        self.assertEqual(apply.call_count, 1)


if __name__ == "__main__":
    unittest.main()
