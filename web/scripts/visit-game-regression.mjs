import { readFileSync } from "node:fs";

function assert(condition, message) {
  if (!condition) {
    console.error(`visit-game regression failed: ${message}`);
    process.exit(1);
  }
}

const visitGameSource = readFileSync(new URL("../lib/visit-game.ts", import.meta.url), "utf8");
const appStateSource = readFileSync(new URL("../lib/app-state.ts", import.meta.url), "utf8");
const recapImageSource = readFileSync(new URL("../lib/recap-image.ts", import.meta.url), "utf8");

assert(visitGameSource.includes("billion_euro_visitor"), "Billion Euro Visitor achievement missing");
assert(visitGameSource.includes("summary.hasIndicativeValue && summary.indicativeValueHigh >= 1000"), "Billion Euro Visitor must use the new indicative total, not artist benchmarks");
assert(visitGameSource.includes('kind: "indicative_total"'), "Indicative total value moment missing");
assert(visitGameSource.includes('kind: "market_context"'), "Biggest market moment fallback missing");
assert(visitGameSource.includes("valueRevealNumericContext"), "Market moment should use trusted value reveal numeric context");
assert(!visitGameSource.includes("estimatedValueHigh += numeric"), "Market context must not be summed as estimate");
assert(appStateSource.includes("nextAdded.add(id);") && appStateSource.includes("nextSeen.push(id);"), "Favoriting must preserve the work in the canonical visit summary");
assert(appStateSource.includes("elyio-current-visit-v1"), "Anonymous visit local persistence missing");
assert(appStateSource.includes("favoriteOrder"), "Favorite order persistence missing");
assert(appStateSource.includes('track("achievement_unlocked"'), "Achievement analytics missing");
assert(appStateSource.includes('track("mission_completed"'), "Mission completion analytics missing");
assert(recapImageSource.includes("RECAP_IMAGE_WIDTH = 1080"), "Share card width must be 1080");
assert(recapImageSource.includes("RECAP_IMAGE_HEIGHT = 1920"), "Share card height must be 1920");
assert(recapImageSource.includes("favoriteArtwork"), "Share card must support favorite artwork");
assert(recapImageSource.includes("valueMoment"), "Share card must support a single value moment");
assert(recapImageSource.includes("#D8B56D") && recapImageSource.includes("#080706"), "Share card must use the gold-on-charcoal trophy art direction");
assert(!recapImageSource.includes("methodology"), "Share card must not render methodology");
assert(!recapImageSource.includes("disclaimer"), "Share card must not render disclaimers");

console.log("visit-game regression passed");
