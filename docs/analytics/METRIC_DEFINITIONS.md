# Canonical Metric Definitions

Status: CURRENT implementation documented exactly; corrected target definitions are explicit where current code is unreliable.

All first-party visitor metrics exclude `properties.internal_test=true` and require `coalesce(user_id, anonymous_id)` unless stated otherwise. History begins 2026-08-20; earlier absence is **unavailable**, never zero.

| Metric | Current source and exact implementation | Time/identity semantics | Known defect / canonical interpretation |
|---|---|---|---|
| Total Users | `registered users all-time + distinct anonymous_id in selected period` | Mixed all-time/period; user/anon not merged | Not globally additive and can double-count an authenticated person. Label current UI as “registered all-time + anonymous in period” until fixed. |
| Active Users | Distinct identity with any `MEANINGFUL_EVENTS` in period | Event time UTC; persistent anon/user | Canonical current active definition. Session/PWA/language-only events are not active. |
| New Users | Basic user panel: registered users created in period. Activation panel: distinct identities with `app_opened`, `visit_started`, or `museum_selected` in period | Two conflicting definitions | Canonical acquisition denominator should be first-ever identity event in global history, not merely an event in the period. Current value is not true new-user count. |
| Activated Users | Distinct identity with `scan_success` or `recognition_succeeded` | Period event; current emitted success is `scan_success` | One identity counted once. This is the canonical activation definition. |
| Returning Users | Active identities with meaningful events on >1 distinct UTC dates within selected period | Does not require a prior-period visit | This is repeat-day active within period, not standard returning user. Future canonical: active now with first_seen before period or activity on a later date. |
| DAU/WAU/MAU | Active Users in rolling 1/7/30 days from query time | UTC timestamps, not calendar day/week/month | Exact current rolling-window definition. |
| Sessions | max(distinct first-party `session_id`, count of Visit rows) | Browser sessionStorage/tab versus authenticated Visit are different units | Not additive/comparable. Canonical future session needs one server-defined inactivity/session contract. |
| Recognition Attempts | Count identified `recognition_started` client events | Browser identity and period | Canonical; dedupe by `recognition_attempt_id` should be added. Identityless server attempts excluded. |
| Successful Recognition | Current code counts `scan_success`/`recognition_succeeded`, then also increments for `recognition_completed` status matched/review | Identified events | **Current implementation double-counts a normal successful attempt.** Canonical: distinct attempt IDs with terminal catalog success; decide separately whether review counts. |
| Failed Recognition | Current failure-event count plus no-match `recognition_completed` increments | Identified events | Can double-count `recognition_failed` + `scan_failed`. Canonical: one terminal failure per attempt, reason dimension. |
| Recognition Success Rate | current `successful / attempts` | Same period | Unreliable and may exceed 100 due double counting. Canonical: distinct successful terminal attempt IDs / distinct started attempt IDs. |
| Scans / Active User | Museum rows use scan events / museum distinct visitors; general dashboard has no exact KPI | Period | Canonical: distinct `recognition_attempt_id` (or scan_attempt count until IDs enforced) / Active Users, same filters. |
| D1 | identities active exactly first_seen UTC date + 1 / all observed identities | All history; meaningful events | Includes immature cohorts in denominator. Canonical should include only D1-mature cohorts. |
| D7 | identities with any active day >= first + 7 / all identities | Cumulative, not exact day 7/window | Label “returned on/after day 7”; mature-cohort denominator required. |
| D30 | identities with any active day >= first + 30 / all identities | Cumulative | Same maturity bias. |
| Funnel conversion | At each named stage, distinct identity with that event / previous stage and / app_opened count | Event occurrence in same selected period, not ordered same-session journey | Not a strict funnel: users can enter stages without prior stage in period. Canonical future: ordered identity/session funnel with stage timestamps. |

## Current funnel stages

`app_opened → museum_selected → visit_started → scan_attempt → recognition_started → scan_success → result_viewed → second_scan_started → recap_viewed`.

## Activation timing

`_activation` finds first event among app/visit/recognition events and first success for an identity inside the selected period; median delta and scans before first success are period-truncated. Future canonical activation must use global first-seen and first-ever success.

## Metric change control

Any code change must version the definition, add tests with duplicate client/server events, internal events, anonymous-to-user merge, immature cohorts and unordered funnels, and annotate the dashboard's availability start. Do not backfill unavailable history with zero.
