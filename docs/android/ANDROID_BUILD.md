# ELYIO Android V1 build

Status: A2 shell built locally; no Play upload. The canonical packaging tool is Bubblewrap CLI `1.25.0`, which generates a TWA using Google Android Browser Helper `2.6.2`. The checked-in project is configured for `co.elyio.app` and `/visit`.

## Prerequisites

- Windows PowerShell, Node.js 18 or later (the build host currently has Node 22.21.0).
- Android Studio SDK/platform/build tools and JDK 17. Bubblewrap may install a private JDK under the user profile when explicitly accepted; do not commit it.
- `ANDROID_HOME`/`ANDROID_SDK_ROOT` and `JAVA_HOME` configured for the chosen toolchain.
- Production Digital Asset Links certificate is not available until Play App Signing is established. Debug association is separate.

## Commands

From repository root:

```powershell
npx --yes @bubblewrap/cli@1.25.0 init --manifest=https://www.elyio.co/manifest.json
# edit twa-manifest.json startUrl to https://www.elyio.co/visit, then:
npx --yes @bubblewrap/cli@1.25.0 update
npx --yes @bubblewrap/cli@1.25.0 build
```

For a checked-in project, build with the generated Gradle wrapper:

```powershell
Set-Location android
.\gradlew.bat assembleDebug
.\gradlew.bat bundleRelease
```

The release task signs only when all four environment variables are present; otherwise it produces an unsigned release bundle and fails no developer debug build. Example for the local non-Play test key (set in the current PowerShell session, never commit these values):

```powershell
$env:ELYIO_RELEASE_STORE_FILE = 'C:\Users\alexs\.elyio\elyio-upload.keystore'
$env:ELYIO_RELEASE_STORE_PASSWORD = '<local secret>'
$env:ELYIO_RELEASE_KEY_ALIAS = 'elyio-upload'
$env:ELYIO_RELEASE_KEY_PASSWORD = '<local secret>'
.\gradlew.bat bundleRelease
```

Expected outputs are `android/app/build/outputs/apk/debug/app-debug.apk` and `android/app/build/outputs/bundle/release/app-release.aab`. An AAB signed with the local test key is an internal test artifact, not Play-ready production signing.

Verified on 2026-09-05: `assembleDebug`, `bundleRelease`, and `lint` pass. The debug APK is approximately 5.1 MB; the release AAB is approximately 1.0 MB and is signed with the local test/upload certificate. Physical-device camera and App Links verification remain open gates.

## Signing

Never commit keystores, private keys, passwords or `*.jks`/`*.keystore`. Debug uses the local Android debug key. Release references a local or CI-only keystore through Gradle properties/environment variables, for example `ELYIO_RELEASE_STORE_FILE`, `ELYIO_RELEASE_STORE_PASSWORD`, `ELYIO_RELEASE_KEY_ALIAS`, and `ELYIO_RELEASE_KEY_PASSWORD`. CI secrets must be supplied by the runner, not checked into this repository.

The final Play build should use Google Play App Signing. Asset Links must contain the Play app-signing SHA-256 certificate, not the upload certificate. Until Play setup exists, publish no production fingerprint and keep the generated endpoint empty or limited to an explicitly documented debug/test host. A debug APK can use a test association with its debug SHA-256 on a test origin.

## Build safety

The Android shell must not enable cleartext traffic, arbitrary WebView navigation, JavaScript bridges, service-worker caching or debug mode in release. Run Gradle lint and manifest/URL/assetlinks checks before producing an internal artifact. A physical Android camera test is required before calling any artifact release-ready.
