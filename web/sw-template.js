// Source template for the service worker -- public/sw.js is GENERATED
// from this file by scripts/stamp-service-worker.mjs (wired as
// prebuild/predev in package.json), which replaces CACHE_VERSION below
// with a fresh value on every dev/build run. public/sw.js itself is
// gitignored; edit THIS file, never public/sw.js directly.
//
// Why the stamping exists at all: browsers only re-run a service worker's
// install/activate cycle when the SW SCRIPT'S BYTES change. This file's
// caching logic rarely changes, but app content (prices, mission text,
// catalog data -- all baked into the Next.js JS bundle, not this file)
// changes on almost every deploy. Without a version stamp forcing this
// file's bytes to differ every build, the browser has no signal that
// anything changed and can leave an already-open tab or installed PWA
// stuck on a months-old cached page indefinitely -- exactly what happened
// during local testing before this fix existed.
const CACHE_VERSION = "__SW_VERSION__";
const CACHE = `elyio-${CACHE_VERSION}`;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/", "/manifest.json"])));
  // Deliberately NOT calling self.skipWaiting() here. A freshly-installed
  // worker now PARKS in the "waiting" state instead of taking over
  // immediately -- it only activates once the page explicitly tells it to
  // (the "message" listener below), which only happens when a visitor taps
  // "Refresh" on ServiceWorkerRegister.tsx's update banner. A museum visit
  // can run 20+ minutes (see RecapScreen's own elapsed-time tracking);
  // auto-activating mid-visit would mean whatever's still-open tab's old,
  // already-loaded JS starts being served by a NEW SW's fetch handling
  // underneath it without a reload -- exactly the silent mid-session
  // content swap this design avoids. clients.claim() below still runs on
  // activate, but activate itself now only happens on request.
});

self.addEventListener("message", (e) => {
  if (e.data === "SKIP_WAITING" || e.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("activate", (e) => {
  // CACHE_VERSION changes every build, so CACHE is a new name every time --
  // this actually deletes every previous version's cache instead of the
  // old code's no-op (it only ever compared against a hardcoded "elyio-v1"
  // that never changed, so there was never an "old" name to clean up).
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

// Next.js fingerprints these by content hash (.../_next/static/.../abc123.js)
// -- if the content changes, the URL changes, so cache-first can never
// serve stale JS/CSS. Same logic for our own generated/static assets under
// /audio/ (60 TTS mp3s) and /icons/ (PWA manifest icons): once generated
// they don't change without a new filename, and the audio files run
// hundreds of KB each, so re-fetching on every play would be wasteful.
// Populates the cache opportunistically on first fetch rather than needing
// a hardcoded manifest of every chunk name.
function isImmutableAsset(url) {
  return (
    url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/audio/") || url.pathname.startsWith("/icons/")
  );
}

// The existing backend (lib/api.ts's BACKEND_URL) is a different origin
// from this SW's own scope, and carries per-request live data --
// recognition results, visit progress -- that must never be served stale.
// Cross-origin GETs in general (this also naturally covers the Wikimedia
// artwork photos <img> tags request) land here too: we don't control that
// origin's freshness, and per-artwork accent-color fallback already covers
// a slow/failed photo load at the UI level, so there's nothing to gain by
// caching those aggressively at the SW layer. Plain network-first, no
// matter how flaky the connection: the freshest available answer beats a
// fast stale one for anything in this bucket.
function isApiOrCrossOrigin(url) {
  return url.pathname.startsWith("/api/") || url.origin !== self.location.origin;
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(CACHE);
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw new Error("network-first: offline and no cache entry for " + request.url);
  }
}

// HTML navigations, manifest.json, and any other same-origin GET that
// isn't a hashed build asset -- answer from cache INSTANTLY when one
// exists (no network round-trip in the critical path at all), then refetch
// in the background and update the cache for next time. This replaces
// what used to be blocking network-first here: on the museum's stone
// walls / flaky WiFi, a visitor standing in front of a painting waiting on
// this app could be staring at a blank tab for however long that fetch
// took to resolve or fail at the TCP level (tens of seconds, not
// milliseconds) before ANYTHING painted. Stale-while-revalidate can't do
// that -- it always answers immediately once anything is cached. The
// tradeoff (a visitor can be looking at last-session's build for one cache
// cycle) is exactly what ServiceWorkerRegister.tsx's "Update available"
// banner exists to close: the moment the background refetch lands a new
// version, that component notices and offers an explicit, non-disruptive
// refresh -- never a silent mid-visit swap.
function staleWhileRevalidate(event) {
  const request = event.request;
  return caches.open(CACHE).then((cache) =>
    cache.match(request).then((cached) => {
      const networkUpdate = fetch(request)
        .then((response) => {
          if (response.ok) cache.put(request, response.clone());
          return response;
        })
        .catch(() => null);
      // respondWith(cached) below returns long before networkUpdate
      // settles -- waitUntil is what stops the browser from killing this
      // worker before the background refetch (and the cache.put it does)
      // finishes.
      event.waitUntil(networkUpdate);
      if (cached) return cached;
      // First-ever visit: nothing cached yet, so the network response IS
      // the only possible answer -- there's no faster fallback to prefer
      // over waiting for it here, unlike every other call site above.
      return networkUpdate.then((response) => {
        if (response) return response;
        throw new Error("stale-while-revalidate: no cache entry and network failed for " + request.url);
      });
    })
  );
}

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (isImmutableAsset(url)) {
    e.respondWith(cacheFirst(e.request));
  } else if (isApiOrCrossOrigin(url)) {
    e.respondWith(networkFirst(e.request));
  } else if (e.request.mode === "navigate" && url.pathname === "/visit" && url.searchParams.get("controlled-preview") === "1") {
    // Internal evidence collection must prefer the current comparison
    // engine instead of serving one stale HTML/build cycle.
    e.respondWith(networkFirst(e.request));
  } else {
    e.respondWith(staleWhileRevalidate(e));
  }
});
