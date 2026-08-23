# Troubleshooting

## Incident first response

Record time/UTC, deployment IDs, affected route/museum/artwork, response status and whether traffic is QA. Do not collect raw visitor images or secrets in tickets.

## Frontend unavailable or stale

Check Vercel deployment/aliases, canonical host, build logs and CSP. For stale PWA, inspect active/waiting worker and cache version; do not force users to clear all data unless local visit loss is acceptable.

## API unhealthy

Check Fly release/image/machine states and `/health`. Auto-stopped machines can add cold start. Verify `DATABASE_URL`/OpenAI variable presence by configuration status only. Roll back image if code regression; DB migration/data needs separate recovery.

## Admin login fails

Unauthenticated `/me` should be 401. A 503 login means schema missing. A 429 means the email/IP failure window is saturated. Verify production overrides for admin email/hash/pepper without printing them. Confirm cookie is Secure/HttpOnly and CORS origin is `www.elyio.co`.

## Dashboard shows zero/unexpected values

Check `product_events` table and tracking availability date. Verify event identity exists and internal flag. Zero before 2026-08-20 is not evidence of no users. Check documented double-count/split-identity defects before interpreting recognition/Total Users.

## Recognition fails

Differentiate validation, DB catalog unavailable, OpenAI key/provider error, no-match, asset fetch rejection and frontend network error. Inspect admin failure rows/logs without raw images. Verify selected museum, active membership/version, candidate count, readiness/rights, and model/threshold. Reproduce only with approved benchmark fixtures.

## Wrong artwork

Immediately verify museum isolation and source identity. Disable membership if user harm is material. Compare top candidates, Stage 1 observations and Stage 2 decision; do not “fix” by lowering thresholds globally or inserting title aliases without benchmark regression.

## Events missing

Check browser storage availability, beacon/fetch network/CSP/CORS and `/v1/events`. PostHog and first-party delivery are independent. Server events are identityless and cannot prove client delivery. Never resend every historical event without idempotent original IDs.

## Catalog/image issue

Distinguish presentation, recognition and source-reference roles. For Louvre, do not fetch metadata-only image references or enable quarantined RecognitionAssets. Use membership deactivation as immediate rollback.
