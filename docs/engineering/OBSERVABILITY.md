# Observability

Status: CURRENT.

## Available signals

- Fly `/health`, release/image/machine state and application logs.
- Vercel deployment/build/runtime logs and live route headers.
- First-party `product_events`, admin dashboards/failure CSV/system timestamps.
- PostHog explicit product events.
- Recognition structured logs and identityless server events.
- Catalog health/readiness/image-gap aggregation.

## Gaps

- No documented SLO/alert thresholds/on-call owner.
- No distributed trace/correlation from browser attempt ID into backend/OpenAI.
- Browser events do not measure latency; admin p50/p95 may be empty.
- No per-model/token/cost metrics.
- No event ingestion failure/drop/lag metric.
- No DB pool/query latency, table growth or migration-version dashboard.
- Server recognition logs before 2026-08-20 are not durable analytics.
- Frontend/backend release SHA variables are not reliably embedded/displayed.

## Minimum next observability block

Pass `recognition_attempt_id`, record server start/end/model/calls/status safely, add event-ingest counters and daily DB/table/query health, embed release SHA, and alert on health/error/cost/latency/success changes using corrected deduplicated metrics.
