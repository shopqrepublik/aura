# Repository Map

Status: CURRENT.

| Path | Responsibility | Production status |
|---|---|---|
| `web/app/[locale]/` | Static localized SEO routes | LIVE |
| `web/app/visit/` | Noindex visitor application entry | LIVE |
| `web/app/admin/` | Control Center UI/login | LIVE since 2026-08-21 |
| `web/components/ElyioApp.tsx` | Screen orchestration, app/session event bootstrapping | LIVE |
| `web/components/screens/` | Home/camera/catalog result/uncataloged/progress/recap | LIVE |
| `web/lib/analytics.ts` | Anonymous/session IDs, internal-test flag, first-party and PostHog transport | LIVE, metric-critical |
| `web/lib/app-state.ts` | Visit persistence, recognition event chain, sighting/favorite/game state | LIVE, product-critical |
| `web/lib/api.ts` | Backend contracts and catalog response mapping | LIVE |
| `web/lib/i18n.ts`, `types.ts` | Fixed three-locale UI/type contract | LIVE, global constraint |
| `web/lib/seo-content.ts` | Explicit curated SEO museum/artwork surface | LIVE, static |
| `web/sw-template.js`, `public/manifest.json` | PWA cache/install contract | LIVE |
| `web/next.config.ts` | CSP, canonical redirect, noindex headers, image policy | LIVE/security-critical |
| `backend/app/main.py` | FastAPI app, recognition/value/image/public/visit endpoints | LIVE, large monolith |
| `backend/app/admin.py` | Event ingestion, admin auth and all metrics/control APIs | LIVE since 2026-08-21 |
| `backend/app/models.py` | SQLAlchemy canonical current schema | LIVE |
| `backend/app/catalog.py` | Catalog membership/version/readiness and presentation mapping | LIVE |
| `backend/app/auth.py` | Supabase visitor JWT verification | LIVE for authenticated visit APIs |
| `backend/app/db.py` | SQLAlchemy engine/session | LIVE |
| `backend/scripts/admin_panel_migration.sql` | Idempotent SQL creation for three admin/event tables | APPLIED; no ledger |
| `backend/tests/test_admin_panel.py` | Admin metric/auth/catalog tests | CURRENT test |
| `backend/scripts/louvre_*.py` | Louvre import/research/benchmark/Phase tooling | MIXED; inspect before use; not request runtime |
| `exports/`, `backups/`, venv/cache output | Local evidence/generated material | NOT runtime; do not bulk commit |
| root `frontend/`, `aura-mvp/`, AURA specs | Historical prototypes/specification | LEGACY |

## Dependency direction

Frontend UI calls `web/lib`; `web/lib/api.ts` calls FastAPI. FastAPI routes call `catalog.py`, SQLAlchemy models/DB, OpenAI and image sources. Admin UI calls only protected admin APIs except login. Avoid reverse dependencies from backend into frontend datasets or from runtime into ignored exports.

## Change-risk map

- Recognition: `main.py`, `catalog.py`, models, API mapper, `app-state.ts`, benchmarks.
- Analytics: `analytics.ts`, every `track()` producer, `ProductEvent`, `admin.py`, migration/tests.
- Catalog onboarding: models, catalog version map, importer, membership, provenance, SEO dataset and recognition benchmark.
- Admin/security: `admin.py`, `AdminApp.tsx`, CORS/CSP, migration, tests.
