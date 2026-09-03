import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.ANALYTICS_TEST_URL || "http://localhost:3100";
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await context.addInitScript(() => {
    Object.defineProperty(HTMLVideoElement.prototype, "videoWidth", { get: () => 512 });
    Object.defineProperty(HTMLVideoElement.prototype, "videoHeight", { get: () => 384 });
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (...args) {
      const ctx = original.apply(this, args);
      if (ctx) ctx.drawImage = () => undefined;
      return ctx;
    };
  });
  const page = await context.newPage();
  const googleRequests = [];
  page.on("request", (request) => {
    if (/google(tagmanager|analytics)\.com/.test(request.url())) googleRequests.push(request.url());
  });
  await page.route("https://www.googletagmanager.com/**", (route) => route.fulfill({ status: 200, contentType: "application/javascript", body: "" }));
  await page.route("**/v1/museums**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "musee-du-louvre", name: "Musée du Louvre", city: "Paris", lat: null, lng: null, geofence_radius_m: 500, experience_level: "CURATED" }]) }));
  await page.route("**/v1/recognize", (route) => route.abort());

  await page.goto(`${baseUrl}/?utm_source=qa&utm_medium=test&utm_campaign=analytics3&utm_content=root&utm_term=art`);
  assert.match(page.url(), /\/en\?utm_source=qa&utm_medium=test&utm_campaign=analytics3&utm_content=root&utm_term=art$/);
  await page.getByRole("heading", { name: "See a painting. Scan it. Understand it." }).waitFor();
  assert.equal(googleRequests.length, 0, "Google must not load before consent");
  assert.equal(await page.locator("#elyio-ga4").count(), 0, "tag must be absent before consent");

  await page.getByRole("button", { name: "Accept" }).click();
  await page.locator("#elyio-ga4").waitFor({ state: "attached" });
  assert.equal(await page.locator("#elyio-ga4").count(), 1, "exactly one Google tag");
  const acceptedCalls = await page.evaluate(() => (window.dataLayer || []).map((entry) => Array.from(entry)));
  const acceptedCount = (name) => acceptedCalls.filter((call) => call[0] === "event" && call[1] === name).length;
  assert.equal(acceptedCalls.filter((call) => call[0] === "js").length, 1, "single GA bootstrap after late consent");
  assert.equal(acceptedCalls.filter((call) => call[0] === "config" && call[1] === "G-GP3VEHLNE2").length, 1, "single GA config after late consent");
  assert.equal(acceptedCount("page_view"), 1, "single current page_view after late consent");
  assert.ok(acceptedCalls.some((call) => call[0] === "consent" && call[1] === "default" && call[2].analytics_storage === "denied"));
  assert.ok(acceptedCalls.some((call) => call[0] === "consent" && call[1] === "update" && call[2].analytics_storage === "granted"));
  assert.ok(acceptedCalls.some((call) => call[0] === "consent" && call[1] === "update" && call[2].ad_storage === "denied" && call[2].ad_user_data === "denied" && call[2].ad_personalization === "denied"));
  const queuedWithoutGtag = await page.evaluate(() => {
    const before = (window.dataLayer || []).filter((entry) => Array.from(entry)[0] === "event" && Array.from(entry)[1] === "begin_visit").length;
    const original = window.gtag;
    window.gtag = undefined;
    const probe = document.createElement("button");
    probe.dataset.gaBeginVisit = "landing_hero";
    document.body.appendChild(probe);
    probe.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    probe.remove();
    window.gtag = original;
    const after = (window.dataLayer || []).filter((entry) => Array.from(entry)[0] === "event" && Array.from(entry)[1] === "begin_visit").length;
    return after - before;
  });
  assert.equal(queuedWithoutGtag, 1, "granted consent must queue begin_visit if gtag is not ready");
  await page.evaluate(() => {
    const original = window.gtag;
    window.gtag = (...args) => {
      const stored = JSON.parse(window.sessionStorage.getItem("elyio-test-gtag-calls") || "[]");
      stored.push(args);
      window.sessionStorage.setItem("elyio-test-gtag-calls", JSON.stringify(stored));
      return original?.(...args);
    };
  });
  await page.locator('[data-ga-begin-visit="landing_hero"]').click();
  await page.waitForURL(/\/visit\?/);

  const visitUrl = new URL(page.url());
  assert.equal(visitUrl.pathname, "/visit", "landing CTA must navigate to /visit");
  assert.equal(visitUrl.searchParams.get("from"), "organic", "landing CTA must preserve from");
  assert.equal(visitUrl.searchParams.get("landing"), "home", "landing CTA must preserve landing");
  assert.equal(visitUrl.searchParams.get("locale"), "en", "landing CTA must preserve locale");
  const beginVisitCalls = await page.evaluate(() => JSON.parse(window.sessionStorage.getItem("elyio-test-gtag-calls") || "[]"));
  const beginVisitCount = beginVisitCalls.filter((call) => call[0] === "event" && call[1] === "begin_visit").length;
  assert.equal(beginVisitCount, 1, "single begin_visit per CTA click");

  await page.locator("button:has(.lucide-chevron-down)").click();
  await page.getByRole("button", { name: /Musée du Louvre/ }).first().click();
  await page.getByRole("button", { name: "Begin your visit" }).click();
  await page.getByRole("button", { name: "Capture" }).waitFor();
  await page.getByRole("button", { name: "Capture" }).click();
  await page.waitForTimeout(100);
  const funnelCalls = await page.evaluate(() => (window.dataLayer || []).map((entry) => Array.from(entry)));
  const funnelCount = (name) => funnelCalls.filter((call) => call[0] === "event" && call[1] === name).length;
  assert.equal(funnelCount("camera_opened"), 1, "single camera_opened per scanner entry");
  assert.equal(funnelCount("scan_started"), 1, "single scan_started per shutter action");

  await context.clearCookies();
  await page.evaluate(() => localStorage.setItem("elyio-google-consent", "denied"));
  googleRequests.length = 0;
  await page.goto(`${baseUrl}/visit`);
  assert.equal(await page.locator("#elyio-ga4").count(), 0, "denied consent must not load tag");
  assert.equal(googleRequests.length, 0, "denied consent must not contact Google");
  console.log("analytics-regression: PASS (UTM, consent denied/granted, single tag, page_view, begin_visit, camera_opened, scan_started)");
} finally {
  await browser.close();
}
