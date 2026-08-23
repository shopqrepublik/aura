# Recognition Readiness

Status: CURRENT operational contract.

## Readiness dimensions

Readiness is not one inferred flag. Review stable object/source identity, correct InstitutionHolding/catalog membership, sufficient metadata, presentation readiness, recognition readiness, provenance verification, rights/processing eligibility and benchmark outcome independently.

| Operational category | Meaning |
|---|---|
| Presentation ready | Approved visitor-facing media exists; not automatically recognition-eligible. |
| Recognition ready | Policy/candidate metadata and, where required, an explicitly eligible RecognitionAsset are ready. |
| Provenance verified | ELYIO verification state is `VERIFIED`; source declaration alone is partial. |
| Provenance incomplete | `DECLARED_BY_SOURCE` or missing required source/license/retrieval evidence. |
| No usable source media | No non-restricted REFERENCE/RECOGNITION_ASSET/SOURCE_ORIGINAL URL for the active artwork. |
| Rights restricted | Explicit restriction; do not present/process beyond the recorded permission. |

Admin Catalog exposes aggregate provenance categories without redesigning Overview. Legacy status strings (`READY`, `VISION_READY`, `VISION_PLUS_ASSET`, `NEEDS_ASSET`, etc.) remain for compatibility; the dimensions above are the canonical interpretation.

## Activation checklist

- [ ] CulturalObject, Holding and provider SourceRecord are stable; no title-derived identity.
- [ ] Membership and holding institution agree with the selected Institution Profile.
- [ ] Candidate universe/version resolves and fails closed when empty/invalid.
- [ ] Presentation/reference/recognition purposes are explicit.
- [ ] UNKNOWN rights remain unknown; AI/TDM/recognition eligibility is explicit.
- [ ] Exact import duplicates are blocked; possible duplicates reviewed, never auto-merged.
- [ ] Wrong-work, wrong-institution, no-art and partial-image benchmark gates pass.
- [ ] `needs_confirmation` is monitored separately from auto-accepted results.
- [ ] Deactivation/rollback uses membership/profile state rather than deleting evidence.

## Current compatibility

Recognition continues using established columns and algorithms. Generic media is an additive provenance system until a later parity-gated reader migration. Louvre-specific import/reference code is a legitimate source adapter; it must not control global candidate/policy logic.
