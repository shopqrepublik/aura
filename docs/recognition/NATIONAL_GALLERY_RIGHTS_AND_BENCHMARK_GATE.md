# National Gallery London — Rights Gate and Benchmark Preparation

Status: CURRENT preparation record, 2026-08-23. No public activation and no benchmark accuracy claim.

## Decision summary

Track A (`VISION_READY` / AI-first) does **not** require a RecognitionAsset, presentation image, source image, or provider reference bytes. It requires a configured institution/profile, a benchmark-only institution-scoped candidate set, stable candidate IDs, and useful title/artist metadata. The current blocker is a rights-safe ground-truth input corpus, not recognition assets.

Track B (`VISION_PLUS_ASSET`) requires separately approved recognition/reference processing. It remains unavailable because zero National Gallery assets have been ELYIO-verified or approved for recognition.

## Code-verified data flow

`backend/app/main.py::recognize_open` sends the visitor/test image and institution context to the vision model. `rank_catalog_candidates` compares the returned title, artist, visual/OCR clues, object type and optional hall hint against institution-scoped candidate metadata. With `recognition_policy=TOP_N_METADATA`, `verify_top_candidates_with_openai` sends the same visitor image plus summaries of at most the configured candidate limit; it fetches or sends no provider media bytes. A successful choice without an approved local reference is labeled `VISION_READY`.

`RecognitionAsset` is queried only as optional candidate evidence/substitution. `visual_verify_single_candidate` is the `VISION_PLUS_ASSET` path and may fetch a rights-allowed reference. Presentation imagery is not a matching prerequisite.

Minimum practical candidate fields are stable ELYIO ID, institution relationship, title, and enough discriminating metadata. Artist and date materially improve ranking; object type, description, inventory number, department/room, materials and other source metadata can supply additional signals. Candidate scope comes from the Institution Profile and benchmark-only membership/configuration; it never broadens globally.

## Rights trust matrix

Official source declaration: [National Gallery licences](https://www.nationalgallery.org.uk/documentation/ngacuk/licences) states structured data is CC0, narrative text is CC BY 4.0, and images are CC BY-NC-ND 4.0. ELYIO records this as `DECLARED_BY_SOURCE`, not legal verification.

| Use | Current status | Gate |
|---|---|---|
| Metadata ingestion | Source-declared usable for controlled normalization; attribution retained for narrative text | No image processing implied |
| Visitor presentation | Not approved | Manual rights/product review; source declaration alone does not activate presentation |
| Recognition reference/model processing | Not approved | Explicit review of intended processing required |
| Benchmark input image | No local rights-safe National Gallery corpus found | Team-owned, explicit permission, CC0/public-domain, or approved visitor photography required |
| Local cache/derivative | Not approved | Separate permission required; ND media is not cropped/augmented by default |
| Generated RecognitionAsset | Not approved | Requires an eligible source and explicit recognition/processing approval |

No provider image is promoted to VERIFIED, presentation eligible, or recognition eligible. This is an operational record, not legal advice.

## Prepared benchmark-only metadata catalog

The frozen official `pre_eminent_work_flag` snapshot contains 170 records. All 170 have stable provider IDs, accession IDs, title, artist and date. This is an objective metadata candidate set rather than an arbitrary numeric sample. It is suitable for an isolated/non-public `TOP_N_METADATA` benchmark catalog after ground-truth images exist. It has 447 source-declared media edges (380 images, 67 videos), but none are approved as benchmark input or recognition assets.

Full source snapshot parity remains 3,785 objects, 3,745 unique media entities and 3,794 exact association edges. Review queue: 3,745 unique assets / 3,794 relationships are SOURCE_DECLARED; 0 VERIFIED; 0 currently approved presentation candidates; 0 currently approved recognition candidates; all 3,745 assets require review before either use.

## Required corpus manifest

Each case must record case ID, ground-truth object/source/accession IDs, image owner/source, permission/license evidence, permitted benchmark/model-processing scope, capture class, expected outcome, institution, checksum, capture/retrieval date and reviewer. Do not commit unauthorized binaries.

Required Track A classes remain separate in reporting:

- pristine/reference-like rights-safe photographs;
- visitor-realistic angle, crop, glare, frame and low-light photographs;
- visually confusable/same-artist hard negatives;
- deliberately excluded but identifiable National Gallery works for uncataloged fallback;
- unrelated art, non-art and wrong-institution images.

No acceptable National Gallery input images were found in the repository on 2026-08-23, so corpus counts are currently zero and no live model benchmark was run. Physical visitor photography under an approved test protocol is the preferred way to obtain realistic cases if no pre-cleared corpus is supplied.

## Metrics and semantics

Report pristine and visitor-realistic cohorts separately: total, correct catalog top-1, correct top-k, confirmation required, incorrect catalog match, correctly triggered uncataloged fallback, unresolved, false-positive rate, average/p50/p95 latency. Engine outcome and visitor resolution remain separate. Existing immutable gates are: confident-wrong and cross-institution leakage are blockers. Numeric recall/latency launch thresholds beyond existing latency tooling are not currently canonical and must be labeled RECOMMENDED before adoption.

## Readiness dimensions

| Dimension | State |
|---|---|
| SOURCE READY | YES — reproducible official snapshots |
| METADATA READY | YES — 170-record objective candidate subset |
| CATALOG READY | YES for isolated benchmark preparation; NO public membership |
| VISION_READY | Technically YES; operational benchmark blocked by input corpus |
| VISION_PLUS_ASSET | NO — zero approved RecognitionAssets |
| BENCHMARK READY | NO — rights-safe ground-truth images absent |
| PUBLIC ACTIVATION READY | NO |

Value output remains disabled: institution currency is GBP while Value Engine V4 is EUR-grounded; no relabeling or conversion is allowed.
