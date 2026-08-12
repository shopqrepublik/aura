# Louvre Recognition Visual Retrieval Decision Report

Generated: 2026-08-12

## Scope

This report covers the RecognitionAsset identity audit, benchmark integrity audit,
and offline visual embedding retrieval experiment for the Louvre Visitor Catalog
`2026-08-11-v1`.

No production rows were modified. No Louvre-hosted image bytes were fetched. No
live external image or asset requests were made during benchmark execution.

## RecognitionAsset Identity Audit

Input assets audited: 180 Louvre assets previously marked `APPROVED`.

Results:

| Status | Count |
| --- | ---: |
| VERIFIED | 60 |
| QUARANTINED_MISMATCH | 64 |
| UNRESOLVED | 56 |

`QUARANTINED_MISMATCH` and `UNRESOLVED` assets must be excluded from visual
benchmarking and runtime visual retrieval.

Root cause:

The earlier SPARQL inventory matcher accepted Wikidata `P217` inventory matches
without constraining the matched item to Louvre collection/location and without
post-validating title, creator, and object-type agreement. Inventory-like
identifiers can collide across unrelated works.

Code fix:

`backend/scripts/louvre_visitor_500_phase1.py` now requires Wikidata SPARQL
inventory matches to have `P195` or `P276` linked to Louvre (`Q19675`) before
accepting the candidate.

## Benchmark Integrity

Original valid pristine rows: 41.

| Category | Count |
| --- | ---: |
| same-source derivative + verified reference | 17 |
| no verified reference | 24 |
| independent query + verified reference | 0 |
| invalid / ambiguous | 0 |

Asset status among the 41 original rows:

| Asset status | Count |
| --- | ---: |
| VERIFIED | 17 |
| QUARANTINED_MISMATCH | 15 |
| UNRESOLVED | 9 |

Important limitation:

The current positive benchmark has no independent visitor-like query images with
verified references. The eligible visual subset is same-source derivative data,
so it is useful for retrieval plumbing but not sufficient for launch accuracy
claims.

## Visual Model Tested

Model: `facebook/dinov2-small`

Embedding input: actual local cached image bytes from `VERIFIED` assets only.

Verified cached references available to the experiment: 25.

No metadata-derived vectors were counted as image embeddings.

## Retrieval Ablation

Original denominator is always the 41-row benchmark. The eligible subset is the
17 same-source derivative rows that have verified references.

| Configuration | Original Top-1 | Original Top-3 | Original Top-5 | Original Top-20 | Eligible Top-1 | Eligible Top-3 | Eligible Top-5 | Eligible Top-20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| metadata only | 36.6% | 41.5% | 41.5% | 41.5% | 88.2% | 100.0% | 100.0% | 100.0% |
| visual only | 41.5% | 41.5% | 41.5% | 41.5% | 100.0% | 100.0% | 100.0% | 100.0% |
| visual 0.90 / metadata 0.10 | 41.5% | 41.5% | 41.5% | 41.5% | 100.0% | 100.0% | 100.0% | 100.0% |
| visual 0.80 / metadata 0.20 | 41.5% | 41.5% | 41.5% | 41.5% | 100.0% | 100.0% | 100.0% | 100.0% |
| visual 0.70 / metadata 0.30 | 41.5% | 41.5% | 41.5% | 41.5% | 100.0% | 100.0% | 100.0% | 100.0% |

Best experimental configuration by Top-5, then Top-3, then Top-1, with visual
evidence preferred on ties: `visual_0.7_metadata_0.3`.

## Eligible Subset Department Coverage

Eligible visual rows are narrow:

| Department | Top-5 hit count |
| --- | ---: |
| Paintings | 10 / 10 |
| Sculptures | 2 / 2 |
| Decorative Arts | 2 / 2 |
| Islamic Art | 2 / 2 |
| Byzantine / Christian East | 1 / 1 |

The eligible subset has no Egyptian Antiquities, Greek/Etruscan/Roman
Antiquities, or Near Eastern Antiquities after identity filtering.

## Failure Taxonomy

Top-5 misses in the strongest configuration: 24.

| Failure category | Count |
| --- | ---: |
| missing verified reference | 24 |

Representative misses include:

| ARK | Title | Asset status |
| --- | --- | --- |
| cl010065720 | Coronation of Napoleon | UNRESOLVED |
| cl010252531 | Winged Victory of Samothrace | UNRESOLVED |
| cl010120564 | element of statue | QUARANTINED_MISMATCH |
| cl010008140 | Cubit of Maya | QUARANTINED_MISMATCH |
| cl010111542 | Stoclet Paten | QUARANTINED_MISMATCH |
| cl010091976 | Psyche Revived by Cupid's Kiss | UNRESOLVED |
| cl010277627 | Venus de Milo | UNRESOLVED |

The remaining misses are data/reference-coverage failures, not evidence that
DINOv2 visual similarity failed on verified references.

## Decision Gate

PASS gate reached: **NO**.

Reason:

The clean eligible visual subset reaches 100% Top-5, but it is only 17 rows and
all are same-source derivatives. The original 41-row denominator remains 41.5%
Top-5 because 24 expected works lack a verified reference after the identity
audit. This cannot be counted as a clean non-leaky 95% recognition benchmark.

## Recommendation

Do not deploy visual recognition changes yet.

Proceed with one targeted data-integrity iteration:

1. Expand verified references for the benchmark ground-truth misses first,
   especially Tier A works such as Winged Victory, Venus de Milo, Psyche, and
   Coronation of Napoleon.
2. Preserve strict identity proof: Louvre-linked Wikidata entity, exact
   inventory/object identifier, or strong title + creator + object-type evidence.
3. Build an independent/non-leaky legal query set where possible; keep
   same-source derivative metrics separate.
4. Rerun DINOv2 visual-only and visual/metadata fused retrieval before invoking
   Stage2.
5. Productionize only after a clean benchmark reaches the 95% Top-5 gate.

## Artifacts

- `exports/louvre/recognition_assets/louvre_recognition_asset_identity_audit.csv`
- `exports/louvre/recognition_assets/louvre_recognition_asset_identity_audit.jsonl`
- `exports/louvre/recognition_assets/louvre_recognition_asset_identity_audit_summary.json`
- `exports/louvre/recognition_benchmark/louvre_benchmark_integrity_audit.jsonl`
- `exports/louvre/recognition_benchmark/louvre_benchmark_integrity_audit_summary.json`
- `exports/louvre/recognition_benchmark/visual_embedding/louvre_visual_embedding_benchmark_2026-08-12T130225+0000.jsonl`
- `exports/louvre/recognition_benchmark/visual_embedding/louvre_visual_embedding_benchmark_summary_2026-08-12T130225+0000.json`
- `exports/louvre/recognition_benchmark/visual_embedding/louvre_visual_embedding_failures_2026-08-12T130225+0000.jsonl`
