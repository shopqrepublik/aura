"""Prepare a reproducible, non-public National Gallery recognition corpus.

This is provider-specific acquisition/fixture tooling. It never writes the DB,
catalog membership, selector, SEO, or analytics. Outputs stay under ignored
``exports/`` and retain source/derivative checksums in a manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

try:
    from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
    from backend.app.ingestion import stable_id
except ModuleNotFoundError:
    from app.adapters.national_gallery_london import NationalGalleryLondonAdapter
    from app.ingestion import stable_id

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2] if (SCRIPT.parents[2] / "backend").exists() else SCRIPT.parents[1]
BACKEND_ROOT = ROOT / "backend" if (ROOT / "backend").exists() else ROOT
DEFAULT_SNAPSHOT = BACKEND_ROOT / "data/onboarding/national_gallery_london/pre_eminent_review_snapshot_2026-08-23.json"
DEFAULT_OUT = ROOT / "exports/national_gallery/recognition_corpus_170_v1"
UA = "ELYIO-National-Gallery-controlled-recognition/1.0"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as response:
                data = response.read(12 * 1024 * 1024 + 1)
            break
        except Exception as exc:
            last = exc
            if attempt == 2: raise
            time.sleep(1.5 * (attempt + 1))
    else:
        raise last or RuntimeError("provider fetch failed")
    if len(data) > 12 * 1024 * 1024:
        raise RuntimeError("provider derivative exceeded 12MB")
    return data


def jpeg(image: Image.Image, width: int = 1024, quality: int = 90) -> bytes:
    image = image.convert("RGB")
    if image.width > width:
        image.thumbnail((width, width * 2), Image.Resampling.LANCZOS)
    out = io.BytesIO(); image.save(out, "JPEG", quality=quality, optimize=True)
    return out.getvalue()


def visitor_variant(source: Image.Image, seed: str) -> Image.Image:
    rng = random.Random(seed)
    art = source.convert("RGB")
    art.thumbnail((780, 780), Image.Resampling.LANCZOS)
    wall = Image.new("RGB", (1024, 1024), (rng.randint(188, 225), rng.randint(184, 220), rng.randint(175, 210)))
    frame = Image.new("RGB", (art.width + 42, art.height + 42), (48, 38, 28))
    frame.paste(art, (21, 21))
    angle = rng.uniform(-5.5, 5.5)
    framed = frame.rotate(angle, Image.Resampling.BICUBIC, expand=True, fillcolor=wall.getpixel((0, 0)))
    x = max(0, (1024 - framed.width) // 2 + rng.randint(-90, 90)); y = max(0, (1024 - framed.height) // 2 + rng.randint(-70, 70))
    wall.paste(framed, (x, y))
    wall = ImageEnhance.Brightness(wall).enhance(rng.uniform(0.62, 1.02))
    wall = ImageEnhance.Contrast(wall).enhance(rng.uniform(0.82, 1.12))
    if rng.random() < .55:
        overlay = Image.new("RGBA", wall.size, (0, 0, 0, 0)); draw = ImageDraw.Draw(overlay)
        gx = rng.randint(300, 760); draw.ellipse((gx, 120, gx + 220, 820), fill=(255, 255, 245, 34))
        wall = Image.alpha_composite(wall.convert("RGBA"), overlay).convert("RGB")
    return wall.filter(ImageFilter.GaussianBlur(rng.uniform(0.15, 0.75)))


def partial_variant(source: Image.Image, seed: str) -> Image.Image:
    rng = random.Random(seed)
    image = source.convert("RGB")
    fraction = rng.uniform(.67, .82)
    w, h = int(image.width * fraction), int(image.height * fraction)
    left = rng.randint(0, max(0, image.width - w)); top = rng.randint(0, max(0, image.height - h))
    crop = image.crop((left, top, left + w, top + h)).resize((min(1024, image.width), min(1024, image.height)), Image.Resampling.LANCZOS)
    return ImageEnhance.Brightness(crop).enhance(rng.uniform(.72, 1.05))


def prepare_one(record, out: Path) -> dict:
    image_media_rows = [m for m in record.media if m.media_type == "IMAGE" and m.provider_asset_id]
    if not image_media_rows:
        return {"provider_record_id": record.provider_record_id, "status": "NO_IMAGE"}
    attempts = []
    for image_media in image_media_rows:
        pid = image_media.provider_asset_id
        source_url = f"https://data.ng.ac.uk/iiif/3/{pid}/full/max/0/default.jpg"
        try:
            raw = fetch(source_url); source = Image.open(io.BytesIO(raw)).convert("RGB")
            break
        except Exception as exc:
            attempts.append({"provider_asset_id": pid, "error": f"{type(exc).__name__}: {exc}"})
    else:
        return {"provider_record_id": record.provider_record_id, "status": "MEDIA_UNAVAILABLE", "attempts": attempts}
    artwork_id = stable_id("artwork", record.provider_id, record.provider_record_id)
    target = out / artwork_id.replace(":", "_"); target.mkdir(parents=True, exist_ok=True)
    files = {}
    variants = {
        "reference": jpeg(source, 768, 92),
        "pristine": jpeg(source, 1100, 91),
        "visitor_like": jpeg(visitor_variant(source, artwork_id), 1024, 86),
        "partial": jpeg(partial_variant(source, artwork_id), 1024, 87),
    }
    for name, data in variants.items():
        path = target / f"{name}.jpg"; path.write_bytes(data)
        files[name] = {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(data), "bytes": len(data)}
    return {
        "status": "READY", "artwork_id": artwork_id, "provider_record_id": record.provider_record_id,
        "accession_id": record.institution_record_id, "title": record.title_original,
        "artist": record.creator_display, "date": record.date_display, "object_type": record.object_type,
        "department": record.department, "room": record.room, "source_media_id": pid,
        "media_attempts_before_success": attempts,
        "source_relationship_key": image_media.source_relationship_key, "source_url": source_url,
        "source_sha256": sha256(raw), "source_bytes": len(raw), "files": files,
        "lineage": {"reference": "provider IIIF derivative", "pristine": "independent JPEG encoding of provider IIIF derivative", "visitor_like": "wall/frame/rotation/light/blur simulation", "partial": "crop/scale/brightness simulation"},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT)); parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--workers", type=int, default=6); parser.add_argument("--limit", type=int)
    parser.add_argument("--exclude-manifest", help="Skip provider record IDs already present in another corpus manifest")
    parser.add_argument("--require-image", action="store_true", help="Select only records declaring at least one image relationship")
    parser.add_argument("--selection-manifest", help="Restrict preparation to provider IDs in a controlled selection manifest")
    args = parser.parse_args(); out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    adapter = NationalGalleryLondonAdapter(args.snapshot); records = list(adapter.records())
    if args.selection_manifest:
        selection = json.loads(Path(args.selection_manifest).read_text(encoding="utf-8"))
        selected = {str(row["provider_record_id"]) for row in selection["records"]}
        records = [row for row in records if row.provider_record_id in selected]
    if args.exclude_manifest:
        prior = json.loads(Path(args.exclude_manifest).read_text(encoding="utf-8"))
        excluded = {row.get("provider_record_id") for row in prior.get("records", [])}
        records = [row for row in records if row.provider_record_id not in excluded]
    if args.require_image:
        records = [row for row in records if any(media.media_type == "IMAGE" for media in row.media)]
    records = records[:args.limit]
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(prepare_one, row, out): row.provider_record_id for row in records}
        for future in as_completed(futures):
            try: results.append(future.result())
            except Exception as exc: results.append({"provider_record_id": futures[future], "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
    results.sort(key=lambda row: row.get("provider_record_id", ""))
    manifest = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(), "source_snapshot": adapter.source_snapshot(), "selection": str(Path(args.selection_manifest).resolve()) if args.selection_manifest else "adapter_snapshot", "production_mutations": 0, "records": results}
    encoded = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    (out / "manifest.json").write_bytes(encoded)
    print(json.dumps({"records": len(results), "ready": sum(r["status"] == "READY" for r in results), "no_image": sum(r["status"] == "NO_IMAGE" for r in results), "errors": sum(r["status"] == "ERROR" for r in results), "manifest_sha256": sha256(encoded), "output": str(out)}, indent=2))


if __name__ == "__main__": main()
