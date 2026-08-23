# Museum Onboarding Playbook

Status: CURRENT process plus explicit gaps. Paper test institution: National Gallery London. This document does not authorize ingestion.

## 1. Institution creation

- Manual: establish canonical institution name, official source, stable ELYIO ID, coordinates, geofence, public slug and operational owner.
- Tool/DB: insert/update `museums` using a reviewed importer/SQL; no generic institution CLI exists.
- Validation: unique ID/slug/external source ID; directory API returns one row.
- Success: museum selectable without replacing another row.
- National Gallery: **migration/design required** for country; current row can only store city/region strings.

## 2. Country/city configuration

- Manual: ISO country, city, timezone, default language/currency/legal context.
- Current DB: only `city`, `department`, `region`, address/postal code; no country/timezone.
- Success target: canonical country/city relations and formatting policy.
- National Gallery: **current global blocker**, not config-only.

## 3. Catalog source

- Manual: identify official API/export/license/update policy and source-of-truth IDs.
- Tool: build source adapter following existing import patterns; Louvre tooling is not reusable generically.
- Validation: raw payload preserved, pagination/retry/checkpoint documented, source count reconciled.
- National Gallery: custom adapter/research required.

## 4. Rights/provenance assessment

- Manual/legal-owner input: metadata license, image license, attribution, AI/TDM, caching/derivative permissions.
- DB: source fields, `RecognitionAsset` rights/eligibility; current presentation field lacks complete per-image provenance.
- Success: every used image role has explicit evidence; unknown means not eligible.

## 5. Artwork ingestion

- Tool: dry-run normalized manifest, then reviewed DB import.
- DB: `artworks`; never overwrite editorial localizations/value rows.
- Validation: exact insert/update/unchanged/rejected counts and source hashes.
- Success: knowledge rows exist but are not yet visitor-active.

## 6. Normalization

Normalize artist/title/date/inventory/object type/material/dimensions/location while preserving raw/original values. Do not translate proper names by guessing. Validate null/error rates and source round-trip.

## 7. Duplicate checks

Check `(source, source_record_id)`, institution inventory namespace, source redirects, title/creator candidates and editions/copies. Human review any merge. Current model cannot express canonical-work/copy relationships; record the gap, do not collapse rows.

## 8. Images

Choose presentation and recognition assets separately. Populate source/license/attribution/AI eligibility; create derivatives only if authorized. Validate identity visually and through source IDs. National Gallery must not reuse Louvre image rules.

## 9. Recognition readiness

Assign metadata/display/recognition/rights status; add eligible `RecognitionAsset` where required. Current status vocabulary needs manual normalization. Success: no active row is accidentally draft/not-ready.

## 10. Visitor catalog activation

Create a versioned membership manifest with priorities/tiers, initially inactive. Current code requires adding a museum-specific environment variable and Python map entry for top-N behavior; **custom backend change required today**. Validate membership museum matches artwork museum.

## 11. Benchmark

Freeze manifest/assets/model/thresholds. Run self, gallery, decoy, wrong-museum, non-art and uncataloged sets. Record confident-wrong, recall, no-match, latency and cost. Success thresholds must be approved before activation; no universal measured threshold exists.

## 12. Frontend availability

Directory selection is data-driven. Curated visitor/SEO copy, museum prominence, homepage city text and locale support are checked-in frontend code/data. National Gallery requires frontend content/config changes; public SEO pages are not generated from DB automatically.

## 13. Analytics

Ensure museum/artwork/attempt IDs are carried on all relevant events and admin filters. Add institution dimensions without event-name forks. Use QA flag for tests, recognizing current flag is client-asserted.

## 14. Production smoke

Run `PRODUCTION_SMOKE_TEST.md`: selection, known/unknown/wrong-museum, repeat, result, game, recap/share, event linkage and admin catalog health. Use controlled fixtures and no real-user media.

## 15. Admin monitoring

Verify catalog size/readiness/images, museum visitors/scans/success rate, failure reasons and top artworks. Current success metric double-count issue must be fixed before using launch KPIs as acceptance criteria.

## 16. Rollback/deactivation

Deactivate membership/version; remove curated frontend/SEO availability through reviewed deploy; retain source/provenance rows; invalidate caches if needed. Roll back code independently. Document search removal and event definition changes.

## National Gallery London paper result

**Could it be onboarded without architectural changes? PARTIAL / NO for clean repeatability.**

| Work item | Today |
|---|---|
| Basic museum row | Config/data import |
| Correct country/timezone/institution semantics | Migration + backend/frontend model change |
| Catalog | New source adapter/data ingestion |
| Stable object IDs | Data design/import; current source uniqueness usable |
| Collection/loan/exhibition | Architecture change if required |
| Images/rights | Manual assessment + asset ingestion |
| Recognition policy/version | Backend code/config change |
| Candidate ranking | Existing generic core can work after configuration |
| UI/SEO museum availability | Frontend content/config change |
| English UI | Already supported |
| UK legal/currency/value copy | Frontend/value policy change |
| Analytics/admin dimensions | Museum ID works; country/institution integrity needs model change |
| Benchmark/smoke | New fixtures/manual QA |

Mandatory before launch: country/institution model, source/right assessment, import and identity manifest, recognition configuration, frontend/SEO content, benchmark, analytics validation, smoke/rollback. Optional later: collection hierarchy, institution B2B role, automated sync and multilingual expansion beyond English.
