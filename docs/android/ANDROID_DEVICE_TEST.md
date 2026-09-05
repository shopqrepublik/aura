# ELYIO Android V1 physical-device test matrix

Status: checklist prepared by A2; **NOT VERIFIED** until run on physical Android hardware. Record device model, Android version, browser/provider version, APK/AAB version, network and consent state for every case.

| ID | Scenario | Expected |
|---|---|---|
| A | Cold launch | TWA opens `https://www.elyio.co/visit`; scanner-first; no login/location gate. |
| B | Scanner load | No black/stuck camera; status and insets are usable. |
| C | Camera allow | Browser permission appears; preview starts; rear camera preferred. |
| D | Camera deny | Localized recovery UI; shutter cannot dead-end; recognition remains conceptually available after retry/settings. |
| E | Camera recovery | Regrant in browser/Android settings, return to app, preview reacquires. |
| F | Rear capture | JPEG is nonblank, correctly oriented, 512px wide/proportional; no microphone permission. |
| G | Known artwork | Existing catalog recognition and result story render. |
| H | AI-only artwork | Existing unknown/catalog-miss AI path renders useful result. |
| I | Scan another | Result returns to scanner and second capture works. |
| J | Background/resume | Lock, app switch and return release/reacquire camera safely. |
| K | Android Back | Modal closes; result returns scanner; scanner root exits/backgrounds without marketing landing. |
| L | Location allow | Optional museum context enriches later recognition; no blocking screen. |
| M | Location deny | Scanner and recognition work with null museum context. |
| N | Offline launch | Native/TWA retry state is readable; no blank Chromium dead end. No worker is enabled. |
| O | Network loss during recognition | Recoverable error, Reference ID when supplied, explicit user retry. |
| P/Q/R | EN / FR / zh-Hans | Scanner, consent/settings, errors and result UI use selected locale. |
| S | External link | Privacy/support/social/museum URLs leave trusted fullscreen UI as intended. |
| T | Deep link | Verified EN/FR/ZH, `/visit`, museum and artwork links open requested destination. |

Additional release-gate checks: clean and previously controlled browser profiles, storage clear/eviction, reinstall, captive portal, DNS/TLS/5xx, process death, rotation, low-memory pressure, Web Share file/text, App Links verification, no service-worker controller/registration/cache, debug vs release manifest, and no release debugging flag.
