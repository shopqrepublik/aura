# Testing

## Current suites

- Frontend: `npm run lint`, `npm run build`, `test:result`, `test:value`, `test:scale`, `test:visit`, `test:pwa`.
- Backend: `backend/tests/test_admin_panel.py`, catalog regression/parity and script-specific validators.
- Recognition: controlled benchmark scripts/fixtures; many are Louvre-specific and can invoke paid/network services.

## Admin test coverage

`test_admin_panel.py` exercises password verification, internal event exclusion, identityless recognition exclusion, identified recognition metrics and catalog image/readiness distinctions using SQLite fixtures. It does not prove browser cookie/CORS behavior, production migration, scale, event abuse resistance or correct deduplication of full client event sequences.

## Required additions

1. Event-contract validation/limits/spoof tests.
2. Authenticated first-party identity merge tests.
3. Recognition attempt dedupe tests containing started/completed/scan_success and failure companions.
4. Retention maturity and ordered-funnel tests.
5. Catalog fail-closed behavior when version config/membership is missing.
6. Generic second-country onboarding fixture with no Louvre/Paris strings.
7. Migration up/down/idempotence/ledger tests.
8. Admin auth cookie/CORS/CSRF/rate-limit integration tests.
9. Physical iOS/Android PWA matrix and browser share/camera cases.

Never run production mutation/import scripts as tests. Every network/cost benchmark must identify fixture rights, model and target environment.
