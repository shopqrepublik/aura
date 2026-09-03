# Analytics Event Contract

Status: CURRENT, schema version `2`. Producers are `web/lib/analytics.ts`, `web/lib/app-state.ts`, and backend recognition in `backend/app/main.py`.

## Envelope

Required: `schema_version=2`, UUID `event_id`, allowlisted `event_name`. Browser events normally include UUID `anonymous_id` and `session_id`. Optional bounded fields are `recognition_attempt_id`, `museum_id` (canonical institution ID), `artwork_id`, `client_occurred_at`, `properties`, acquisition/referrer/UTM, language/device/browser/OS and path. `occurred_at` is accepted only for schema-v1 rolling compatibility and is never canonical. `user_id` is forbidden in public payloads; valid bearer auth is resolved server-side.

Unknown events and malformed envelopes return 422; spoofed `user_id` or invalid dimensions return 400; conflicting identities return 409; oversized bodies return 413; rate excess returns 429. Reusing an `event_id` is idempotent.

## Public allowlist

| Area | Exact event names | Business role |
|---|---|---|
| Session/onboarding | `session_started`, `app_opened`, `language_selected`, `onboarding_completed`, `seo_begin_visit` | Raw/client-observed; not Active by itself |
| Museum/visit | `museum_selected`, `visit_started`, `visit_completed`, `finish_visit_clicked` | Selection/start are meaningful Active actions |
| Scan UX | `scan_opened`, `image_captured`, `scan_attempt`, `second_scan_started` | `scan_attempt` meaningful UX; denominator is attempt ledger |
| Recognition companions | `recognition_started`, `recognition_completed`, `recognition_failed`, `scan_success`, `scan_failed`, `catalog_match`, `catalog_no_match`, `candidate_confirmed` | Raw diagnosis only for recognition KPIs |
| Result/content | `result_viewed`, `artwork_viewed`, `artwork_added`, `artwork_card_opened`, `artwork_card_read_time`, `artwork_favorited`, `favorite_added`, `audio_started`, `audio_completed` | Artwork dimensions validated |
| Game/recap/share | `achievement_unlocked`, `mission_completed`, `progress_viewed`, `recap_generated`, `recap_viewed`, `share_card_viewed`, `share_clicked`, `share_started`, `share_completed`, `share_saved` | Selected completion actions are meaningful |
| PWA | `pwa_install_cta_clicked`, `pwa_install_cta_shown`, `pwa_install_prompt_accepted`, `pwa_install_prompt_dismissed`, `pwa_installed`, `pwa_ios_instructions_shown` | Raw/client-observed; not Active alone |

Adding an event requires updating the producer taxonomy, backend allowlist, tests and this contract; increment schema version for incompatible semantic changes.

## GA4 funnel contract

GA4 is an additional consent-gated acquisition destination; it does not replace or rename the first-party schema above. Its canonical events are `begin_visit`, `camera_opened`, `scan_started`, `artwork_recognized`, `recognition_failed`, `story_viewed`, `museum_guide_opened`, and the secondary reliable browser signals `pwa_install_prompt` and `pwa_installed`. `artwork_recognized` is the activation event; key-event configuration remains a GA4 property setting and is not performed in code.

Allowed GA4 parameters are factual, bounded, non-PII values already present at the action: `locale`, `museum_slug`, `museum_city`, `recognition_mode` (`catalog`, `ai_fallback`, `other`), `source_surface`, `artwork_id`, and `catalog_status`. Camera/image content, image URLs, user-entered text, identity data, model scores, tokens and precise location are never sent. `begin_visit` is emitted by the actual CTA click, `camera_opened` when a selected museum opens the scanner, `scan_started` on submission, recognition terminal events from the real response/error branch, and `story_viewed` only when the result is opened.

## Recognition linkage

One `recognition_attempt_id` is shared by scan/recognition events, backend request/row/response, terminal companions and relevant result/artwork events. The server-owned terminal outcome is the business fact. `success` and `uncataloged_result` are successful; `no_match`, `invalid_image`, `timeout`, and `failed` are failed. `institution_not_ready` is operational configuration state and not a valid visitor-attempt KPI.

## Dimension integrity

`museum_id` remains the backward-compatible field name for an Institution ID. Institutions must exist and be active. Artwork-bearing event types must reference an existing artwork and, when institution is supplied, it must own that artwork. Recognition institution/artwork/outcome comes from server execution. An uncataloged result has no fabricated catalog artwork ID.

## Internal QA and legacy

Normal browsers cannot set internal status. A server-secret QA header produces `internal_test=true`; payload properties with that name are removed. Raw diagnostics may include QA, while founder KPI excludes it. Client events have trust `CLIENT_VALIDATED_V2`; backend operations use `SERVER_OPERATIONAL`; pre-v2 data uses `LEGACY_UNVERIFIED` and is excluded from trusted KPI definitions.
