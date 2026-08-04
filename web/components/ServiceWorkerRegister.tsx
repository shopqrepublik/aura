"use client";

import { useEffect, useState } from "react";

// Registers sw.js scoped to "/" — the real app now lives at the root route
// (app/page.tsx), so the installed PWA experience covers the whole origin;
// /design (the dev-facing design system) is technically in scope too, but
// nothing in the app links to it, so no real visitor ever lands there.
//
// Also surfaces a minimal "Update available" banner: sw.js is generated
// with a fresh version stamp every build (see sw-template.js +
// scripts/stamp-service-worker.mjs) and calls skipWaiting()/clients.claim()
// on activate, so a new service worker takes control of already-open tabs
// automatically in the background — but the PAGE itself (already-loaded
// HTML/JS in memory) doesn't refresh itself just because the SW controller
// changed underneath it. "controllerchange" fires exactly when that
// happens; only prompt on a REAL update (a controller already existed),
// not on the very first-ever registration. Kept deliberately simple
// (fixed English copy, no i18n) since this renders in the root layout,
// outside the app's own locale state (lib/app-state.ts), and this is a
// rare, non-critical system-level notice, not app content.
export default function ServiceWorkerRegister() {
  const [updateAvailable, setUpdateAvailable] = useState(false);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      // registration is a progressive enhancement — the app works fine without it
    });

    let hadController = !!navigator.serviceWorker.controller;
    const onControllerChange = () => {
      if (hadController) setUpdateAvailable(true);
      hadController = true;
    };
    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);
    return () => navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
  }, []);

  if (!updateAvailable) return null;

  return (
    <button
      type="button"
      onClick={() => window.location.reload()}
      className="fixed top-3 left-1/2 -translate-x-1/2 z-[999] h-[36px] px-4 rounded-full bg-black text-white text-[13px] font-semibold shadow-[0_8px_24px_rgba(0,0,0,0.3)] active:scale-[0.98] transition-transform"
    >
      Update available · Tap to refresh
    </button>
  );
}
