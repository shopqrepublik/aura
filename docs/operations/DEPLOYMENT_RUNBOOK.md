# Deployment Runbook

Status: CURRENT architecture; documentation does not authorize deployment.

## Current production

- Frontend: Vercel deployment `dpl_48JY2fJoKBB3ZWEUgVKPMRkag2Vw`, canonical `www.elyio.co`.
- Backend: Fly release v43 `nRqjnzJmmaOq8HObg8PVKNL5`, image `registry.fly.io/elyio-api:deployment-01M0GVRBB3XN0AFMEFY5STJBHQ`.
- DB: Supabase PostgreSQL; admin/event migration tables verified.
- Source: production aligns to `5c5ac7e`, but `origin/main` is still `3adf605`. Correct this through reviewed Git governance before the next product deployment.

## Preflight

1. Clean working tree; reviewed deploy commit reachable from intended mainline.
2. Record current Vercel deployment, Fly release/image/machines and health.
3. Classify change as frontend/backend/schema/data/docs.
4. Run scoped tests and build.
5. For schema: backup/recovery plan, idempotent migration, read-only precheck, apply once, verify columns/indices, record a migration ledger entry (currently missing).
6. Verify required variable names, never print values.

## Frontend

From `web/`: `npm ci`, regression tests, `npm run build`. Vercel build stamps `public/sw.js`. After deployment verify aliases, `/admin` noindex, `/visit`, locale pages, sitemap, CSP and service-worker update behavior.

## Backend

Build/deploy using `backend/Dockerfile` and `backend/fly.toml`; verify immutable image/release and both machine versions. Health check `https://api.elyio.co/health`; OpenAPI must contain expected paths. A backend deploy does not apply SQL migration automatically.

## Schema

`backend/scripts/admin_panel_migration.sql` is idempotent `CREATE TABLE/INDEX IF NOT EXISTS`, and is applied in production. There is no Alembic/schema-version table; until one exists, operators must record exact SQL SHA/date/result externally. Never infer migration completion solely from backend release success.

## Compatibility order

- Additive DB → backend tolerant of absent/new schema → frontend.
- Contract rename/removal: deploy backward-compatible backend, migrate callers, then remove later.
- Event contract: accept old/new version during transition and keep metric definition explicit.

## Rollback

Promote prior Vercel deployment and redeploy prior Fly image. Schema/event data are not reverted by code rollback. Revoke new catalog membership rather than delete data. Service-worker clients can retain old assets until activation/reload. Verify smoke checklist after rollback.

## Current governance blocker

Do not normalize the branch discrepancy by force-pushing or undocumented deploys. Create a reviewed integration path that preserves the eight production commits, tests them, merges into `main`, and embeds Git SHA in Vercel/Fly release metadata.
