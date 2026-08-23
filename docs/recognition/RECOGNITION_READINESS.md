# Recognition Readiness

Status: CURRENT definitions with required normalization noted.

## Minimum readiness gate

An artwork should be activated only when:

1. stable artwork/source identity is verified;
2. membership points to the correct institution/catalog version;
3. title/object metadata is sufficient for candidate ranking;
4. presentation image role is known;
5. recognition asset/reference policy is explicit;
6. rights and AI/TDM eligibility are recorded independently;
7. wrong-work and wrong-museum benchmarks pass;
8. no-match behavior is safe;
9. admin catalog health shows no unexplained missing data;
10. rollback means membership deactivation, not row deletion.

## Current status computation

The DB stores `display_status`, `metadata_status`, `recognition_status`, rights status/review flag, and asset rows independently. Admin `not_ready` treats insufficient metadata and `NOT_READY`, `NO_USABLE_ASSET`, `RIGHTS_RESTRICTED` as not ready. `VISION_PLUS_ASSET`/`VISION_READY` are also used as database statuses, while response `recognition_mode` uses the same two strings. `READY` and `NEEDS_ASSET` remain in production data. A canonical state machine is not enforced by DB constraints.

## Required per-institution configuration

Current code requires a catalog-version environment variable and Python-map entry to receive the top-N policy. Until generalized, onboarding must document whether the museum uses top-N metadata verification or per-candidate asset verification and why.

## Activation checklist

- [ ] Active membership count equals approved manifest count.
- [ ] Every membership `museum_id` matches its artwork.
- [ ] No duplicate `(source, source_record_id)`.
- [ ] Asset identity and license review completed.
- [ ] Presentation/recognition/reference roles are not conflated.
- [ ] Self-match recall, decoy rejection, wrong-museum and no-art image tests pass.
- [ ] Confidence/status distribution reviewed.
- [ ] No benchmark uses production visitor images without authorization.
- [ ] Admin health and public catalog count agree.
