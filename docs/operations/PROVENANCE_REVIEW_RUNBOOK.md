# Provenance Review Runbook

Status: CURRENT. Automation records evidence; it does not make unsupported legal conclusions.

Authenticated admins use `GET /v1/admin/provenance` with institution, provider, rights/verification, eligibility and no-usable-media filters. Review one asset via `PATCH /v1/admin/provenance/{media_asset_id}`. There is no bulk verify endpoint. Each mutation writes `MediaProvenanceReview` with admin identity, timestamp, before/after state and notes.

1. Confirm provider/source URL and exact source record.
2. Record source-provided right statement, license and attribution.
3. Choose UNKNOWN, DECLARED_BY_SOURCE, VERIFIED or RESTRICTED. API text alone is not VERIFIED.
4. Choose presentation and recognition eligibility independently. True requires VERIFIED plus LICENSED or VERIFIED_PUBLIC_DOMAIN. RESTRICTED forces both false.
5. Record evidence/decision notes. Never infer public domain from age, filename, artist death, or Wikimedia presence alone.

Neutralize a bad import by deactivating membership/source/media or InstitutionProfile, not deleting CulturalObjects. `safe_deactivate_source_record()` retains identity/provenance, disables linked media and memberships, and audits the media decision.
