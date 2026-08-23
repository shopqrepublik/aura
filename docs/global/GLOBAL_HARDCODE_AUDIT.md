# Global Hardcode Audit

Status: CURRENT tracked-source audit at `5c5ac7e`. Content mentions inside artwork prose are not architectural hardcodes; historical AURA specs, generated exports and research scripts are classified separately.

## Meaningful findings

| Path / component | Current assumption | Class | Impact | Recommended remediation |
|---|---|---|---|---|
| `backend/app/catalog.py` version constants/map | Ten exact museum IDs and one env variable per version | **GLOBAL_BLOCKER** | New curated museum needs backend code/deploy; absent map falls back to all museum artworks | `visitor_catalogs`/recognition profile table and active version pointer |
| `backend/app/main.py:TOPN_VERIFIER_MUSEUMS` | Recognition policy equals keys of that map | **GLOBAL_BLOCKER** | Policy cannot be configured per institution/catalog | Data-driven recognition profile |
| `backend/app/main.py:recognize_open` | Named prompts only for Louvre/Orsay/Orangerie; fallback shows raw museum ID | **SHOULD_GENERALIZE** | Poor/inconsistent context for new museum | Load localized institution name/source policy from DB/config |
| `backend/app/main.py` confidence constants | 0.92 auto, 0.82 review, 0.55 fuzzy globally | **SHOULD_GENERALIZE** | Different object/media classes cannot be calibrated independently | Benchmark-versioned profile thresholds |
| `backend/app/main.py:VISUAL_VERIFY_MODEL` | Stage 2 hardcoded `gpt-4o` | **SAFE_CONFIGURATION** today | Model change requires deploy; benchmark coupling | Environment/profile plus frozen benchmark approval |
| `backend/app/main.py:DEMO_ARTWORKS` | Large Orsay/Orangerie fallback catalog in code | **GLOBAL_BLOCKER** | Duplicate source of truth, bundle/module weight, one-pilot assumptions | Remove runtime fallback after DB availability contract/tests |
| `backend/app/main.py` museum sort | Louvre, Orsay, Orangerie fixed priority | **SHOULD_GENERALIZE** | Global directory privileges Paris museums | Institution prominence/market config in data |
| `backend/app/catalog.py:artwork_to_catalog_dict` | Louvre RecognitionAsset substitution always blocked | **SAFE_CONFIGURATION** temporary | Correct safety quarantine but institution name embedded | Asset review state/policy rather than museum ID branch |
| `backend/app/main.py` source URL policy/comments | Louvre/RMN is metadata-only; Wikimedia behavior generic | **SAFE_CONFIGURATION** | Rights-safe but provider-specific logic can spread | Provider policy registry keyed by source/license |
| `backend/app/models.py:LouvreImageReference` | Dedicated provider/museum table | **SHOULD_GENERALIZE** | New providers need new tables/code | Generic `source_media_references` with typed raw metadata |
| `backend/app/models.py:Artwork` | Louvre-era department/collection/location fields added to universal row | **SHOULD_GENERALIZE** | Semantics unclear across institutions | Normalized collection/holding/location with source mapping |
| `backend/app/admin.py:_catalog_health` | Imports/queries Louvre table and returns Louvre-only block | **SHOULD_GENERALIZE** | Admin global health is partially museum-specific | Generic per-institution/provider breakdown |
| `backend/app/admin.py:ADMIN_EMAIL` | One default founder email | **SHOULD_GENERALIZE** | No roles/multiple operators; source default identity | Admin users/roles from identity provider; no default account |
| `backend/app/admin.py` default password hash/pepper | Safe only if production overrides | **GLOBAL_BLOCKER** security | Misconfiguration activates known source defaults; weakens IP pseudonymization | Fail closed when secrets absent; rotate env secrets |
| `backend/app/admin.py:TRACKING_AVAILABLE_SINCE` | Date string hardcoded | **SAFE_CONFIGURATION** | Correct known data boundary but manual | Derive earliest event plus immutable deployment annotation |
| `backend/app/admin.py` readiness values | Mixes READY/VISION_READY/VISION_PLUS_ASSET/NEEDS_ASSET | **SHOULD_GENERALIZE** | Ambiguous readiness counts | Enforced enum/state dimensions and migration |
| `web/lib/types.ts` | Locale union exactly en/fr/zh-Hans | **GLOBAL_BLOCKER** for new language | Every language needs code/content/schema edits | Locale registry + BCP-47 rows |
| `web/lib/i18n.ts` | UI dictionaries inline; Paris time/featured/France-wide labels | **GLOBAL_BLOCKER** for another country UX | London would show Paris/France copy | Institution/location templating and locale resource modules/CMS |
| `web/lib/api.ts:localizeValueCopy` | French public-collection law and Leonardo string pattern branches | **GLOBAL_BLOCKER** | UK/global works can receive false France legal context | Jurisdiction/content-policy records, structured localized fields |
| `web/lib/valueReveal.ts`, `indicative-value.ts` | EUR-only AI estimate/aggregation | **SHOULD_GENERALIZE** | Non-euro institution UX/market context constrained | Base currency policy and locale formatting; keep canonical calculation currency explicit |
| `web/lib/scaleComparison.ts` | Paris apartments/European reference prices | **SHOULD_GENERALIZE** | Comparisons can be culturally irrelevant | Locale/market reference packs with dated provenance |
| `web/lib/seo-content.ts` | 12 museum pages and 117 works explicitly checked in | **SAFE_CONFIGURATION** for quality | New museum requires frontend content deploy | Keep editorial approval, but use validated content package schema |
| `web/components/seo/SeoNav.tsx` | Exactly three locale links | **SHOULD_GENERALIZE** | Adding locale requires component edit | Iterate configured locale registry/alternates |
| `web/app/[locale]` static params | Three URL locale values | **SHOULD_GENERALIZE** | Code deploy for locale expansion | Generated from approved locale config/content |
| `web/lib/app-state.ts` | One selected museum per visit | **SAFE_CONFIGURATION** | Correct visit invariant; not a global blocker | Preserve, while allowing institution switch only via new visit |
| `web/lib/app-state.ts` uncataloged ID | Time-derived identity | **SHOULD_GENERALIZE** | Repeat scans inflate and cannot analyze cross-session object | Stable normalized/fingerprint temporary identity |
| `web/lib/analytics.ts` | Browser language, no country/city derivation | **SAFE_CONFIGURATION** privacy / incomplete analytics | Global geography unavailable | Consent/privacy-reviewed coarse server dimension if needed |
| `web/app/admin` | English-only founder UI/`en-US` formatting | **SAFE_CONFIGURATION** internal | Not visitor blocker; poor multi-region ops | Locale-neutral dates/numbers and optional operator locale |
| `web/next.config.ts` | Fixed Supabase project/API/PostHog/Wikimedia origins | **SAFE_CONFIGURATION** per deployment | New provider/region requires deploy | Validated env-derived allowlist with secure defaults |
| `web/public/manifest.json` | Stale Orsay description | **LEGACY** | Install metadata misstates product | Update separately with global product copy |
| `web/app/louvre-golden20-preview` | Louvre-specific internal route/export path | **LEGACY** | Future sessions may confuse it with runtime | Keep noindex or move to research tooling/archive |
| `backend/scripts/louvre_*`, `exports/louvre/*` | Institution-specific research/import pipeline | **LEGACY** as generic tooling | Cannot onboard London from it directly | Extract adapter interfaces/fixtures; retain provenance evidence |
| root AURA spec/`frontend/` | Orsay-only MVP assumptions | **LEGACY** | Documentation/code confusion | Keep explicitly historical; canonical docs start at `docs/README.md` |

## Implicit assumptions without literal keywords

- Artwork has one required museum FK; ownership/display/loan cannot diverge.
- Catalog activation silently falls back to all museum artworks when no configured version is found.
- Candidate ranking materializes a museum's entire list in Python per request.
- First-party identity is browser-local and not linked to authenticated user.
- Event integrity trusts public clients.
- Session means tab sessionStorage, not product inactivity.
- Collection hierarchy, country, timezone and institution default language are absent.
- Static SEO/public content and DB catalog have no generic publication workflow.

## Counts by requested category

Meaningful production findings: Louvre-specific 8, Paris-specific 4, France/legal/currency-specific 6, implicit single-institution/global assumptions 8. Counts overlap by design and exclude historical prose/data mentions.
