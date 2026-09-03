import { spawn } from "node:child_process";
import { setMaxListeners } from "node:events";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const urlArgIndex = process.argv.indexOf("--url");
const targetUrl = urlArgIndex >= 0 ? process.argv[urlArgIndex + 1] : process.env.PWA_CHECK_URL || "https://www.elyio.co";
const chromePath =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

let nextId = 0;

async function delay(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function cdpJson(port) {
  const res = await fetch(`http://127.0.0.1:${port}/json`);
  if (!res.ok) throw new Error(`/json failed: ${res.status}`);
  return res.json();
}

async function send(ws, method, params = {}) {
  const id = ++nextId;
  ws.send(JSON.stringify({ id, method, params }));
  while (true) {
    const raw = await new Promise((resolve, reject) => {
      ws.addEventListener("message", (event) => resolve(event.data), { once: true });
      ws.addEventListener("error", reject, { once: true });
    });
    const message = JSON.parse(raw);
    if (message.id === id) {
      if (message.error) throw new Error(`${method}: ${message.error.message}`);
      return message.result || {};
    }
  }
}

async function runtimeChecks() {
  const port = 9241;
  const profile = await mkdtemp(path.join(tmpdir(), "elyio-pwa-check-"));
  const chrome = spawn(chromePath, [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank",
  ], { stdio: "ignore" });

  try {
    let page;
    for (let i = 0; i < 80; i += 1) {
      try {
        const tabs = await cdpJson(port);
        page = tabs.find((tab) => tab.type === "page");
        if (page) break;
      } catch {}
      await delay(250);
    }
    if (!page) throw new Error("Chrome page target was not available");

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener("open", resolve, { once: true });
      ws.addEventListener("error", reject, { once: true });
    });
    setMaxListeners(1000, ws);

    await send(ws, "Runtime.enable");
    await send(ws, "Page.enable");
    await send(ws, "Network.enable");
    await send(ws, "Page.addScriptToEvaluateOnNewDocument", {
      source: `
        window.__elyioBipFired = false;
        window.addEventListener('beforeinstallprompt', () => { window.__elyioBipFired = true; }, { capture: true });
      `,
    });
    await send(ws, "Emulation.setDeviceMetricsOverride", {
      width: 390,
      height: 844,
      deviceScaleFactor: 3,
      mobile: true,
    });
    await send(ws, "Network.setUserAgentOverride", {
      userAgent:
        "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    });
    await send(ws, "Page.navigate", { url: targetUrl });
    await delay(5000);

    const preControl = await send(ws, "Runtime.evaluate", {
      awaitPromise: true,
      returnByValue: true,
      expression: `Promise.resolve({
        controller: Boolean(navigator.serviceWorker?.controller)
      })`,
    });

    if (!preControl.result.value.controller) {
      await send(ws, "Page.reload", { ignoreCache: false });
      await delay(2500);
    }

    const manifest = await send(ws, "Page.getAppManifest");
    const installability = await send(ws, "Page.getInstallabilityErrors").catch(() => ({ installabilityErrors: [] }));
    const runtime = await send(ws, "Runtime.evaluate", {
      awaitPromise: true,
      returnByValue: true,
      expression: `Promise.resolve().then(async () => {
        const registrations = 'serviceWorker' in navigator ? await navigator.serviceWorker.getRegistrations() : [];
        const cacheNames = 'caches' in window ? await caches.keys() : [];
        return {
          secure: window.isSecureContext,
          manifestHref: document.querySelector('link[rel="manifest"]')?.href || null,
          controller: Boolean(navigator.serviceWorker.controller),
          registrationCount: registrations.length,
          elyioCacheCount: cacheNames.filter((name) => name.startsWith('elyio-')).length,
          bipFired: Boolean(window.__elyioBipFired),
          installTextVisible: document.body.innerText.includes('Install ELYIO'),
          appleCapable: document.querySelector('meta[name="apple-mobile-web-app-capable"]')?.content || null,
        };
      })`,
    });

    await send(ws, "Network.emulateNetworkConditions", {
      offline: true,
      latency: 0,
      downloadThroughput: 0,
      uploadThroughput: 0,
    });
    await send(ws, "Page.reload", { ignoreCache: false });
    await delay(2500);
    const offline = await send(ws, "Runtime.evaluate", {
      awaitPromise: true,
      returnByValue: true,
      expression: `Promise.resolve({
        title: document.title,
        controller: Boolean(navigator.serviceWorker.controller),
        bodyHasElyio: document.body.innerText.includes('ELYIO'),
      })`,
    });

    ws.close();

    return {
      manifestErrors: manifest.errors || [],
      installabilityErrors: installability.installabilityErrors || [],
      runtime: runtime.result.value,
      offline: offline.result.value,
    };
  } finally {
    chrome.kill();
  }
}

async function sourceGuards() {
  const [layout, home, camera, state] = await Promise.all([
    readFile("app/layout.tsx", "utf8"),
    readFile("components/screens/HomeScreen.tsx", "utf8"),
    readFile("components/screens/CameraScreen.tsx", "utf8"),
    readFile("lib/app-state.ts", "utf8"),
  ]);
  return {
    explicitAppleCapable: layout.includes('"apple-mobile-web-app-capable": "yes"'),
    mobileInstallHook: home.includes("usePwaInstall") && home.includes("pwa_ios_install_body"),
    standaloneAwareInstall: home.includes("installed") && home.includes("canPromptInstall"),
    offlineRecognitionState: state.includes('"network_error"') && camera.includes("recognition_network_error"),
  };
}

const [runtime, source] = await Promise.all([runtimeChecks(), sourceGuards()]);
const result = { targetUrl, runtime, source };
console.log(JSON.stringify(result, null, 2));

const failures = [];
if (runtime.manifestErrors.length) failures.push("manifest errors present");
if (runtime.installabilityErrors.length) failures.push("Chromium installability errors present");
if (!runtime.runtime.secure) failures.push("page is not a secure context");
if (runtime.runtime.controller) failures.push("service worker still controls page");
if (runtime.runtime.registrationCount !== 0) failures.push("service worker registration still present");
if (runtime.runtime.elyioCacheCount !== 0) failures.push("ELYIO cache storage still present");
if (runtime.runtime.appleCapable !== "yes") failures.push("apple-mobile-web-app-capable=yes missing");
if (runtime.offline.controller) failures.push("offline reload unexpectedly controlled by service worker");
for (const [key, value] of Object.entries(source)) {
  if (!value) failures.push(`source guard failed: ${key}`);
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
