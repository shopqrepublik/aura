# Global Blockers

Effort: S/M/L/XL only; no hour estimates.

| Priority | Issue/evidence | Consequence | Affected | Approach | Effort |
|---|---|---|---|---|---|
| P0 | Production `5c5ac7e` not reachable from `origin/main` | Unreproducible release/governance/rollback | Git, Vercel, Fly | Reviewed integration; embed source SHA | M |
| P0 | No country/institution/collection configuration model | Another country becomes strings/special cases | models, museum API/UI/SEO | Add Country/Institution/Collection baseline migration/API | L |
| P0 | `/v1/events` trusts arbitrary public event/identity/time/internal flag | Founder metrics can be poisoned; storage abuse | analytics.ts, admin.py, ProductEvent | Versioned allowlist, limits, trusted identity/internal classification, rate control | L |
| P1 | Catalog activation/recognition policy is museum-ID Python map; fallback exposes all rows | Every museum needs code; drafts can become candidates | catalog.py, main.py, env | DB/config visitor catalog + recognition profile; fail closed | L |
| P1 | First-party user identity is not linked to Supabase user | Double/split users, bad retention | analytics.ts, useAuth, ingestion | Signed user token or server alias/merge | M |
| P1 | Recognition success/failure metrics double-count companion events | Success rate/funnel untrustworthy | admin.py, event contract/tests | Deduplicate terminal outcome by attempt ID | M |
| P1 | Presentation/source/recognition provenance incomplete and provider-specific | Rights/identity risk for new sources | models, catalog, proxy/importers | Generic media/source/derivative provenance model | L |
| P1 | Fixed three locales + Paris/France/legal/EUR copy | Incorrect London/global UX | types/i18n/api/value/SEO | Locale registry; jurisdiction/currency content policy | L |
| P2 | Full museum catalog materialized/ranked per recognition | Large catalogs raise DB/CPU/latency | catalog.py/main.py | Indexed shortlist/search, bounded candidates, cache | L |
| P2 | Synchronous raw event inserts and request-time dashboard aggregates | DB contention/slow admin at 100k DAU | events/admin/DB | Batch/queue, partition/retention, daily rollups | L |
| P2 | No migration ledger | Schema state relies on inspection/operator memory | backend/scripts/DB/deploy | Adopt Alembic or equivalent version table | M |
| P2 | Admin single account/default fallback credentials/no roles | Operational/security scaling limit | admin.py/models/UI | Fail-closed secrets, IdP/MFA, RBAC/audit log | L |
| P2 | No defined visitor-image/event retention policy | Privacy/storage operations uncertain | browser state, DB, providers | Inventory, TTL/deletion controls, provider review | M |
| P2 | Recognition correlation/latency incomplete | Hard to diagnose funnel/cost/quality | client request, backend events | Pass attempt ID and server timing end to end | M |
| P3 | PWA physical-device matrix/performance baseline absent | Platform regressions discovered late | SW/manifest/QA | Device matrix and repeatable budgets | M |
| P3 | Legacy AURA/preview/Louvre tooling near production source | Engineer confusion | root/frontend/previews/scripts | Mark/archive after provenance review | S |

P0 means before another country; P1 before 10 repeatably onboarded curated museums; P2 before serious scale; P3 optimization/operational maturity.
