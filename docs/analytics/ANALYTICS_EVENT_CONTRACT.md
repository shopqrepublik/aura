# Analytics Event Contract

Status: CURRENT emitted events verified from producers. Reserved type names with no producer are listed separately and are not called production events.

## Common envelope

For client events, `event_id`, `event_name` and `occurred_at` are generated per send. `anonymous_id` and `session_id` are expected when browser storage works but may be absent. Optional common fields: `museum_id`, `artwork_id`, `recognition_attempt_id`, `properties`, source/referrer/UTMs, browser language/device/OS/browser/path. First-party `user_id` is currently absent. All client events inherit organic landing properties and `internal_test=true` when enabled.

“Active” below means included in `MEANINGFUL_EVENTS`. “Activation” means one of `scan_success` or `recognition_succeeded`; because `recognition_succeeded` is not currently emitted, `scan_success` is the effective activation event.

## Actual current client events

| Event | Producer/trigger | Required event properties | Optional/linkage | Funnel | Active | Activation |
|---|---|---|---|---|:---:|:---:|
| `session_started` | `trackSessionStartedOnce` on `ElyioApp` mount per sessionStorage | locale | anon/session | No admin stage | NO | NO |
| `app_opened` | `ElyioApp` mount/locale effect | locale, display_mode | anon/session | App opened | NO | NO |
| `seo_begin_visit` | `/visit?from=organic` effect | traffic_source, landing_page, landing_locale | anon/session, attribution | Pre-funnel | NO | NO |
| `language_selected` | Home/desktop selector | locale | anon/session | No | NO | NO |
| `museum_selected` | manual/detected selection action | museum_id plus selection source/confidence where supplied | museum | Museum selected | YES | NO |
| `visit_started` | Begin Visit state transition | museum_id | museum | Visit started | YES | NO |
| `scan_opened` | visit start | museum_id, source=`visit_started` | museum | No separate stage | YES | NO |
| `image_captured` | before API call | museum_id, recognition_attempt_id | recognition/museum | No | YES | NO |
| `scan_attempt` | before API call | museum_id, seen_count, recognition_attempt_id | recognition/museum | Image captured/uploaded | NO | NO |
| `second_scan_started` | attempt when seen count > 0 | museum_id, seen_count, recognition_attempt_id | recognition/museum | Second scan | NO | NO |
| `recognition_started` | immediately before API call | museum_id, recognition_attempt_id | recognition/museum | Recognition submitted | YES | NO |
| `recognition_completed` | API returned any status | museum_id, recognition_attempt_id, status, confidence | recognition_mode, resolved_artwork_id | No direct funnel row | YES | NO |
| `recognition_failed` | thrown API/client error | museum_id, recognition_attempt_id, reason | recognition/museum | Failure | YES | NO |
| `scan_success` | catalog artwork accepted by current UI | artwork_id, museum_id, confidence, status, recognition_attempt_id | artwork/museum/recognition | Successful recognition | YES | **YES** |
| `scan_failed` | uncataloged, no-match or error | reason, recognition_attempt_id | museum sometimes absent | Failure | YES | NO |
| `catalog_match` | catalog result | museum_id, artwork_id, confidence, recognition_mode, recognition_attempt_id | full linkage | No | NO | NO |
| `catalog_no_match` | uncataloged/pure no-match | museum_id, confidence, recognition_attempt_id | `ai_candidate` for uncataloged | No | NO | NO |
| `candidate_confirmed` | current `needs_confirmation` branch, before any user confirmation | artwork_id, confidence, recognition_attempt_id | artwork/recognition | No | NO | NO |
| `result_viewed` | catalog or generated result selected | result_type, museum_id, recognition_attempt_id, confidence | artwork/status/AI candidate | Result viewed | YES | NO |
| `artwork_viewed` | catalog result only | result_type, museum_id, artwork_id, recognition_attempt_id | full linkage | No | YES | NO |
| `artwork_card_opened` | catalog card effect | artwork_id | artwork; museum absent | No | NO | NO |
| `artwork_card_read_time` | catalog card unmount | artwork_id, read_time_ms | artwork | No | NO | NO |
| `audio_started` | audio play begins | artwork_id, locale | artwork | No | NO | NO |
| `audio_completed` | audio ends | artwork_id, locale | artwork | No | NO | NO |
| `artwork_added` | auto sighting, manual/backfill, catalog/generated | artwork_id, source | result_type/artist/title; museum often absent | No | YES | NO |
| `artwork_favorited` | favorite added | artwork_id | result_type | No | NO | NO |
| `favorite_added` | same favorite-add action | artwork_id | result_type | No | YES | NO |
| `achievement_unlocked` | newly derived achievement | achievement_id | visit linkage only via identity/session | No | NO | NO |
| `mission_completed` | newly derived mission | mission_id | identity/session | No | NO | NO |
| `progress_viewed` | Progress render | museum_id, works_count | museum | No | YES | NO |
| `finish_visit_clicked` | complete action | works_count | museum absent | No | NO | NO |
| `visit_completed` | complete action | works_count | museum absent | No | NO | NO |
| `recap_viewed` | complete action | works_count | museum absent | Recap | YES | NO |
| `recap_generated` | Trophy/recap data generated | works_count, artists_count, duration_minutes, museum_id | value/achievement fields | No | NO | NO |
| `share_card_viewed` | generated card preview opened | works_count, museum_id | museum | No | NO | NO |
| `share_clicked` | share action | works_count, museum_id | museum | No | YES | NO |
| `share_started` | share action starts | works_count, museum_id | museum | No | NO | NO |
| `share_completed` | file/text/download succeeds | method | museum/artwork absent | No | YES | NO |
| `share_saved` | explicit save | works_count, museum_id | museum | No | NO | NO |
| `pwa_install_cta_shown` | Chromium install prompt available | none | device envelope | No | NO | NO |
| `pwa_install_cta_clicked` | user asks to install | none | device envelope | No | NO | NO |
| `pwa_install_prompt_accepted` | browser choice | platform | device envelope | No | NO | NO |
| `pwa_install_prompt_dismissed` | browser choice | platform | device envelope | No | NO | NO |
| `pwa_installed` | browser `appinstalled` | none | device envelope | No | NO | NO |
| `pwa_ios_instructions_shown` | iOS hint displayed | none | device envelope | No | NO | NO |
| `onboarding_completed` | Supabase SIGNED_IN event | auth_provider | anon/session; first-party user_id absent | No | NO | NO |

## Actual server events

| Event | Trigger | Fields/linkage | Active/Activation handling |
|---|---|---|---|
| `recognition_started` | `/v1/recognize` begins | museum and locale in properties; no identity/session/attempt | Identityless: excluded from visitor metrics. |
| `recognition_completed` | match/review/no-match result | museum, status, confidence, resolved artwork, recognition mode as available | Identityless: operational only. |
| `recognition_failed` | catalog/config/recognition failure | museum and reason | Identityless: operational only. |

## Reserved but not currently emitted

`seo_landing`, `recognition_succeeded`, `content_opened`, `mission_shown`, `paywall_viewed`, and `purchase_completed` exist in the TypeScript union but no current producer was found. They must not be counted as historical events. `recognition_succeeded` appears in admin success sets for future/backward compatibility; current effective success is `scan_success` plus status interpretation of `recognition_completed`.

## Contract defects to fix before trusted scale

- Mandatory fields are not server-enforced by event name.
- Public callers can spoof `user_id`, `anonymous_id`, `internal_test`, event name/time and dimensions.
- Several late-visit events omit museum/artwork.
- `candidate_confirmed` name is false today: it is emitted automatically.
- Client and server events do not share attempt ID.
- No event schema version or consent/version field exists.
