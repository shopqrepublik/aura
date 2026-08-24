# National Gallery Controlled 1,000 Benchmark — 2026-08-24

Status: CURRENT CONTROLLED PREVIEW. Public selector, public artwork API, SEO and sitemap activation remain off.

## Package

`ng-controlled-1000-v1-retrieval` preserves all 500 prior stable identities and adds 500 deterministic, non-source-order selections. The package contains 1,000 active controlled memberships, 1,000 RecognitionAssets and 1,000 `elyio-lowfreq-rgb-v1` descriptors across 677 artists. Descriptors are non-authoritative retrieval evidence; at most five fused candidates enter the bounded funnel and at most three references enter one verifier call.

The new 500 primary-reference audit found 473 technically strong references and 27 low-resolution references. It found no duplicate reference checksums and no automatically detectable contextual/wrong primaries. All 500 descriptors are distinct 456-value spatial/color vectors; they are not visitor-facing factual descriptions.

## Frozen visitor-like results

| Population | Cases | Top-1 | Top-k | Confirmation | Fallback | Unresolved | Incorrect | Confident incorrect | p50 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Original 170 | 170 | 133 | 144 | 1 | 36 | 1 | 0 | 0 | 8.22 s | 20.30 s |
| Works 171–500 sample | 60 | 29 | 43 | 3 | 30 | 0 | 1 cautious | 0 | 8.44 s | 12.59 s |
| New 501–1,000 sample | 60 | 27 | 40 | 0 | 33 | 0 | 0 | 0 | 7.39 s | 11.14 s |
| Outside controlled catalog | 20 | — | — | 0 | 20 | 0 | 0 | 0 | 5.62 s | 10.45 s |

The original-170 p95 includes provider/model tail variability: another same-package run was 10.49 s p95 with 135 top-1. Its p50 remained close to the 500-candidate baseline (8.21 s). The catalog-size-dependent steps remain cheap: on the final original-170 run metadata ranking averaged 0.30 s and visual retrieval 0.21 s; Stage 1 averaged 9.01 s due provider outliers and asset verification 5.57 s. Model calls averaged 1.89 versus 1.84 at 500 candidates.

The same new-work sample produced 30 and 27 correct catalog attachments on two runs. This is provider/model variability, not a change in catalog identity. Both post-safety results preserved zero confident-wrong attachment.

## New-work retrieval and failure attribution

For the final 60 new-work sample, metadata recall@1/3/5/10/20 was 10/13/15/19/22; visual-descriptor recall was 33/38/39/43/46; combined retrieval recall was 35/39/41/46/50.

The 33 fallback/failure cases were attributed using recorded metadata rank, visual rank, bounded verifier membership and technical reference audit: 7 Stage-1/semantic-analysis failures, 10 candidate-retrieval misses, 3 fused-ranking misses, 0 demonstrated reference-asset defects, 13 verifier rejections, 0 confidence-only failures, 0 source-data defects and 0 benchmark defects. These labels are stage evidence, not claims that fallback is a product failure; safe fallback is preferred to a wrong attachment.

## Safety and confirmation semantics

Five blank/non-art hard negatives produced zero catalog attachments. Twenty National Gallery works outside the controlled 1,000 produced 20/20 AI fallback and zero forced catalog attachment. Existing institution isolation and unknown-institution fail-closed regressions remain mandatory.

`NEEDS_CONFIRMATION` is intentionally reachable. The verifier decision is now prevented from becoming auto-accepted merely because its numeric confidence exceeds the auto threshold. A generic same-artist conflict guard also converts a metadata-only verifier choice to confirmation when another same-artist candidate has competing visual-retrieval evidence. Thresholds remain `.92/.82`; neither was lowered. This addressed an observed Moses/Isaiah confusion without an artwork or institution special case.

## Remaining collection preparation

The official snapshot contains 3,785 objects. After the controlled 1,000, 2,785 remain inactive: 1,566 declare image media and are potential RecognitionAsset candidates; 1,219 are metadata-only under the current snapshot. Stable title/institution identity is present for all remaining rows, while 935 lack a named artist and 14 lack a date. These are preparation counts, not active readiness claims.

## Decision

The controlled 1,000 is suitable to continue toward a controlled 2,000-work package: confident incorrect is zero after the generic caution fix, long-tail and hard-negative behavior remain safe, and expensive model work remains bounded. This does not authorize public National Gallery activation.

Production ingestion applies this package in idempotent 100-record batches so the source adapter, normalized raw payload and reconciliation plan do not exceed the 256 MB Fly machine. Membership/profile activation remains a separate final step after complete parity; a failed batch leaves only inactive canonical evidence and is safely retryable.
