# National Gallery London Controlled 500 Recognition Benchmark

Date: 2026-08-24

Catalog: `ng-controlled-500-v1`

Status: CONTROLLED PREVIEW; public selector, public artwork access and SEO remain disabled.

## Selection and readiness

The deterministic selector preserves all 170 `pre_eminent_work_flag` baseline records and adds 330 records from the frozen 3,785-record official snapshot. It balances artist, 50-year period and title/object-type visual proxies rather than taking source order. The resulting 500 cover 356 named artists and portrait, landscape, religious, multi-figure, still-life and other proxy groups.

An initial mixed plan included 30 metadata-only additions. A 30-case VISION_READY safety diagnostic produced 6 confident incorrect attachments, so the plan was rejected without changing recognition code or thresholds. The active controlled selection instead uses 330 image-bearing additions with technically prepared references. Three provider derivatives returning bounded 403/404 failures were excluded and replaced deterministically. Final readiness is 500 `VISION_PLUS_ASSET`, 0 active metadata-only `VISION_READY`, 0 `NOT_READY`. Metadata-qualified records remain available for AI long-tail fallback outside the controlled catalog.

`backend/data/onboarding/national_gallery_london/controlled_catalog_500_v1.json` is the canonical selection. `controlled_catalog_500_recognition_readiness_v1.json` records readiness without committing generated image binaries. Corpus and result JSONL remain ignored under `exports/`.

## Benchmark method

All cases use deterministic visitor-like variants with recorded derivative lineage, not physical gallery photographs. The institution-scoped candidate universe is exactly 500. Recognition algorithm, thresholds (`auto=.92`, `review=.82`) and Value Engine were unchanged. The original-170 comparison uses the prior 170 visitor-like VISION_PLUS_ASSET result from `NATIONAL_GALLERY_BENCHMARK_2026-08-24.md`.

| Suite | Cases | Correct top-1 | Correct top-k | Confirmation | AI fallback | Unresolved | Incorrect catalog | Confident incorrect | p50 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Original 170, candidate universe 170 (before) | 170 | 119 | not recorded | 66 | 51 | 0 | 0 | 0 | 5.845s | 9.833s |
| Original 170, candidate universe 500 (after) | 170 | 124 | 133 | 71 | 46 | 1 | 0 | 0 | 7.745s | 14.614s |
| New-work representative sample | 60 | 13 | 24 | 9 | 47 | 0 | 0 | 0 | 7.841s | 11.748s |
| Confusion subset (within new sample) | 30 | 6 | 11 | 3 | 24 | 0 | 0 | 0 | not separately measured | not separately measured |
| Out-of-catalog National Gallery | 20 | n/a | n/a | 0 | 20 | 0 | 0 | 0 | 6.085s | 13.073s |

The expanded ASSET_VERIFY catalog preserves the primary safety gate: zero confident incorrect and zero incorrect catalog attachments across the final 250-case original/new/out-of-catalog suites. Original-170 recall did not regress. Latency did regress, especially p95, and new-work recall is low: most new cases safely fall back rather than attach canonical catalog identity.

## Decision

The 500-work controlled catalog is safe for controlled-preview use because it fails cautiously, but it is **not yet evidence-backed for expansion to 1,000**. Dominant blockers are weak new-work candidate discovery/top-1 recall, high fallback concentration, and increased tail latency. No threshold or algorithm change was made in this block.
