import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import main


class ReferenceImageCacheTests(unittest.TestCase):
    def setUp(self):
        main._REFERENCE_MEMORY_CACHE.clear()
        self.artwork = {
            "id": "orsay_rf_1978_13",
            "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Pierre-Auguste%20Renoir%20019.jpg",
        }

    def test_memory_hit_reuses_reference_bytes_and_is_profiled(self):
        profile = main._new_latency_profile("cache-test")
        encoded = base64.b64encode(b"reference-jpeg").decode("ascii")
        key = main._reference_cache_key(self.artwork)
        main._store_reference_memory_cache(key, encoded)

        with patch.object(main, "_read_reference_thumbnail") as network_fetch:
            result = main._fetch_reference_image_b64(self.artwork, profile=profile)

        self.assertEqual(result, encoded)
        network_fetch.assert_not_called()
        self.assertEqual(profile["stages"][-1]["name"], "reference_image.cache_hit")
        self.assertEqual(profile["stages"][-1]["storage"], "memory")

    def test_filesystem_hit_populates_memory_and_source_change_invalidates_key(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(main, "REFERENCE_CACHE_DIR", directory):
            cache_path = Path(main._reference_cache_path(self.artwork))
            cache_path.write_bytes(b"reference-jpeg")
            profile = main._new_latency_profile("disk-test")

            first = main._fetch_reference_image_b64(self.artwork, allow_remote=False, profile=profile)
            cache_path.unlink()
            second = main._fetch_reference_image_b64(self.artwork, allow_remote=False, profile=profile)

            changed = {**self.artwork, "image_url": self.artwork["image_url"] + "?revision=2"}
            with self.assertRaisesRegex(RuntimeError, "reference_image_not_cached"):
                main._fetch_reference_image_b64(changed, allow_remote=False, profile=profile)

        self.assertEqual(first, second)
        hits = [stage for stage in profile["stages"] if stage["name"] == "reference_image.cache_hit"]
        self.assertEqual([stage["storage"] for stage in hits], ["filesystem", "memory"])
        self.assertTrue(any(stage["name"] == "reference_image.cache_miss" for stage in profile["stages"]))

    def test_memory_cache_is_lru_bounded(self):
        with patch.object(main, "REFERENCE_MEMORY_CACHE_MAX_ENTRIES", 2):
            main._store_reference_memory_cache("one", "1")
            main._store_reference_memory_cache("two", "2")
            main._store_reference_memory_cache("three", "3")

        self.assertEqual(list(main._REFERENCE_MEMORY_CACHE), ["two", "three"])


if __name__ == "__main__":
    unittest.main()
