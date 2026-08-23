# ELYIO Global System Audit — 2026-08-23

Status: **CURRENT EXECUTIVE TECHNICAL AUDIT**

## Production evidence

| Fact | Current state | Evidence |
|---|---|---|
| `origin/main` | `3adf605aca3ae5afd6f6d879b717c4f69682ad0c` | Git fetch, 2026-08-23 |
| Production source | `5c5ac7ed11573e4079b073cdb2598334eeac573f` on `docs/elyio-full-system-audit` | Commit/deploy timestamps and live features align; provider image labels do not embed Git SHA |
| Frontend | Vercel `dpl_48JY2fJoKBB3ZWEUgVKPMRkag2Vw`, Ready, `www.elyio.co` | LIVE |
| Backend | Fly v43, release `nRqjnzJmmaOq8HObg8PVKNL5`, image `deployment-01M0GVRBB3XN0AFMEFY5STJBHQ` | LIVE |
| Migrations | `product_events`, `admin_sessions`, `admin_login_attempts` and expected columns exist | DATA; no migration ledger exists |
| Catalog | 1,222 museums, 944 artwork knowledge rows, 790 active memberships | DATA snapshot 2026-08-23 |
| Recognition readiness | 180 `VISION_PLUS_ASSET`, 610 `VISION_READY`, 116 `READY`, 38 `NEEDS_ASSET` | DATA snapshot; status vocabulary is not yet normalized |
| First-party history | 102 events, 2026-08-20 23:14 UTC to 2026-08-22 08:19 UTC | DATA snapshot; dated, not a live KPI |

## Changes since the 2026-08-16 audit

The old audit predates eight commits that introduced the production Control Center and data plane. Current production adds:

- `/admin` client UI with server-authorized API calls and noindex headers.
- `backend/app/admin.py` with login/logout/session authorization, dashboard, user, recognition, artwork, museum, acquisition, system and CSV endpoints.
- `product_events` first-party event ingestion with persistent `anonymous_id`, tab-scoped `session_id`, museum/artwork/recognition dimensions and coarse device/acquisition fields.
- admin session/login-attempt tables, PBKDF2 password verification, hashed cookie tokens, hashed IP login throttling and seven-day sessions.
- Active/activation/funnel/retention/recognition/catalog-health definitions and QA exclusion using `properties.internal_test`.
- per-recognition `recognition_attempt_id` generated in the browser and attached through result events.
- server-side identityless recognition operations stored for diagnosis and explicitly excluded from visitor KPIs.
- current Fly v43 and Vercel deployment, replacing the old v37 snapshot.

No country/collection entity, generic onboarding manifest, migration framework, event authentication, or global recognition configuration was added.

## Ten executive answers

### 1. What is ELYIO today?

ELYIO is a France-oriented, multi-museum PWA and public SEO site with a FastAPI/Postgres recognition backend. It has 12 curated museums, AI-guide behavior for the wider Muséofile directory, a two-stage museum-scoped recognition system, visitor game/value/share flows, first-party product analytics, and an authenticated founder Control Center.

### 2. What already scales?

Museum and artwork foreign keys, versioned catalog membership, static public pages, anonymous identity, event dimensions, and museum-scoped candidate queries are multi-museum-capable. Stateless Vercel/Fly application deployment can scale horizontally subject to DB and external AI capacity.

### 3. What remains Louvre/Paris-specific?

Catalog-version configuration is a Python map of ten museum IDs; the open-recognition prompt special-cases Louvre/Orsay/Orangerie; Louvre has a dedicated image-reference table and explicit asset quarantine; admin catalog health exposes a Louvre-only block; museum ordering and homepage copy privilege Paris/Louvre/Orsay/Orangerie; EUR/French public-collection text and exactly three locales are embedded in frontend logic.

### 4. Can another Paris museum be added?

**PARTIAL/mostly yes.** A Muséofile museum row already exists and artwork/catalog data can be imported. Clean curated activation still requires code/config for catalog version, SEO content, recognition policy, images, locale copy and benchmark evidence.

### 5. Can another European city be added?

**PARTIAL.** City is data, but homepage copy/search prioritization and curated SEO content assume Paris/France. No country dimension exists, catalog source tooling is museum-specific, and currency/legal copy is France-oriented.

### 6. Can another country be added?

**NO, not cleanly.** It can be forced with custom rows/scripts, but country/institution/collection modeling, source adapters, rights policy, locale registry, catalog activation and generic recognition configuration require architectural work.

### 7. Could National Gallery London be added now?

**PARTIAL.** A pilot could be built by custom import plus backend/frontend configuration, but not by data/config alone. Mandatory work: institution/country data, National Gallery source adapter and rights review, stable identities/memberships, image assets, catalog-version/recognition policy, English museum/SEO content, benchmarks, admin validation and production smoke. See the onboarding playbook.

### 8. What are P0 blockers?

1. Production source is not in `origin/main`, preventing reproducible governance/rollback.
2. There is no first-class country/institution/collection model or generic museum configuration contract before another country.
3. Public `/v1/events` accepts arbitrary/spoofable events and identities; founder metrics are not integrity-protected.

### 9. What breaks first at scale?

At 100k DAU, synchronous per-event inserts, unbounded raw event retention, repeated dashboard scans/group-bys, and synchronous multi-call OpenAI recognition become the first likely pressure points. At million-artwork candidate universes, loading/ranking a full museum catalog in Python per scan is unacceptable. These are architectural projections, not measured capacity claims.

### 10. What should be built next?

Build one **Global Institution Configuration & Trusted Analytics block**: restore production source to reviewed `main`; add Country/Institution/Collection plus DB-backed catalog/recognition configuration; harden/version event ingestion and identity linkage; implement a migration ledger. Use National Gallery London as a paper/fixture acceptance test, not yet a production import.

## Old audit section disposition

Every numbered section in the 2026-08-16 audit was reassessed:

| Old section | Disposition | Reason |
|---:|---|---|
| 0 Methodology | HISTORICAL ONLY | Old SHA/deploy evidence. |
| 1 Summary | PARTIALLY OUTDATED | Core loop remains; admin/analytics absent. |
| 2 Production snapshot | OBSOLETE | Deployments v37/old Vercel replaced. |
| 3 Repository map | PARTIALLY OUTDATED | Admin/migration/tests added. |
| 4 Frontend architecture | STILL CURRENT | Public/app boundary remains; add admin route. |
| 5 Routes | PARTIALLY OUTDATED | Admin and event APIs added. |
| 6 PWA | STILL CURRENT | No material code change after baseline. |
| 7 Museum directory | STILL CURRENT | Counts remain 1,222/12 on audit date. |
| 8 Artwork model | PARTIALLY OUTDATED | Admin health/readiness now operationally consumed. |
| 9 Recognition | PARTIALLY OUTDATED | Pipeline remains; durable server/client analytics added. |
| 10 Generated experience | STILL CURRENT | No material change. |
| 11 Images | STILL CURRENT | Provenance gaps remain. |
| 12 Value Engine | STILL CURRENT | No V4 change. |
| 13 Scale engine | STILL CURRENT | No change. |
| 14 Modes | STILL CURRENT | No change. |
| 15 Visit state | PARTIALLY OUTDATED | Recognition attempt/event identity added. |
| 16 Missions | STILL CURRENT | No change. |
| 17 Achievements | STILL CURRENT | No change. |
| 18 Favorites | STILL CURRENT | No change. |
| 19 Progress | STILL CURRENT | Added first-party event transport only. |
| 20 Recap | STILL CURRENT | Added first-party event transport only. |
| 21 Trophy | STILL CURRENT | No change. |
| 22 Share | STILL CURRENT | Events now first-party too. |
| 23 Audio | STILL CURRENT | No change. |
| 24 Localization | PARTIALLY OUTDATED | Global constraints now explicitly audited. |
| 25 SEO | STILL CURRENT | `/admin` added to noindex. |
| 26 Sitemaps | STILL CURRENT | 393 current URLs verified previously; not changed by admin. |
| 27 Search engines | HISTORICAL ONLY | Provider console status remains external. |
| 28 Structured data | STILL CURRENT | No change. |
| 29 Analytics | OBSOLETE | First-party event store/admin metrics now exist. |
| 30 Auth | PARTIALLY OUTDATED | Visitor auth unchanged; separate admin auth added. |
| 31 Backend | PARTIALLY OUTDATED | `admin.py` and three tables added. |
| 32 API | OBSOLETE | 13 admin/event paths added. |
| 33 Diagrams | PARTIALLY OUTDATED | Missing admin/event data plane. |
| 34 Media | STILL CURRENT | No material change. |
| 35 Performance | STILL CURRENT | Still no current measured baseline. |
| 36 Security/privacy | OBSOLETE | Admin/event surfaces materially expand it. |
| 37 Environment | OBSOLETE | Admin variables added. |
| 38 Commands | PARTIALLY OUTDATED | Admin tests/migration added. |
| 39 Deployment | OBSOLETE | v43/current source divergence. |
| 40 Verification | PARTIALLY OUTDATED | Must include admin/events/migration. |
| 41 Rollback | PARTIALLY OUTDATED | Event/schema effects need recovery. |
| 42 Tests | PARTIALLY OUTDATED | `test_admin_panel.py` added. |
| 43 Phase2D | HISTORICAL ONLY | Still unmerged research; not production. |
| 44 Git state | OBSOLETE | Branch advanced and now deployed. |
| 45 Local artifacts | STILL CURRENT | Categories unchanged. |
| 46 Invariants | PARTIALLY OUTDATED | Analytics/admin/global invariants added. |
| 47 Limitations | PARTIALLY OUTDATED | New integrity/scale risks. |
| 48 Debt | OBSOLETE | Replaced by current register. |
| 49 Dormant code | STILL CURRENT | Same broad research/legacy classes. |
| 50 Status matrix | OBSOLETE | Admin/analytics status changed. |
| 51 Onboarding | PARTIALLY OUTDATED | New canonical reading path. |
| 52 Safe change matrix | PARTIALLY OUTDATED | Add admin/events/data-plane tests. |
| 53 User flows | PARTIALLY OUTDATED | Identity/events now accompany flow. |
| 54 Ownership | OBSOLETE | Missing new files. |
| 55 Summary | HISTORICAL ONLY | Old snapshot only. |

## Old unresolved items re-evaluated

| # | Item | Status | Owner/manual verification | Global blocker? |
|---:|---|---|---|---|
| 1 | Vercel Git metadata | RESOLVED operationally by timestamp/source match; SHA embedding still absent | Vercel project metadata | Governance issue, yes with branch divergence |
| 2 | Fly image Git SHA | STILL UNRESOLVED | Build pipeline/image labels should embed SHA | Yes for reproducible rollback |
| 3 | Production secret values | NO LONGER RELEVANT to docs | Vercel/Fly secret stores; values must remain uninspected | No, presence smoke is enough |
| 4 | Google Search Console | STILL UNRESOLVED | Google Search Console owner | No for product architecture |
| 5 | Bing Webmaster | STILL UNRESOLVED | Bing Webmaster owner | No |
| 6 | PostHog delivery/config | PARTIALLY RESOLVED; code and US host confirmed, console retention unknown | PostHog project admin | Privacy/measurement follow-up |
| 7 | Live recognition request | STILL UNRESOLVED in this audit | Controlled benchmark with consented fixtures | Yes before new museum activation |
| 8 | Physical-device PWA | STILL UNRESOLVED | iOS/Android device matrix | No before data architecture; yes before launch QA |
| 9 | Lighthouse/CWV | STILL UNRESOLVED | PSI/CrUX or repeatable lab | P2, not country blocker |
| 10 | Provider limits/log retention/rollback permissions | STILL UNRESOLVED | Fly/Vercel/OpenAI/PostHog/Supabase owners | Partly; retention/security must be resolved before scale |

Resolved: 1; partially resolved: 1; no longer relevant: 1; still unresolved: 7.
