# Technical Debt Register

Status: CURRENT evidence-based register.

| Priority | Debt | Evidence / impact | Next action |
|---|---|---|---|
| P0 | Production branch divergence | Live source `5c5ac7e`, origin/main `3adf605` | Reviewed integration/mainline release metadata |
| P0 | Country/institution model absent | Museum strings only | Add baseline entities/migration |
| P0 | Event integrity absent | Public arbitrary ingestion | Version/validate/sign/limit |
| P1 | Metric double counting/split identity | admin success loop; no first-party user_id | Dedup + identity alias contract/tests |
| P1 | Museum-specific config map/fallback-all | catalog.py | DB-backed fail-closed catalog/profile |
| P1 | Image provenance incomplete | image_url lacks license/retrieval/derivative | Generic media provenance |
| P1 | Closed three-locale/France copy | types/i18n/api | Locale/jurisdiction configuration |
| P1 | Confirmation event/UX mismatch | auto `candidate_confirmed` | Real confirm/reject flow |
| P1 | Uncataloged repeat ID unstable | timestamp-based ID | Stable temporary identity |
| P2 | No migration ledger | SQL scripts/table inspection | Alembic/equivalent |
| P2 | Backend monolith | recognition/value/image/API in main.py, admin.py 1,141 lines | Extract modules only with regression coverage |
| P2 | Readiness vocabulary inconsistent | READY/VISION states/NEEDS_ASSET | Enum/state migration |
| P2 | Admin single account/no roles | defaults + global access | IdP/MFA/RBAC/audit |
| P2 | Event/admin retention absent | raw tables, no TTL/rollup | Partition/TTL/aggregates |
| P2 | Full candidate materialization | catalog list per request | Indexed bounded retrieval/cache |
| P2 | No end-to-end attempt/latency/cost correlation | separate client/server events | Carry correlation and timings |
| P2 | Browser capture retention unclear | localStorage base64 | TTL/clear/IndexedDB/privacy policy |
| P3 | Stale manifest Orsay copy | manifest description | Dedicated PWA metadata update |
| P3 | Legacy mission/AURA/preview code | nearby but dormant | Reference-test then archive/mark |
| P3 | No current performance baseline | docs/source audit | Repeatable lab/field monitoring |

No product behavior should be changed as part of documentation remediation itself.
