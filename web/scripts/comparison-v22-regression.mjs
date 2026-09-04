import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import ts from "typescript";

const assert = (condition, message) => { if (!condition) throw new Error(message); };
const require = createRequire(import.meta.url);
const compile = (file) => ts.transpileModule(fs.readFileSync(file, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true, resolveJsonModule: true } }).outputText;
const enginePath = path.join(process.cwd(), "lib", "comparisonEngineV22.ts");
const engineModule = { exports: {} };
const engineRequire = (specifier) => specifier === "./data/comparison-v2.2-core.json" ? require(path.join(process.cwd(), "lib", "data", "comparison-v2.2-core.json")) : require(specifier);
vm.runInNewContext(compile(enginePath), { module: engineModule, exports: engineModule.exports, require: engineRequire, process, URL, Intl, Date, Set, Map }, { filename: enginePath });
const engine = engineModule.exports;
const storage = new Map();
const remoteContext = {
  module: { exports: {} }, process, URL, Date, Set, Map,
  window: { localStorage: { getItem: (key) => storage.get(key) || null, setItem: (key, value) => storage.set(key, value) } },
  fetch: async () => { throw new Error("remote unavailable"); },
};
remoteContext.exports = remoteContext.module.exports;
const remotePath = path.join(process.cwd(), "lib", "comparisonRemotePack.ts");
const remoteRequire = (specifier) => specifier === "./comparisonEngineV22" ? engine : require(specifier);
remoteContext.require = remoteRequire;
vm.runInNewContext(compile(remotePath), remoteContext, { filename: remotePath });
const remote = remoteContext.module.exports;

const ref = (id, category, modes, cities, price = 10, extra = {}) => ({
  id, category, modes, cities, calculation_price_eur: price, original_currency: "EUR", original_price: `EUR ${price}`,
  source_url: `https://sources.elyio.test/${id}`, source_name: "Test source", verified_at: "2026-09-01", valid_until: "2030-01-01",
  status: "VERIFIED", labels: { en: `${id} EN`, fr: `${id} FR`, "zh-Hans": `${id} ZH` }, emoji: "•", punchlines: [{ min_count: 0, max_count: null, text: { en: "Punch EN", fr: "Punch FR", "zh-Hans": "Punch ZH" } }], ...extra,
});
const comparisons = [
  ref("luxury_a", "luxury", ["normal"], ["global"], 1_000_000), ref("luxury_b", "tech", ["normal"], ["global"], 500_000),
  ref("food_a", "food", ["normal", "simple"], ["global"], 5), ref("food_b", "everyday", ["normal", "simple"], ["global"], 10),
  ref("universal_a", "tech", ["normal", "simple"], ["global"], 500), ref("fallback_a", "pop", ["normal"], ["global"], 100),
  ref("paris_a", "city", ["normal", "simple"], ["paris"], 20), ref("paris_b", "city", ["normal", "simple"], ["paris"], 30),
  ref("london_a", "city", ["normal", "simple"], ["london"], 20), ref("newyork_a", "city", ["normal", "simple"], ["newyork"], 20),
  ...Array.from({ length: 7 }, (_, i) => ref(`kid_${i}`, "kids", ["kids"], ["global"], 3 + i)),
  { id: "founder_meeting", category: "easter_egg", modes: ["normal", "kids"], cities: ["global"], calculation_price_eur: null, original_currency: null, original_price: null, source_url: "", source_name: "ELYIO", verified_at: "", valid_until: "", status: "EASTER_EGG", allow_math: false, labels: { en: "One founder meeting — apparently priceless", fr: "Une rencontre — apparemment inestimable", "zh-Hans": "一次创始人会面——据说无价" } },
];
const catalog = { version: "2.2", schema_version: "2.2", comparisons };
const context = (mode, city, sessionId = "visit-1", extra = {}) => ({ artworkId: "art-1", estimatedEur: 100_000_000, mode, city, sessionId, locale: "en", environment: "test", ...extra });

for (const [mode, city, expected] of [["normal", "paris", 3], ["normal", "london", 3], ["normal", null, 3], ["simple", "paris", 2], ["simple", "newyork", 2], ["simple", null, 2], ["kids", "paris", 3], ["kids", "london", 3]]) {
  const set = engine.resolveV22Set(context(mode, city), catalog);
  assert(set?.rows.length === expected, `${mode}/${city} row count`);
  if (mode === "simple" && city) assert(set.rows[1].category === "city" && set.rows[1].id.startsWith(city), `Simple ${city} must prefer local city second`);
  if (mode === "kids") assert(set.rows.every((row) => row.category === "kids"), "Kids adult-pool leak");
  if (city) assert(!set.rows.some((row) => row.category === "city" && !row.id.startsWith(city)), `wrong-city leak for ${city}`);
  assert(set.rows.filter((row) => row.punchline).length <= 1, "one punchline maximum");
}

const first = engine.resolveV22Set(context("normal", "paris"), catalog);
const rerender = engine.resolveV22Set(context("normal", "paris"), catalog);
assert(JSON.stringify(first) === JSON.stringify(rerender), "same artwork/session must be identical across rerender");
const landingFixed = engine.resolveV22Set(context("normal", "paris", "elyio_landing_fixed_2026_09_04", { fixedIds: ["luxury_a", "food_a", "paris_a"] }), catalog);
assert(JSON.stringify(landingFixed.rows.map((row) => row.id)) === JSON.stringify(["luxury_a", "food_a", "paris_a"]), "landing fixed IDs must use application calculation in stable order");
const surprise = engine.resolveV22Set(context("normal", "paris", "visit-1", { surpriseCounter: 1, excludeIds: first.rows.map((r) => r.id) }), catalog);
assert(surprise && !surprise.rows.some((row) => first.rows.some((old) => old.id === row.id)), "Surprise Me must avoid immediate repeats where pools permit");
const sessions = new Set(Array.from({ length: 20 }, (_, i) => JSON.stringify(engine.resolveV22Set(context("kids", "paris", `visit-${i}`), catalog).rows.map((r) => r.id))));
assert(sessions.size > 1, "new sessions must permit deterministic variation");
const punchlineRates = {};
for (const mode of ["normal", "kids"]) {
  let hits = 0;
  for (let i = 0; i < 1000; i += 1) if (engine.resolveV22Set(context(mode, "paris", `punch-${i}`), catalog).hasPunchline) hits += 1;
  punchlineRates[mode] = hits / 10;
}
assert(punchlineRates.normal >= 25 && punchlineRates.normal <= 35, `Normal punchline probability ${punchlineRates.normal}%`);
assert(punchlineRates.kids >= 75 && punchlineRates.kids <= 85, `Kids punchline probability ${punchlineRates.kids}%`);
assert(!engine.resolveV22Set(context("simple", "paris"), catalog).hasPunchline, "Simple punchlines are disabled by default");

for (const status of ["REVIEW_REQUIRED", "STALE", "UNSOURCED"]) {
  const candidate = { ...ref(`status_${status}`, "food", ["normal"], ["global"]), status };
  assert(engine.productionEligibleReferences({ version: "2.2", comparisons: [candidate] }).length === 0, `${status} must be excluded`);
}
assert(engine.productionEligibleReferences({ version: "2.2", comparisons: [ref("verified", "food", ["normal"], ["global"])] }).length === 1, "VERIFIED must be included");
assert(engine.productionEligibleReferences({ version: "2.2", comparisons: [{ ...ref("unsourced", "food", ["normal"], ["global"]), source_url: "" }] }).length === 0, "blank source must be rejected");
assert(engine.productionEligibleReferences({ version: "2.2", comparisons: [{ ...ref("expired", "food", ["normal"], ["global"]), valid_until: "2020-01-01" }] }).length === 0, "expired reference must be rejected");

for (const locale of ["en", "fr", "zh-Hans"]) {
  const set = engine.resolveV22Set({ ...context("kids", "paris"), locale }, catalog);
  assert(set.rows.every((row) => row.label.endsWith(locale === "zh-Hans" ? "ZH" : locale.toUpperCase())), `${locale} localized output`);
  assert(set.rows.every((row) => row.text.startsWith("~")), `${locale} approximation prefix`);
}
for (const value of [1.04, 8.7, 347, 1183, 18_181_818, 1_800_000_000]) {
  for (const locale of ["en", "fr", "zh-Hans"]) assert(!engine.humanizeCount(value, locale).includes("."), `humanization precision ${value}/${locale}`);
}
assert(engine.humanizeCount(18_181_818, "en") === "~18 million", "English millions");
assert(engine.humanizeCount(18_181_818, "fr") === "~18 millions", "French millions");
assert(engine.humanizeCount(18_181_818, "zh-Hans") === "~1800万", "Chinese compact convention");

let founder = null;
for (let i = 0; i < 1000 && !founder; i += 1) founder = engine.resolveV22Set(context("kids", "paris", `founder-${i}`), catalog).easterEgg;
assert(founder && founder.count === 1 && founder.category === "easter_egg", "Founder must be appended outside math at ~1% eligibility");

const coreReadiness = engine.catalogReadiness();
assert(coreReadiness.ready === true && coreReadiness.eligibleCount === 15, "Wave 1 must satisfy the launch readiness matrix");

const remoteItems = engine.COMPARISON_V22_REMOTE_IDS.map((id) => ref(id, "pop", ["normal"], ["global"], 100));
const validPack = { version: "1.0", schema_version: "2.2", pack_id: "test-pack", expires_at: "2030-01-01", allowlist: true, source_required: true, comparisons: remoteItems };
assert(remote.validateRemotePack(validPack).valid, "valid remote pack");
assert(!remote.validateRemotePack({ ...validPack, expires_at: "2020-01-01" }).valid, "expired remote pack");
assert(!remote.validateRemotePack({ ...validPack, comparisons: remoteItems.map((item, i) => i ? item : { ...item, source_url: "" }) }).valid, "invalid sourced remote pack");
assert(await remote.loadRemotePack({ url: "https://packs.elyio.test/v1.json", disabled: true }) === null, "remote disabled");
remoteContext.fetch = async () => ({ ok: true, headers: { get: () => "application/json" }, json: async () => validPack });
assert((await remote.loadRemotePack({ url: "https://packs.elyio.test/v1.json" }))?.pack_id === "test-pack", "valid remote fetch");
remoteContext.fetch = async () => { throw new Error("unavailable"); };
assert((await remote.loadRemotePack({ url: "https://packs.elyio.test/v1.json" }))?.pack_id === "test-pack", "last-known-good remote fallback");

console.log(JSON.stringify({ passed: true, coreReadiness, sessionVariations: sessions.size, punchlineRates, founderExample: founder.text, remotePack: "PASS" }, null, 2));
