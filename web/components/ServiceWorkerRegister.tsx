"use client";

import { useEffect } from "react";

// Registers sw.js scoped to "/" — the real app now lives at the root route
// (app/page.tsx), so the installed PWA experience covers the whole origin;
// /design (the dev-facing design system) is technically in scope too, but
// nothing in the app links to it, so no real visitor ever lands there.
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      // registration is a progressive enhancement — the app works fine without it
    });
  }, []);

  return null;
}
