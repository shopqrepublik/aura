"""Offline, non-mutating probe for cheap reference-image candidate recall.

This deliberately does not call OpenAI.  It measures whether compact,
deterministic image descriptors can complement metadata retrieval before the
bounded expensive verification stage.  Results are diagnostic only.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]


def descriptor(path: Path) -> tuple[float, ...]:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        # Synthetic visitor variants and real phone framing commonly add a
        # nearly uniform wall around the work.  Remove only a demonstrably
        # uniform border; never guess a crop on ordinary artwork pixels.
        probe = image.resize((96, 96), Image.Resampling.BILINEAR)
        corners = [probe.getpixel(point) for point in ((0, 0), (95, 0), (0, 95), (95, 95))]
        spread = max(max(values) - min(values) for values in zip(*corners))
        if spread < 18:
            background = tuple(sum(values) / 4 for values in zip(*corners))
            mask = Image.new("1", probe.size)
            mask.putdata([
                sum(abs(pixel[channel] - background[channel]) for channel in range(3)) > 42
                for pixel in getattr(probe, "get_flattened_data", probe.getdata)()
            ])
            box = mask.getbbox()
            if box:
                coverage = ((box[2] - box[0]) * (box[3] - box[1])) / (96 * 96)
                if 0.25 <= coverage <= 0.90:
                    scale_x, scale_y = image.width / 96, image.height / 96
                    image = image.crop(tuple(round(value * (scale_x if index % 2 == 0 else scale_y)) for index, value in enumerate(box)))
        # Preserve the whole composition.  The visitor-like corpus contains
        # realistic border/wall transformations, so crop-only matching would
        # flatter near-source tests and hide that failure mode.
        image.thumbnail((48, 48), Image.Resampling.LANCZOS)
        image_pixels = list(getattr(image, "get_flattened_data", image.getdata)())
        canvas = Image.new("RGB", (48, 48), tuple(sum(c) // len(c) for c in zip(*image_pixels)))
        canvas.paste(image, ((48 - image.width) // 2, (48 - image.height) // 2))
        low = canvas.resize((12, 12), Image.Resampling.LANCZOS)
        pixels = list(getattr(low, "get_flattened_data", low.getdata)())
        means = [sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3)]
        scale = max(24.0, math.sqrt(sum((value - means[channel]) ** 2 for pixel in pixels for channel, value in enumerate(pixel)) / (len(pixels) * 3)))
        spatial = [(value - means[channel]) / scale for pixel in pixels for channel, value in enumerate(pixel)]
        hist = []
        for channel in range(3):
            counts = [0] * 8
            for pixel in pixels:
                counts[min(7, pixel[channel] // 32)] += 1
            hist.extend(value / len(pixels) for value in counts)
        return tuple(spatial + hist)


def distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right)) / len(left)


def load_records(manifests: list[Path]) -> dict[str, dict]:
    records = {}
    for manifest in manifests:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        for row in payload["records"]:
            if row.get("status") == "READY":
                records[str(row["provider_record_id"])] = row
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--sample-name", required=True)
    parser.add_argument("--variant", default="visitor_like")
    args = parser.parse_args()

    records = load_records([Path(value) for value in args.manifest])
    selected = {
        str(row["provider_record_id"])
        for row in json.loads(Path(args.selection).read_text(encoding="utf-8"))["records"]
    }
    sample_ids = json.loads(Path(args.samples).read_text(encoding="utf-8"))["samples"][args.sample_name]
    references = {
        provider_id: descriptor(ROOT / row["files"]["reference"]["path"])
        for provider_id, row in records.items()
        if provider_id in selected
    }
    ranks = []
    diagnostics = []
    for provider_id in sample_ids:
        row = records[provider_id]
        query = descriptor(ROOT / row["files"][args.variant]["path"])
        distances = {candidate: distance(query, reference) for candidate, reference in references.items()}
        ordered = sorted(references, key=distances.get)
        ranks.append(ordered.index(provider_id) + 1)
        diagnostics.append({
            "provider_record_id": provider_id,
            "rank": ranks[-1],
            "best_distance": round(distances[ordered[0]], 6),
            "second_distance": round(distances[ordered[1]], 6),
            "expected_distance": round(distances[provider_id], 6),
        })
    summary = {
        "cases": len(ranks),
        "recall_at_1": sum(rank <= 1 for rank in ranks),
        "recall_at_3": sum(rank <= 3 for rank in ranks),
        "recall_at_5": sum(rank <= 5 for rank in ranks),
        "recall_at_10": sum(rank <= 10 for rank in ranks),
        "recall_at_20": sum(rank <= 20 for rank in ranks),
        "median_rank": sorted(ranks)[len(ranks) // 2],
        "ranks": ranks,
        "diagnostics": diagnostics,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
