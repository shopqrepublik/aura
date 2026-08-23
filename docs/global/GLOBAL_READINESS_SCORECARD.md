# Global Readiness Scorecard

Scale: 0 absent; 1 prototype; 2 works for current deployment; 3 cleanly multi-museum ready; 4 global-scale ready.

| Capability | Score | Evidence |
|---|---:|---|
| Country/city model | 2 | Country FK and institution city/timezone/locales work; City remains an unnormalized string. |
| Museum model | 3 | 1,222 rows, geolocation and museum-scoped FKs/API; naming still “museum”. |
| Collection model | 2 | Optional hierarchical Collection exists; current artworks are not yet mapped. |
| Artwork identity | 2 | Stable ID and unique source record; no work/object/copy/holding model. |
| Catalog architecture | 3 | Versioned memberships and Institution Profile resolve active universe/version; invalid/empty configuration fails closed. |
| Recognition | 3 | Institution-scoped configurable policies/prompts/thresholds preserve current paths; large-catalog shortlist scale remains future work. |
| Image provenance | 2 | RecognitionAsset is strong; presentation/reference/derivative provenance incomplete and Louvre-specific table. |
| Multilingual | 2 | Three real locales; closed union and inline branching. |
| Analytics | 2 | First-party dimensions/admin work; spoofable events, split identity and metric defects. |
| Admin | 2 | Authenticated live Control Center; single account, no roles/audit scope, raw aggregation. |
| PWA | 2 | Install/cache/update current deployment; physical-device/global offline tests pending. |
| Security | 2 | Server auth/cookies/CORS/CSP exist; default hash/pepper and public event integrity risks. |
| Privacy | 1 | No raw image catalog persistence, but browser capture/event retention and provider policies undefined. |
| Deployment | 3 | Reviewed source reconciled; backend/frontend release metadata and migration ledger are implemented. |
| Onboarding | 1 | Powerful museum-specific scripts; no repeatable generic pipeline. |
| Observability | 2 | Health/admin/events/logs; no alerting/SLO/tracing and latency linkage gaps. |
| Scale | 1 | Current volume works; synchronous events/AI/full-catalog ranking/raw admin scans. |
| Cost visibility | 1 | Architecture implies OpenAI/PostHog/storage costs; no per-attempt/institution cost ledger. |

## Executive rollups

Multi-museum 3; multi-city 2; multi-country 2; multilingual 2; recognition 3; catalog 3; analytics 2; admin 2; security 2; PWA 2; scale 1; deployment governance 3.
