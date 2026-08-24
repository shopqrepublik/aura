"""Select a deterministic, diverse National Gallery controlled catalog.

The selector preserves every member of the controlled 170 baseline and adds a
stratified set from the frozen full official snapshot. It writes identifiers
and selection evidence only; it never mutates a database or activates a
catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    from backend.app.adapters.national_gallery_london import NationalGalleryLondonAdapter
except ModuleNotFoundError:
    from app.adapters.national_gallery_london import NationalGalleryLondonAdapter

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2] if (SCRIPT.parents[2] / "backend").exists() else SCRIPT.parents[1]
DATA = (ROOT / "backend" if (ROOT / "backend").exists() else ROOT) / "data/onboarding/national_gallery_london"
BASELINE = DATA / "pre_eminent_review_snapshot_2026-08-23.json"
FULL = DATA / "source_snapshot_2026-08-23.json"
DEFAULT_OUT = DATA / "controlled_catalog_500_v1.json"
DEFAULT_SAMPLES_OUT = DATA / "controlled_catalog_500_benchmark_samples_v1.json"
DEFAULT_EXCLUSIONS = DATA / "media_technical_exclusions_v1.json"


def period(value: str | None) -> str:
    match = re.search(r"(1[0-9]{3}|20[0-9]{2})", value or "")
    if not match:
        return "unknown"
    year = int(match.group(1))
    return f"{(year // 50) * 50}-{(year // 50) * 50 + 49}"


def visual_proxy(title: str, object_type: str | None) -> str:
    text = f"{title} {object_type or ''}".lower()
    groups = {
        "portrait": ("portrait", "head", "woman", "man", "girl", "boy"),
        "landscape": ("landscape", "river", "view", "sea", "mountain", "field"),
        "religious": ("virgin", "christ", "saint", "adoration", "crucifix", "madonna"),
        "multi_figure": ("family", "feast", "battle", "crowd", "disciples", "marriage"),
        "still_life": ("still life", "flowers", "fruit"),
    }
    return next((name for name, words in groups.items() if any(word in text for word in words)), "other")


def stable_rank(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default=str(BASELINE)); parser.add_argument("--full", default=str(FULL))
    parser.add_argument("--out", default=str(DEFAULT_OUT)); parser.add_argument("--target", type=int, default=500)
    parser.add_argument("--samples-out", default=str(DEFAULT_SAMPLES_OUT))
    parser.add_argument("--metadata-only-additions", type=int, default=0)
    parser.add_argument("--technical-exclusions", default=str(DEFAULT_EXCLUSIONS))
    parser.add_argument("--preserve-selection", help="Preserve every provider ID from a prior controlled selection")
    parser.add_argument("--prior-samples", help="Prior benchmark sample manifest to preserve for regression")
    args = parser.parse_args()

    baseline = list(NationalGalleryLondonAdapter(args.baseline).records())
    full = list(NationalGalleryLondonAdapter(args.full).records())
    baseline_ids = {row.provider_record_id for row in baseline}
    full_by_id = {row.provider_record_id: row for row in full}
    preserved_ids = baseline_ids
    if args.preserve_selection:
        preserved_payload = json.loads(Path(args.preserve_selection).read_text(encoding="utf-8"))
        preserved_ids = {str(row["provider_record_id"]) for row in preserved_payload["records"]}
        missing = preserved_ids - set(full_by_id)
        if missing:
            raise SystemExit(f"preserved IDs missing from source snapshot: {sorted(missing)[:5]}")
    preserved = [full_by_id[row.provider_record_id] for row in baseline]
    preserved.extend(sorted((full_by_id[value] for value in preserved_ids - baseline_ids), key=lambda row: stable_rank("preserved", row.provider_record_id)))
    available = [row for row in full if row.provider_record_id not in preserved_ids]
    additions_needed = args.target - len(preserved)
    if additions_needed <= 0:
        raise SystemExit("target must exceed baseline")

    exclusions_path = Path(args.technical_exclusions)
    exclusions = {str(row["provider_record_id"]) for row in json.loads(exclusions_path.read_text(encoding="utf-8"))["records"]} if exclusions_path.exists() else set()
    with_media = [row for row in available if any(media.media_type == "IMAGE" for media in row.media) and row.provider_record_id not in exclusions]
    metadata_only = [row for row in available if not any(media.media_type == "IMAGE" for media in row.media)]
    media_target = additions_needed - args.metadata_only_additions

    def pick(rows, count, label):
        # Greedy coverage: reward under-represented artists, periods and visual
        # proxies. Stable hashes resolve ties and make the manifest reproducible.
        chosen = []
        artist_counts = Counter(row.creator_display or "Unknown" for row in preserved)
        period_counts = Counter(period(row.date_display) for row in preserved)
        proxy_counts = Counter(visual_proxy(row.title_original, row.object_type) for row in preserved)
        remaining = list(rows)
        while remaining and len(chosen) < count:
            def key(row):
                artist = row.creator_display or "Unknown"
                bucket = period(row.date_display)
                proxy = visual_proxy(row.title_original, row.object_type)
                # Lower coverage wins. Keep a controlled share of repeated
                # artists because those provide valuable confusion families.
                return (artist_counts[artist] * 3 + period_counts[bucket] + proxy_counts[proxy], stable_rank(label, row.provider_record_id))
            row = min(remaining, key=key); remaining.remove(row); chosen.append(row)
            artist_counts[row.creator_display or "Unknown"] += 1
            period_counts[period(row.date_display)] += 1
            proxy_counts[visual_proxy(row.title_original, row.object_type)] += 1
        if len(chosen) != count:
            raise SystemExit(f"not enough {label} candidates: requested {count}, found {len(chosen)}")
        return chosen

    additions = pick(with_media, media_target, "media") + pick(metadata_only, args.metadata_only_additions, "metadata")
    selected = preserved + additions
    selected_ids = [row.provider_record_id for row in selected]
    if len(selected_ids) != args.target or len(set(selected_ids)) != args.target:
        raise SystemExit("selection cardinality/uniqueness invariant failed")

    summary = {
        "target": args.target, "baseline_preserved": len(baseline), "prior_controlled_preserved": len(preserved), "additions": len(additions),
        "new_with_image_media": sum(any(media.media_type == "IMAGE" for media in row.media) for row in additions),
        "new_metadata_only": sum(not any(media.media_type == "IMAGE" for media in row.media) for row in additions),
        "unique_artists": len({row.creator_display for row in selected if row.creator_display}),
        "periods": dict(sorted(Counter(period(row.date_display) for row in selected).items())),
        "visual_proxies": dict(sorted(Counter(visual_proxy(row.title_original, row.object_type) for row in selected).items())),
    }
    payload = {
        "schema_version": 1, "catalog_version": f"ng-controlled-{args.target}-v1",
        "source_snapshot": NationalGalleryLondonAdapter(args.full).source_snapshot(),
        "baseline_snapshot": NationalGalleryLondonAdapter(args.baseline).source_snapshot(),
        "selection_policy": f"preserve controlled {len(preserved)} (including original 170); greedy artist/50-year-period/visual-proxy coverage; activate only technically prepared ASSET_VERIFY candidates after safety regression",
        "technical_exclusions": sorted(exclusions),
        "summary": summary,
        "records": [{
            "position": index, "provider_record_id": row.provider_record_id,
            "baseline_170": row.provider_record_id in baseline_ids,
            "prior_controlled": row.provider_record_id in preserved_ids,
            "readiness": "VISION_PLUS_ASSET_CANDIDATE" if any(media.media_type == "IMAGE" for media in row.media) else "VISION_READY",
            "artist": row.creator_display, "title": row.title_original, "date": row.date_display,
            "period": period(row.date_display), "visual_proxy": visual_proxy(row.title_original, row.object_type),
        } for index, row in enumerate(selected)],
    }
    out = Path(args.out); out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected_artist_counts = Counter(row.creator_display or "Unknown" for row in selected)
    confusable = sorted(
        [row for row in additions if row.creator_display and selected_artist_counts[row.creator_display] >= 2],
        key=lambda row: stable_rank("confusion", row.creator_display or "", row.provider_record_id),
    )[:30]
    new_sample = list(confusable)
    for row in sorted(additions, key=lambda row: stable_rank("new-sample", period(row.date_display), visual_proxy(row.title_original, row.object_type), row.provider_record_id)):
        if row not in new_sample:
            new_sample.append(row)
        if len(new_sample) == 60:
            break
    outside = [row for row in full if row.provider_record_id not in set(selected_ids) and any(media.media_type == "IMAGE" for media in row.media)]
    outside_sample = sorted(outside, key=lambda row: stable_rank("outside", period(row.date_display), visual_proxy(row.title_original, row.object_type), row.provider_record_id))[:20]
    prior_regression = []
    if args.prior_samples:
        prior_samples = json.loads(Path(args.prior_samples).read_text(encoding="utf-8"))["samples"]
        prior_regression = list(prior_samples.get("new_work_60") or prior_samples.get("works_171_500") or [])
    sample_payload = {
        "schema_version": 1, "catalog_version": f"ng-controlled-{args.target}-v1",
        "samples": {
            "original_170": [row.provider_record_id for row in baseline],
            "works_171_500": prior_regression,
            "new_work_60": [row.provider_record_id for row in new_sample],
            "confusion_30": [row.provider_record_id for row in confusable],
            "out_of_catalog_20": [row.provider_record_id for row in outside_sample],
        },
        # `records` makes the out-of-catalog subset directly consumable by the
        # existing corpus preparer without changing its source-adapter contract.
        "records": [{"provider_record_id": row.provider_record_id} for row in outside_sample],
    }
    samples_out = Path(args.samples_out); samples_out.write_text(json.dumps(sample_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "output": str(out), "samples_output": str(samples_out), "selection_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
