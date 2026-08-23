# Canonical Metric Definitions

Status: CURRENT for trusted analytics v2, effective 2026-08-23. All time is canonical server UTC. Legacy absence is **NOT AVAILABLE**, not zero.

Canonical person key is verified `user_id` when present, otherwise a linked user from `analytics_identity_links`, otherwise UUID `anonymous_id`. Known anonymous-to-authenticated links prevent double counting; unknown cross-device identity cannot be inferred. A browser session is one UUID stored in sessionStorage and fixed in `analytics_sessions` to its identity context.

Meaningful client activity is one of: `museum_selected`, `visit_started`, `scan_attempt`, `result_viewed`, `artwork_viewed`, `artwork_added`, `favorite_added`, `progress_viewed`, `recap_viewed`, `share_completed`. A visitor-linked authoritative recognition attempt is also meaningful. Every metric excludes trusted QA, identityless operations, invalid dimensions and legacy-unverified rows.

| Metric | Canonical definition |
|---|---|
| Total Users | Distinct canonical identities ever seen in trusted v2 activity, union registered users. |
| Active Users | Distinct identities with meaningful activity in period, using event `occurred_at` or attempt `started_at`. |
| New Users | Identities whose first-ever trusted meaningful activity is in the period. |
| Activated Users | New identities in the period whose first authoritative `success` or `uncataloged_result` terminal attempt is also in the period; once per linked person. Activation rate is this count / New Users. |
| Returning Users | Active identities with meaningful activity on more than one distinct UTC day over trusted history. Reload/session/admin/QA do not qualify. |
| DAU / WAU / MAU | Active Users in rolling 1/7/30-day windows ending at query time. |
| Sessions | Distinct validated `session_id` represented by trusted events or valid attempts. Session means sessionStorage/tab lifetime, not inactivity timeout. |
| Recognition Attempts | Visitor-linked, non-QA attempt rows with KPI terminal outcome; one UUID/row per attempt. |
| Successful Recognitions | Attempts terminal `success` or `uncataloged_result`. |
| Failed Recognitions | Attempts terminal `no_match`, `invalid_image`, `timeout`, or `failed`. |
| Recognition Success Rate | Successful / (successful + failed) attempts × 100; never summed from companion events. |
| Scans / Active User | Authoritative attempt count / Active Users for identical period/filter. |
| Funnel | Distinct identities per stage; client stages explicitly client-observed, recognition submission/success server-confirmed from attempts. |

## Retention

Cohort date is an identity's first trusted meaningful UTC date. D1/D7/D30 numerator is cohort identities with trusted meaningful activity exactly 1/7/30 days later. Denominator includes only cohorts mature enough to reach that horizon. Known links collapse anonymous and authenticated activity; no heuristic cross-device merge occurs. A horizon without eligible history returns unavailable (`null`), not 0%.

## Trust caveats

Acquisition, locale and early UI funnel stages are validated client observations, not server-proven actions. Recognition terminal outcomes and authenticated IDs are server facts. Historical pre-v2 rows remain queryable for diagnosis but are never recast as current trusted KPI inputs.
