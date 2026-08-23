# Architectural Invariants

- **MediaAsset is not MediaAssociation.** Provider media identity is unique independently of all exact CulturalObject/InstitutionHolding relationship edges; no valid source edge may be silently lost or represented by a fake duplicate asset.
- Media rights/eligibility and association role/eligibility must both permit presentation or recognition. Contextual shared media never becomes a recognition reference by association alone.
- Configured institution + known reliable catalog work uses the catalog-backed result. Configured institution + no reliable catalog match retains the truthful AI uncataloged fallback and records demand. Unknown/unconfigured institution fails closed. In engineering shorthand: “Catalog when we know. AI when we don't. Learn from what visitors scan.”
- RecognitionAsset absence does not disable `VISION_READY` metadata-first recognition or the configured-institution uncataloged AI fallback. Reference/presentation/benchmark-input rights remain separate gates.

## Block 4 ingestion invariants (CURRENT)

- Provider adapters describe external sources; generic ingestion owns ELYIO rules and never branches on institution/provider names.
- APPLY is explicit, audited and idempotent; dry-run modes perform zero database mutation.
- Ingestion, visitor-catalog activation and recognition activation are separate gates.
- Weak metadata may suggest a duplicate but cannot merge objects.
- Provider declarations never self-promote to VERIFIED or media eligibility.
- Bad imports are neutralized reversibly, not by deleting canonical identity/provenance.
- EUR-grounded Value Engine output cannot be relabelled GBP or another currency.

Status: CURRENT rules future changes must preserve.

1. Institution is data/configuration in `museums` + `institution_profiles`, never a permanent core branch. Provider adapters may be source-specific.
2. Missing/invalid Institution Profile fails closed; candidate lookup never broadens to another institution or all artworks.
3. Recognition candidates and outcomes preserve institution, artwork and attempt context end to end.
4. Every object has stable ELYIO identity; title+artist, translated title, museum slug and image similarity are not canonical identity.
5. Provider/source identity is namespaced and exact duplicates are constrained. Uncertain duplicate candidates remain separate until explicit review.
6. Cultural object, institution holding, provider source record and visitor Artwork are separate concepts even while compatibility columns remain.
7. Presentation image, source/reference, recognition asset, derivative and private visitor capture are separate purposes.
8. Rights UNKNOWN stays UNKNOWN. Public-domain artwork status does not imply image rights or recognition/AI-processing permission.
9. Presentation and recognition eligibility are independent, explicit decisions.
10. Source metadata and source language are preserved; localized editorial/generated content never overwrites provider truth.
11. Human-reviewed catalog/editorial/value data wins over generated enrichment.
12. `ARTIST_MARKET_CONTEXT` is not the viewed-work value; LOW-confidence AI estimates do not enter totals. Value Engine V4 remains EUR-grounded until an explicitly reviewed currency model exists; institution display currency never implies conversion.
13. Institution timezones govern local display/business context; canonical analytics timestamps and cohorts remain server-trusted UTC.
14. UI bundle availability and institution-supported locales are separate. Do not claim a locale works without a shipped/reviewed message/content bundle.
15. QA traffic never enters founder metrics; only server-secret QA context assigns internal status.
16. Authenticated identity is server-derived; anonymous history is linked, not destructively rewritten.
17. One `recognition_attempt_id` has one terminal KPI outcome. Raw companion events cannot multiply recognition counts.
18. Engine outcome and visitor resolution are distinct. `CONFIRMATION_REQUIRED` is not silently described as user-confirmed.
19. Repeat scans do not inflate discoveries; favorites are separate; no-match/network failure does not count as a sighting.
20. Private captures are not public catalog/SEO media.
21. Admin API requires backend authorization; no frontend-only guard or plaintext secret.
22. Production schema changes use ordered checksummed migrations; no destructive reset or fabricated backfill.
23. Production is reproducible from reviewed main/release Git and reports deployed identity.
24. Existing institution/artwork IDs, routes and analytics dimensions remain stable through normalization.
25. Historical missing data is unavailable, not zero; dated counts are snapshots, not defaults.
