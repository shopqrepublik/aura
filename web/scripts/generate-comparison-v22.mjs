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

const wave1Verification = {
  iphone_16_pro_max: {
    status: "NEEDS_DECISION", source_name: "Apple France", source_url: "https://www.apple.com/fr/newsroom/2024/09/apple-debuts-iphone-16-pro-iphone-16-pro-max/",
    source_price: "€1,479 launch price for iPhone 16 Pro Max; supplied $1,200 differs materially",
  },
  tesla_cybertruck: {
    status: "NEEDS_DECISION", source_name: "Tesla Cybertruck official page", source_url: "https://www.tesla.com/cybertruck?redirect=no",
    source_price: "Official page does not expose a stable public price; supplied $80k cannot be verified as a current representative basis",
  },
  ferrari_supercar: {
    status: "VERIFIED", source_name: "Car and Driver", source_url: "https://www.caranddriver.com/ferrari/296-gtb-2025",
    source_price: "$346,950 MSRP (2025 Ferrari 296 GTB)",
    labels: { en: "Ferrari-class supercars", fr: "supercars de type Ferrari", "zh-Hans": "法拉利级超跑" },
  },
  baguette: {
    status: "VERIFIED", source_name: "Le Bon Pain de Paris", source_url: "https://lebonpaindeparis.com/",
    source_price: "€1.40 baguette tradition (listed retail price)",
    labels: { en: "French baguettes tradition", fr: "baguettes tradition françaises", "zh-Hans": "法式传统长棍面包" },
    punchlines: { fr: ["Ça fait beaucoup de miettes."], "zh-Hans": ["这得掉下不少面包屑。"] },
  },
  netflix_year: {
    status: "VERIFIED", source_name: "Netflix France", source_url: "https://www.netflix.com/fr/browse/genre/81683021",
    source_price: "€21.99/month Premium = €263.88/year; supplied €240 is within 20% as a rounded annual plan basis",
    labels: { en: "Years of Netflix Family plan", fr: "années d’abonnement Netflix Famille", "zh-Hans": "Netflix家庭套餐年数" },
  },
  kids_lego_falcon: {
    status: "VERIFIED", source_name: "LEGO Official Shop US", source_url: "https://www.lego.com/en-us/product/millennium-falcon-75192?age-gate=grown_up",
    source_price: "$849.99 (LEGO Millennium Falcon 75192)",
    labels: { en: "LEGO Millennium Falcon sets", fr: "sets LEGO Millennium Falcon", "zh-Hans": "乐高千年隼套装" },
    punchlines: { fr: ["Il faudra peut-être une pièce en plus.", "En fait, une ville en plus."], "zh-Hans": ["可能得再腾出一个房间。", "不如说，还得再建一座城。"] },
  },
  paris_studio_year: {
    status: "VERIFIED", source_name: "SeLoger", source_url: "https://www.seloger.com/annonces/locations/appartement/paris-3eme-75/archives/274569893.htm",
    source_price: "€1,450/month for a 23 m² furnished studio in Paris 3e (representative current asking rent; supplied €18,000/year = €1,500/month within 20%)",
    labels: { en: "Years of a Paris studio", fr: "années de location d’un studio parisien", "zh-Hans": "巴黎单间公寓年租" },
  },
  paris_moulin_rouge: {
    status: "NEEDS_DECISION", source_name: "Paris je t’aime / Moulin Rouge ticketing", source_url: "https://ticket.parisjetaime.com/spectacles-et-cabarets-c5/cabaret-moulin-rouge-spectacles-and-diners-spectacles-103",
    source_price: "€263+ dinner-show menus in 2026; supplied €120 show basis differs materially",
  },
  avocado_toast_london: {
    status: "NEEDS_DECISION", source_name: "Deliveroo UK", source_url: "https://deliveroo.co.uk/menu/London/london-bridge/",
    source_price: "Representative listed London avocado toast around £8.50; supplied £14 is venue-dependent",
  },
  london_black_cab: {
    status: "VERIFIED", source_name: "Transport for London", source_url: "https://content.tfl.gov.uk/taxi-fare-card-2026.pdf",
    source_price: "£70–£120 typical Heathrow–central London black-cab fare (representative trip; supplied £80 within range)",
    labels: { en: "London black-cab rides", fr: "courses en taxi noir londonien", "zh-Hans": "伦敦黑色出租车车程" },
  },
  kids_ps5: {
    status: "NEEDS_DECISION", source_name: "PlayStation Direct", source_url: "https://direct.playstation.com/en-us/hardware/ps5",
    source_price: "$649 new PS5 (current listing); supplied $500 is below current new-console basis",
  },
  kids_disneyland_family: {
    status: "NEEDS_DECISION", source_name: "Disneyland Paris", source_url: "https://www.disneylandparis.com/en-usd/faq/tickets-and-vacation-packages/buy-tickets-at-parks-entrance-ticket-counters",
    source_price: "€638 for representative 2-adult/2-child one-day, two-park tickets; supplied €400 differs materially",
  },
};

function read(name) {
  return JSON.parse(fs.readFileSync(path.join(repoRoot, name), "utf8"));
}

function normalizeComparison(item) {
  const category = item.category === "travel" || item.category === "life" ? "everyday" : item.category;
  const originalCurrency = item.category === "easter_egg"
    ? null
    : currencyById.get(item.id) || (item.original_currency === "GBP" ? "GBP" : item.original_currency === "JPY" ? "JPY" : "EUR");
  const verification = wave1Verification[item.id];
  return {
    ...item,
    category,
    original_currency: originalCurrency,
    labels: verification?.labels || { en: item.name_en || null, fr: null, "zh-Hans": null },
    ...(verification || {}),
    punchlines: (item.punchlines || []).map((p, index) => ({
      ...p,
      text: {
        en: p.text_en || null,
        fr: wave1Verification[item.id]?.punchlines?.fr?.[index] || null,
        "zh-Hans": wave1Verification[item.id]?.punchlines?.["zh-Hans"]?.[index] || null,
      },
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
