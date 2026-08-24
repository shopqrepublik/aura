import type { Locale } from "./types";

export const COMPARISON_ENGINE_VERSION = "scale-comparison-v2.0.0";

export type ComparisonCategory =
  | "SUPERCAR"
  | "PRIME_PROPERTY"
  | "YACHT"
  | "LIGHT_PRIVATE_JET"
  | "LARGE_BUSINESS_JET"
  | "COMMERCIAL_AIRCRAFT"
  | "SPACEFLIGHT"
  | "LUXURY_HOLIDAY"
  | "LUXURY_HOTEL"
  | "PRIVATE_ISLAND"
  | "EDUCATION"
  | "ENTERTAINMENT_BUDGET";

export type ScaleAudience = "adult" | "kids";

export interface ScaleReference {
  id: string;
  category: ComparisonCategory;
  label: Record<Locale, string>;
  singularLabel?: Partial<Record<Locale, string>>;
  unitValueMillions: { low: number; high: number };
  currency: "USD_MILLION" | "EUR_MILLION" | "GBP_MILLION";
  geographicScope: "GLOBAL" | "CITY";
  source: string;
  methodology: string;
  lastReviewedDate: string;
  engineVersion: string;
  active: boolean;
  allowedLocales: Locale[];
  ageSuitability: ScaleAudience[];
  usefulAmountMillions: { min: number; max: number };
  usefulQuantity: { min: number; max: number };
}

const common = {
  geographicScope: "GLOBAL" as const,
  lastReviewedDate: "2026-08-24",
  engineVersion: COMPARISON_ENGINE_VERSION,
  active: true,
  allowedLocales: ["en", "fr", "zh-Hans"] as Locale[],
};

export const COMPARISON_REFERENCES: ScaleReference[] = [
  {
    ...common, id: "supercar_global_v2", category: "SUPERCAR",
    label: { en: "Ferrari-class supercars", fr: "supercars de type Ferrari", "zh-Hans": "法拉利级别超跑" },
    singularLabel: { en: "Ferrari-class supercar" },
    unitValueMillions: { low: 0.35, high: 0.45 }, currency: "USD_MILLION",
    source: "ELYIO reviewed high-end supercar order-of-magnitude reference.", methodology: "Rounded ranges only.",
    ageSuitability: ["adult", "kids"], usefulAmountMillions: { min: 0.2, max: 80 }, usefulQuantity: { min: 1, max: 250 },
  },
  {
    ...common, id: "light_private_jet_global_v2", category: "LIGHT_PRIVATE_JET",
    label: { en: "light private jets", fr: "jets privés légers", "zh-Hans": "轻型私人飞机" },
    singularLabel: { en: "light private jet" },
    unitValueMillions: { low: 4, high: 7 }, currency: "USD_MILLION",
    source: "ELYIO reviewed light-private-jet order-of-magnitude reference.", methodology: "Whole-aircraft scale; no fractional aircraft.",
    ageSuitability: ["adult", "kids"], usefulAmountMillions: { min: 4, max: 120 }, usefulQuantity: { min: 1, max: 30 },
  },
  {
    ...common, id: "large_business_jet_global_v2", category: "LARGE_BUSINESS_JET",
    label: { en: "large business jets", fr: "grands jets d’affaires", "zh-Hans": "大型商务飞机" },
    singularLabel: { en: "large business jet" },
    unitValueMillions: { low: 50, high: 75 }, currency: "USD_MILLION",
    source: "ELYIO reviewed large-business-jet order-of-magnitude reference.", methodology: "Whole-aircraft scale; no fractional aircraft.",
    ageSuitability: ["adult", "kids"], usefulAmountMillions: { min: 45, max: 900 }, usefulQuantity: { min: 1, max: 20 },
  },
  {
    ...common, id: "commercial_aircraft_global_v2", category: "COMMERCIAL_AIRCRAFT",
    label: { en: "commercial-airliner-class aircraft", fr: "avions de ligne long-courriers", "zh-Hans": "大型民航客机" },
    singularLabel: { en: "commercial-airliner-class aircraft" },
    unitValueMillions: { low: 110, high: 140 }, currency: "USD_MILLION",
    source: "ELYIO reviewed commercial-aircraft order-of-magnitude reference.", methodology: "Used only for nine-figure ranges and above.",
    ageSuitability: ["adult", "kids"], usefulAmountMillions: { min: 100, max: 1200 }, usefulQuantity: { min: 1, max: 12 },
  },
  {
    ...common, id: "luxury_yacht_global_v2", category: "YACHT",
    label: { en: "50-metre luxury yachts", fr: "yachts de luxe de 50 mètres", "zh-Hans": "50米级豪华游艇" },
    singularLabel: { en: "50-metre luxury yacht" },
    unitValueMillions: { low: 25, high: 45 }, currency: "USD_MILLION",
    source: "ELYIO reviewed specialist yacht-build order-of-magnitude reference.", methodology: "Whole-yacht scale; broad ranges only.",
    ageSuitability: ["adult"], usefulAmountMillions: { min: 25, max: 700 }, usefulQuantity: { min: 1, max: 30 },
  },
  {
    ...common, id: "suborbital_seat_global_v2", category: "SPACEFLIGHT",
    label: { en: "suborbital spaceflight seats", fr: "places pour un vol spatial suborbital", "zh-Hans": "亚轨道太空飞行席位" },
    singularLabel: { en: "suborbital spaceflight seat" },
    unitValueMillions: { low: 0.45, high: 0.6 }, currency: "USD_MILLION",
    source: "ELYIO reviewed public suborbital-seat order-of-magnitude reference; provider-neutral.", methodology: "Seat-scale comparison, not a live quote.",
    ageSuitability: ["adult", "kids"], usefulAmountMillions: { min: 0.5, max: 180 }, usefulQuantity: { min: 1, max: 400 },
  },
  {
    ...common, id: "luxury_holiday_global_v2", category: "LUXURY_HOLIDAY",
    label: { en: "exceptional family holidays", fr: "vacances familiales d’exception", "zh-Hans": "高端家庭旅行" },
    singularLabel: { en: "exceptional family holiday" },
    unitValueMillions: { low: 0.04, high: 0.07 }, currency: "EUR_MILLION",
    source: "ELYIO reviewed luxury-holiday order-of-magnitude reference.", methodology: "Broad trip-budget comparison; never a booking quote.",
    ageSuitability: ["adult", "kids"], usefulAmountMillions: { min: 0.2, max: 25 }, usefulQuantity: { min: 3, max: 500 },
  },
  {
    ...common, id: "luxury_hotel_year_global_v2", category: "LUXURY_HOTEL",
    label: { en: "years in a landmark luxury-hotel suite", fr: "années dans une suite d’hôtel de prestige", "zh-Hans": "入住地标豪华酒店套房的年数" },
    singularLabel: { en: "year in a landmark luxury-hotel suite" },
    unitValueMillions: { low: 0.35, high: 0.55 }, currency: "EUR_MILLION",
    source: "ELYIO reviewed year-long landmark-suite order-of-magnitude reference.", methodology: "Annualized suite scale; not a live room rate.",
    ageSuitability: ["adult"], usefulAmountMillions: { min: 0.5, max: 100 }, usefulQuantity: { min: 1, max: 250 },
  },
  {
    ...common, id: "private_island_global_v2", category: "PRIVATE_ISLAND",
    label: { en: "private-island-class properties", fr: "propriétés de type île privée", "zh-Hans": "私人岛屿级别地产" },
    singularLabel: { en: "private-island-class property" },
    unitValueMillions: { low: 8, high: 15 }, currency: "USD_MILLION",
    source: "ELYIO reviewed private-island-property order-of-magnitude reference.", methodology: "Broad property class, not a specific listing.",
    ageSuitability: ["adult"], usefulAmountMillions: { min: 10, max: 450 }, usefulQuantity: { min: 1, max: 60 },
  },
  {
    ...common, id: "university_scholarship_global_v2", category: "EDUCATION",
    label: { en: "four-year university scholarships", fr: "bourses universitaires de quatre ans", "zh-Hans": "四年制大学奖学金" },
    singularLabel: { en: "four-year university scholarship" },
    unitValueMillions: { low: 0.18, high: 0.28 }, currency: "USD_MILLION",
    source: "ELYIO reviewed four-year scholarship order-of-magnitude reference.", methodology: "Broad full-study support scale; not a tuition quote.",
    ageSuitability: ["adult", "kids"], usefulAmountMillions: { min: 0.2, max: 150 }, usefulQuantity: { min: 1, max: 800 },
  },
  {
    ...common, id: "major_film_budget_global_v2", category: "ENTERTAINMENT_BUDGET",
    label: { en: "major film-production budgets", fr: "budgets de grandes productions cinéma", "zh-Hans": "大型电影制作预算" },
    singularLabel: { en: "major film-production budget" },
    unitValueMillions: { low: 15, high: 30 }, currency: "USD_MILLION",
    source: "ELYIO reviewed major-film-production order-of-magnitude reference.", methodology: "Production-budget class, not a named film claim.",
    ageSuitability: ["adult", "kids"], usefulAmountMillions: { min: 15, max: 600 }, usefulQuantity: { min: 1, max: 40 },
  },
];

interface CityPropertyConfig {
  labels: Record<Locale, string>;
  unitValueMillions: { low: number; high: number };
  currency: "EUR_MILLION" | "GBP_MILLION" | "USD_MILLION";
  source: string;
}

const CITY_PROPERTIES: Record<string, CityPropertyConfig> = {
  paris: {
    labels: { en: "prime central-Paris apartments", fr: "appartements haut de gamme au centre de Paris", "zh-Hans": "巴黎市中心高端公寓" },
    unitValueMillions: { low: 1.5, high: 3 }, currency: "EUR_MILLION",
    source: "ELYIO reviewed central-Paris prime-property order-of-magnitude reference.",
  },
  london: {
    labels: { en: "prime central-London apartments", fr: "appartements haut de gamme au centre de Londres", "zh-Hans": "伦敦市中心高端公寓" },
    unitValueMillions: { low: 1.5, high: 3 }, currency: "GBP_MILLION",
    source: "ELYIO reviewed central-London prime-property order-of-magnitude reference.",
  },
  madrid: {
    labels: { en: "prime central-Madrid apartments", fr: "appartements haut de gamme au centre de Madrid", "zh-Hans": "马德里市中心高端公寓" },
    unitValueMillions: { low: 1, high: 2 }, currency: "EUR_MILLION",
    source: "ELYIO reviewed central-Madrid prime-property order-of-magnitude reference.",
  },
};

export function localPropertyReference(city?: string | null): ScaleReference | null {
  const key = city?.trim().toLocaleLowerCase("en") || "";
  const config = CITY_PROPERTIES[key];
  if (!config) return null;
  return {
    ...common,
    id: `prime_property_${key}_v2`, category: "PRIME_PROPERTY", label: config.labels,
    singularLabel: { en: config.labels.en.replace(/apartments$/, "apartment") },
    unitValueMillions: config.unitValueMillions, currency: config.currency, geographicScope: "CITY",
    source: config.source, methodology: `Broad ${city} property-scale analogy; not a listing or appraisal.`,
    ageSuitability: ["adult"], usefulAmountMillions: { min: 1, max: 1200 }, usefulQuantity: { min: 1, max: 500 },
  };
}
