"use client";

import { useEffect } from "react";

// P0 recovery, 2026-09-03: stop registering the origin-wide service worker.
// Already-registered browsers update through /sw.js, whose current script
// purges ELYIO caches and unregisters itself. This component runs globally
// so current clients also clean up any registration/caches directly.
export default function ServiceWorkerRegister() {
  useEffect(() => {
    const cleanup = async () => {
      try {
        if ("serviceWorker" in navigator) {
          const registrations = await navigator.serviceWorker.getRegistrations();
          await Promise.all(registrations.map((registration) => registration.unregister()));
        }
        if ("caches" in window) {
          const keys = await caches.keys();
          await Promise.all(keys.filter((key) => key.startsWith("elyio-")).map((key) => caches.delete(key)));
        }
      } catch {
        // The app must remain usable even if browser storage APIs fail.
      }
    };
    void cleanup();
  }, []);

  return null;
}
