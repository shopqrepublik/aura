# Architectural Invariants

Status: CURRENT rules plus global safety requirements.

1. A museum/institution is data/configuration in `museums` + `institution_profiles`, never a permanent core code branch. Source adapters may remain provider-specific.
2. Recognition candidate lookup is scoped to the selected institution/catalog; no cross-museum leakage.
3. Every catalog object has a stable ELYIO ID and traceable source record; inventory numbers alone are not globally unique.
4. Presentation image, source/reference image and `RecognitionAsset` are distinct roles.
5. A recognition asset is eligible only through explicit rights and AI/TDM fields, not because the depicted artwork is public domain.
6. Human-reviewed catalog/editorial/value data wins over generated enrichment.
7. QA/internal traffic must never contaminate founder visitor metrics; the exclusion flag must eventually be server-trusted.
8. Analytics identity persists across browser sessions through `anonymous_id`; a session ID is scoped separately. Missing historical data is `unavailable`, never zero.
9. Authenticated visitor linkage must not silently split one person into unrelated first-party identities.
10. Recognition events preserve museum, artwork when resolved, and a correlation ID across attempt/result boundaries.
11. Identityless backend operations are operational telemetry, not Active Users.
12. Admin data/API requires server authorization; no frontend-only guard or plaintext credential.
13. Public event ingestion cannot be allowed to define trusted metrics indefinitely without integrity controls.
14. `ARTIST_MARKET_CONTEXT` is never a viewed-work value; LOW-confidence AI estimates do not enter totals.
15. Stable catalog repeat scans do not inflate discovery count; no-match/network failures do not count.
16. Private visitor captures are not SEO/public catalog media.
17. Global expansion must not require separate application branches/deployments per museum.
18. Schema changes are versioned, repeatable and observable; deployed tables without a migration ledger are transitional debt.
19. Production source must be reproducible from reviewed mainline Git history and embedded in deployment metadata.
20. Historical audit counts are dated snapshots, not constants or KPI defaults.
21. Missing, inactive or invalid Institution Profile configuration fails closed; it must never broaden to institution-wide or global candidates implicitly.
22. Existing institution IDs and analytics `museum_id` dimensions remain stable through the Institution transition.
