# Scale and Performance Architecture

No measured capacity is claimed. This is code-path risk analysis.

## Scenario A — 10 museums, 100k artworks, 1k DAU

Likely viable after indexes/config cleanup. Risks: candidate query materializes all rows for a selected museum; synchronous OpenAI dominates latency/cost; event writes and admin raw aggregation are acceptable only with monitoring. Static SEO must not generate thin 100k pages.

## Scenario B — 100 museums, 1M artworks, 100k DAU

Current architecture needs changes. Full-catalog Python ranking per attempt, one transaction per event, unpartitioned raw events, request-time retention/cohort/group queries, filesystem image cache per Fly machine, single admin account and manual import scripts become operational bottlenecks. Add bounded indexed retrieval/cache, event batching/queue, partition/retention/rollups, object/CDN storage and institution-scoped tooling.

## Scenario C — global, 10M artworks, 1M DAU

Current data model and flow are not ready. Country/institution/collection/holding identity, global source/media provenance, multilingual packages, distributed asset storage, high-selectivity retrieval, asynchronous ingestion/enrichment, cost routing/fallbacks, warehouse/OLAP analytics, SLOs and multi-region/privacy policy are required. This does not automatically require splitting recognition into many microservices; measure modular-monolith limits first.

## Subsystem risks

| Subsystem | Current behavior | Scale risk |
|---|---|---|
| Postgres catalog | Indexed museum/membership fields | Full candidate row hydration; ambiguous identity model |
| Recognition | 1–3 synchronous OpenAI calls | Cost, tail latency, provider quota |
| Images | Wikimedia/proxy + per-machine disk cache | Cache inconsistency/eviction/egress |
| Events | synchronous insert per explicit event | Write amplification and public abuse |
| Admin | raw group queries on request | Slow/expensive cohorts and high-cardinality dimensions |
| Frontend | static SEO + client visit | Content build volume/locale bundle growth |
| Caching | SW and in-process/disk caches | Instance-local invalidation, no shared policy |

## Current performance evidence

No current reproducible Lighthouse/Core Web Vitals baseline was found/run for this audit. Public SEO pages remain separated from `/visit`, but `/visit` statically imports its screens. Physical PWA and field performance remain verification items.
