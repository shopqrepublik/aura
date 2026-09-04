import base64
import io
import json
import unittest
from pathlib import Path

from PIL import Image

from backend.app.visual_retrieval import (
    DESCRIPTOR_VERSION,
    descriptor_from_image,
    rank_visual_candidates,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend/data/onboarding/national_gallery_london"


def encoded(color, accent=None):
    image = Image.new("RGB", (96, 72), color)
    if accent:
        for x in range(20, 70):
            for y in range(15, 55):
                image.putpixel((x, y), accent)
    output = io.BytesIO(); image.save(output, "JPEG")
    return base64.b64encode(output.getvalue()).decode()


class VisualCandidateRetrievalTests(unittest.TestCase):
    def test_descriptor_manifest_has_exact_controlled_catalog_parity(self):
        selection = json.loads((DATA / "controlled_catalog_500_v1.json").read_text(encoding="utf-8"))
        descriptors = json.loads((DATA / "controlled_catalog_500_visual_descriptors_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(descriptors["descriptor_version"], DESCRIPTOR_VERSION)
        self.assertEqual(len(descriptors["records"]), 500)
        self.assertEqual(
            {row["provider_record_id"] for row in descriptors["records"]},
            {row["provider_record_id"] for row in selection["records"]},
        )

    def test_visual_retrieval_is_candidate_only_and_institution_scoped(self):
        red = encoded((180, 20, 20), (250, 220, 40))
        blue = encoded((20, 20, 180), (40, 220, 250))
        with Image.open(io.BytesIO(base64.b64decode(red))) as image:
            red_descriptor = descriptor_from_image(image)
        with Image.open(io.BytesIO(base64.b64decode(blue))) as image:
            blue_descriptor = descriptor_from_image(image)
        candidates = [
            {"id": "in-scope-red", "visual_descriptor": {"version": DESCRIPTOR_VERSION, "values": red_descriptor}},
            {"id": "in-scope-blue", "visual_descriptor": {"version": DESCRIPTOR_VERSION, "values": blue_descriptor}},
        ]
        ranked = rank_visual_candidates(red, candidates)
        self.assertEqual(ranked[0]["candidate"]["id"], "in-scope-red")
        self.assertNotIn("out-of-scope", {row["candidate"]["id"] for row in ranked})

    def test_stale_descriptor_versions_are_ignored(self):
        query = encoded((100, 80, 60))
        ranked = rank_visual_candidates(query, [{
            "id": "stale", "visual_descriptor": {"version": "old", "values": [0.0] * 456}
        }])
        self.assertEqual(ranked, [])

    def test_legacy_raw_vector_descriptor_records_are_retrievable(self):
        query = encoded((180, 20, 20), (250, 220, 40))
        with Image.open(io.BytesIO(base64.b64decode(query))) as image:
            descriptor = descriptor_from_image(image)
        ranked = rank_visual_candidates(query, [{"id": "legacy", "visual_descriptor": descriptor}])
        self.assertEqual(ranked[0]["candidate"]["id"], "legacy")

    def test_1000_descriptor_manifest_has_exact_selection_parity(self):
        selection = json.loads((DATA / "controlled_catalog_1000_v1.json").read_text(encoding="utf-8"))
        descriptors = json.loads((DATA / "controlled_catalog_1000_visual_descriptors_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(descriptors["descriptor_version"], DESCRIPTOR_VERSION)
        self.assertEqual(len(descriptors["records"]), 1000)
        self.assertEqual(
            {row["provider_record_id"] for row in descriptors["records"]},
            {row["provider_record_id"] for row in selection["records"]},
        )

    def test_2000_descriptor_manifest_has_exact_selection_parity(self):
        selection = json.loads((DATA / "controlled_catalog_2000_v1.json").read_text(encoding="utf-8"))
        descriptors = json.loads((DATA / "controlled_catalog_2000_visual_descriptors_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(descriptors["descriptor_version"], DESCRIPTOR_VERSION)
        self.assertEqual(len(descriptors["records"]), 2000)
        self.assertEqual(
            {row["provider_record_id"] for row in descriptors["records"]},
            {row["provider_record_id"] for row in selection["records"]},
        )


if __name__ == "__main__":
    unittest.main()
