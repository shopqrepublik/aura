# Global Hardcode Audit

Status: CURRENT Block 3 review. Content facts inside the checked-in France SEO/editorial package and provider-specific adapter/research scripts are not core hardcodes.

| Path/component | Current assumption / Block 3 result | Classification | Impact / next action |
|---|---|---|---|
| `backend/app/catalog.py`, `InstitutionProfile` | Catalog universe/policy/version/thresholds are DB-backed; missing config fails closed | SAFE_CONFIGURATION / RESOLVED | Preserve adversarial tests; no institution branch. |
| `backend/app/main.py` directory ordering | Former Louvre/Orsay/Orangerie sort moved to `directory_priority` profile data | SAFE_CONFIGURATION / RESOLVED | Onboard through data. |
| `web/components/screens/HomeScreen.tsx` featured IDs/France fallbacks | Removed ID set and France fallback; consumes backend curated ordering/country | SAFE_CONFIGURATION / RESOLVED | Hero/theme remains current product art direction. |
| `backend/app/models.py:Artwork` | Former object==holding==source mixture now points to CulturalObject + InstitutionHolding; provider SourceRecord separate | SAFE_COMPATIBILITY / RESOLVED FOUNDATION | Legacy columns remain until reader migration. |
| `backend/app/models.py:LouvreImageReference` | Louvre-specific source table mirrored into generic MediaAsset | LEGACY SOURCE ADAPTER | Keep as evidence/compatibility; future Louvre adapter emits generic contract. |
| `backend/app/source_adapter.py` | Generic provider/institution/media/provenance output contract | SAFE_CONFIGURATION / RESOLVED | Implement adapter-specific fetch/parsing only. |
| `media_assets` | Presentation/reference/recognition/source/derivative and rights/eligibility explicit | SAFE_CONFIGURATION / RESOLVED FOUNDATION | Review/backfill UNKNOWN; later switch runtime reader. |
| `backend/app/admin.py:_catalog_health` | Louvre compatibility block remains; generic provenance categories added | SHOULD_GENERALIZE | Per-institution breakdown later; not onboarding core blocker. |
| `backend/app/main.py:DEMO_ARTWORKS` | Orsay/Orangerie runtime fallback catalog remains | GLOBAL_BLOCKER P1 | Remove after DB-only parity/availability gate. |
| `backend/app/main.py` recognition comments/source policies | Louvre references remain legitimate provider policy; shared decision code uses profile | LEGACY/SOURCE_ADAPTER | Isolate fetch/policy registry during adapter migration. |
| `web/lib/types.ts` | Shipped UI bundle union remains en/fr/zh-Hans; `LocaleCode` and DB config allow arbitrary BCP-47 | SHOULD_GENERALIZE P1 | A new primary UI language still needs a reviewed bundle; no schema/core branch. |
| `web/lib/i18n.ts` | Reusable UI copy centralized; museum/France/Paris continuation and directory copy generalized | PARTIALLY RESOLVED | Inline ternaries remain; migrate progressively to resource modules. |
| `web/lib/api.ts` legal copy | France string-pattern policy removed; structured policy code/localizations returned from DB | SAFE_CONFIGURATION / RESOLVED | New jurisdiction claims require explicit reviewed policy content. |
| `backend/app/main.py`, `web/lib/valueReveal.ts` | Value Engine V4 uses explicit EUR ladder; institution can configure display currency but no FX exists | SAFE_CURRENT_POLICY / P1 PRODUCT LIMITATION | Do not relabel EUR values as GBP; future reviewed multi-currency value block. |
| `web/lib/international.ts` | Generic `Intl` currency/date helpers; no conversion | SAFE_CONFIGURATION | Adopt on new institution surfaces. |
| `web/lib/scaleComparison.ts` | RESOLVED 2026-08-24: local property comparison is selected from Institution city; Paris is no longer the implicit global property reference | SAFE_CONFIGURATION | Add reviewed city packs as institutions launch; unknown cities retain global comparisons without a fabricated local label. |
| `web/lib/seo-content.ts`, `web/app/[locale]` | France 12-museum/117-work, three-locale checked-in SEO package | SAFE_CONTENT_PACKAGE | New country SEO requires approved package/routes; do not treat as core directory. |
| `web/components/seo/SeoNav.tsx` | Three shipped locale links | SHOULD_GENERALIZE | Generate from approved SEO locale package later. |
| `web/next.config.ts` | Current provider origin allowlist | SAFE_DEPLOYMENT_CONFIGURATION | Add a reviewed provider origin when onboarding sources. |
| `web/public/manifest.json` / museum theme | Some Orsay-era presentation copy/assets | LEGACY/SHOULD_GENERALIZE | Product copy/theme cleanup later; not recognition/catalog architecture. |
| `backend/scripts/louvre_*`, `exports/louvre/*` | Louvre-specific acquisition/research | LEGACY SOURCE WORK | Retain evidence; do not call it global core. |
| `/louvre-golden20-preview`, root AURA/frontend specs | Historical/internal | LEGACY | Keep noindex and labeled historical. |
| `backend/app/admin.py` default founder credentials | Source defaults exist if env absent | GLOBAL_BLOCKER P1 SECURITY | Fail closed, external IdP/MFA/RBAC in security block. |

## Implicit assumptions

- **Resolved foundation:** object identity no longer requires one permanent institution relation; holdings have status/effective dates.
- **Resolved:** exact provider and institution-record identities are constrained; title/artist never auto-merges.
- **Resolved foundation:** arbitrary country/locale/timezone/currency configuration is representable.
- **Remaining:** current UI message bundles, generated enrichment templates and public SEO only ship three locales.
- **Remaining:** full institution catalog is materialized/ranked in process per request.
- **Remaining:** generic adapter ingest/upsert CLI is not implemented; existing import scripts are provider/institution-specific.
- **Remaining:** legacy media/runtime columns remain authoritative until parity migration.

## National Gallery paper test

GB/London/Europe-London/en-GB/GBP, object/holding/source/media and profile rows require no core schema, catalog or recognition conditional. Remaining custom code is a source adapter plus ingest/rights/content/benchmark work. A complete en-GB-specific visitor bundle is optional while English fallback is accepted; a new non-shipped language would require a reviewed bundle.
