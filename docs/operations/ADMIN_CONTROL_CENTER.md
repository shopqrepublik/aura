# Admin Control Center

Status: LIVE at `/admin`; backend Fly v43.

## Architecture

`web/app/admin/AdminApp.tsx` is a client UI. It has no metric computation or credential secret; it calls `https://api.elyio.co/v1/admin/*` with `credentials: include`. The backend `backend/app/admin.py` authenticates every read/export endpoint through `require_admin`.

## Authentication

- Login: configured single `ADMIN_EMAIL` plus PBKDF2-SHA256 `ADMIN_PASSWORD_HASH`.
- Throttle: failed attempts by email or peppered IP hash, default 8 in 15 minutes.
- Session: random 32-byte URL-safe token; only SHA-256 token hash stored.
- Cookie: configurable name, HttpOnly, Secure in production, SameSite=Lax, path `/`, default seven days.
- Every authorized request updates `last_seen_at`; logout revokes row and deletes cookie.
- Live unauthenticated `/v1/admin/me` and `/dashboard` return 401. `/admin` returns noindex/no-follow.

Risk: code contains a default admin email and fallback password hash and a default IP pepper. Production must always override these; source must not be treated as a secret store. No plaintext password is documented here.

## Current views/endpoints

| UI area | Backend source |
|---|---|
| Overview/users/activation | `/v1/admin/dashboard` |
| Funnel/retention | dashboard raw-event aggregations |
| Recognition/failures | dashboard + `/v1/admin/recognition/failures` |
| Artwork health/search | `/v1/admin/artworks` |
| Museums | `/v1/admin/museums` |
| Catalog readiness/provenance gaps | `/v1/admin/catalog` |
| Acquisition | `/v1/admin/acquisition` |
| System | `/v1/admin/system` |
| CSV | `/v1/admin/export/{failures|museums|other→artworks}` |

## Data cautions

Tracking starts 2026-08-20. Current success/failure metrics can double-count companion events; Total/New/Returning/Session definitions have documented limitations. Recognition failure images are unavailable. Country/city are generally null because client and server do not derive them. Always read `analytics/METRIC_DEFINITIONS.md` before interpreting a number.

## Operational checks

1. Verify `/admin` 200 + noindex.
2. Verify unauthenticated admin API 401.
3. With authorized operator, verify `/me`, dashboard period and data-gap banner.
4. Confirm migration tables/indices exist.
5. Verify QA test session is excluded.
6. Log out and confirm session is revoked.

Never paste credentials, cookie values, event rows containing identifiers, or exported user timelines into documentation/issues.
