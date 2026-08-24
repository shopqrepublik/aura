# ELYIO Documentation

Status: **CURRENT CANONICAL ENTRY POINT**

Audited production source: `5c5ac7ed11573e4079b073cdb2598334eeac573f`

Audit date: 2026-08-23

The current production application is ahead of `origin/main`. Production deployments align with the remote branch `docs/elyio-full-system-audit` at `5c5ac7e`; `origin/main` remains `3adf605`. Treat that branch divergence as an operational blocker, not as permission to merge it from documentation work.

## Evidence labels

- **CODE** — verified in the audited source.
- **LIVE** — verified against production HTTP/Vercel/Fly on 2026-08-23.
- **DATA** — verified by read-only production DB/API query.
- **PROPOSED** — target design, not implemented.
- **UNKNOWN** — provider/manual fact not independently verified.

## Reading paths

### New engineer

1. [System overview](architecture/SYSTEM_OVERVIEW.md)
2. [Repository map](architecture/REPOSITORY_MAP.md)
3. [Data model](architecture/DATA_MODEL.md)
4. [Recognition pipeline](recognition/RECOGNITION_PIPELINE.md)
5. [Analytics architecture](analytics/ANALYTICS_ARCHITECTURE.md)
6. [Architectural invariants](architecture/ARCHITECTURAL_INVARIANTS.md)

### Adding a museum

1. [Museum onboarding playbook](operations/MUSEUM_ONBOARDING_PLAYBOOK.md)
2. [Catalog architecture](catalog/CATALOG_ARCHITECTURE.md)
3. [Artwork identity](catalog/ARTWORK_IDENTITY.md)
4. [Image provenance](catalog/IMAGE_PROVENANCE.md)
5. [Recognition readiness](recognition/RECOGNITION_READINESS.md)
6. [Internationalization](global/INTERNATIONALIZATION.md)

### Recognition problem

1. [Recognition pipeline](recognition/RECOGNITION_PIPELINE.md)
2. [Recognition readiness](recognition/RECOGNITION_READINESS.md)
3. [Recognition benchmarking](recognition/RECOGNITION_BENCHMARKING.md)
4. [Troubleshooting](operations/TROUBLESHOOTING.md)
5. [Admin Control Center](operations/ADMIN_CONTROL_CENTER.md)

### Production incident

1. [Troubleshooting](operations/TROUBLESHOOTING.md)
2. [Production smoke test](operations/PRODUCTION_SMOKE_TEST.md)
3. [Deployment runbook](operations/DEPLOYMENT_RUNBOOK.md)
4. [Observability](engineering/OBSERVABILITY.md)

### Analytics

1. [Analytics architecture](analytics/ANALYTICS_ARCHITECTURE.md)
2. [Event contract](analytics/ANALYTICS_EVENT_CONTRACT.md)
3. [Metric definitions](analytics/METRIC_DEFINITIONS.md)
4. [Admin Control Center](operations/ADMIN_CONTROL_CENTER.md)

### Global expansion

1. [Executive global audit](ELYIO_GLOBAL_AUDIT_2026-08-23.md)
2. [Global hardcode audit](global/GLOBAL_HARDCODE_AUDIT.md)
3. [Global readiness scorecard](global/GLOBAL_READINESS_SCORECARD.md)
4. [Global blockers](global/GLOBAL_BLOCKERS.md)
5. [Target architecture](architecture/GLOBAL_TARGET_ARCHITECTURE.md)
6. [Expansion roadmap](global/GLOBAL_EXPANSION_ROADMAP.md)

## Canonical documents

| Area | Document |
|---|---|
| Executive state | [ELYIO_GLOBAL_AUDIT_2026-08-23.md](ELYIO_GLOBAL_AUDIT_2026-08-23.md) |
| Current architecture | [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md) |
| Current/target data | [architecture/DATA_MODEL.md](architecture/DATA_MODEL.md) |
| Recognition | [recognition/RECOGNITION_PIPELINE.md](recognition/RECOGNITION_PIPELINE.md) |
| Value experience | [architecture/VALUE_EXPERIENCE.md](architecture/VALUE_EXPERIENCE.md) |
| Catalog and provenance | [catalog/CATALOG_ARCHITECTURE.md](catalog/CATALOG_ARCHITECTURE.md) |
| First-party analytics | [analytics/ANALYTICS_ARCHITECTURE.md](analytics/ANALYTICS_ARCHITECTURE.md) |
| Operations | [operations/DEPLOYMENT_RUNBOOK.md](operations/DEPLOYMENT_RUNBOOK.md) |
| Security/privacy | [security/SECURITY_ARCHITECTURE.md](security/SECURITY_ARCHITECTURE.md) |
| Global readiness | [global/GLOBAL_READINESS_SCORECARD.md](global/GLOBAL_READINESS_SCORECARD.md) |
| Engineering risk | [engineering/TECH_DEBT_REGISTER.md](engineering/TECH_DEBT_REGISTER.md) |

## Historical material

- [ELYIO_FULL_SYSTEM_AUDIT_2026-08-16.md](ELYIO_FULL_SYSTEM_AUDIT_2026-08-16.md) — historical baseline only.
- Root AURA specifications, legacy `frontend/`, old previews and Louvre research exports are not canonical current architecture unless explicitly referenced by a current document.
