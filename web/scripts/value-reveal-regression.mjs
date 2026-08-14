import fs from "node:fs";
import path from "node:path";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function valueRevealFromEstimate(estimate) {
  if (estimate?.low == null || estimate.high == null) return null;
  return {
    mode: "ESTIMATED_VALUE",
    aggregateValueEligible: true,
    estimatedValue: {
      low: estimate.low,
      high: estimate.high,
      currency: "EUR",
    },
  };
}

function getArtworkValueReveal(artwork) {
  return artwork.valueReveal ?? valueRevealFromEstimate(artwork.estimate);
}

function getAggregateEligibleValue(artwork) {
  const reveal = getArtworkValueReveal(artwork);
  if (reveal?.mode !== "ESTIMATED_VALUE" || reveal.aggregateValueEligible !== true) return null;
  return reveal.estimatedValue;
}

function getIndicativeEligibleValue(artwork) {
  const reveal = getArtworkValueReveal(artwork);
  if (reveal?.mode === "ESTIMATED_VALUE" && reveal.aggregateValueEligible === true) return reveal.estimatedValue;
  if (reveal?.mode === "AI_INDICATIVE_ESTIMATE" && reveal.indicativeAggregateEligible === true) {
    const estimate = reveal.aiIndicativeEstimate;
    if (estimate.version !== "ai-indicative-estimate-v3") return null;
    if (!Number.isFinite(estimate.lowEur) || !Number.isFinite(estimate.highEur)) return null;
    if (estimate.lowEur <= 0 || estimate.highEur <= estimate.lowEur || estimate.highEur > 1_000_000_000) return null;
    return { low: estimate.lowEur / 1_000_000, high: estimate.highEur / 1_000_000, currency: estimate.currency };
  }
  return null;
}

function summarizeVisitValue(artworks) {
  return artworks.reduce(
    (summary, artwork) => {
      const reveal = getArtworkValueReveal(artwork);
      const value = getAggregateEligibleValue(artwork);
      const indicative = getIndicativeEligibleValue(artwork);
      summary.totalArtworkCount += 1;
      if (value) {
        summary.estimatedValueLow += value.low;
        summary.estimatedValueHigh += value.high;
        summary.estimatedValueArtworkCount += 1;
        summary.hasEstimatedValue = true;
      }
      if (indicative) {
        summary.indicativeValueLow += indicative.low;
        summary.indicativeValueHigh += indicative.high;
        summary.indicativeValueArtworkCount += 1;
        summary.hasIndicativeValue = true;
      }
      if (reveal?.mode === "MARKET_CONTEXT") {
        summary.marketContextCount += 1;
      } else if (reveal?.mode === "BEYOND_MARKET") {
        summary.beyondMarketCount += 1;
      } else if (!indicative) {
        summary.unvaluedCount += 1;
      }
      return summary;
    },
    {
      estimatedValueLow: 0,
      estimatedValueHigh: 0,
      estimatedValueArtworkCount: 0,
      indicativeValueLow: 0,
      indicativeValueHigh: 0,
      indicativeValueArtworkCount: 0,
      marketContextCount: 0,
      beyondMarketCount: 0,
      unvaluedCount: 0,
      totalArtworkCount: 0,
      hasEstimatedValue: false,
      hasIndicativeValue: false,
    }
  );
}

function getMostValuableArtwork(artworks) {
  let best = null;
  let bestHigh = Number.NEGATIVE_INFINITY;
  for (const artwork of artworks) {
    const value = getAggregateEligibleValue(artwork);
    if (!value) continue;
    if (value.high > bestHigh) {
      best = artwork;
      bestHigh = value.high;
    }
  }
  return best;
}

function cleanVisitorText(value) {
  if (!value) return "";
  if (/[{}[\]"]|source_ids|catalog_version|review_status/.test(value)) {
    try {
      const parsed = JSON.parse(value);
      return [parsed.label, parsed.explanation].filter((x) => typeof x === "string").join(". ");
    } catch {
      return value
        .replace(/"source_ids"\s*:\s*\[[^\]]*\],?/g, "")
        .replace(/[{}[\]"]/g, "")
        .replace(/\b(number|currency|label|explanation)\s*:/g, "")
        .trim();
    }
  }
  return value;
}

const estimated = { id: "estimated", estimate: { low: 80, high: 120 }, valueReveal: null };
const billion = { id: "billion", estimate: { low: 900, high: 1000 }, valueReveal: null };
const marketContext = {
  id: "mona-context",
  estimate: { low: null, high: null },
  valueReveal: {
    mode: "MARKET_CONTEXT",
    aggregateValueEligible: false,
    marketContext: {
      headlineNumber: 450.3,
      currency: "USD_MILLION",
      label: "Leonardo auction record",
      explanation: "Context only.",
      relationshipToArtwork: "Not an estimate of this artwork.",
      contextType: "ARTIST_AUCTION_RECORD",
    },
  },
};
const aiIndicative = {
  id: "ai-indicative",
  estimate: { low: null, high: null },
  valueReveal: {
    mode: "AI_INDICATIVE_ESTIMATE",
    aggregateValueEligible: false,
    indicativeAggregateEligible: true,
    aiIndicativeEstimate: {
      lowEur: 70_000_000,
      highEur: 100_000_000,
      currency: "EUR",
      valuationBandId: "V10",
      confidence: "MEDIUM",
      shortReason: "Hypothetical scale estimate.",
      assumptions: ["Museum work is not for sale."],
      version: "ai-indicative-estimate-v3",
      generatedAt: new Date().toISOString(),
      groundingFingerprint: "test",
    },
  },
};
const staleAiIndicative = {
  id: "stale-ai-indicative",
  estimate: { low: null, high: null },
  valueReveal: {
    mode: "AI_INDICATIVE_ESTIMATE",
    aggregateValueEligible: false,
    indicativeAggregateEligible: true,
    aiIndicativeEstimate: {
      low: 7_000_000,
      high: 15_000_000,
      lowEur: 7_000_000_000_000,
      highEur: 15_000_000_000_000,
      currency: "EUR",
      valuationBandId: "V99",
      confidence: "LOW",
      shortReason: "Bad stale payload.",
      assumptions: [],
      version: "ai-indicative-estimate-v1",
      generatedAt: new Date().toISOString(),
      groundingFingerprint: "bad",
    },
  },
};
const beyondMarket = {
  id: "beyond",
  estimate: { low: null, high: null },
  valueReveal: {
    mode: "BEYOND_MARKET",
    aggregateValueEligible: false,
    beyondMarket: {
      headline: "No ordinary market price.",
      explanation: "Outside the normal art market.",
    },
  },
};
const unvalued = { id: "pending", estimate: { low: null, high: null }, valueReveal: null };

let summary = summarizeVisitValue([estimated]);
assert(summary.estimatedValueLow === 80 && summary.estimatedValueHigh === 120, "ESTIMATED_VALUE must contribute to totals");
assert(getMostValuableArtwork([estimated, marketContext])?.id === "estimated", "ESTIMATED_VALUE must be eligible for most valuable");
assert(summarizeVisitValue([billion]).estimatedValueHigh >= 1000, "ESTIMATED_VALUE must contribute to Billion Euro progress");

summary = summarizeVisitValue([marketContext]);
assert(summary.estimatedValueHigh === 0, "MARKET_CONTEXT must contribute zero to totals");
assert(summary.marketContextCount === 1, "MARKET_CONTEXT count must be tracked");
assert(getMostValuableArtwork([marketContext]) === null, "MARKET_CONTEXT cannot be most valuable");

summary = summarizeVisitValue([aiIndicative]);
assert(summary.estimatedValueHigh === 0, "AI_INDICATIVE_ESTIMATE must not enter reviewed totals");
assert(summary.indicativeValueLow === 70 && summary.indicativeValueHigh === 100, "AI_INDICATIVE_ESTIMATE must enter indicative totals");
assert(summary.hasIndicativeValue === true, "AI_INDICATIVE_ESTIMATE should set indicative total state");
assert(getMostValuableArtwork([aiIndicative]) === null, "AI_INDICATIVE_ESTIMATE cannot be most valuable reviewed artwork");
assert(summarizeVisitValue([staleAiIndicative]).hasIndicativeValue === false, "Stale/catastrophic AI values must not enter totals");

summary = summarizeVisitValue([beyondMarket]);
assert(summary.estimatedValueHigh === 0, "BEYOND_MARKET must contribute zero to totals");
assert(summary.beyondMarketCount === 1, "BEYOND_MARKET count must be tracked");
assert(getMostValuableArtwork([beyondMarket]) === null, "BEYOND_MARKET cannot be most valuable");

summary = summarizeVisitValue([estimated, aiIndicative, marketContext, beyondMarket, unvalued]);
assert(summary.estimatedValueLow === 80 && summary.estimatedValueHigh === 120, "Mixed visit totals must include only eligible estimates");
assert(summary.estimatedValueArtworkCount === 1, "Mixed visit estimated count must be correct");
assert(summary.indicativeValueLow === 150 && summary.indicativeValueHigh === 220, "Mixed visit indicative total must include reviewed plus AI indicative");
assert(summary.marketContextCount === 1, "Mixed visit market context count must be correct");
assert(summary.beyondMarketCount === 1, "Mixed visit beyond-market count must be correct");
assert(summary.unvaluedCount === 1, "Mixed visit unvalued count must be correct");

summary = summarizeVisitValue([marketContext, beyondMarket, unvalued]);
assert(summary.hasEstimatedValue === false, "No estimated values must not create a fake zero-value estimate");
assert(getMostValuableArtwork([marketContext, beyondMarket, unvalued]) === null, "No estimated values must not create a fake most valuable artwork");

const leakedContext = '{"number":450.3,"currency":"USD_MILLION","label":"Leonardo auction record","explanation":"Context only, not a valuation.","source_ids":["christies_salvator_mundi"]}';
const cleanedContext = cleanVisitorText(leakedContext);
assert(!/[{}[\]"]/.test(cleanedContext), "Visitor value copy must not expose raw JSON");
assert(!/source_ids|christies_salvator_mundi/.test(cleanedContext), "Visitor value copy must not expose internal source ids");
assert(/Leonardo auction record/.test(cleanedContext), "Visitor value copy must preserve the human label");
assert(/not a valuation/.test(cleanedContext), "Visitor value copy must preserve the value caveat");

const artworksPath = path.join(process.cwd(), "lib", "data", "artworks.json");
const artworks = JSON.parse(fs.readFileSync(artworksPath, "utf8"));
const orangerieCount = artworks.filter((artwork) => artwork.museumId === "orangerie" || artwork.museum_id === "orangerie").length;
const orsayCount = artworks.length - orangerieCount;
assert(orsayCount === 101, `Expected 101 Orsay legacy records, got ${orsayCount}`);
assert(orangerieCount === 15, `Expected 15 Orangerie legacy records, got ${orangerieCount}`);
for (const artwork of artworks) {
  const legacyHasEstimate = artwork.estimate?.low != null && artwork.estimate?.high != null;
  const aggregate = getAggregateEligibleValue(artwork);
  assert(Boolean(aggregate) === legacyHasEstimate, `Legacy estimate mapping mismatch for ${artwork.id}`);
}

console.log("value reveal regression: PASS");
