# AGENTS.md

ELYIO (formerly AURA) — museum artwork recognition app. Next.js 16 frontend in `web/`,
FastAPI backend in `backend/`, Supabase Postgres, OpenAI vision. Production: `www.elyio.co`
(Vercel) + Fly app `elyio-api` (region `cdg`).

## Read this first

- `docs/README.md` is the canonical entry point; `docs/architecture/REPOSITORY_MAP.md` and
  `docs/architecture/ARCHITECTURAL_INVARIANTS.md` list rules every change must preserve.
- Root `README.md` (Russian) describes the early MVP and is partly stale (e.g. claims backend
  runs in-memory and mocks recognition without a key — both no longer true). Trust code/docs/.
- `frontend/` (vanilla PWA), `aura-mvp/`, root `main.py`, and the `AURA_MVP_*` spec files are
  legacy. `aura-mvp/` and root `main.py` are gitignored duplicates — never edit them.
- `android/` is a Bubblewrap-generated TWA (Gradle) pointing at `www.elyio.co/visit`; see
  `docs/android/`. It is currently untracked.

## Backend (`backend/`)

- Python 3.11. Use `.venv-elyio` (has pytest); the older `venv/` does not.
- `.env` lives at the **repo root** (`.env.example` there); `backend/app/main.py` and scripts
  load it via python-dotenv.
- `DATABASE_URL` is required for almost every endpoint — there is no in-memory fallback,
  `get_db()` returns 503 without it. `OPENAI_API_KEY` is required for `/v1/recognize`; the
  random mock only activates with `ALLOW_RECOGNITION_MOCK=true` (dev only).
- Run locally on **8090** (`uvicorn app.main:app --reload --port 8090` from `backend/`);
  `web/lib/api.ts` defaults to that. The Dockerfile/Fly serve on 8080.
- `app/main.py` is a ~2900-line monolith holding all public routes; only `app/admin.py` is a
  separate `APIRouter`. Imports are `backend.app.*` (namespace package from repo root).
- Tests (unittest-style, run with pytest, pure unit on in-memory SQLite, no network/env needed):
  ```
  .\.venv-elyio\Scripts\python.exe -m pytest backend/tests            # from repo root
  .\.venv-elyio\Scripts\python.exe -m pytest backend/tests/test_admin_panel.py -k <name>
  ```
  No `conftest.py`, `pytest.ini`, or Python lint/format config exists. No CI runs tests.
- Migrations: `backend/migrations/NNNN_snake_case.sql`, applied by the checksummed ledger
  `python scripts/migrate.py status|baseline|apply` (from `backend/`, needs `DATABASE_URL`).
  Never edit an applied migration — add a new ID. A Fly deploy does **not** run migrations
  (no `release_command`). Older `backend/scripts/*_migration.sql` files are outside the ledger.
- `backend/scripts/` (~100 files, no README) are museum importers, benchmarks and
  DB/prod tooling. Many call paid OpenAI/provider APIs or mutate the production DB. Never run
  them as tests; prefer their dry-run modes; `APPLY` modes are audited and idempotent by design.

## Frontend (`web/`)

- Next.js 16 App Router, React 19, Tailwind v4, `@/*` -> `web/*` alias. Copy
  `.env.local.example` to `.env.local` (`NEXT_PUBLIC_BACKEND_URL`).
- `public/sw.js` is **generated and gitignored**: `predev`/`prebuild` run
  `scripts/stamp-service-worker.mjs` over `sw-template.js`. Edit the template, not the output.
- `proxy.ts` is the Next 16 middleware replacement (canonical-host redirect). `next.config.ts`
  holds the CSP, security headers, noindex rules, and image remote patterns — security-critical.
- No jest/vitest. `npm run test:*` are plain `node scripts/*.mjs`:
  - Offline: `test:value`, `test:result`, `test:scale`, `test:comparison-variety`,
    `test:comparison-v22`, `test:visit`.
  - Need Playwright (present in node_modules but not in package.json) and a dev server on
    `:3100` (override via `*_TEST_URL` env): `test:analytics`, `test:landing-cta`,
    `test:direct-scanner`.
  - `test:pwa` drives headless Chrome (`CHROME_PATH`) against **live** `www.elyio.co` unless
    `--url`/`PWA_CHECK_URL` is given.
- Verify frontend changes with `npm run lint` then `npm run build`.

## Product/domain rules agents most often break

- UI locales are fixed to EN/FR/zh-Hans (`web/lib/i18n.ts`, `types.ts`).
- Never fabricate monetary estimates or scale comparisons; Value Engine is EUR-grounded and
  LOW-confidence AI values never enter totals. Missing data is "unavailable", not zero.
- Recognition: do not lower confidence thresholds for recall; verifier `NEEDS_CONFIRMATION`
  is never promoted to auto-accept; catalog grounding is enrichment, not a gate.
- Unknown/misconfigured institution fails closed — never broaden candidate lookup to all artworks.
- QA/internal traffic must never enter founder metrics; admin auth is server-side only.

## Repo hygiene

- Working tree routinely holds uncommitted work plus scratch: `.tmp/`, `*.err`/`*.out`,
  `backups/` (ignored via `.git/info/exclude`), `exports/`, `backend/.reference_cache/`.
  Stage only intended files; never bulk-add.
- Production deploys only from reviewed `main` (or a documented release commit). See
  `docs/operations/DEPLOYMENT_RUNBOOK.md` for the additive-DB -> backend -> frontend order.
