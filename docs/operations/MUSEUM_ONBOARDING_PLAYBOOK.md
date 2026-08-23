# Museum Onboarding Playbook

Status: CURRENT after Block 3. National Gallery London is a paper test only; this does not authorize ingestion.

## 1. Institution/country configuration

- Approve stable ELYIO ID/slug/name, ISO country, city, coordinates/geofence, IANA timezone, BCP-47 locales, display currency and owner.
- Upsert `countries`, then compatible Institution in `museums`; add `collections` only where source hierarchy is real.
- Validate `get_institution_international_config`, uniqueness and exactly one active directory row.

## 2. Initial fail-closed profile

- Create `institution_profiles` with `candidate_universe=NONE`, `recognition_policy=NOT_READY`, reviewed modes/thresholds/context and an inactive/not-ready catalog version.
- Verify missing/empty configuration returns `institution_not_ready`, never global candidates.

## 3. Source and rights assessment

- Identify official API/export, provider IDs, terms, metadata/image licenses, attribution, caching/derivative and AI/TDM/recognition permission.
- Implement a provider adapter against `backend/app/source_adapter.py`. Fetch/parsing may be custom; core entity/recognition logic may not.
- Round-trip sample raw payload, source URL/language, retrieval time and media declarations. UNKNOWN remains UNKNOWN.

## 4. Dry-run manifest

- Emit provider/source record ID, institution ID, original metadata/language, URL, collection source ID, retrieval time, raw payload and typed media.
- Produce insert/update/unchanged/rejected/collision counts and hashes. A generic runner is not yet implemented; custom integration glue remains.
- Success: deterministic rerun and reviewed sample; no writes by default.

## 5. Object and holding identity

- Upsert SourceProvider/SourceRecord, CulturalObject, InstitutionHolding and namespaced identifiers.
- Exact provider record is idempotent; institution record is unique within institution. Never use title+artist/image as merge identity; translations do not create objects.
- Record `POSSIBLE_DUPLICATE`, `CONFIRMED_SAME`, or `DISTINCT`; never auto-merge uncertain editions/casts/copies.

## 6. Metadata/localization

- Preserve original/source-language metadata and raw payload. Normalize facts without destroying source values.
- Store visitor narrative/translation in locale rows with review state; generated translations do not overwrite museum metadata.

## 7. Media/provenance

- Create `SOURCE_ORIGINAL`, `REFERENCE`, `PRESENTATION`, `RECOGNITION_ASSET` and authorized `DERIVATIVE` separately.
- Record provider/record/URL, license/attribution, rights + verification, retrieval/checksum/lineage and independent presentation/recognition eligibility.
- No UNKNOWN asset is activated by implication and no visitor capture is imported.

## 8. Compatibility Artwork/catalog

- Create stable `Artwork.id` pointing at object + holding; preserve institution/source IDs and editorial/value rows.
- Add versioned memberships initially inactive. Validate membership/profile/holding institution and manifest counts.

## 9. Recognition/benchmark

- Configure profile universe/policy/version/modes/thresholds and independent readiness dimensions.
- Benchmark self/gallery/partial/decoy/wrong-institution/non-art/uncataloged sets; record auto-accepted, confirmation-required, no-match, confident-wrong, latency and cost.
- Approve gates and rollback before activation; no provider-specific core branch.

## 10. Frontend/content/SEO

- Directory ordering is profile data. Add institution content/theme deliberately; current SEO is a France content package and global routes are separate work.
- Create/review a UI bundle when the default language is not shipped. `en-GB` may deliberately use English fallback but is not a distinct reviewed bundle.
- Never relabel EUR V4 values as GBP; explicitly configure or omit unsupported jurisdiction/value claims.

## 11. Analytics/admin

- Reuse canonical events with valid institution/artwork/attempt IDs; QA uses server-secret context.
- Verify catalog/readiness/provenance categories, confirmation-required rate and institution filters. QA remains operationally visible but excluded from founder metrics.

## 12. Smoke/activation/rollback

- Run `PRODUCTION_SMOKE_TEST.md`: selection, known/unknown/wrong-institution/repeat, result/game/recap/share, attempt linkage, admin/system/catalog and current SEO/PWA regression.
- Apply migrations through ledger and deploy reviewed main/release. Activate membership/profile only after smoke.
- Roll back by restoring membership/profile/catalog version; retain object/source/media evidence. Roll back code/content separately and account for SW/cache/SEO.

## National Gallery London paper result

**YES: architecturally ready to begin controlled onboarding, not activation.**

| Item | Required |
|---|---|
| GB, London, Europe/London, en-GB, GBP | Configuration/data only |
| Object/holding/source/media | Current generic schema; no core change |
| Catalog/recognition | Institution Profile; no core change |
| Candidate/ranking | Shared core; benchmark selects configuration |
| Custom engineering | National Gallery source adapter and generic-runner glue |
| Review/ops | Rights, normalization/dedupe, content, benchmark, smoke/rollback |
| Frontend | Institution content/availability and English fallback review; SEO only if separately approved |
| Optional | City entity, richer loans/collections, en-GB distinctions, automation/B2B roles |

No National Gallery-specific core catalog or recognition conditional is required. Adapter/ingest, rights review, profile/catalog, benchmark, content and production validation remain mandatory before visitor activation.
