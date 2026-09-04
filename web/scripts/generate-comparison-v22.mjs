import fs from "node:fs";
import path from "node:path";

const webRoot = path.resolve(import.meta.dirname, "..");
const repoRoot = path.resolve(webRoot, "..");
const outputRoot = path.join(webRoot, "lib", "data");

const inputs = {
  core: "Comparison-Engine-V2-2-Catalog.json",
  remote: "Remote-Meme-Pack-V1.json",
  landing: "Landing-Demo-Seed.json",
};

const currencyById = new Map([
  ["ferrari_supercar", "USD"], ["light_private_jet", "USD"], ["large_business_jet", "USD"],
  ["commercial_aircraft", "USD"], ["yacht_50m", "USD"], ["private_island", "USD"],
  ["suborbital_seat", "USD"], ["iphone_16_pro_max", "USD"], ["rolex_daytona", "USD"],
  ["birkin_bag", "USD"], ["tesla_cybertruck", "USD"], ["university_scholarship", "USD"],
  ["nyc_hotdog", "USD"], ["nyc_apt_month", "USD"], ["broadway_ticket", "USD"],
  ["chatgpt_pro_year", "USD"], ["private_chef_year", "USD"], ["kids_lego_falcon", "USD"],
  ["kids_ps5", "USD"], ["super_bowl_ad", "USD"], ["film_budget", "USD"],
  ["eras_tour_ticket", "USD"], ["labubu_doll", "USD"], ["champions_final_ticket", "USD"],
  ["bored_ape", "USD"], ["lebron_james_rookie_card", "USD"],
]);

function read(name) {
  return JSON.parse(fs.readFileSync(path.join(repoRoot, name), "utf8"));
}

function normalizeComparison(item) {
  const category = item.category === "travel" || item.category === "life" ? "everyday" : item.category;
  const originalCurrency = item.category === "easter_egg"
    ? null
    : currencyById.get(item.id) || (item.original_currency === "GBP" ? "GBP" : item.original_currency === "JPY" ? "JPY" : "EUR");
  return {
    ...item,
    category,
    original_currency: originalCurrency,
    labels: { en: item.name_en || null, fr: null, "zh-Hans": null },
    punchlines: (item.punchlines || []).map((p) => ({
      ...p,
      text: { en: p.text_en || null, fr: null, "zh-Hans": null },
    })),
  };
}

const core = read(inputs.core);
const remote = read(inputs.remote);
const landing = read(inputs.landing);

const normalizedCore = {
  ...core,
  schema_version: "2.2",
  comparisons: core.comparisons.map(normalizeComparison),
};
const normalizedRemote = {
  ...remote,
  comparisons: remote.comparisons.map(normalizeComparison),
};

fs.mkdirSync(outputRoot, { recursive: true });
fs.writeFileSync(path.join(outputRoot, "comparison-v2.2-core.json"), `${JSON.stringify(normalizedCore, null, 2)}\n`);
fs.writeFileSync(path.join(outputRoot, "comparison-v2.2-remote.json"), `${JSON.stringify(normalizedRemote, null, 2)}\n`);
fs.writeFileSync(path.join(outputRoot, "comparison-v2.2-landing.json"), `${JSON.stringify(landing, null, 2)}\n`);

console.log(`Generated ${normalizedCore.comparisons.length} core + ${normalizedRemote.comparisons.length} remote V2.2 records.`);
