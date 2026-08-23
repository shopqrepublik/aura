# Cost Architecture

Status: CURRENT cost drivers; no provider prices or measured totals asserted.

## Variable drivers

- OpenAI Stage 1 on every recognition attempt.
- Stage 2 top-N or asset verification; runner-up can add another call.
- Indicative-value OpenAI calls, partially in-process cached.
- Image fetch/resize/egress and Fly disk/cache misses.
- PostgreSQL per-event writes, raw retention and admin scans.
- PostHog duplicate event transport and person/event retention.
- Vercel build/static outputs, bandwidth and image optimization.
- Static audio generation/storage/egress.

## Missing visibility

No event stores AI model, tokens, provider request ID, cache hit, number of Stage 2 calls or estimated cost per recognition. No cost by museum/catalog/active user. Event ingestion itself can be spammed.

## Target controls

Record safe per-attempt model/call/cache/latency counters tied to attempt ID; attribute costs by institution/catalog and internal flag; enforce upload/event quotas; monitor cost per attempt/success/active visitor; define cache and retry budgets; never degrade recognition safety only to lower synthetic cost.
