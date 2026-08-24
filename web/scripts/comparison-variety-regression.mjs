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
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
  }).outputText;
}

const require = createRequire(import.meta.url);
const referencesPath = path.join(process.cwd(), "lib", "comparisonReferences.ts");
const referencesModule = { exports: {} };
vm.runInNewContext(compile(referencesPath), { module: referencesModule, exports: referencesModule.exports, require }, { filename: referencesPath });
const enginePath = path.join(process.cwd(), "lib", "scaleComparison.ts");
const engineModule = { exports: {} };
const localRequire = (specifier) => specifier === "./comparisonReferences" ? referencesModule.exports : require(specifier);
vm.runInNewContext(compile(enginePath), { module: engineModule, exports: engineModule.exports, require: localRequire }, { filename: enginePath });

const { resolveScaleComparisonsForAmount } = engineModule.exports;
const cases = 150;
const categoryArtworkCounts = new Map();
const combinations = new Map();
let easterEggs = 0;
let parisReferenceRows = 0;
const examples = [];

for (let index = 0; index < cases; index += 1) {
  const amount = 0.25 * Math.pow(3200, index / (cases - 1)); // €0.25M–€800M
  const rows = resolveScaleComparisonsForAmount(amount, "EUR_MILLION", "en", "normal", undefined, {
    city: "London",
    countryCode: "GB",
    artworkId: `artwork:variety-${String(index).padStart(3, "0")}`,
  });
  assert(rows.length === 3, `Expected three rows for variety case ${index}, received ${rows.length}`);
  assert(rows.filter((row) => row.category === "FOUNDER_EASTER_EGG").length <= 1, "At most one founder easter egg is allowed");
  parisReferenceRows += rows.filter((row) => /Paris/.test(row.shortSentence)).length;
  const monetary = rows.filter((row) => row.monetary);
  assert(new Set(monetary.map((row) => row.category)).size === monetary.length, "Monetary rows must use distinct categories");
  if (rows.some((row) => row.category === "FOUNDER_EASTER_EGG")) easterEggs += 1;
  for (const category of new Set(monetary.map((row) => row.category))) {
    categoryArtworkCounts.set(category, (categoryArtworkCounts.get(category) || 0) + 1);
  }
  const combination = monetary.map((row) => row.category).sort().join("+");
  combinations.set(combination, (combinations.get(combination) || 0) + 1);
  if (examples.length < 10 && !examples.some((entry) => entry.combination === combination)) {
    examples.push({ artwork: `variety-${index}`, amount_eur_millions: Number(amount.toFixed(2)), combination, rows: rows.map((row) => row.shortSentence) });
  }
}

const distribution = Object.fromEntries(
  [...categoryArtworkCounts.entries()].sort().map(([category, count]) => [category, { artworks: count, percentage: Number((count / cases * 100).toFixed(1)) }])
);
const easterRate = Number((easterEggs / cases * 100).toFixed(1));
assert(easterRate >= 3 && easterRate <= 5, `Founder easter egg rate must be approximately 3–5%, received ${easterRate}%`);
assert(categoryArtworkCounts.size >= 9, `Expected broad category usage, received ${categoryArtworkCounts.size}`);
assert(combinations.size >= 10, `Expected at least ten monetary combinations, received ${combinations.size}`);
assert(parisReferenceRows === 0, `London context must contain zero Paris rows, received ${parisReferenceRows}`);

console.log(JSON.stringify({
  engine_version: referencesModule.exports.COMPARISON_ENGINE_VERSION,
  artworks_tested: cases,
  categories_used: categoryArtworkCounts.size,
  unique_monetary_combinations: combinations.size,
  london_paris_reference_rows: parisReferenceRows,
  category_distribution: distribution,
  founder_easter_egg: { appearances: easterEggs, percentage: easterRate, monetary: false },
  examples,
}, null, 2));
