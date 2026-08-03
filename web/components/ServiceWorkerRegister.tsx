"use client";

import { useEffect } from "react";

// Registers sw.js scoped to /app only — the installed PWA experience is the
// real app, not the / design-system landing page, so nothing outside /app
// needs to be (or should be) controlled by the service worker.
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/app" }).catch(() => {
      // registration is a progressive enhancement — the app works fine without it
    });
  }, []);

  return null;
}
