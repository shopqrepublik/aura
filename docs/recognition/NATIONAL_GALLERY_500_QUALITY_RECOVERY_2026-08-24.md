# National Gallery 500-Work Recognition Quality Recovery

Date: 2026-08-24  
Controlled runtime catalog: `ng-controlled-500-v2-retrieval`  
Status: CONTROLLED PREVIEW ONLY; 500 memberships; no selector, SEO, or public artwork activation.

## Frozen baseline and diagnosis

The frozen 60-case added-work baseline was 13 correct top-1, 24 top-5, 47 fallback, zero confident incorrect, p50 7.84s and p95 11.75s. Of the 47 fallback/failure cases, 36 were primarily `VISUAL_ANALYSIS_FAILURE` (Stage 1 confidently named a different real work or returned insufficient identity), nine were `CANDIDATE_RANKING_MISS` (the correct work was rank 3–5 but outside the two-reference verification cutoff), and two were `REFERENCE_ASSET_FAILURE`/verifier rejection despite a top-two candidate. Candidate-generation, confidence-only, source-data, benchmark-input, and metadata-verifier primary failures were zero.

The original 170 and added 330 have identical normalized field completeness: title, creator, date, object type, department, accession and source URL are present for every row; neither population has normalized description text. Reference dimensions are also similar (original median 700.5×800; added median 687.5×800). The operational difference is that the original pre-eminent group is much more often identified correctly by open vision, while obscure additions produce plausible but wrong famous-work names.

## Reference audit

All 330 added primaries were audited from the frozen corpus. There are 313 good technical primaries, 17 low-resolution primaries, zero contextual/video/wrong primaries, and zero duplicate checksums. The adapter/ingestion path selects an IMAGE association attached to the correct holding; shared contextual videos are not RecognitionAssets. No replacement was required in this recovery block. `VISION_PLUS_ASSET` remains readiness, not proof of quality.

## Implemented bounded funnel

Migration `0007_visual_candidate_retrieval` adds an optional versioned JSON descriptor to `recognition_assets`. `elyio-lowfreq-rgb-v1` is a compact low-frequency RGB/composition descriptor generated from the selected primary. It is used only for cheap institution-scoped retrieval. It never creates a match or changes thresholds.

The runtime fuses cheap metadata and visual retrieval into at most five candidates. One bounded verifier call compares the visitor photo with at most three real references and must return the same physical object or `NO_MATCH`. This replaces up to two serialized reference-verifier calls. Legacy museums without descriptors retain their existing recognition path.

On the profiled 60-case run, metadata-only recall was 9/15/22/27/35 at @1/@3/@5/@10/@20. Visual retrieval recall was 35/41/41/43/50. Final verified output was 33/60 correct top-1, 27 fallback, zero incorrect and zero confident incorrect. The earlier non-profiled repeat was 24 top-1/36 fallback with the same zero-wrong result, demonstrating model variability but consistent direction versus baseline.

## Regression results

| Suite | Cases | Correct top-1 | Top-k | Confirmation | Fallback | Incorrect | Confident incorrect | p50 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Added works before | 60 | 13 | 24 | 9 | 47 | 0 | 0 | 7.84s | 11.75s |
| Added works after, profiled | 60 | 33 | 46 | 0 | 27 | 0 | 0 | 7.59s | 12.84s |
| Original 170 before | 170 | 124 | 133 | 71 | 46 | 0 | 0 | 7.74s | 14.61s |
| Original 170 after | 170 | 129 | 150 | 0 | 41 | 0 | 0 | 8.21s | 11.12s |
| Out-of-catalog after | 20 | n/a | n/a | 0 | 20 | 0 | 0 | 5.46s | 10.99s |

The benchmark's confirmation count follows returned confidence, not a simulated visitor tap. The new multi-reference verifier returned either high-confidence same-object evidence or safe fallback in these runs; thresholds remained `.92/.82`.

## Latency and cost proxy

For the profiled added-work suite: Stage 1 averaged 4.49s; metadata ranking 0.09s; descriptor retrieval 0.08s; reference verification 3.06s; finalization below 1ms. For original 170: Stage 1 averaged 4.17s; metadata ranking 0.09s; descriptor retrieval 0.09s; reference verification 3.62s; finalization below 1ms. The dominant latency is provider/model network time in Stage 1 and reference verification, not scoring 500 rows. Expensive calls are bounded at two per matched-path scan (one Stage 1 plus one reference verifier); the observed suite average was 1.7 calls for added works and 1.84 for original works because early fallback skips verification.

## Safety conclusion

Out-of-catalog National Gallery inputs produced 20/20 AI fallbacks, zero forced catalog matches and zero confident incorrect. Institution scoping and unknown-institution fail-closed remain unchanged. Louvre, Orsay and Orangerie use the unchanged legacy path because they have no descriptor payload. Catalog membership remains exactly 500.

The controlled 500 is evidence-backed for the next controlled expansion block. This is not public-launch approval and does not replace a physical-phone gallery sample.
