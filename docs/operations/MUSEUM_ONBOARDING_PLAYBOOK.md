# Museum Onboarding Playbook

Media validation must compare both unique media entities and relationship edges. Zero edge loss is an activation prerequisite. Shared/contextual media remains independently gated for presentation and recognition.

The hybrid visitor invariant remains independent of media readiness: configured + catalog match uses canonical content; configured + no reliable match uses truthful AI uncataloged fallback and records the sighting; unknown/unconfigured institution fails closed. Catalog when we know. AI when we don't. Learn from what visitors scan.

Status: CURRENT. National Gallery London now has a frozen 1,000-work controlled recognition package and benchmark tooling; it is not publicly activated.

Block 4 path: register provider/adapter/institution mapping, then DISCOVER → DRY_RUN → PLAN → RECONCILE → reviewed APPLY using [Source Adapter Guide](SOURCE_ADAPTER_GUIDE.md). Complete [provenance review](PROVENANCE_REVIEW_RUNBOOK.md), readiness and benchmark before separate activation. New institutions must not use legacy direct-upsert scripts.

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
- Produce insert/update/unchanged/rejected/collision counts and hashes with `backend/scripts/ingest_catalog.py`; custom provider logic remains in its adapter.
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
- Audit every primary reference for object association role, media type, resolution, crop/background and checksum uniqueness. Contextual media must not become a recognition primary merely because it is technically eligible.
- Measure metadata and visual candidate recall@1/3/5/10/20 before changing confidence. Cheap versioned descriptors may improve retrieval, but only same-object verification may attach canonical identity.
- Profile Stage 1, metadata ranking, visual retrieval, verification and finalization. Catalog growth must not increase expensive model calls linearly.
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
- Large controlled snapshots use bounded idempotent ingestion batches; never materialize a full raw-provider plan merely to activate one catalog version. On auto-stop platforms, run explicit single-batch commands and a separate `--activate-only` parity step. Switch membership/profile only after every batch reaches parity.
- Roll back by restoring membership/profile/catalog version; retain object/source/media evidence. Roll back code/content separately and account for SW/cache/SEO.

## National Gallery London controlled result (2026-08-25)

**YES: 2,000 works are available for controlled testing, not public activation.** See [the 2,000-work benchmark](../recognition/NATIONAL_GALLERY_CONTROLLED_2000_BENCHMARK_2026-08-25.md). The additive expansion preserves all prior identities, retains bounded verification and produces zero confident-wrong results after the artist-conflict caution regression. The next recommended tranche is the remaining image-backed cohort; metadata-only holdings require an independently sourced test-image corpus before their AI-first quality can be measured.

| Item | Required |
|---|---|
| GB, London, Europe/London, en-GB, GBP | Configuration/data only |
| Object/holding/source/media | Current generic schema; no core change |
| Catalog/recognition | Institution Profile; no core change |
| Candidate/ranking | Shared core; benchmark selects configuration |
| Custom engineering | Existing National Gallery source adapter plus controlled corpus/benchmark tools |
| Review/ops | Real independent visitor captures, content, smoke/rollback and product-owner gates |
| Frontend | Institution content/availability and English fallback review; SEO only if separately approved |
| Optional | City entity, richer loans/collections, en-GB distinctions, automation/B2B roles |

No National Gallery-specific core catalog or recognition conditional is required. The server-side `controlled_preview_only` policy and trusted QA token isolate the catalog. Public content, selector and SEO activation remain separate decisions.
