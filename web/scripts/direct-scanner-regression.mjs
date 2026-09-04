import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.DIRECT_SCANNER_TEST_URL || "http://localhost:3100";
const museum = { id: "louvre", name: "Musée du Louvre", city: "Paris", lat: null, lng: null, geofence_radius_m: 500, experience_level: "CURATED" };
const cases = [
  ["iphone-safari", { width: 390, height: 844 }, "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1", true, false],
  ["instagram-in-app", { width: 360, height: 740 }, "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Instagram 350.0.0", true, false],
  ["chrome-desktop", { width: 1440, height: 1000 }, undefined, true, false],
  ["camera-denied", { width: 390, height: 844 }, undefined, false, false],
  ["geolocation-detected", { width: 390, height: 844 }, undefined, true, true],
];

async function runCase(browser, name, viewport, userAgent, cameraAccepted, geolocationDetected) {
  const context = await browser.newContext({ viewport, ...(userAgent ? { userAgent } : {}) });
  await context.addInitScript(({ accepted, detected }) => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition: (success, failure) => detected ? success({ coords: { latitude: 48.8606, longitude: 2.3376 } }) : failure?.(new Error("permission denied")) },
    });
    if (!navigator.mediaDevices) Object.defineProperty(navigator, "mediaDevices", { value: {}, configurable: true });
    navigator.mediaDevices.getUserMedia = async () => {
      if (!accepted) throw new DOMException("Permission denied", "NotAllowedError");
      return new MediaStream();
    };
  }, { accepted: cameraAccepted, detected: geolocationDetected });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/v1/museums**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ ...museum, lat: 48.8606, lng: 2.3376 }]) }));
  await page.route("**/v1/events", (route) => route.fulfill({ status: 204, body: "" }));
  await page.route("**/v1/visits", (route) => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "anonymous visit" }) }));

  await page.goto(`${baseUrl}/visit?from=organic&landing=home&locale=fr&utm_source=qa&utm_medium=in_app`);
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.reload({ waitUntil: "domcontentloaded" });
  const consentButton = page.getByRole("button", { name: cameraAccepted ? /Accept|Accepter|接受/ : /Decline|Refuser|拒绝/ });
  try {
    await consentButton.waitFor({ state: "visible", timeout: 2000 });
    await consentButton.click();
  } catch { /* a prior persisted consent choice intentionally has no prompt */ }
  assert.equal(await page.getByRole("button", { name: /Begin your visit|Commencez votre visite/ }).count(), 0, `${name}: duplicate CTA`);
  if (!geolocationDetected) await page.getByRole("button", { name: /Musée du Louvre/ }).click();
  await page.getByRole("button", { name: "Capture" }).waitFor();
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("elyio-current-visit-v2") || "null"));
  assert.equal(stored.state.locale, "fr", `${name}: locale not preserved`);
  assert.equal(stored.state.museumId, "louvre", `${name}: museum not initialized`);
  const attribution = await page.evaluate(() => JSON.parse(sessionStorage.getItem("elyio-organic-landing") || "null"));
  assert.deepEqual(attribution, { traffic_source: "organic", landing_page: "home", landing_locale: "fr" }, `${name}: attribution not preserved`);

  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Capture" }).waitFor();
  assert.equal(await page.getByRole("button", { name: /Musée du Louvre/ }).count(), 0, `${name}: returning visit reopened selection`);
  assert.deepEqual(errors, [], `${name}: page errors`);
  await context.close();
}

const browser = await chromium.launch({ headless: true });
try {
  for (const testCase of cases) await runCase(browser, ...testCase);
  console.log("direct-scanner-regression: PASS (iPhone, Instagram in-app, desktop, camera denied, locale, attribution, fresh and returning /visit)");
} finally {
  await browser.close();
}
