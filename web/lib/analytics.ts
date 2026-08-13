"use client";

import posthog from "posthog-js";

// PostHog (§13) -- the tool the original product spec names directly
// ("PostHog or equivalent", §13). No-ops entirely (init and every
// track/identify call become cheap no-ops) when NEXT_PUBLIC_POSTHOG_KEY
// isn't set, so local dev without a key, and any environment that hasn't
// opted in yet, never sends anything.
//
// Region: the actual PostHog project backing production is on US Cloud
// (NEXT_PUBLIC_POSTHOG_HOST in Vercel is us.i.posthog.com, confirmed live
// via network traffic) -- the code default below used to be eu.i.posthog.com
// on the assumption this would run on EU Cloud for the Paris museum pilot's
// GDPR posture, but that was never actually true in production and nobody
// caught the mismatch. Product decision (resolved, 2026-08, reviewed with
// the user): stay on US Cloud rather than migrate (PostHog can't move an
// existing project's region in place) -- but the default here now matches
// where data actually goes instead of where it was originally assumed to
// go, and HomeScreen's privacy_footer_note (lib/i18n.ts) says so too.
const KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com";

let initialized = false;

function ensureInit() {
  if (initialized || !KEY || typeof window === "undefined") return;
  posthog.init(KEY, {
    api_host: HOST,
    // Only the explicit, named events below are ever sent -- no autocapture
    // of clicks/inputs, no session replay, no page-leave heuristics. This is
    // what makes the "anonymized visit analytics" framing in HomeScreen's
    // footer copy (i18n key: privacy_footer_note) actually true.
    //
    // autocapture only covers DOM click/change capture -- heatmaps, dead-click
    // detection and Web Vitals are separate opt-in channels that otherwise
    // fall back to the PostHog project's own remote dashboard toggles (caught
    // live: production was fetching web-vitals.js and dead-clicks-autocapture.js
    // with autocapture already off). All three are disabled explicitly here so
    // this doesn't depend on the project's dashboard settings staying a
    // particular way.
    autocapture: false,
    capture_pageview: false,
    capture_heatmaps: false,
    capture_dead_clicks: false,
    capture_performance: false,
    disable_session_recording: true,
    // A distinct_id exists (auto-generated, anonymous) from first load for
    // pre-auth events like language_selected, but no Person profile is
    // created for it -- profiles (and their cost/exposure) only start once
    // identify() below runs, i.e. once someone actually has a real user_id.
    // PostHog's default behavior on identify() merges that anonymous id's
    // prior events into the resulting Person automatically.
    person_profiles: "identified_only",
  });
  initialized = true;
}

// Kept in sync with the required-events list in AURA_MVP_Product_Technical_Spec_v1.1.md
// §13. paywall_viewed / purchase_completed are listed here on purpose even
// though nothing calls track() with them yet -- monetization (§14) isn't
// built. They stay defined so the eventual paywall screen has a name to
// call rather than inventing one later.
export type EventName =
  | "onboarding_completed"
  | "language_selected"
  | "museum_selected"
  | "visit_started"
  | "recognition_started"
  | "recognition_completed"
  | "recognition_failed"
  | "catalog_match"
  | "catalog_no_match"
  | "scan_attempt"
  | "scan_success"
  | "scan_failed"
  | "candidate_confirmed"
  | "result_viewed"
  | "artwork_card_opened"
  | "artwork_card_read_time"
  | "audio_started"
  | "audio_completed"
  | "artwork_added"
  | "artwork_favorited"
  | "mission_completed"
  | "visit_completed"
  | "recap_viewed"
  | "recap_generated"
  | "second_scan_started"
  | "share_started"
  | "share_completed"
  | "paywall_viewed"
  | "purchase_completed"
  | "pwa_install_cta_shown"
  | "pwa_install_cta_clicked"
  | "pwa_install_prompt_accepted"
  | "pwa_install_prompt_dismissed"
  | "pwa_installed"
  | "pwa_ios_instructions_shown";

export function track(event: EventName, properties?: Record<string, unknown>) {
  ensureInit();
  if (!KEY || typeof window === "undefined") return;
  posthog.capture(event, properties);
}

// Called once a Supabase session resolves to a real user. Only the id is
// sent as the distinct_id -- deliberately no email/name/PII as person
// properties, so a PostHog person profile identifies *which* anonymized user
// did something, not who they are by name/email.
export function identify(userId: string) {
  ensureInit();
  if (!KEY || typeof window === "undefined") return;
  posthog.identify(userId);
}
