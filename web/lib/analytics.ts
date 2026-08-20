"use client";

import posthog from "posthog-js";
import { BACKEND_URL } from "./api";

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
  | "app_opened"
  | "seo_landing"
  | "seo_begin_visit"
  | "session_started"
  | "onboarding_completed"
  | "language_selected"
  | "museum_selected"
  | "visit_started"
  | "recognition_started"
  | "recognition_succeeded"
  | "recognition_completed"
  | "recognition_failed"
  | "catalog_match"
  | "catalog_no_match"
  | "scan_attempt"
  | "scan_opened"
  | "image_captured"
  | "scan_success"
  | "scan_failed"
  | "candidate_confirmed"
  | "result_viewed"
  | "artwork_viewed"
  | "artwork_card_opened"
  | "content_opened"
  | "artwork_card_read_time"
  | "audio_started"
  | "audio_completed"
  | "artwork_added"
  | "artwork_favorited"
  | "favorite_added"
  | "mission_shown"
  | "mission_completed"
  | "achievement_unlocked"
  | "progress_viewed"
  | "finish_visit_clicked"
  | "visit_completed"
  | "recap_viewed"
  | "recap_generated"
  | "second_scan_started"
  | "share_card_viewed"
  | "share_clicked"
  | "share_saved"
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

const ANON_KEY = "elyio-anonymous-id";
const SESSION_KEY = "elyio-session-id";

function uuid() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function getOrCreateStoredId(storage: Storage, key: string) {
  let value = storage.getItem(key);
  if (!value) {
    value = uuid();
    storage.setItem(key, value);
  }
  return value;
}

function getAnonymousId() {
  try {
    return getOrCreateStoredId(window.localStorage, ANON_KEY);
  } catch {
    return undefined;
  }
}

function getSessionId() {
  try {
    return getOrCreateStoredId(window.sessionStorage, SESSION_KEY);
  } catch {
    return undefined;
  }
}

function parseUtm() {
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get("utm_source") || undefined,
    utm_medium: params.get("utm_medium") || undefined,
    utm_campaign: params.get("utm_campaign") || undefined,
    utm_content: params.get("utm_content") || undefined,
  };
}

function deviceType() {
  const ua = navigator.userAgent;
  if (/ipad|tablet/i.test(ua)) return "tablet";
  if (/mobile|iphone|android/i.test(ua)) return "mobile";
  return "desktop";
}

function osName() {
  const ua = navigator.userAgent;
  if (/iphone|ipad|ios/i.test(ua)) return "iOS";
  if (/android/i.test(ua)) return "Android";
  if (/windows/i.test(ua)) return "Windows";
  if (/mac os|macintosh/i.test(ua)) return "macOS";
  return "other";
}

function browserName() {
  const ua = navigator.userAgent;
  if (/edg/i.test(ua)) return "Edge";
  if (/crios|chrome/i.test(ua)) return "Chrome";
  if (/firefox|fxios/i.test(ua)) return "Firefox";
  if (/safari/i.test(ua)) return "Safari";
  return "other";
}

function sendFirstPartyEvent(event: EventName, properties?: Record<string, unknown>, landing: Record<string, unknown> = {}) {
  if (typeof window === "undefined") return;
  const payload = {
    event_id: uuid(),
    event_name: event,
    occurred_at: new Date().toISOString(),
    anonymous_id: getAnonymousId(),
    session_id: getSessionId(),
    museum_id: typeof properties?.museum_id === "string" ? properties.museum_id : undefined,
    artwork_id: typeof properties?.artwork_id === "string" ? properties.artwork_id : undefined,
    recognition_attempt_id: typeof properties?.recognition_attempt_id === "string" ? properties.recognition_attempt_id : undefined,
    properties: { ...landing, ...properties },
    source: typeof landing.source === "string" ? landing.source : undefined,
    referrer: document.referrer || undefined,
    ...parseUtm(),
    language: navigator.language,
    device_type: deviceType(),
    os: osName(),
    browser: browserName(),
    path: `${window.location.pathname}${window.location.search}`,
  };
  const body = JSON.stringify(payload);
  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      if (navigator.sendBeacon(`${BACKEND_URL}/v1/events`, blob)) return;
    }
  } catch { /* event transport must never interfere with the visit */ }
  void fetch(`${BACKEND_URL}/v1/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => undefined);
}

export function track(event: EventName, properties?: Record<string, unknown>) {
  ensureInit();
  if (typeof window === "undefined") return;
  let landing: Record<string, unknown> = {};
  try {
    const stored = window.sessionStorage.getItem("elyio-organic-landing");
    if (stored) landing = JSON.parse(stored) as Record<string, unknown>;
  } catch { /* attribution must never interfere with the visit */ }
  sendFirstPartyEvent(event, properties, landing);
  if (!KEY) return;
  posthog.capture(event, { ...landing, ...properties });
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
