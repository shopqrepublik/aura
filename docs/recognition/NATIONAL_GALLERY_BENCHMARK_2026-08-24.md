# National Gallery London Controlled Recognition Benchmark

Date: 2026-08-24

Catalog: `ng-controlled-170-v1`

Source: frozen official CIIM pre-eminent-work snapshot (170 objects)
Status: CONTROLLED PREVIEW; not public selector, SEO or general visitor activation

## Method

`backend/scripts/national_gallery_prepare_recognition_corpus.py` prepared independent JPEG encodings plus deterministic wall/frame/light/blur and partial-crop variants. Reference and test byte checksums are distinct; all lineage is recorded in the ignored local manifest. These are provider-related technical tests, not independent physical gallery photographs, so they establish pipeline behavior rather than final real-world accuracy.

The controlled candidate universe contained exactly 170 institution-scoped works. `VISION_READY` used visitor bytes plus open vision and top-five metadata verification. `VISION_PLUS_ASSET` used the same flow plus one explicitly selected reference comparison. The same canonical thresholds were used (`auto=.92`, `review=.82`, fuzzy candidate `.55`).

## Results

| Suite | Mode | Cases | Correct top-1 | Confirmation | AI fallback | Unresolved | Incorrect catalog | Confident incorrect | p50 | p95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Pristine | VISION_READY | 169 | 119 | 10 | 43 | 1 | 7 | 6 | 6.014s | 8.236s |
| Pristine | VISION_PLUS_ASSET | 170 | 131 | 58 | 39 | 0 | 0 | 0 | 5.549s | 9.041s |
| Visitor-like | VISION_READY | 170 | 120 | 27 | 43 | 2 | 7 | 5 | 6.141s | 8.392s |
| Visitor-like | VISION_PLUS_ASSET | 170 | 119 | 66 | 51 | 0 | 0 | 0 | 5.845s | 9.833s |
| Partial/crop stress | VISION_READY | 170 | 81 | 23 | 27 | 58 | 5 | 3 | 6.721s | 11.824s |
| Partial/crop stress | VISION_PLUS_ASSET | 170 | 80 | 39 | 38 | 52 | 1 | 0 | 6.536s | 11.821s |
| Out-of-catalog NG | VISION_PLUS_ASSET | 20 | n/a | 0 | 20 | 0 | 0 | 0 | 3.999s | 12.009s |

The first pristine VISION_READY run preceded successful retrieval of one transiently unavailable media record, hence 169 rather than 170. Corpus preparation was rerun with bounded retries and ended at 170/170.

## Failure analysis and decision

VISION_READY confident errors clustered in genuine confusion families: Mantegna/Bellini versions of *Agony in the Garden*, Titian's Diana cycle, Veronese allegories, and visually similar narrative panels. This is not cross-institution leakage. Metadata-only vision can confidently name the wrong member of a real visual pair.

VISION_PLUS_ASSET removed every confident-wrong result in pristine and visitor-like tests. Its single partial-crop wrong candidate remained below auto-accept and therefore required confirmation. The safety improvement is evidence-backed, so the controlled launch catalog uses `ASSET_VERIFY`; VISION_READY remains valid long-tail/fallback architecture but is not the recommended auto-accept path for this confusion-heavy set.

All 20 deliberately out-of-catalog National Gallery cases avoided a catalog attachment and returned explicit uncataloged AI candidates. Manual comparison found 8 clearly useful/correct or near-equivalent identifications; the remaining guesses demonstrate why generated results must not claim canonical catalog certainty. No uncataloged result was auto-promoted.

## Full-source readiness snapshot

The frozen full source contains 3,785 records. Under the current technical readiness rule all 3,785 have stable provider identity and a title, so none is metadata-`NOT_READY`. The controlled state is:

- `VISION_PLUS_ASSET`: 170 prepared controlled works;
- `VISION_READY`: 3,615 remaining metadata-ready works;
- `NOT_READY`: 0 under current minimum metadata rule;
- works declaring some media: 2,570;
- works without declared media: 1,215.

These numbers do not activate the remaining works and do not claim benchmark quality for them.

## Gates and limitations

Passed: institution isolation by code/tests; zero confident wrong for PLUS_ASSET pristine/visitor-like; out-of-catalog fallback; deterministic lineage; public preview isolation; idempotent 170-work provisioning.

Still required before public launch: independent real gallery captures across devices/lighting/angles; production controlled browser smoke; product-owner content/media decisions; public activation decision. Local OpenAI quota was exhausted after the complete suites, so an extra ad-hoc Louvre/Orsay/non-art network run was not executed; existing deterministic wrong-institution/non-art regressions remain mandatory in CI.

Technical decision: ready for controlled real-world scan testing using `VISION_PLUS_ASSET`, with AI uncataloged fallback preserved.
