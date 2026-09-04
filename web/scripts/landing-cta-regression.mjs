import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.LANDING_CTA_TEST_URL || "http://localhost:3100";
const ctas = [
  ["header", 'header [data-ga-begin-visit="landing_header"]'],
  ["hero", '[data-ga-begin-visit="landing_hero"]'],
  ["footer", '[data-ga-begin-visit="landing_footer"]'],
];
const viewports = [
  ["desktop", { width: 1440, height: 1000 }],
  ["mobile", { width: 390, height: 844 }],
];
const consentStates = ["declined", "accepted"];

function assertVisitUrl(url) {
  const parsed = new URL(url);
  assert.equal(parsed.pathname, "/visit", "CTA must navigate to /visit");
  assert.equal(parsed.searchParams.get("from"), "organic", "from query must be preserved");
  assert.equal(parsed.searchParams.get("landing"), "home", "landing query must be preserved");
  assert.equal(parsed.searchParams.get("locale"), "en", "locale query must be preserved");
}

async function chooseConsent(page, state) {
  const name = state === "accepted" ? /Accept|Accepter|接受/i : /Decline|Refuser|拒绝/i;
  const button = page.getByRole("button", { name });
  if ((await button.count()) > 0) {
    await button.click();
    await page.waitForTimeout(300);
  }
}

async function runCase(browser, viewportName, viewport, consent, ctaName, selector, forceAnalyticsThrow = false) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.route("https://www.googletagmanager.com/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/javascript", body: "" })
  );
  await page.route("**/v1/museums**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([{ id: "louvre", name: "Musée du Louvre", city: "Paris", lat: null, lng: null, geofence_radius_m: 500, experience_level: "CURATED" }]),
  }));

  await page.goto(`${baseUrl}/en`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(500);
  await chooseConsent(page, consent);
  if (forceAnalyticsThrow) {
    await page.evaluate(() => {
      window.gtag = () => {
        throw new Error("forced GA failure");
      };
    });
  }

  const link = page.locator(selector);
  await link.scrollIntoViewIfNeeded();
  assert.equal(await link.getAttribute("href"), "/visit?from=organic&landing=home&locale=en");
  const beforeUrl = page.url();
  await link.click();
  await page.waitForURL(/\/visit\?/, { waitUntil: "domcontentloaded", timeout: 10000 });
  assert.notEqual(page.url(), beforeUrl, `${viewportName}/${consent}/${ctaName} did not navigate`);
  assertVisitUrl(page.url());
  assert.equal(await page.getByRole("button", { name: "Begin your visit" }).count(), 0, `${viewportName}/${consent}/${ctaName} rendered a duplicate CTA`);
  await page.getByRole("button", { name: "Capture" }).waitFor();
  assert.deepEqual(pageErrors, [], `${viewportName}/${consent}/${ctaName} had page errors`);
  await context.close();
}

const browser = await chromium.launch({ headless: true });
try {
  for (const [viewportName, viewport] of viewports) {
    for (const consent of consentStates) {
      for (const [ctaName, selector] of ctas) {
        await runCase(browser, viewportName, viewport, consent, ctaName, selector);
      }
    }
    await runCase(browser, viewportName, viewport, "accepted", "hero", '[data-ga-begin-visit="landing_hero"]', true);
  }
  console.log("landing-cta-regression: PASS (header/hero/footer, desktop/mobile, accepted/declined, GA failure-safe navigation)");
} finally {
  await browser.close();
}
