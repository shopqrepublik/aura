// Emergency recovery service worker. public/sw.js is GENERATED from this
// template by scripts/stamp-service-worker.mjs, which replaces CACHE_VERSION.
//
// P0 recovery, 2026-09-03: the previous worker controlled the whole origin
// and served HTML navigations from Cache Storage. That can strand existing
// users on stale landing/visit bundles and can surface Chrome ERR_FAILED when
// a controlled navigation has no cached response and the network fetch fails.
// Keep this file in place so already-registered browsers receive an update,
// but make the updated worker immediately remove itself and all ELYIO caches.
const CACHE_VERSION = "__SW_VERSION__";
const CACHE_PREFIX = "elyio-";
self.ELYIO_SW_RECOVERY_VERSION = CACHE_VERSION;

self.addEventListener("install", (e) => {
  e.waitUntil(self.skipWaiting());
});

self.addEventListener("message", (e) => {
  if (e.data === "SKIP_WAITING" || e.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith(CACHE_PREFIX)).map((key) => caches.delete(key))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll({ type: "window", includeUncontrolled: true }))
      .then((clients) => {
        for (const client of clients) client.navigate(client.url);
      })
  );
  self.clients.claim();
});
