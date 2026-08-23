# Deployment Runbook

Status: CURRENT Block 1 release process.

## Current production

- Frontend: Vercel deployment `dpl_48JY2fJoKBB3ZWEUgVKPMRkag2Vw`, canonical `www.elyio.co`.
- Backend: Fly release v43 `nRqjnzJmmaOq8HObg8PVKNL5`, image `registry.fly.io/elyio-api:deployment-01M0GVRBB3XN0AFMEFY5STJBHQ`.
- DB: Supabase PostgreSQL; admin/event migration tables verified.
- Historical source discrepancy: production `5c5ac7e` was ahead of `origin/main` `3adf605`; Block 1 reconciles the reviewed production commits before deployment.
- Canonical rule: production deploys from reviewed `main` or an explicitly documented release commit reachable from it.

## Preflight

1. Clean working tree; reviewed deploy commit reachable from intended mainline.
2. Record current Vercel deployment, Fly release/image/machines and health.
3. Classify change as frontend/backend/schema/data/docs.
4. Run scoped tests and build.
5. For schema: backup/recovery plan, `python scripts/migrate.py status`, review pending checksums, apply, then verify ledger/head and diagnostics.
6. Verify required variable names, never print values.

## Frontend

From `web/`: `npm ci`, regression tests, `npm run build`. Vercel build stamps `public/sw.js`. After deployment verify aliases, `/admin` noindex, `/visit`, locale pages, sitemap, CSP and service-worker update behavior.

## Backend

Build/deploy using `backend/Dockerfile` and `backend/fly.toml`; pass `GIT_COMMIT_SHA`, UTC `BUILD_TIMESTAMP` and `DEPLOYMENT_ENV` as build args. Verify immutable image/release and machine versions. `/health` must report the expected SHA. A backend deploy does not apply SQL automatically.

## Schema

From `backend/`, load the production `DATABASE_URL` without printing it. For the first ledger adoption only, run `python scripts/migrate.py baseline`: it verifies required current tables and records `0001_production_schema_baseline` without executing historical DDL. Review `status`, then run `python scripts/migrate.py apply`. Migrations are ordered/checksummed, run transactionally, and record APPLIED/FAILED attempts. Never edit an applied migration; add a new ID. Never use schema reset against production.

## Compatibility order

- Additive DB → backend tolerant of absent/new schema → frontend.
- Contract rename/removal: deploy backward-compatible backend, migrate callers, then remove later.
- Event contract: accept old/new version during transition and keep metric definition explicit.

## Rollback

Promote prior Vercel deployment and redeploy prior Fly image. Schema/event data are not reverted by code rollback. Revoke new catalog membership rather than delete data. Service-worker clients can retain old assets until activation/reload. Verify smoke checklist after rollback.

## Institution migration verification

After Block 1 migration verify: all current `museums` rows have country/timezone/locales; each has exactly one active profile; the 10 versioned visitor catalogs resolve `ACTIVE_CATALOG`; Orsay/Orangerie resolve `INSTITUTION_ARTWORKS`; AI-guide entries resolve `NONE/UNCATALOGED_ONLY`; Louvre keeps asset substitution disabled; an unknown ID returns HTTP 409 `institution_not_ready`.
