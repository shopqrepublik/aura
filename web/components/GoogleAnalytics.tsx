"use client";

import { useEffect, useState } from "react";
import {
  GA_CONSENT_KEY,
  GA_MEASUREMENT_ID,
  trackGoogleEvent,
  type GoogleConsentChoice,
} from "@/lib/analytics";

const CONSENT_FIELDS = {
  analytics_storage: "denied",
  ad_storage: "denied",
  ad_user_data: "denied",
  ad_personalization: "denied",
  wait_for_update: 500,
} as const;

const GRANTED_CONSENT_FIELDS = {
  analytics_storage: "granted",
  ad_storage: "denied",
  ad_user_data: "denied",
  ad_personalization: "denied",
} as const;

const DENIED_CONSENT_FIELDS = {
  analytics_storage: "denied",
  ad_storage: "denied",
  ad_user_data: "denied",
  ad_personalization: "denied",
} as const;

let consentDefaultsInitialized = false;
let gaBootstrapInitialized = false;
let gaConfigured = false;
let currentPageViewSent = false;

function localeFromPath() {
  const locale = window.location.pathname.split("/")[1]?.toLowerCase();
  return locale === "fr" || locale === "zh-hans" ? locale : "en";
}

function ensureConsentDefaults() {
  window.dataLayer = window.dataLayer || [];
  // Google documents the gtag shim with the Arguments object; keep this shape so gtag.js drains the queue correctly.
  // eslint-disable-next-line prefer-rest-params
  window.gtag = window.gtag || function gtag() { window.dataLayer?.push(arguments); };
  if (consentDefaultsInitialized) return;
  window.gtag("consent", "default", CONSENT_FIELDS);
  consentDefaultsInitialized = true;
}

function loadGoogleTag() {
  if (!GA_MEASUREMENT_ID || document.getElementById("elyio-ga4")) return;
  const script = document.createElement("script");
  script.id = "elyio-ga4";
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
  document.head.appendChild(script);
}

function sendCurrentPageView() {
  if (currentPageViewSent) return;
  window.gtag?.("event", "page_view", {
    page_location: window.location.href,
    page_title: document.title,
  });
  currentPageViewSent = true;
}

function initializeGrantedAnalytics() {
  if (!GA_MEASUREMENT_ID) return;
  ensureConsentDefaults();
  loadGoogleTag();
  if (!gaBootstrapInitialized) {
    window.gtag?.("js", new Date());
    gaBootstrapInitialized = true;
  }
  window.gtag?.("consent", "update", GRANTED_CONSENT_FIELDS);
  if (!gaConfigured) {
    window.gtag?.("config", GA_MEASUREMENT_ID, { send_page_view: false });
    gaConfigured = true;
  }
  sendCurrentPageView();
}

function updateConsent(choice: GoogleConsentChoice) {
  ensureConsentDefaults();
  if (choice === "granted") {
    initializeGrantedAnalytics();
    return;
  }
  // This UI asks only for analytics permission. Advertising consent must
  // remain denied unless ELYIO later presents a separate explicit choice.
  window.gtag?.("consent", "update", DENIED_CONSENT_FIELDS);
}

export default function GoogleAnalytics() {
  const enabled = process.env.NODE_ENV === "production" && Boolean(GA_MEASUREMENT_ID);
  const [choice, setChoice] = useState<GoogleConsentChoice | null | undefined>(undefined);

  useEffect(() => {
    if (!enabled) return;
    ensureConsentDefaults();
    let stored: GoogleConsentChoice | null = null;
    try {
      const value = window.localStorage.getItem(GA_CONSENT_KEY);
      stored = value === "granted" || value === "denied" ? value : null;
    } catch { /* consent can still be selected for this page load */ }
    queueMicrotask(() => setChoice(stored));
    if (stored) updateConsent(stored);

    let previousUrl = window.location.href;
    let previousGuide = "";
    const trackGuide = () => {
      const match = window.location.pathname.match(/^\/(en|fr|zh-hans)\/museums\/([^/]+)\/?$/i);
      if (match && match[2] !== previousGuide) {
        previousGuide = match[2];
        trackGoogleEvent("museum_guide_opened", { locale: match[1].toLowerCase(), museum_slug: match[2], source_surface: "direct" });
      }
    };
    const onNavigation = () => {
      if (window.location.href === previousUrl) return;
      previousUrl = window.location.href;
      trackGuide();
    };
    if (stored === "granted") trackGuide();
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    history.pushState = function (...args) { originalPushState.apply(this, args); queueMicrotask(onNavigation); };
    history.replaceState = function (...args) { originalReplaceState.apply(this, args); queueMicrotask(onNavigation); };
    window.addEventListener("popstate", onNavigation);

    const onClick = (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target.closest<HTMLElement>("[data-ga-begin-visit]") : null;
      if (!target) return;
      trackGoogleEvent("begin_visit", {
        locale: localeFromPath(),
        source_surface: (target.dataset.gaBeginVisit || "direct") as "landing_hero" | "landing_header" | "landing_footer" | "museum_page" | "direct",
      });
    };
    document.addEventListener("click", onClick);
    return () => {
      history.pushState = originalPushState;
      history.replaceState = originalReplaceState;
      window.removeEventListener("popstate", onNavigation);
      document.removeEventListener("click", onClick);
    };
  }, [enabled]);

  if (!enabled || choice !== null) return null;
  const locale = typeof window === "undefined" ? "en" : localeFromPath();
  const copy = locale === "fr"
    ? { title: "Votre choix de confidentialité", body: "ELYIO souhaite utiliser Google Analytics pour comprendre les parcours de visite. Aucun contenu de caméra ni donnée personnelle n’est envoyé.", reject: "Refuser", accept: "Accepter" }
    : locale === "zh-hans"
      ? { title: "您的隐私选择", body: "ELYIO 希望使用 Google Analytics 了解参观流程。不会发送相机内容或个人信息。", reject: "拒绝", accept: "接受" }
      : { title: "Your privacy choice", body: "ELYIO would like to use Google Analytics to understand visit journeys. Camera content and personal information are never sent.", reject: "Decline", accept: "Accept" };

  const choose = (next: GoogleConsentChoice) => {
    try { window.localStorage.setItem(GA_CONSENT_KEY, next); } catch { /* in-memory choice still applies */ }
    setChoice(next);
    updateConsent(next);
  };

  return (
    <aside className="ga-consent" aria-label={copy.title}>
      <div><strong>{copy.title}</strong><p>{copy.body}</p></div>
      <div className="ga-consent-actions">
        <button type="button" onClick={() => choose("denied")}>{copy.reject}</button>
        <button type="button" className="ga-consent-accept" onClick={() => choose("granted")}>{copy.accept}</button>
      </div>
    </aside>
  );
}
