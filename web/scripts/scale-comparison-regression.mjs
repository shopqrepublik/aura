import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import ts from "typescript";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function compile(sourcePath) {
  return ts.transpileModule(fs.readFileSync(sourcePath, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  },
  }).outputText;
}

const referencesPath = path.join(process.cwd(), "lib", "comparisonReferences.ts");
const referencesModule = { exports: {} };
const require = createRequire(import.meta.url);
vm.runInNewContext(compile(referencesPath), { module: referencesModule, exports: referencesModule.exports, require }, { filename: referencesPath });
const sourcePath = path.join(process.cwd(), "lib", "scaleComparison.ts");
const cjsModule = { exports: {} };
const localRequire = (specifier) => specifier === "./comparisonReferences" ? referencesModule.exports : require(specifier);
vm.runInNewContext(compile(sourcePath), { module: cjsModule, exports: cjsModule.exports, require: localRequire }, { filename: sourcePath });

const {
  resolveScaleComparisonForAmount,
  resolveScaleComparisonsForAmount,
  resolveValueRevealScaleComparison,
  resolveValueRevealScaleComparisons,
  isResponsibleNumericEstimate,
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

assert(resolveScaleComparisonsForAmount(100, "EUR_MILLION", "en", "normal").length >= 3, "Normal scale should show three comparisons");
assert(resolveScaleComparisonsForAmount(100, "EUR_MILLION", "en", "simple").length >= 2, "Simple scale should show two comparisons");
const kidsComparisons = resolveScaleComparisonsForAmount(100, "EUR_MILLION", "en", "kids");
assert(kidsComparisons.length >= 3, "Kids scale game should show three playful comparisons");
assert(new Set(kidsComparisons.map((c) => c.category)).size === kidsComparisons.length, "Rows should use distinct categories");
assert(resolveScaleComparisonForAmount(20, "CATEGORY_SOURCE", "en", "normal") === null, "Unsupported currency must not produce analogy");

const arnolfiniLondon = resolveScaleComparisonsForAmount(1.5, "EUR_MILLION", "en", "normal", undefined, { city: "London", artworkId: "artwork:0D8P-0001-0000-0000" });
assert(arnolfiniLondon.length >= 2, "A valid €1–2M London estimate must have useful scale comparisons");
assert(!arnolfiniLondon.some((c) => /Paris/.test(c.shortSentence)), "London context must never leak Paris comparisons");
assert(arnolfiniLondon.every((c) => c.engineVersion === "scale-comparison-v2.0.0"), "Every row must carry engine version");
const sameArnolfini = resolveScaleComparisonsForAmount(1.5, "EUR_MILLION", "en", "normal", undefined, { city: "London", artworkId: "artwork:0D8P-0001-0000-0000" });
assert(JSON.stringify(arnolfiniLondon) === JSON.stringify(sameArnolfini), "Same artwork/version/context must be deterministic");
const bathersLondon = resolveScaleComparisonsForAmount(95, "EUR_MILLION", "en", "normal", undefined, { city: "London", artworkId: "artwork:0CP9-0001-0000-0000" });
assert(bathersLondon.length >= 3, "A major numeric estimate must retain three scale comparisons");
assert(!bathersLondon.some((c) => /Paris/.test(c.shortSentence)), "Bathers in London must not use Paris geography");
const mobileExamples = [
  ["Arnolfini Portrait", "0D8P-0001-0000-0000", 1.5],
  ["Whistlejacket", "0ETF-0001-0000-0000", 12],
  ["Woman Bathing in a Stream", "0D7O-0001-0000-0000", 5],
  ["A Young Woman in a Hat", "young-woman-in-a-hat", 3],
  ["Bathers at Asnières", "0CP9-0001-0000-0000", 95],
];
const mobileCombinations = new Set();
for (const [title, artworkId, amount] of mobileExamples) {
  const rows = resolveScaleComparisonsForAmount(amount, "EUR_MILLION", "en", "normal", undefined, { city: "London", countryCode: "GB", artworkId });
  assert(rows.length === 3, `${title} must render exactly three scale rows`);
  assert(!rows.some((row) => /Paris/.test(row.shortSentence)), `${title} must not inherit Paris context`);
  mobileCombinations.add(rows.filter((row) => row.monetary).map((row) => row.category).sort().join("+"));
}
assert(mobileCombinations.size >= 3, "Mobile examples must not all repeat the same category combination");
const louvreParis = resolveScaleComparisonsForAmount(95, "EUR_MILLION", "en", "normal", undefined, { city: "Paris", artworkId: "louvre-regression" });
assert(!louvreParis.some((c) => /London/.test(c.shortSentence)), "Paris context must never use London property copy");
const madrid = resolveScaleComparisonsForAmount(20, "EUR_MILLION", "en", "normal", undefined, { city: "Madrid", artworkId: "madrid-regression" });
assert(!madrid.some((c) => /Paris|London/.test(c.shortSentence)), "Third-city context must not inherit Paris/London");
assert(!resolveScaleComparisonsForAmount(1.5, "CATEGORY_SOURCE", "en", "normal", undefined, { city: "London" }).length, "Unavailable value must not fabricate comparisons");

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
assert(!resolveValueRevealScaleComparison(marketContextReveal, "en", "normal"), "MARKET_CONTEXT must not get viewed-work monetary analogies");
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
assert(!resolveValueRevealScaleComparison(beyondReveal, "en", "normal"), "BEYOND_MARKET must not get monetary analogies");
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
assert(isResponsibleNumericEstimate(aiIndicativeReveal), "Eligible V4 estimate must satisfy numeric contract");
assert(resolveValueRevealScaleComparisons(aiIndicativeReveal, "en", "normal", { city: "London", artworkId: "numeric-contract" }).length === 3, "Responsible numeric estimate must get three rows");
const badAiIndicativeReveal = {
  ...aiIndicativeReveal,
  aiIndicativeEstimate: { ...aiIndicativeReveal.aiIndicativeEstimate, highEur: 15_000_000_000_000 },
};
assert(valueRevealNumericContext(badAiIndicativeReveal) === null, "Catastrophic AI indicative values must be presentation-rejected");
assert(!isResponsibleNumericEstimate(badAiIndicativeReveal), "Catastrophic estimate must fail numeric contract");
assert(resolveValueRevealScaleComparisons(null, "en", "normal", { city: "London", artworkId: "pending-review" }).length === 0, "Pending/no estimate must not fabricate comparisons");

console.log("scale comparison regression: PASS");
