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
assert(visitGameSource.includes("summary.hasIndicativeValue && summary.indicativeValueLow >= 1000"), "Billion Euro Visitor must use the conservative low bound, not artist benchmarks or corrupted high ranges");
assert(visitGameSource.includes('kind: "indicative_total"'), "Indicative total value moment missing");
assert(visitGameSource.includes('kind: "market_context"'), "Biggest market moment fallback missing");
assert(visitGameSource.includes("valueRevealNumericContext"), "Market moment should use trusted value reveal numeric context");
assert(!visitGameSource.includes("estimatedValueHigh += numeric"), "Market context must not be summed as estimate");
assert(appStateSource.includes("recordCatalogDiscovery") && appStateSource.includes("recordUncatalogedDiscovery"), "Successful recognitions must auto-record visit discoveries");
assert(appStateSource.includes('source: "auto_sighting"'), "Auto-sightings must be distinguishable from manual/favorite actions");
assert(appStateSource.includes("appendUnique"), "Visit discoveries must dedupe repeated scans");
assert(!appStateSource.includes("nextAdded.delete(id);"), "Add-to-visit must not remove successful discoveries from the canonical visit summary");
assert(appStateSource.includes('imageSourceType: "VISITOR_CAPTURE"'), "Visitor-captured scans must be explicitly marked as VISITOR_CAPTURE");
assert(appStateSource.includes('return "PLACEHOLDER"'), "Placeholder images must be explicitly classified as PLACEHOLDER");
assert(appStateSource.includes("withCapturedScanFallbackImage"), "Catalog placeholder images must be replaceable by the captured scan");
assert(recapImageSource.includes('selectedImageSourceType(artwork) !== "PLACEHOLDER"'), "Share-card canvas must not draw placeholders as trophy hero artwork");
assert(appStateSource.includes("elyio-current-visit-v2"), "Anonymous visit local persistence/version invalidation missing");
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
