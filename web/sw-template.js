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
  self.skipWaiting();
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
// serve stale JS/CSS. Same logic for our own generated audio files: once
// generated they don't change without a new filename/regeneration, and
// they're large enough (hundreds of KB each) that re-fetching on every
// play would be wasteful. Populates the cache opportunistically on first
// fetch rather than needing a hardcoded manifest of every chunk name.
function isImmutableAsset(url) {
  return url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/audio/");
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

// Everything else -- HTML navigations, manifest.json, and any other GET --
// always prefers the network, so a price/estimate/mission-copy/catalog
// update (all shipped as part of the JS bundle the HTML document
// references) is picked up the moment the user has a connection, not just
// whenever they happen to hard-refresh. Cache is only a fallback for
// genuinely being offline, updated opportunistically on every successful
// fetch so offline mode still reflects the last time the app was online.
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

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  e.respondWith(isImmutableAsset(url) ? cacheFirst(e.request) : networkFirst(e.request));
});
