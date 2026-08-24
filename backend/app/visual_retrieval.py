"""Cheap, deterministic visual descriptors for bounded candidate retrieval.

This is not a recognition decision.  It only supplies institution-scoped
candidates to the existing high-precision verifier.  Descriptor versioning
prevents stale catalog assets from being compared silently.
"""
from __future__ import annotations

import base64
import io
import math
from typing import Iterable

from PIL import Image, ImageOps


DESCRIPTOR_VERSION = "elyio-lowfreq-rgb-v1"


def _pixels(image: Image.Image) -> list[tuple[int, int, int]]:
    flattened = getattr(image, "get_flattened_data", None)
    return list(flattened() if flattened else image.getdata())


def _content_image(source: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(source).convert("RGB")
    probe = image.resize((96, 96), Image.Resampling.BILINEAR)
    corners = [probe.getpixel(point) for point in ((0, 0), (95, 0), (0, 95), (95, 95))]
    spread = max(max(values) - min(values) for values in zip(*corners))
    if spread < 18:
        background = tuple(sum(values) / 4 for values in zip(*corners))
        pixels = _pixels(probe)
        mask = Image.new("1", probe.size)
        mask.putdata([
            sum(abs(pixel[channel] - background[channel]) for channel in range(3)) > 42
            for pixel in pixels
        ])
        box = mask.getbbox()
        if box:
            coverage = ((box[2] - box[0]) * (box[3] - box[1])) / (96 * 96)
            if 0.25 <= coverage <= 0.90:
                scale_x, scale_y = image.width / 96, image.height / 96
                image = image.crop(tuple(
                    round(value * (scale_x if index % 2 == 0 else scale_y))
                    for index, value in enumerate(box)
                ))
    return image


def descriptor_from_image(source: Image.Image) -> list[float]:
    image = _content_image(source)
    image.thumbnail((48, 48), Image.Resampling.LANCZOS)
    pixels = _pixels(image)
    background = tuple(sum(values) // len(values) for values in zip(*pixels))
    canvas = Image.new("RGB", (48, 48), background)
    canvas.paste(image, ((48 - image.width) // 2, (48 - image.height) // 2))
    low = canvas.resize((12, 12), Image.Resampling.LANCZOS)
    pixels = _pixels(low)
    means = [sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3)]
    scale = max(24.0, math.sqrt(sum(
        (value - means[channel]) ** 2
        for pixel in pixels
        for channel, value in enumerate(pixel)
    ) / (len(pixels) * 3)))
    spatial = [(value - means[channel]) / scale for pixel in pixels for channel, value in enumerate(pixel)]
    histogram: list[float] = []
    for channel in range(3):
        counts = [0] * 8
        for pixel in pixels:
            counts[min(7, pixel[channel] // 32)] += 1
        histogram.extend(value / len(pixels) for value in counts)
    return [round(value, 5) for value in spatial + histogram]


def descriptor_from_base64(image_base64: str) -> list[float]:
    with Image.open(io.BytesIO(base64.b64decode(image_base64))) as image:
        return descriptor_from_image(image)


def descriptor_distance(left: Iterable[float], right: Iterable[float]) -> float:
    left_values, right_values = list(left), list(right)
    if len(left_values) != len(right_values) or not left_values:
        return math.inf
    return sum((a - b) ** 2 for a, b in zip(left_values, right_values)) / len(left_values)


def rank_visual_candidates(image_base64: str, candidates: list[dict], limit: int = 5) -> list[dict]:
    query = descriptor_from_base64(image_base64)
    scored = []
    for candidate in candidates:
        payload = candidate.get("visual_descriptor") or {}
        if payload.get("version") != DESCRIPTOR_VERSION:
            continue
        distance = descriptor_distance(query, payload.get("values") or [])
        if math.isfinite(distance):
            scored.append((distance, candidate))
    scored.sort(key=lambda row: row[0])
    return [
        {"candidate": candidate, "distance": round(distance, 6), "visual_rank": index + 1}
        for index, (distance, candidate) in enumerate(scored[:limit])
    ]
