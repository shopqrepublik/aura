# Analytics Architecture

Status: CURRENT first-party + PostHog dual transport.

## Identity and transport

`web/lib/analytics.ts` creates:

- `anonymous_id`: UUID-like value in `localStorage` key `elyio-anonymous-id`; persists for the browser origin until cleared.
- `session_id`: value in `sessionStorage` key `elyio-session-id`; tab/session-storage lifetime, not a 30-minute inactivity session.
- `recognition_attempt_id`: generated in `app-state.ts` for each scan and attached to browser recognition/result events.
- `internal_test`: set in sessionStorage when URL query `elyio_internal_test=1`; copied into event `properties`.

Every `track()` sends a first-party JSON envelope to `POST /v1/events` via `sendBeacon` or keepalive fetch. If PostHog is configured, it also sends the named event there. PostHog autocapture/pageviews/replay/heatmaps/dead clicks/performance are disabled.

## First-party storage

`product_events` stores event ID/name/time; user/anonymous/session/museum/artwork/recognition IDs; JSON properties; acquisition/referrer/UTM; country/city/language/device/OS/browser/user-agent/path; created time. Event ID is idempotent. Current endpoint is public and accepts arbitrary names, identities, timestamps and properties; it does not authenticate or sign browser events.

Although `user_id` exists, the client payload never populates it. `identify(user.id)` affects PostHog only. Authenticated visitors therefore remain anonymous in first-party events and can also exist as a registered `users` row, producing split/double-counted identity.

## Server recognition events

`backend/app/main.py` writes `recognition_started`, `recognition_completed`, and `recognition_failed` through `record_product_event_from_server`. These rows have museum/resolved artwork/properties but no anonymous/session/attempt identity. Admin retains them as operational telemetry and excludes them from visitor KPIs.

## Internal QA exclusion

Admin query helpers exclude `properties.internal_test=true` by default. This is correct in intent but client-asserted: a QA visitor can omit the flag and a public caller can set it. There is no trusted QA token/IP/account policy. Historical server smoke calls are identityless and excluded from visitor recognition KPIs, but may remain visible operationally.

## Data availability

Production first-party history starts 2026-08-20 (`TRACKING_AVAILABLE_SINCE`); the observed first event was 2026-08-20 23:14 UTC. Missing earlier analytics means unavailable, not zero. PostHog can contain earlier events, but provider history/retention was not queried in this audit.

## Admin consumption

`backend/app/admin.py` derives users, activation, funnel, retention, recognition, catalog health, museums, top artworks, acquisition, device/language/country segments and system timestamps on request. Most aggregations scan/group raw events; no rollup/materialized aggregate exists.

## Integrity priorities

1. Add schema-versioned allowlisted event contracts and payload limits.
2. Issue/sign anonymous identity and internal-test state server-side or at a trusted edge.
3. Pass authenticated user linkage and merge aliases deterministically.
4. Deduplicate recognition success by `recognition_attempt_id`.
5. Add retention/partitioning and daily rollups before high volume.
