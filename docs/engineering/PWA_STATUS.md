# PWA Status

Status: CURRENT source verification, 2026-09-05, commit `b8046c8aead4ce208a6b116c140812960a56fbe3`. Physical-device/browser-profile verification is separate.

## Current safe architecture

ELYIO intentionally has **no active application service worker**. The previous caching description in this document was obsolete following the 2026-09-03 recovery change.

- `web/app/layout.tsx` mounts `ServiceWorkerRegister` globally. Despite its historical name, the component registers nothing: it unregisters existing service workers and deletes `elyio-*` Cache Storage entries.
- `web/sw-template.js` is stamped into `web/public/sw.js` by the existing predev/prebuild script. This is a recovery worker for already-registered clients, not an offline/cache implementation.
- Recovery installs with `skipWaiting`, clears ELYIO caches, temporarily claims clients, attempts same-origin client navigation after a delay, then unregisters. It has no fetch handler and does not intercept HTML/API/image requests.
- An old client can remain controlled during recovery until navigation/reload. Source and HTTP inspection do not prove every existing profile has recovered. The accepted steady state is a null controller, zero registrations and zero ELYIO Cache Storage entries.
- Keep the recovery URL available to old registrations. Do not reactivate worker caching to satisfy an Android packaging checklist.

This constraint concerns service-worker interception/caching. Normal browser HTTP caching, Next image optimization and existing application localStorage are distinct: current visit state can include camera data URLs and pending retry base64. Do not describe the application as having no local image persistence.

## Manifests and install assets

- `/manifest.json`: ELYIO name/description, `start_url: /en`, scope `/`, standalone portrait, normal/maskable 192/512 icons, theme/background colors.
- `/manifest/{en|fr|zh-hans}`: localized start URLs. The current `lang` values are display names rather than BCP 47 tags; correction is planned, not implemented by this documentation audit.
- `/visit` is the scanner entry. `/en`, `/fr`, `/zh-hans` are public landing pages; do not assume the current manifest launches the scanner.
- `web/lib/pwaInstall.ts` handles install events, standalone/fullscreen detection and install analytics. Home-screen promotion follows demonstrated value. An Android package must avoid redundant install promotion.
- Public HTTP checked on 2026-09-05: main/French manifests and recovery `/sw.js` return 200. This does not certify browser installability or a physical Android package.

## Offline boundary

There is no guaranteed cold offline application shell and no offline recognition model. An already loaded page may continue showing current state, but recognition needs the backend. A network failure retains a retry image in the current implementation; this is application state, not service-worker replay. Full offline navigation/reload can fail. Never promise that localStorage history makes the hosted application itself launch offline.

For Android, the selected TWA architecture proposes a native offline/retry launch screen without changing the web worker policy. Mid-navigation network failure still requires device proof. See the canonical [Android architecture and roadmap](../android/ANDROID_ARCHITECTURE.md).

## Verification still required

- Fresh browser and previously controlled-profile recovery: null controller, no registrations or ELYIO Cache Storage after recovery/reload; navigation to landing, scanner and guide paths.
- Android Chrome/TWA and iOS Safari installation/standalone behavior and manifest diagnostics.
- Physical rear camera, capture, permission denial/recovery, orientation, background/resume.
- Web Share file/text/download and user-activation behavior.
- Cold/repeat offline launch, network loss during recognition/navigation, and recovery without enabling a worker.
- Browser storage clearing/eviction and Android uninstall/reinstall semantics.

`web/scripts/pwa-runtime-check.mjs` contains no-controller/no-registration/no-cache guards. Its browser/HTTP tests are useful evidence when run, but do not replace hardware camera or packaged-app testing. It was inspected, not executed, during Android A1.
