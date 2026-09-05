# ELYIO Android V1 — architecture and production readiness

Status: A2 IMPLEMENTATION IN PROGRESS; TWA shell and web safety prerequisites being built; physical-device acceptance pending.

Audit date: 2026-09-05. Canonical Android document. No previous Android/mobile architecture document or Android project was found in the tracked repository.

## Decision and scope

**Choose TWA (Trusted Web Activity), using a small Android Browser Helper/Bubblewrap shell around the hosted production Next.js application.** Launch the existing `/visit` scanner, not the public landing page named by the current web manifest. Keep the existing FastAPI backend and recognition contract.

This choice preserves the browser camera runtime, hosted Next.js routes, same-origin storage and consent, web sharing, and ordinary frontend deployments. Guest identity, IndexedDB history and optional browser-based authentication can evolve on the web without requiring a native plugin system. The native application cannot directly read browser storage; that is an explicit boundary, not an assumed capability. See the [Android TWA overview](https://developer.android.com/develop/ui/views/layout/webapps/trusted-web-activities).

Verdict: **A. READY TO BUILD ANDROID V1**, beginning with a physical-device TWA proof. This is readiness to implement, not certification that a camera build or Play release has passed. The release gates below are mandatory. No intrinsic conflict requiring a service worker was established. If the no-worker build cannot pass the offline/navigation or camera gates, reopen this decision; do not relax the product invariants.

Frozen invariants:

- OPEN APP → CAMERA → SCAN → RESULT → SCAN ANOTHER. No account, email, Google login or onboarding form before scanning.
- Known museum → catalog path. Unknown museum/catalog miss → AI identification → optional catalog reconciliation → catalog result or AI result. Catalog grounding is preferred, not required.
- Backend baseline supplied by the owner: Fly v94, deployment `deployment-01M1QCT4VN5Y85RTST61XBBTCQ`, commit `b8046c8aead4ce208a6b116c140812960a56fbe3`. Local HEAD equals that exact commit. Fly release metadata and runtime environment were not independently queried in A1.
- `GENERIC_VISUAL_RETRIEVAL_ENABLED=false`. The source default is false in `backend/app/main.py`; do not change this flag, recognition algorithms, thresholds or provider configuration.
- No service-worker registration, navigation interception, or service-worker caching of HTML, API responses or images. Existing recovery code stays in place.
- Location is optional enrichment. Recognition must work with location denied, pending, unavailable, or outside every known museum.
- A1 changes documentation only. No production deployment, database mutation, recognition request, Android publication, account creation, SDK installation or signing-key generation.

## Evidence and verification boundary

CODE means inspected at the commit above. HTTP means a public read-only response inspected on the audit date. PROPOSED means future work, not an existing capability. Device behavior, GA property settings, provider dashboards, Play account ownership and signing credentials remain unverified unless explicitly stated.

Public HTTP observations:

| Resource | Observed |
|---|---|
| `https://elyio.co/en` | 308 to `https://www.elyio.co/en` |
| `https://www.elyio.co/manifest.json` | 200 JSON; `start_url: /en`; normal/maskable icons |
| `https://www.elyio.co/manifest/fr` | 200 JSON; `start_url: /fr`; `lang: Français` |
| `https://www.elyio.co/sw.js` | 200 JavaScript; recovery/unregister worker; no fetch handler |
| `https://www.elyio.co/.well-known/assetlinks.json` | 404 |
| `https://elyio.co/.well-known/assetlinks.json` | 308 to the www URL |

HTTP does not prove `navigator.serviceWorker.controller === null` on an existing visitor's device. A1 did not operate a physical Android camera, run a packaged APK, inspect a live browser profile, or verify GA event receipt. Existing browser regression scripts use mocked media; they are not camera evidence.

## Current frontend architecture — CODE

| Requested area | Actual implementation and evidence |
|---|---|
| Framework | `web/package.json`: Next.js **16.2.12**, React/React DOM **19.2.4**, TypeScript, Tailwind CSS 4. Hosted Next.js, not a static-export build. `frontend/` is a legacy vanilla-JS prototype, not the packaging target. |
| Routing | Next App Router in `web/app`. `/` permanently redirects to `/en`, preserving query parameters. `/en`, `/fr`, `/zh-hans` render public landing pages. `/visit` is the actual scanner entry with `directToScanner`. Localized museum, artwork and privacy routes exist; `/admin`, `/design` and controlled previews are separate. |
| In-app navigation | `web/components/ElyioApp.tsx` and `web/lib/app-state.ts`: React state switches `home`, `camera`, `card`, `progress`, `recap`. `goto()` persists state but does **not** push browser history. Browser/Android Back therefore does not yet implement the screen transitions. |
| Camera | `web/components/screens/CameraScreen.tsx`: `navigator.mediaDevices?.getUserMedia({video:{facingMode:"environment"}})`; `<video autoPlay playsInline muted>`, `srcObject`, explicit `play()`; stops tracks on unmount and for cancelled startup. No audio capture. |
| Capture | Same component: draw the full video frame to canvas, width 512, proportional height, `toDataURL("image/jpeg", 0.85).split(",")[1]`. Manual shutter; no automatic visual detection, native Camera API, gallery input, or Blob upload in the recognition path. |
| Geolocation | `web/lib/geolocation.ts`: GET `/v1/museums`, then one `getCurrentPosition`; nearest museum within its own geofence, calculated locally. Options: high accuracy, 10-second timeout, 60-second maximum age; separate 5-second UI watchdog. No continuous watch/background location. |
| Museum context | Nullable `museumId`, name, city in app state and persisted visit. `museumContextRef` provides current context to asynchronous recognition. Scanner mounts while detection runs; later GPS result or optional picker updates context. No coordinate fields in `RecognizeRequest`. |
| API client | `web/lib/api.ts`: browser `fetch`, JSON, AbortController timeout; recognition timeout 60 seconds. `NEXT_PUBLIC_BACKEND_URL` with development fallback `http://localhost:8090`. Public production origin appears as `https://api.elyio.co` in CSP/CORS. Optional Supabase bearer header; `museum_id` omitted when absent. |
| GA4 | `web/components/GoogleAnalytics.tsx`, `web/lib/analytics.ts`, landing CTA and result components. `gtag.js`, a web measurement ID from `NEXT_PUBLIC_GA_MEASUREMENT_ID`, explicit events and manual initial page view. Enabled bootstrap requires production mode and an ID. |
| Consent | `elyio-google-consent` stores `granted`/`denied`. Google tag loads only after grant; analytics/ad consent defaults denied; advertising fields remain denied on acceptance. `trackGoogleEvent` checks stored consent before enqueueing. This gate does not cover every other analytics transport. |
| Local storage | Current visit, anonymous ID, acquisition ID, Google consent, generated enrichment, optional comparison pack cache, iOS install dismissal and Supabase-managed sessions. Full inventory below. No IndexedDB implementation found in current frontend. |
| Manifest | `web/public/manifest.json`, `web/app/manifest/[locale]/route.ts`; standalone portrait, scope `/`, 192/512 normal and maskable icons, theme/background colors. Current starts are locale landing pages. Localized `lang` contains display names (`English`, `Français`, `简体中文`), not valid language tags; correct in a later packaging block. |
| PWA code | `web/lib/pwaInstall.ts`, HomeScreen promotion after demonstrated value, install/standalone analytics, head metadata/icons, worker stamping script. No Android wrapper, native plugins or Digital Asset Links file. |
| Service worker | Root layout mounts `ServiceWorkerRegister`, whose actual job is unregistering all registrations and deleting `elyio-*` caches. `web/sw-template.js` and generated `public/sw.js` are recovery workers; no fetch handler. See the corrected [PWA status](../engineering/PWA_STATUS.md). |
| Deep links | Public localized SEO URLs are addressable. `/visit?locale=...` works. Current recognition cards are state at `/visit`, not stable result URLs. No Android App Links/intent handlers. |
| Auth already present | **YES.** Supabase JS client, `useAuth`, email OTP/magic-link and Google OAuth methods, unreferenced `AuthModal` component, backend JWT verification, users and authenticated visit ownership. The active scanner tree does not render a mandatory auth modal or wait for auth loading. |

Comments and older documentation are sometimes stale: root route comments still describe an older manifest start; `ElyioApp` comments describe historical root behavior; older PWA documentation described active caching. Findings above follow executable code.

## Packaging evaluation

### Option A — TWA

| Dimension | Assessment |
|---|---|
| Code reuse / fit | Highest for this repository: retain hosted Next.js, server routes, client screens, API client and backend. Launcher URL must explicitly target `/visit`. |
| Camera | Uses the selected browser's web media implementation; strongest continuity with Android Chrome web behavior. Rear preference/canvas/JPEG path can remain. Physical-device proof is still required. |
| File/Blob | Browser canvas, Blob, File, object URLs and Web Share remain available subject to browser support and user activation. No native path conversion for recognition. |
| Geolocation | Keep browser geolocation without native location delegation in V1. Denial leaves null context/manual selection. |
| Permissions | Browser/site permission flow for camera and optional location. Proposed shell has only normal network permissions; no redundant native camera/location prompts. See exact model below. |
| Deep links | Verified Android App Links plus Digital Asset Links; validate incoming URLs and launch the canonical trusted origin. |
| GA4 | Existing HTTPS web stream and consent gate; no Firebase SDK needed for these events. Attribution/direct-entry gaps require small web fixes. |
| Offline | Hosted app cannot guarantee a cold offline scanner. Native offline/retry screen before every offline launch; loaded app retains recognition retry. Full navigation failure after launch is the main unresolved device gate. |
| Store readiness | Established Android packaging route, AAB/signing/App Links required. Functionality, privacy, testing and policy review still apply; TWA is not automatic Play approval. |
| Native extensibility | Adequate for V1. Guest history/auth/share remain web features. Native activities and a narrowly verified messaging channel are possible later; no general plugin access or direct browser-storage access. |
| Maintenance cost | Lowest application-code divergence; maintain Gradle/Android Browser Helper, manifests, links, signing and browser/device regression coverage. |
| Risks | Browser/provider dependency; permission state shared with browser origin; storage clearing/profile changes; missing DAL causes browser UI; React state not in Back stack; offline navigation; installed/PWA attribution ambiguity. |

The browser rendering/storage boundary is documented in the [TWA overview](https://developer.android.com/develop/ui/views/layout/webapps/trusted-web-activities). A future authenticated, origin-verified message channel is technically possible through [TWA postMessage](https://developer.chrome.com/docs/android/post-message-twa); it is not part of A2.

### No-service-worker compatibility

Do not equate TWA runtime with old PWA install-prompt checklists. TWA can launch before any worker is installed; Chrome's own [native offline-launch example](https://developer.chrome.com/docs/android/trusted-web-activity/offline-first) explicitly handles this case. There is no need to add a worker to render the HTTPS site in a TWA.

There is a real **offline quality gap**, not permission to enable caching. Historical [TWA quality guidance](https://blog.chromium.org/2020/06/changes-to-quality-criteria-for-pwas.html) treats browser error/offline failures as a quality problem. That 2020 article must not be used as a timeless claim that a fetch worker is an unavoidable Android requirement.

PROPOSED: adapt the native offline activity to **every** offline launch. Do not copy the example's `hasTwaLaunchedSuccessfully()` bypass: it assumes a worker will handle subsequent launches. Use current connectivity APIs; the old example's API choices are not a new-project template. Never cache/replay navigation responses to solve this.

Connectivity checks cannot guarantee the site is reachable: captive portals, DNS, TLS, 5xx and a connection lost immediately after launch remain possible. A2 must test supported browser navigation-failure callbacks and recovery/relaunch behavior. Do not claim the native guard replaces browser error pages in every case. An unrecoverable browser error/dead end is a release blocker; adding a service worker is not an accepted remedy.

### Option B — Capacitor

| Dimension | Assessment |
|---|---|
| Code reuse / fit | Reuses React screens and API types, but the supported bundled-assets approach needs an Android web entry/build boundary. Current `/visit` reads server `searchParams`; redirects/headers, dynamic routes and Next image optimization need review. Not a direct copy of the current hosted build. |
| Camera | `getUserMedia` can work in Android WebView with Android runtime CAMERA permission plus correct WebChromeClient resource grants. A native Camera plugin's separate capture UI is not the existing live scanner and is not needed by default. |
| File/Blob | Web JavaScript objects/canvas work; Web Share and blob downloads need device verification or a small native share adapter. Native camera outputs may be URIs, requiring conversion if introduced. |
| Geolocation | WebView origin permission handling or an explicit native adapter. Start with foreground approximate location only if implementing native enrichment; scanning never awaits it. |
| Permissions | CAMERA in shell; optional foreground location only for enrichment; no microphone or broad media/storage permission. Plugins and merged manifests must be inspected for additional requests. |
| Deep links | App Links delivered to Capacitor app URL handlers and mapped into the web state/router; auth callbacks need separate handling. |
| GA4 | Web gtag can execute, but bundled localhost origin/cookies/page URLs and attribution are different and need validation. Native Firebase is an option for a future app stream, not a prerequisite or a second event sender. |
| Offline | Bundled shell can open without network and without a worker. Recognition still needs network. Bundled shell is a capability advantage over TWA. |
| Store readiness | Standard native Android build/signing process, same Play review requirements. Remote loading does not remove review obligations. |
| Native extensibility | Strong plugin ecosystem for native storage, sharing, lifecycle and later auth. More power than this V1 needs. |
| Maintenance cost | Medium: Android + Capacitor/plugins + a compatible bundled frontend build, CORS/CSP differences and update compatibility. |
| Risks | WebView camera lifecycle/vendor differences, plugin bridge surface, different storage identity, native share glue, localhost CORS not currently allowed, Next export work and frontend release coupling. |

Capacitor's [`server.url` and `allowNavigation` configuration](https://capacitorjs.com/docs/config) is explicitly documented as not intended for production. Do not recommend pointing `server.url` at production as if it were a supported deployment architecture. A supported bundled approach is viable but costs more here. Next's [static-export limitations](https://nextjs.org/docs/app/guides/static-exports) explain why the existing server-backed routes cannot be assumed portable unchanged.

### Option C — custom hosted Android WebView shell (not selected)

Concrete reason to consider it: direct control over offline/error UI and native permission callbacks while keeping hosted Next.js deployments. It would reuse the hosted UI, browser JSON/base64 API client and consent code; WebView would require CAMERA grants, optional location callbacks, App Links routing, explicit external navigation and share/download support. No service worker is necessary, and native extensions are possible.

It also makes ELYIO responsible for WebView navigation, permission security, lifecycle, file access, sharing and any bridge. It has higher bespoke maintenance and camera/analytics compatibility risk than TWA, with the same Play obligations. It is not justified for A2 while TWA can be tested against the requirements. No React Native/Flutter rebuild: there is no repository-driven reason for one.

## Camera and recognition proof contract

The selected TWA preserves the existing capture transport described in the frontend table. The [browser capture documentation](https://web.dev/articles/media-capturing-images) covers live media and canvas capture. This establishes API feasibility, not successful testing of ELYIO on hardware.

Observed gaps to cover in A2 without changing recognition architecture:

- `facingMode: "environment"` is a preference, not an exact rear-lens guarantee. No `enumerateDevices`, selected `deviceId`, width/height constraint or lens switch exists. Confirm the actual rear stream on multi-camera phones; if needed, add a bounded camera-selection fallback after permission.
- `hasCamera` becomes true before a playable frame is proven; `play()` errors are swallowed. Shutter is disabled while scanning, not while the camera is unavailable. Missing permission currently leaves a gradient and a shutter that cannot capture. Add localized denial/unavailable/retry/settings guidance and disable capture until frames are ready.
- Capture checks `videoWidth`, but not `readyState` or a nonzero height. The preview uses `object-cover`; the captured full frame is not a crop to the on-screen guide. Preserve the existing JPEG dimensions/quality and test framing, orientation and aspect ratio.
- Tracks stop on component unmount, but there is no explicit `visibilitychange`, `pagehide`, track-ended or resume recovery. Test camera release on background/screen lock and reacquisition on return without a frozen preview or duplicate streams.
- Network retry sends the stored base64 again. A new frontend attempt UUID is generated for every invocation; a retry is not currently idempotent against the original attempt. Do not silently auto-replay uploads or alter ownership/idempotency in A2.
- HTTP errors preserve structured backend `recognition_request_id` in `RecognitionHttpError`. The camera displays the last six characters as Reference/Référence/参考 only in the network-retry branch. HTTP 4xx/5xx often fall into `not_identified` because `isRecognitionNetworkError` is transport-oriented. Some backend errors lack a reference. Do not invent a server Reference ID for a request that never reached the server. Preserve full diagnostics, and separately address visibility of real backend references in A2 error UI.

| Proof scenario | Required evidence / pass condition |
|---|---|
| Fresh install and first permission | Physical rear-camera preview, usable shutter, no sign-in/location gate; exact device, Android, browser and APK version recorded. |
| Capture | Decode a test capture locally: JPEG, width 512, valid proportional height, correct orientation, nonblank artwork. Never log visitor base64. |
| Recognition | Capture reaches POST `/v1/recognize` using existing JSON fields; known-museum catalog, absent-museum AI and catalog-miss AI remain usable. Validate with approved fixtures/test environment; no bulk production benchmark. |
| Results | Catalog and AI result cards render; `Scan another` reopens a working camera; repeated scans keep optional context current. |
| Failures | Camera denied, one-time grant expired, OS camera disabled/in use, API timeout, offline, no match, 4xx/5xx, malformed response and delayed detail fetch produce recoverable UI. Reference retained when supplied. |
| Lifecycle | Back, rotate, lock/unlock, background/foreground, incoming interruption and process recreation do not strand the scanner or upload twice. |
| Storage pressure | Long visit/AI image storage quota failure does not prevent another scan. |

For Capacitor/custom WebView specifically, both runtime permission and `WebChromeClient.onPermissionRequest` handling are needed. Validate the full requesting origin, grant only requested video capture after OS approval, and deny other resources. Android warns against blindly granting the entire resource list in [`PermissionRequest`](https://developer.android.com/reference/android/webkit/PermissionRequest). Test autoplay, secure context, rendering/GPU, orientation, process death, blob sharing and vendor WebView updates separately. TWA does not embed this WebView layer.

## Exact proposed permissions and location UX

For the selected non-delegating TWA shell:

| Permission/capability | Model |
|---|---|
| `android.permission.INTERNET` | Normal install-time permission; hosted site/network requests. |
| `android.permission.ACCESS_NETWORK_STATE` | Normal install-time permission for native offline/retry launch UI; no runtime prompt. |
| Camera | Required user capability, requested by HTTPS `getUserMedia` in the browser. Browser manages site consent and its own Android CAMERA permission. Do **not** add a redundant ELYIO-native CAMERA request in this TWA design. |
| Location | Optional browser geolocation request only; no ELYIO-native `ACCESS_COARSE_LOCATION`/`ACCESS_FINE_LOCATION`, no location-delegation library/service. Site denial or browser OS denial remains valid. |
| Other permissions | No RECORD_AUDIO, background location, notifications, contacts, broad storage/media access, advertising ID or foreground camera service. Audio playback does not require microphone access. |

Chromium currently documents delegation for notifications/location, not camera, in its [permission-delegation implementation](https://chromium.googlesource.com/chromium/src/+/HEAD/chrome/android/java/src/org/chromium/chrome/browser/browserservices/permissiondelegation/README.md). Keep V1 on browser permission ownership; inspect generated/merged manifests and the actual provider prompt path in A2. A generated delegation service must not silently change this model. If native location delegation becomes necessary, make it a separate reviewed change, starting with optional foreground coarse permission and proving denial still works. Do not request fine location merely because the old web hook sets high accuracy. See [Play's minimum-scope permission guidance](https://support.google.com/googleplay/android-developer/answer/16558241?hl=en).

Scanner rendering/start never awaits location or museum list completion. Schedule any new location prompt after camera interaction has settled so prompts do not compete; prefer reusing a prior grant and an optional nearby-museum action for a fresh prompt. A timeout changes only optional context UI. Exact coordinates stay local in the current museum matching hook; only the selected museum enters recognition. The 5-second watchdog is not a scanner timer. Never restore a full-screen `Locating...` state.

## Analytics and consent

### Reuse one GA4 web implementation

Keep the current GA4 web property/stream instrumentation in the TWA. No Firebase SDK, native `screen_view` duplication, Measurement Protocol relay or second GA client identity in A2. Native launches need a non-secret `source=android` hint consumed by web instrumentation; this is attribution, never authorization. A standalone display-mode check alone cannot distinguish a Play app from an installed PWA.

| Required event | Existing producer / gap |
|---|---|
| `page_view` or equivalent | `GoogleAnalytics`: one manual current page view after grant, `send_page_view:false`. Module-level sent flag is not reset on SPA navigation; history hooks track museum guides, not additional page views. Audit enhanced-measurement settings to avoid duplicates; settings are not visible in this repo. |
| `begin_visit` | LandingVisitLink/delegated CTA listeners. Direct `/visit` launch has no CTA, so it does not currently emit this GA event. Add one consent-allowed scanner-entry event with a defined deduplication rule. |
| `camera_opened` | `startVisit` in app-state, before camera readiness; not every return to camera. Define/document scanner-open semantics and verify no duplicate on React state updater/re-entry; do not claim this event proves camera permission. |
| `scan_started` | `recognizeFrame`, once per submission, including manual retry. |
| `artwork_recognized` | Both catalog and uncataloged AI success paths. **Primary activation/key event.** Preserve both; GA Admin key-event configuration needs read-only verification later. |
| `recognition_failed` | No-match and exception branches. Preserve distinction in allowed parameters; HTTP failures must not be counted as activation. |
| `story_viewed` | Catalog CardScreen and UncatalogedCardScreen effects. Verify one intended display event per result, including return/locale behavior. |

Additional audit findings: GA museum/locale parameters sometimes read state while the recognition request correctly reads `museumContextRef`; this can mislabel a scan that races GPS. Some catalog recognition modes map to GA `other`. `localeFromPath()` in GoogleAnalytics reads `/visit` as English even when `?locale=fr` or `zh-hans` drives scanner language. Fix reporting/consent-language plumbing in A2, without changing recognition selection.

Capacitor/custom WebView could retain gtag, but a bundled local origin changes page/cookie semantics. Google documents a [WebView-to-Firebase event bridge](https://codelabs.developers.google.com/ga4f-event-tracking-webview) when an app stream is desired; that is an alternative architecture with consent and deduplication work, not a requirement to run this existing web instrumentation. It is unnecessary for the selected TWA.

### Consent audit and required adaptation

GA's current basic-consent behavior can be reused: no tag load before grant, no GA business-event enqueue before grant, ad consent always denied, no camera image or precise coordinates in explicitly typed GA business-event parameters. Declining analytics must leave recognition enabled. A late grant sends the current page view; do not retrospectively replay pre-consent scan events.

**Existing mismatch:** `track()` sends first-party `/v1/events`, invokes acquisition calls, and calls PostHog when configured without checking `elyio-google-consent`. `ensureInit()` also has no consent check. `PrivacyContent.tsx` says first-party events and PostHog are consent-gated; code does not establish that. Acquisition requests target `agent.elyio.co`, which is absent from current CSP `connect-src`; attempted transport is not evidence of successful production receipt. A1 did not inspect production PostHog configuration.

A2.5 must align optional analytics transports with a documented consent decision and accurate EN/FR/ZH privacy copy, preserving only explicitly defined operational processing required to serve recognition. Gate optional collection/SDK initialization; do not treat a possible CSP failure as a consent mechanism. Backend recognition-attempt persistence is separate operational behavior and must be disclosed and classified; the wrapper must not disable recognition persistence to implement GA consent.

Other concrete work: expose a way to change/revoke consent (current banner disappears after choice), apply denial immediately and handle known analytics cookies/storage, test storage-unavailable behavior (custom events reread localStorage despite the banner's in-memory choice), and sanitize page URLs before analytics. GA page views and acquisition touch use full `location.href`; auth hash stripping in `useAuth` is not a global guarantee that another component never sees a token. Never send auth fragments, guest credentials, emails, raw camera frames or precise location in page URLs/events.

TWA may reuse previously granted consent from the same browser profile and origin; an install does not imply consent. Different profiles or cleared site data require a fresh choice. Do not synthesize consent in native code or use browser permission grants as analytics consent.

### Privacy / Data Safety preparation

Reuse public localized privacy routes and existing controller/contact copy, subject to owner verification. Additional technical work is needed for the consent mismatch, clear-data/revoke UX, bounded local image retention and an accurate inventory of actual SDK/network behavior. Do not promise a deletion period absent from implementation: current backend attempts retain response payloads and current local visit can retain images. Inspect provider processing, server logs, backups and deletion mechanisms before completing declarations.

Inventory camera photos sent to the backend/model provider, pseudonymous IDs, interactions, diagnostics, optional museum/location-derived context, and optional account data if accounts become exposed. Local-only coordinates and off-device inferred museum information need separate treatment. Do not declare “no data collected” because the shell has no Firebase SDK. Assess collection, purposes, optionality, retention, deletion and provider sharing exceptions under the current [Play Data Safety instructions](https://support.google.com/googleplay/android-developer/answer/10787469). This is a preparation task; no declarations submitted in A1.

## URLs, App Links and language

Canonical web origin is **`https://www.elyio.co`**, with apex aliases redirecting there. TWA verified origin is the frontend; API, Supabase and museum websites are not additional trusted UI origins.

| Incoming destination | Proposed Android behavior |
|---|---|
| Launcher icon | `/visit?source=android`; scanner immediately. Native device locale may be passed as a separate allowlisted hint, used only when no explicit/stored user choice exists. |
| `/en`, `/fr`, `/zh-hans` (and `/`) | When opened as a verified external App Link, map to scanner with explicit supported locale where present. Ordinary browser navigation keeps the existing landing pages. |
| `/visit?locale=...` | Open scanner, preserve validated locale and bounded supported attribution fields. No login/QA gate inferred from the URL. |
| `/{locale}/museums` and `/{locale}/museums/{slug}` | Open the actual guide in app; its scanner CTA remains available. Do not discard a user's requested guide in favor of the camera. |
| `/{locale}/artworks/{slug}` | Open the existing public editorial page. Only configured slugs exist; this is not a permalink to an arbitrary recognition attempt. |
| Privacy | Accessible within the app from web UI. No need to claim privacy links as an Android entry point. |
| Admin/design/controlled preview, unknown paths and hosts | Do not claim as app destinations. Public web policy/auth continues to apply. |
| External museum/social/support links | Browser/Custom Tab or explicit mail handler, with normal origin UI. Never silently extend TWA trust or loop the URL back into ELYIO. |

No recognition result/visit permalinks exist. `seen` includes catalog and locally generated AI IDs; none is a server credential or share token. Current recap shares a PNG/text, not a durable guest visit URL. A3 can add explicit result sharing later, with publication/privacy semantics; never put base64 or an attempt/guest credential in a URL.

PROPOSED App Links setup: choose a final application ID (working proposal `co.elyio.android`, availability/owner approval pending); add HTTPS VIEW/DEFAULT/BROWSABLE filters with `android:autoVerify="true"` and explicit supported path scopes. Use separate well-understood host/filter definitions for `www.elyio.co` and `elyio.co`. Validate scheme, exact hostname, port, normalized path, locale and allowed query fields at entry; reject userinfo, deceptive suffix hosts, file/data/javascript/intent URLs and externally supplied redirect targets.

Serve `/.well-known/assetlinks.json` with a direct HTTPS 200 JSON response on **each** claimed host. Include `delegate_permission/common.handle_all_urls`, the final package, and Play **app-signing** certificate SHA-256. The apex redirect currently prevents this: add a narrowly scoped `.well-known` redirect exception in A2. A TWA with missing/incorrect trust can show browser chrome; do not hide failed verification. Debug certificates belong on test origins; the upload certificate is not a substitute for Play's runtime signing certificate. Verify installed release links using Android's [App Links verification procedure](https://developer.android.com/training/app-links/verify-applinks).

Locale audit: public routes use `en`, `fr`, `zh-hans`; scanner/API types use `en`, `fr`, `zh-Hans`. `/visit` parses an explicit query locale; app-state can restore a stored locale and otherwise defaults to English. No navigator-language-based UI detection was found; `navigator.language` is currently analytics metadata. Reuse `i18n.ts`, existing translated screens and route mapping. Proposed precedence: explicit App Link/user selection → stored choice → supported Android locale hint → English. Do not force the device hint on every launch over a saved choice. Correct manifest language tags and `/visit` consent language; add only minimal translated native splash/offline strings, not a second product translation system.

## Minimum shell and security boundary

Native: launcher/activity, packaged adaptive icon derived from existing artwork, splash/background colors, status/navigation bar and insets configuration, verified App Link parsing, provider selection with visible browser fallback, native offline/retry UI, and normal Android task behavior. No native tab bar, museum database, recognition pipeline, Firebase SDK or general JavaScript bridge.

Web: live camera, capture/compression, museum enrichment, recognition HTTP/error/result/retry flow, stories, progress/recap, local guest state, consent/analytics and outbound Web Share. Reuse [Web Share](https://web.dev/articles/web-share) with capability checks. Recap currently awaits asynchronous image preparation before `navigator.share` and catches all share failures as cancellation; test transient user activation and pre-prepare where needed. File download fallback and immediate object-URL revocation also need real-device coverage.

Android Back needs a small **web** history adapter because native TWA cannot inspect React state: dismiss an open sheet first, card/progress → camera, honor normal guide history, then exit/background at scanner root. Avoid extra entries per state update or duplicate uploads on popstate. System Back must not erase the current guest visit. Test predictive Back/current Android behavior and camera insets; current CameraScreen uses fixed top/bottom offsets.

| Security area | Audit / proposed control |
|---|---|
| Public API URL | Public URL is expected, not a secret. Production build must resolve HTTPS API, never localhost. Keep provider/admin/service-role keys server-side. Public Supabase config does not replace backend authorization. |
| CORS | Backend permits production apex/www and web development origins. TWA keeps the same production browser origin; no new allowance needed. Capacitor's bundled `https://localhost` is not currently allowed and would require scoped configuration. |
| CSP | Existing Next headers restrict scripts/connections/images, forbid framing and set HSTS/nosniff. `unsafe-inline` remains; do not describe this as a fully hardened nonce policy. Preserve existing policy through packaging. |
| Navigation | Trusted TWA origin only for fullscreen app UI. External origins receive browser UI. Android manifest scopes apply to incoming intents; they are not a sandbox for every same-origin web route. Backend auth protects admin data. |
| File/content URLs | No local file navigation or inbound file handling in TWA V1. Outbound browser share owns its file handoff. Do not expose filesystem paths or grant storage access. |
| Bridge | None in A2. Any future postMessage capability requires explicit origin verification, a tiny command schema and capability checks. No generic execute-JS, filesystem, HTTP or intent bridge. |
| Mixed content/TLS | HTTPS only. Do not allow cleartext, bypass certificates, ignore SSL errors or trust user-supplied certificates. Browser handles certificate validation; custom WebView must cancel SSL errors. |
| Deep links | Exact URL parsing/allowlist; app-source hints are not trusted identities. Strip auth fragments/secret query values from attribution. Do not expand trust to API/Supabase or wildcard subdomains. |
| Guest ownership | Existing anonymous IDs and attempt IDs are correlation identifiers. They are not sufficient proof for a future private-history read, deletion or account-claim endpoint. |

Android's [WebView bridge guidance](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges) describes the extra risk a Capacitor/custom bridge would introduce. TWA avoids that general bridge surface, but web XSS and backend authorization still matter.

## Guest identity, local history and optional accounts

### Existing identity/storage inventory

| Identifier/storage | Current lifetime and role |
|---|---|
| `elyio-anonymous-id` | localStorage UUID from `analytics.getAnonymousId`; stable until cleared/evicted, no explicit expiry. Sent to events and recognition; can be absent if storage fails. |
| `elyio-session-id` | sessionStorage UUID; browser browsing-context lifecycle, not a timed guest/account session. |
| `elyio-session-started` | sessionStorage event deduplication marker. Not an authorization/session token. |
| `elyio-acquisition-session` | localStorage `{id, expires}`, seven-day expiry; creation duplicated in API and analytics modules. Attribution, not guest identity. |
| `elyio-google-consent` | localStorage consent choice; independent of location/camera grants and auth. |
| `elyio-current-visit-v2` | localStorage serialized state with payload `version:1`; Sets converted to arrays. Includes locale, museum, seen/favorites, catalog/AI records, timestamps and potentially captured-image data URLs and pending retry base64. No history count/TTL bound. |
| `elyio.generatedArtworkEnrichment.v2:*` | Per-result generated enrichment in localStorage; not a persistent private guest database. |
| `elyio-comparison-v22-remote-lkg` | Optional validated comparison-pack last-known-good cache; not HTTP/worker caching. |
| `elyio-ios-install-dismissed` | localStorage install-promotion preference. |
| `elyio-organic-landing` | sessionStorage acquisition metadata. |
| `elyio-trusted-qa-token` | sessionStorage controlled-preview credential; exclude from Android app links and all analytics exports. |
| Supabase session | SDK-managed persistent/refreshing session storage; independent of anonymous IDs. Do not assume a stable browser cookie is an authenticated guest. |
| GA client ID / PostHog ID | Managed separately by their SDKs. No GA `client_id`/`user_id` wiring to recognition or guest ownership found. PostHog identifies a resolved Supabase user if configured. |

`RecognitionAttempt` stores `anonymous_id`, nullable authenticated `user_id`, `session_id`, nullable institution/artwork, outcomes and response JSON. `AnalyticsSession` checks conflicts when an existing session is reused. `AnalyticsIdentityLink` links an anonymous ID to a verified user and rejects reassignment to another user (`backend/app/admin.py`). These are useful foundations for attribution, not a secure guest credentials model.

There is no dedicated Guest/Visitor account model or authenticated anonymous history API. `Visit.user_id` is NOT NULL; `/v1/visits*` requires a verified Supabase user and checks ownership. The scanner starts regardless and catches failed `createVisit` calls. With no museum it does not create a backend visit at all. Local progress is the current guest path.

Security gap for A3: the recognition idempotency lookup returns a stored response by attempt UUID before an ownership comparison in `main.py`. UUID unpredictability is not a history-access policy. Do not build private history reads or account claims by treating knowledge of anonymous/attempt IDs as authorization. This finding does not authorize changing frozen recognition in A1/A2.

### A3 guest identity proposal (not implemented)

Separate an essential guest identity/credential from optional analytics identity and seven-day attribution. Scanning must remain possible when no guest credential can be persisted. A3 should define a backend-issued opaque credential or signed guest session, secure lifecycle/rotation/deletion, and an explicit guest ownership relation for visits/results. Existing IDs can support correlation and a local migration, but must not permit arbitrary historical server rows to be claimed by supplying an ID. Define safe authenticated ownership checks, conflict handling and idempotent optional account attachment before exposing history endpoints.

TWA guest state is origin/browser-profile state. Clearing browser site data can lose it; uninstalling the APK must not be assumed to clear browser storage. Reinstall, profile switching and backup behavior need explicit UX and testing. Native storage cannot be silently substituted for browser storage without a messaging design and migration.

### Local history proposal (not implemented)

| Option | Evaluation |
|---|---|
| localStorage | Reuse for small preferences/current-visit metadata and migration. Synchronous whole-state serialization, quotas and embedded base64 make it a poor long-term multi-visit/image store. Failures are currently caught and memory state continues. |
| IndexedDB | Recommended for later bounded recent results/current museum visit/last N history: asynchronous structured records and Blob thumbnails, schema migrations and indexes. Works in TWA without a service worker. Storage eviction still applies; does not make the hosted app launch offline. |
| Native preferences/database | Available through Capacitor or custom native integration, but TWA cannot access it directly. Unnecessary for V1/A3 local history; reconsider only for a demonstrated requirement. |

A3 should keep both catalog IDs and AI result snapshots, attempt linkage where available, language, museum provenance and timestamps; define N, thumbnail byte budget and retention explicitly. Migrate the current visit once, transactionally, with corrupt/quota fallback. Exclude retry payloads from long-lived history by default, provide clear/delete actions, and avoid persisting full photos unless necessary and disclosed. Current state stores one visit and resets on `newVisit`; it is not a multi-visit archive. “Recent discoveries” currently deduplicates IDs, so repeated sightings need an explicit history schema if each scan is to appear.

### Optional auth — future only

Frontend infrastructure is present: `supabase.ts`, `useAuth.ts`, `AuthModal.tsx`; the modal is not mounted by the current production scanner components. Email magic links and Google OAuth redirect to `window.location.origin`; there is no dedicated Android callback. Backend verifies ES256/JWKS tokens and the authenticated audience, upserts User and owns visits. Production provider configuration and delivery were not tested in A1.

Future UX may offer `Save your visit` after value, with Google/email/Not now. Implement a secure guest-to-account attachment workflow and validated callback/resume URLs then. TWA can keep OAuth in the browser; a WebView implementation should use a supported external browser auth flow, not assume embedded Google login works. Supabase session failure must not become a scanner gate; test expired/invalid optional tokens, since an invalid supplied token can currently return 401 even though absent auth is allowed. Account deletion requirements must be reviewed when enabling account creation. Do not activate auth UI or require a backend Visit in Android V1.

## Updates and Play preparation

| Change | TWA (selected) | Capacitor bundled | Custom hosted WebView |
|---|---|---|---|
| Backend recognition/content/data fix | Normal backend deploy; preserve contract | Same | Same |
| Frontend scanner/result/consent/product fix | Normal hosted web deploy | New bundled build/Play release by default; an OTA system would be a separate audited design | Normal hosted web deploy |
| Public guide/SEO update | Normal web deploy | Hosted pages update normally; bundled content needs release | Normal web deploy |
| Native icon/splash/dependency/SDK/permission change | Play release | Play release | Play release |
| Package/intent filter/native handler change | Play release; package ID is a durable identity | Same | Same |
| DAL certificate statement | Web change coordinated with actual signing identity; changing native identity/config also needs release | Same | Same |

An already loaded page may keep its old JS until a safe reload/relaunch; no-worker does not mean every open client hot-swaps instantly. Keep APIs backward compatible, use normal web rollback, and avoid force-reloading during a scan. Hosted JavaScript updates still must comply with Play policy; they are not a way to replace native binaries or evade review. See [Device and network abuse policy](https://support.google.com/googleplay/android-developer/answer/16559646?rd=2).

Preparation inventory, not a submission:

- Final application ID, display name and app ownership. Working ID `co.elyio.android` is a proposal, not reserved. Verify the publishing legal entity against the privacy controller, domain rights and existing Play account. Use owner-controlled account access and appropriate team roles; no personal contractor ownership of signing credentials.
- Play App Signing with a separate protected upload key; secure backup/CI secrets, signing certificate fingerprints for DAL, deterministic versionCode/versionName and release provenance. Produce AAB and device-installable test APKs. Follow [Android signing guidance](https://developer.android.com/studio/publish/app-signing).
- Verify target/compile SDK and toolchain immediately before A2.6/A2.8. On 2026-09-05 the [official target API page](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en) states Android 16/API 36 or higher for new phone apps/updates from 2026-08-31. This is dated evidence, not a permanent version constant or a chosen minSdk. Choose minSdk from supported devices/provider compatibility and test it separately.
- Owner/developer identity, contact/payment-profile and organization verification, including D-U-N-S if applicable. Account type/creation date are unknown; verify against [developer identity requirements](https://support.google.com/googleplay/android-developer/answer/10841920?hl=en).
- Public privacy policy matching actual Android/web processing, Data Safety inventory, ads declaration, target audience and IARC content rating. Existing `kids` explanation mode does not by itself determine the declared target audience; assess actual intended audience/content and applicable requirements.
- Adaptive launcher/store icon, phone screenshots of actual EN/FR/ZH app flows, feature graphic, localized title/short/full descriptions and support contact. Verify current Play asset dimensions/limits at preparation time; do not publish mock screenshots as tested behavior.
- Reviewer access instructions for guest scanning and representative artwork fixtures; no mandatory demo login. Demonstrate useful camera/result/story functionality and recoverable network errors under [Play functionality requirements](https://support.google.com/googleplay/android-developer/answer/9898783).
- Internal testing first, then required closed testing/production-access workflow for the actual account. Internal testing is not proof of public-release eligibility. Recheck [new personal-account testing rules](https://support.google.com/googleplay/android-developer/answer/14151465?hl=en) and any device-verification requirement; do not assume account type, tester count or duration.

No Play Console app, store listing, declaration, signing setup, upload or rollout was created in A1.

## Implementation roadmap and acceptance criteria

### A2.1 — TWA shell and no-worker launch proof

Create an isolated Android project using pinned, currently supported Bubblewrap/Android Browser Helper tooling; explicitly set the scanner start URL. Use a test origin for signing/DAL development. Add icon/splash/status bar and native offline/retry activity; browser fallback must be visible. Generated tooling must not create/register a web worker.

Acceptance: installable test APK; online launcher opens `/visit` with no registration/location gate; no runtime bridge/Firebase; merged permission list matches this document; no worker controller/registration/ELYIO Cache Storage after clean launch and recovery/reload on a previously controlled test profile. Repeat offline launch after a prior successful launch. Record browser/provider behavior, including unsupported-provider fallback. No production deployment in this proof.

### A2.2 — Physical camera, permission and lifecycle proof

Preserve getUserMedia/canvas JPEG; add only the camera readiness/permission recovery and lifecycle handling needed by the proof contract. Schedule optional location independently of scanner readiness, reuse translations and retain null context.

Acceptance: real rear camera/capture on at least a Pixel-class device, a Samsung device and a lower-memory device spanning the chosen minimum and current Android/provider versions. Permission deny/revoke/regrant, one-time grant, rotate, lock and resume all recover. JPEG dimensions/orientation verified; location denied/pending never disables shutter or displays blocking Locating UI. No microphone/storage/background permission prompts.

### A2.3 — Existing recognition contract and error integration

Exercise the existing API client and both result paths from the package. Use approved test fixtures/environment and mock deterministic error responses where appropriate; preserve frozen recognition backend and flag. Improve only caller/error presentation as required.

Acceptance: catalog, unknown-museum AI, catalog-miss AI, no-match, timeout/offline retry and HTTP error cases work; absent `museum_id` is omitted; latest optional museum context is used; request Reference survives when supplied; retry requires a user action; scan-result-scan repeats without duplicate background uploads. No new mandatory auth or visit API dependency.

### A2.4 — Back navigation, App Links, language and sharing

Add bounded web history integration and validated native link mapping. Prepare DAL/redirect exception and publish only in its separately authorized implementation workflow. Reuse existing locale system, preserve stored language, correct consent/manifest locale handling, and test recap file/text sharing and external URLs. Suppress redundant web-install promotion in the Android entry experience.

Acceptance: Back closes sheet/result before leaving scanner, guides retain their destination, all three locales work on cold/warm launch, exact supported paths verify with the installed signing certificate, apex/www DAL respond directly, malformed/unsupported links do not enter trusted UI, external links show their real origin, PNG/text share cancellation is harmless and successful sharing works without storage permission. Arbitrary recognition URLs are not falsely advertised as shareable.

### A2.5 — GA4, consent and privacy alignment

Retain one GA web transport; fix direct-entry `begin_visit`, page-view/screen definitions, locale/context attribution and consent gating discrepancies. Add reachable consent/clear-data controls and accurate localized privacy copy. No native Firebase or replay of pre-consent events.

Acceptance: unknown/declined choice produces no optional GA/PostHog/acquisition/product-analytics collection; any essential operational traffic is separately documented. Grant sends allowed events once, `artwork_recognized` covers catalog and AI activation, late consent does not replay earlier scans, revoke applies immediately, no auth token/photo/precise coordinate is exported. Verify receipt and key-event configuration in a test GA property, then document production configuration separately. Scanner works under every consent/storage choice. Complete the technical Data Safety inventory; do not submit it yet.

### A2.6 — Reproducible AAB, signing and release preparation

Finalize app ID/ownership, SDK/toolchain, versioning and protected signing workflow; prepare localized store assets and review instructions. A1 findings requiring runtime changes must be reviewed and tested before this build becomes a candidate.

Acceptance: signed reproducible release AAB plus installable test artifact; secrets absent from repository/bundle; current target requirement checked and dated; release signing fingerprint/DAL match; dependency and merged-permission inventory reviewed; store/privacy/testing prerequisites explicitly resolved or listed as remaining release blockers. No upload merely to finish this block.

### A2.7 — Device and adverse-network release gate

Run the entire camera proof matrix on release-signed artifacts. Test first/repeat offline launch, loss during capture/upload/guide navigation/full reload, captive portal, DNS/TLS/server failure, recovery, browser updates, long visits, memory pressure, reinstall and cleared browser storage. Existing mocked browser regressions supplement hardware tests; they cannot replace them.

Acceptance: recorded device/browser/build evidence; no white-screen/navigation dead end, no blocking location/auth, no lost scan-another path, correct consent and safe local-state recovery. Demonstrate TWA navigation failure/recovery without a worker. If this cannot pass, block A2.8 and reopen architecture rather than add caching. Log any transient browser error UI with its recovery evidence and review before release.

### A2.8 — Play internal testing release (future authorization/work block)

After A2.1–A2.7 pass and owner/account/privacy prerequisites are resolved, submit the approved AAB and declarations to the internal testing workflow; no public rollout. This roadmap does not authorize an A1 submission.

Acceptance: internal testers can install the Play-signed build; DAL verification and camera/denied-location/consent/three-language/scan-another checks pass from that install; distribution is restricted to testers; actual account-specific closed-testing/production requirements are documented. Public release remains a later decision.

### A3 — Guest identity and bounded history (separate block)

Implement the guest credential/ownership model, migration and IndexedDB history specified above before promising durable guest accounts or server-backed history. Optional account attachment belongs to a later retention block.

Acceptance: scan with no registration, absent/denied analytics and failed storage; stable guest across supported relaunches; authenticated ownership isolation; safe migration of current visit; bounded catalog/AI history and clear/delete UX; no cross-guest reads/claims based solely on UUIDs. No automatic account creation or login prompt to scan.

## A2 implementation record

- Bubblewrap CLI `1.25.0` is the selected generator/tooling version. The project target is `co.elyio.app`; this was not present elsewhere in the repository, docs, Firebase configuration or asset links before A2.
- `web/app/.well-known/assetlinks.json/route.ts` now emits a standard association statement from deployment-configured certificate fingerprints. `web/proxy.ts` preserves the apex canonical redirect while exempting the asset-links path so both claimed hosts can return direct responses. Production deployment of the fingerprint configuration remains required; a missing fingerprint intentionally returns an empty JSON array rather than a false association.
- Optional analytics transports now use the same explicit consent gate as GA4. A small persistent “Privacy / Analytics settings” control reopens the existing choice UI; denial remains non-blocking for scanning. Current-visit serialization applies an approximately 4 MB bound and removes older visitor-capture data URLs first.
- Additional canonical documents: [build](ANDROID_BUILD.md), [Play Data Safety inventory](PLAY_DATA_SAFETY.md), and [physical-device matrix](ANDROID_DEVICE_TEST.md).
- A2 local verification: debug APK and release AAB both build with Gradle 8.11.1; Android lint passes. The release AAB uses a local non-Play certificate (SHA-256 `DD:4B:A3:82:02:06:B6:A5:0D:32:92:02:05:39:5F:DF:25:F7:8E:3B:7E:A1:D0:0E:22:0F:EE:75:A8:C3:1A:95`) and is not a production Play-signed artifact. Web source now contains direct asset-link routes for both hosts, but the live endpoints remain unverified until the authorized web deployment supplies the release fingerprint. Browser history state is bounded to the existing screen state machine for Android Back; no recognition path was changed.
- A2 gate status: build-ready for physical-device testing, but not release-ready until the web asset-links route/fingerprint is deployed and verified on both origins, production consent changes are deployed/observed, and the physical matrix is run.

## A1 completion record

Production modified: **NO**. Recognition architecture/flag, frontend behavior, backend schema and live deployment unchanged. Unrelated existing working-tree files preserved.

Documentation-only verification: local/source references and Markdown links checked; diff checked for whitespace errors and changes outside documentation. No full frontend build was needed: `prebuild` stamps a generated worker file and would add unrelated mutation. Device, Android build, GA receipt and Play acceptance are explicitly future gates, not claimed test results.
