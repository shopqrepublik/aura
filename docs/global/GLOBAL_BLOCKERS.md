# Global Blockers

Effort: S/M/L/XL only; no hour estimates.

| Priority | Issue/evidence | Consequence | Affected | Approach | Effort |
|---|---|---|---|---|---|
| RESOLVED Block 1 | Production `5c5ac7e` was not reachable from `origin/main` | Reviewed production commits are reconciled and releases expose source metadata | Git, Vercel, Fly | Preserve reviewed-main/release-commit rule | M |
| RESOLVED Block 1 | No country/institution/collection configuration model | Country, compatible Institution, optional Collection and Institution Profile are additive schema | models, catalog, migration | Populate via onboarding workflow; do not bypass profiles | L |
| RESOLVED Block 2 | `/v1/events` trusted arbitrary public event/identity/time/internal flag | Allowlist, schema v2, server time/auth/QA, dimensions, limits/idempotency now protect founder facts | analytics.ts, admin.py, ProductEvent | Preserve contract and adversarial tests | L |
| RESOLVED Block 1 | Catalog activation/recognition policy was a museum-ID Python map; fallback exposed broader rows | Profile-backed explicit universe/policy; missing/empty config fails closed | catalog.py, main.py, institution_profiles | Preserve fail-closed tests | L |
| RESOLVED Block 2 | First-party anonymous/authenticated identity was split | Verified bearer identity, identity links and session bindings correlate without rewriting history | analytics.ts, useAuth, ingestion | Preserve anti-reassignment tests | M |
| RESOLVED Block 2 | Recognition metrics double-counted companion events | One authoritative terminal `recognition_attempts` row now supplies KPI | main.py, admin.py, tests | Preserve end-to-end attempt ID | M |
| P1 | Presentation/source/recognition provenance incomplete and provider-specific | Rights/identity risk for new sources | models, catalog, proxy/importers | Generic media/source/derivative provenance model | L |
| P1 | Fixed three locales + Paris/France/legal/EUR copy | Incorrect London/global UX | types/i18n/api/value/SEO | Locale registry; jurisdiction/currency content policy | L |
| P2 | Full museum catalog materialized/ranked per recognition | Large catalogs raise DB/CPU/latency | catalog.py/main.py | Indexed shortlist/search, bounded candidates, cache | L |
| P2 | Synchronous raw event inserts and request-time dashboard aggregates | DB contention/slow admin at 100k DAU | events/admin/DB | Batch/queue, partition/retention, daily rollups | L |
| RESOLVED Block 1 | No migration ledger | Checksummed `schema_migrations` plus attempt history now authoritative | backend/migrations, scripts/migrate.py | Run status/baseline/apply in deploy order | M |
| P2 | Admin single account/default fallback credentials/no roles | Operational/security scaling limit | admin.py/models/UI | Fail-closed secrets, IdP/MFA, RBAC/audit log | L |
| P2 | No defined visitor-image/event retention policy | Privacy/storage operations uncertain | browser state, DB, providers | Inventory, TTL/deletion controls, provider review | M |
| RESOLVED Block 2 | Recognition correlation/latency incomplete | Attempt UUID, visitor/session/institution/artwork/outcome/latency now persist end-to-end | client, recognize, attempts | Preserve contract | M |
| P2 | Event limiter is process-local and raw event/admin aggregation is synchronous | Multi-instance floods and large history can stress DB/admin | events/admin/DB | Edge/shared quota; partition/retention and rollups when justified | L |
| P3 | PWA physical-device matrix/performance baseline absent | Platform regressions discovered late | SW/manifest/QA | Device matrix and repeatable budgets | M |
| P3 | Legacy AURA/preview/Louvre tooling near production source | Engineer confusion | root/frontend/previews/scripts | Mark/archive after provenance review | S |

P0 means before another country; P1 before 10 repeatably onboarded curated museums; P2 before serious scale; P3 optimization/operational maturity.
