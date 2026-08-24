# National Gallery Controlled 2,000 Benchmark — 2026-08-25

Status: CURRENT CONTROLLED PREVIEW. Public selector, public artwork API, SEO and sitemap activation remain off.

## Package

`ng-controlled-2000-v1-retrieval` preserves all 1,000 prior identities and adds 1,000 deterministic, non-source-order, image-backed selections. It contains 2,000 controlled memberships, 2,000 RecognitionAssets and 2,000 `elyio-lowfreq-rgb-v1` descriptors across 993 artists. The new-reference audit classified 941 as technically strong and 59 as low-resolution; three unavailable source derivatives were excluded and deterministically replaced. No duplicate checksums or automatically detectable contextual/wrong primaries remained.

The candidate funnel remains bounded: 2,000 institution candidates → cheap metadata top 20 and visual retrieval top 5 → at most five fused candidates → at most three reference images in one verifier call. Descriptors remain non-authoritative retrieval evidence.

## Frozen visitor-like results

| Cohort | Cases | Top-1 | Top-k | Confirmation | Fallback | Unresolved | Incorrect | Confident incorrect | p50 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Original 170 | 170 | 131 | 141 | 22* | 39 | 0 | 0 | 0 | 10.02 s | 15.08 s |
| Works 171–500 | 60 | 30 | 41 | 19* | 30 | 0 | 0 | 0 | 9.09 s | 17.02 s |
| Works 501–1,000, safety rerun | 60 | 24 | 37 | 15 | 36 | 0 | 0 | 0 | 8.84 s | 11.66 s |
| New works 1,001–2,000 | 60 | 27 | 42 | 16 | 33 | 0 | 0 | 0 | 9.77 s | 13.03 s |
| Outside controlled catalog | 20 | — | — | 0 | 20 | 0 | 0 | 0 | 7.97 s | 13.06 s |

Five blank/non-art hard negatives produced zero catalog attachments. The 20 outside-catalog works produced 20/20 AI fallback and zero forced attachments.

`*` The original-170 and 171–500 model calls completed before the final generic artist-conflict guard was added. Their confirmation counts are deterministic replays of the captured Stage-1 and verifier evidence through that guard (21 and 17 additional cautious resolutions respectively); artwork attachment, fallback and latency do not change. The 501–1,000 and new 1,001–2,000 cohorts were run through the final guard directly.

## Retrieval and failure evidence

For the new 60-work cohort, metadata recall@1/3/5/10/20 was 9/16/19/22/26; visual recall was 35/41/43/44/46; combined recall was 37/46/49/50/53.

The 33 new-cohort fallbacks were attributed deterministically from Stage-1 evidence, ranks, fused membership and verifier output: 17 visual-analysis insufficiencies, 7 retrieval misses, 5 bounded-ranking misses and 4 verifier rejections. There were no demonstrated bad-reference, confidence-only, source-data or benchmark-input failures. The verifier rejections were dominated by visitor/reference transformation uncertainty and insufficient discriminative evidence; the verifier was not loosened.

A related-panel case in the 501–1,000 regression initially produced a confident incorrect attachment. The visitor image was one Giovanni dal Ponte roundel while the verifier selected another. The generic safety guard now converts a reference match to `NEEDS_CONFIRMATION` when confident Stage-1 artist evidence conflicts with the selected reference candidate. This does not change `.92/.82` and is covered by a deterministic regression. The safety rerun produced zero incorrect attachment.

## Performance and provider variance

At 2,000, metadata ranking averaged approximately 0.54–0.57 s and visual retrieval 0.36–0.45 s in the representative cohorts. Model calls remained bounded around 1.73–1.91 per scan. Stage 1 and bounded asset verification remained the dominant costs. Tail variation was provider/model-driven; catalog retrieval did not grow linearly with catalog size. Existing OpenAI request timeouts and bounded retry behavior prevent indefinite waiting.

## Metadata-only shadow limitation

The frozen source snapshot has 1,219 remaining holdings without source image relationships. They can be catalog-metadata-qualified for `VISION_READY`, but the repository has no ground-truth visitor/test images for them. A recognition benchmark cannot truthfully be run without an independent image corpus. Sample size and accuracy therefore remain **NOT AVAILABLE**, and none were activated. This does not block the 2,000-work VISION_PLUS_ASSET package.

## Decision

The 2,000-work controlled catalog is safe and useful: all final cohorts have zero confident incorrect attachment, long-tail fallback is 20/20, hard negatives are safe and model work remains bounded. The next path is **A: complete the remaining image-backed National Gallery catalog**, then evaluate metadata-only coverage using independently acquired ground-truth images. This document does not authorize public activation.
