# Architectural Invariants

Status: CURRENT rules plus global safety requirements.

1. A museum/institution is data/configuration in `museums` + `institution_profiles`, never a permanent core code branch. Source adapters may remain provider-specific.
2. Recognition candidate lookup is scoped to the selected institution/catalog; no cross-museum leakage.
3. Every catalog object has a stable ELYIO ID and traceable source record; inventory numbers alone are not globally unique.
4. Presentation image, source/reference image and `RecognitionAsset` are distinct roles.
5. A recognition asset is eligible only through explicit rights and AI/TDM fields, not because the depicted artwork is public domain.
6. Human-reviewed catalog/editorial/value data wins over generated enrichment.
7. QA/internal traffic must never contaminate founder visitor metrics; only the server-secret QA context can assign `internal_test`.
8. Analytics identity persists across browser sessions through `anonymous_id`; a session ID is scoped separately. Missing historical data is `unavailable`, never zero.
9. Authenticated visitor linkage is derived from a verified server session; historical anonymous rows are linked, not destructively rewritten, and one browser identity cannot be reassigned silently.
10. One validated `recognition_attempt_id` follows a scan request, backend execution, response and companion events; exactly one server-owned terminal outcome is counted.
11. Identityless backend operations are operational telemetry, not Active Users.
12. Admin data/API requires server authorization; no frontend-only guard or plaintext credential.
13. Public event ingestion accepts only a versioned allowlist and bounded schema. Client time, user ID, QA status and recognition result are never authoritative.
14. `ARTIST_MARKET_CONTEXT` is never a viewed-work value; LOW-confidence AI estimates do not enter totals.
15. Stable catalog repeat scans do not inflate discovery count; no-match/network failures do not count.
16. Private visitor captures are not SEO/public catalog media.
17. Global expansion must not require separate application branches/deployments per museum.
18. Schema changes are versioned, repeatable and observable; deployed tables without a migration ledger are transitional debt.
19. Production source must be reproducible from reviewed mainline Git history and embedded in deployment metadata.
20. Historical audit counts are dated snapshots, not constants or KPI defaults.
21. Missing, inactive or invalid Institution Profile configuration fails closed; it must never broaden to institution-wide or global candidates implicitly.
22. Existing institution IDs and analytics `museum_id` dimensions remain stable through the Institution transition.
23. Raw events and trusted business facts are distinct; legacy or client companion events cannot be silently promoted into founder KPIs.
24. Missing historical analytics is unavailable, not zero; trusted metric cohorts start at the explicit schema-v2 boundary.
