# Global Blockers

## Block 4 resolution (2026-08-23)

RESOLVED: generic adapter/runner, idempotent reconciliation, ingestion audit, explicit provenance review and import/activation separation. Distributed execution remains later scale work and does not block controlled second-country onboarding.

Effort uses S/M/L/XL, not hour estimates.

| Priority | Issue/evidence | Consequence | Approach | Effort |
|---|---|---|---|---|
| RESOLVED Block 1 | Production source governance, migration ledger, Country/Institution/Profile and unsafe global candidate fallback | Reviewed source, observable migrations and fail-closed institution configuration | Preserve release/migration/profile tests | L |
| RESOLVED Block 2 | Event/identity/time/QA spoofing and recognition double counting | Trusted analytics/attempt facts and linked identity | Preserve event-contract/adversarial tests | L |
| RESOLVED Block 3 | Artwork conflated object, institution holding and provider record | CulturalObject/Holding/SourceRecord with stable compatibility IDs | Future adapters write normalized entities | L |
| RESOLVED Block 3 | Presentation/reference/recognition media and rights were provider-specific/ambiguous | Generic MediaAsset purposes, provenance/rights states, independent eligibility | Review legacy UNKNOWN before activation | L |
| RESOLVED Block 3 foundation | France/Paris/timezone/currency/locale assumed by institution core | Country/Institution arbitrary BCP-47, IANA timezone, currency and policy configuration | Ship institution content/bundles deliberately | M |
| P1 | Generic adapter ingest/upsert/reconciliation workflow absent | Second institution still needs engineering glue and careful scripts | Build adapter runner + manifest/dry-run/idempotent upsert | L |
| P1 | Legacy media/source columns remain runtime truth; provenance VERIFIED=0 in current catalog snapshot | Rights/readiness cannot be asserted globally yet | Provider review/backfill, parity reader migration | L |
| P1 | UI/generated content only fully supports en/fr/zh-Hans; inline ternaries remain | A museum requiring another visitor language needs UI/content work | Resource modules, fallback tests, reviewed locale pack | L |
| P1 | EUR-only Value Engine V4 and Paris/European comparison packs | GBP institution can configure currency but values must remain honestly EUR until reviewed model | Separate market/context packs; never implicit FX | L |
| P1 | Runtime DEMO_ARTWORKS fallback duplicates DB catalog | Availability/source-of-truth fragility | Remove after DB-only parity and fail-closed availability tests | M |
| P1 | Admin has fallback founder credential/single role | Security/operational expansion risk | Fail-closed secrets, IdP/MFA/RBAC/audit | L |
| P2 | Full institution catalog materialized/ranked per recognition | Large catalog DB/CPU/latency risk | Indexed bounded preselection/cache after measurement | L |
| P2 | Process-local event rate limit, synchronous ingestion/raw admin aggregation | Multi-instance/high-volume trust and performance limit | Shared quota, retention/partition and rollups when justified | L |
| P2 | Visitor media/event retention/provider policies incomplete | Privacy operations remain uncertain | Define TTL/deletion and verify providers | M |
| P3 | Physical PWA device/performance matrix incomplete | Platform regressions discovered late | Repeatable device matrix/budgets | M |

No mandatory core schema/catalog/recognition blocker remains before beginning a controlled National Gallery onboarding. P1 ingest, rights/provenance review, content and benchmark gates remain mandatory onboarding work before activation.
