import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import ts from "typescript";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const sourcePath = path.join(process.cwd(), "lib", "scaleComparison.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  },
}).outputText;

const cjsModule = { exports: {} };
const require = createRequire(import.meta.url);
vm.runInNewContext(compiled, { module: cjsModule, exports: cjsModule.exports, require }, { filename: sourcePath });

const {
  resolveScaleComparisonForAmount,
  resolveScaleComparisonsForAmount,
  resolveValueRevealScaleComparison,
  valueRevealNumericContext,
} = cjsModule.exports;

for (const amount of [5, 20, 50, 100, 450]) {
  const normal = resolveScaleComparisonForAmount(amount, "USD_MILLION", "en", "normal");
  const simple = resolveScaleComparisonForAmount(amount, "USD_MILLION", "en", "simple");
  const kids = resolveScaleComparisonForAmount(amount, "USD_MILLION", "en", "kids");
  assert(normal, `Expected normal analogy for ${amount}M`);
  assert(simple, `Expected simple analogy for ${amount}M`);
  assert(kids, `Expected kids analogy for ${amount}M`);
  assert(normal.sentence !== kids.sentence, `Kids copy must differ from Normal for ${amount}M`);
  assert(!/\d+\.\d/.test(normal.sentence + simple.sentence + kids.sentence), `No decimal precision for ${amount}M`);
  assert(!/(^|[^0-9])0 /.test(normal.sentence + simple.sentence + kids.sentence), `No zero-count analogy for ${amount}M`);
}

assert(/wide-body aircraft/.test(resolveScaleComparisonForAmount(117.2, "USD_MILLION", "en", "normal").sentence), "117.2M should use aircraft scale");
assert(/Ferrari-class supercars/.test(resolveScaleComparisonForAmount(22.2, "USD_MILLION", "en", "normal").sentence), "22.2M should use supercar scale");
assert(/wide-body aircraft/.test(resolveScaleComparisonForAmount(450.3, "USD_MILLION", "en", "normal").sentence), "450.3M should use aircraft scale");
assert(resolveScaleComparisonsForAmount(100, "EUR_MILLION", "en", "normal").length >= 3, "Normal scale should show three comparisons");
assert(resolveScaleComparisonsForAmount(100, "EUR_MILLION", "en", "simple").length >= 2, "Simple scale should show two comparisons");
const kidsComparisons = resolveScaleComparisonsForAmount(100, "EUR_MILLION", "en", "kids");
assert(kidsComparisons.length >= 3, "Kids scale game should show three playful comparisons");
assert(kidsComparisons.some((c) => /ice creams|bicycles/.test(c.shortSentence)), "Kids scale game should include child-friendly units");
assert(resolveScaleComparisonForAmount(20, "CATEGORY_SOURCE", "en", "normal") === null, "Unsupported currency must not produce analogy");

const marketContextReveal = {
  mode: "MARKET_CONTEXT",
  aggregateValueEligible: false,
  marketContext: {
    headlineNumber: 117.2,
    currency: "USD_MILLION",
    label: "Van Gogh market context",
    explanation: "Another Van Gogh sold for this amount.",
    relationshipToArtwork: "Not a valuation of this work.",
    contextType: "artist auction record",
  },
};
assert(valueRevealNumericContext(marketContextReveal).amountMillions === 117.2, "MARKET_CONTEXT numeric context should be readable");
assert(resolveValueRevealScaleComparison(marketContextReveal, "en", "normal"), "MARKET_CONTEXT should get an analogy");
assert(marketContextReveal.aggregateValueEligible === false, "MARKET_CONTEXT must remain aggregate-ineligible");

const beyondReveal = {
  mode: "BEYOND_MARKET",
  aggregateValueEligible: false,
  beyondMarket: {
    headline: "No ordinary market price.",
    explanation: "Outside ordinary market valuation.",
    optionalContext: "Leonardo auction record: $450.3M. Context only, not a valuation.",
  },
};
assert(resolveValueRevealScaleComparison(beyondReveal, "en", "normal"), "BEYOND_MARKET numeric context should get an analogy");
assert(beyondReveal.aggregateValueEligible === false, "BEYOND_MARKET must remain aggregate-ineligible");

const aiIndicativeReveal = {
  mode: "AI_INDICATIVE_ESTIMATE",
  aggregateValueEligible: false,
  indicativeAggregateEligible: true,
  aiIndicativeEstimate: {
    lowEur: 70_000_000,
    highEur: 120_000_000,
    currency: "EUR",
    valuationBandId: "V10",
    confidence: "MEDIUM",
    shortReason: "QA",
    assumptions: [],
    version: "ai-indicative-estimate-v4",
    generatedAt: new Date().toISOString(),
    groundingFingerprint: "qa",
  },
};
assert(valueRevealNumericContext(aiIndicativeReveal).amountMillions === 95, "AI indicative context must convert absolute EUR to EUR millions exactly once");
const badAiIndicativeReveal = {
  ...aiIndicativeReveal,
  aiIndicativeEstimate: { ...aiIndicativeReveal.aiIndicativeEstimate, highEur: 15_000_000_000_000 },
};
assert(valueRevealNumericContext(badAiIndicativeReveal) === null, "Catastrophic AI indicative values must be presentation-rejected");

console.log("scale comparison regression: PASS");
