# Source Adapter Guide

Adapters must emit every provider relationship, including repeated references to a shared media ID. Set `association_scope` (`OBJECT` or `HOLDING`), contextual `association_role`, stable `source_relationship_key`, and source ordering/primary hints when known. Never drop shared media, clone it per object, or special-case a provider's shared IDs; the generic runner reconciles one media entity and N association edges.

Status: CURRENT. This guide does not authorize production import.

Implement `CatalogSourceAdapter` in `backend/app/source_adapter.py`: stable `adapter_key`, configured `provider_id`, `records()`, and `source_snapshot()`. Register it in `backend/app/adapters/__init__.py`; configure the matching active SourceProvider and explicit allowed institution IDs. Institution and InstitutionProfile must already exist, otherwise the runner fails closed.

Keep HTTP, authentication, pagination, conditional requests, retry/backoff and schema mapping inside the adapter. Never branch on a provider in generic ingestion. Abort visibly on partial pagination or schema failure. Preserve raw payload, source URL/language, provider timestamps, source rights statements and attribution; do not invent rate limits or rights.

Before APPLY: archive a reproducible snapshot; run DISCOVER, DRY_RUN, PLAN and RECONCILE; resolve blockers; review duplicates/rights; retain the plan/checksum; run APPLY with operator identity. Next perform provenance review, asset preparation, readiness, benchmark, and only then separate catalog activation.

`normalized_json_v1` is the adapter template and deterministic test implementation. It accepts an array or `{ "records": [...] }` using `AdapterObjectRecord` fields.
