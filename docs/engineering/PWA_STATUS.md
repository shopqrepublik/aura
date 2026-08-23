# PWA Status

Status: CURRENT code verification; physical-device verification separate.

## Verified in code/live HTTP

- Manifest `/manifest.json`, start `/visit`, scope `/`, standalone portrait, 192/512 normal/maskable icons.
- Service worker source `web/sw-template.js`; generated/stamped `public/sw.js` on prebuild/predev.
- Registration occurs on `/visit` through `ServiceWorkerRegister`, not all public SEO pages.
- New worker waits; user-triggered `SKIP_WAITING` prevents silent mid-visit replacement.
- Old named caches deleted on activation.
- Hashed Next/audio/icon assets cache-first.
- Cross-origin/API GET network-first with cached fallback; same-origin navigation/other GET stale-while-revalidate.
- Install analytics: CTA shown/clicked, prompt accepted/dismissed, installed and iOS instructions.
- Standalone detection covers display-mode/fullscreen/iOS navigator flag.

## Offline boundary

Cached shell/assets/pages can load. Recognition, uncached catalog/API content and provider images require network; there is no offline model. First-ever offline launch has no complete guarantee. POST recognition/events are not handled by SW caching.

## Requires physical-device test

- iOS Safari Add to Home Screen/install instructions and storage eviction.
- Android Chrome install prompt/standalone/camera.
- Camera permissions/orientation/background/resume.
- Web Share file/text/download behavior.
- Waiting-worker update during a long visit.
- Flaky network and offline restore with real prior cache.

## Known issue

Manifest description still says Musée d'Orsay, which is stale/globalization debt. Code verification is not a substitute for iOS/Android sign-off.
