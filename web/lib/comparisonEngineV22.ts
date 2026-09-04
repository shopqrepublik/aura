import coreCatalogJson from "./data/comparison-v2.2-core.json";
import type { Locale, Mode } from "./types";

export const COMPARISON_ENGINE_V22_VERSION = "scale-comparison-v2.2.0";
export const COMPARISON_V22_REMOTE_IDS = [
  "super_bowl_ad", "film_budget", "eras_tour_ticket", "labubu_doll",
  "champions_final_ticket", "bored_ape", "lebron_james_rookie_card",
] as const;

export type V22Category = "luxury" | "food" | "everyday" | "tech" | "pop" | "city" | "kids" | "easter_egg";
export type V22Status = "VERIFIED" | "EASTER_EGG" | "REVIEW_REQUIRED" | "STALE" | "UNSOURCED" | "NEEDS_DECISION";

export interface V22Reference {
  id: string;
  emoji?: string;
  category: V22Category;
  modes: Mode[];
  cities: string[];
  calculation_price_eur: number | null;
  original_currency: "USD" | "EUR" | "GBP" | "JPY" | null;
  original_price: string | number | null;
  source_url: string;
  source_name: string;
  verified_at: string;
  valid_until: string;
  status: V22Status;
  allow_math?: boolean;
  labels: Record<Locale, string | null>;
  punchlines?: Array<{ min_count?: number | null; max_count?: number | null; text: Record<Locale, string | null> }>;
}

export interface V22Catalog { version: string; schema_version?: string; comparisons: V22Reference[] }
export interface V22Row { id: string; category: V22Category; icon: string; count: number; humanized: string; label: string; text: string; punchline: string | null }
export interface V22Set { rows: V22Row[]; easterEgg: V22Row | null; engineVersion: typeof COMPARISON_ENGINE_V22_VERSION; hasPunchline: boolean }
export interface V22Context {
  artworkId: string;
  estimatedEur: number;
  mode: Mode;
  city?: string | null;
  sessionId: string;
  surpriseCounter?: number;
  excludeIds?: string[];
  environment?: "production" | "development" | "test";
  allowReviewRecords?: boolean;
  locale?: Locale;
  fixedIds?: string[];
}

const CATEGORIES = new Set<V22Category>(["luxury", "food", "everyday", "tech", "pop", "city", "kids", "easter_egg"]);
const CURRENCIES = new Set(["USD", "EUR", "GBP", "JPY"]);
const SIMPLE_FORBIDDEN = new Set(["light_private_jet", "large_business_jet", "commercial_aircraft", "yacht_50m", "private_island", "luxury_hotel_suite_year", "film_budget"]);
const CORE_CATALOG = coreCatalogJson as unknown as V22Catalog;

export function isV22Requested(): boolean {
  return process.env.NEXT_PUBLIC_COMPARISON_ENGINE_VERSION === "2.2";
}

export function validateReference(reference: V22Reference, now = new Date(), options?: { production?: boolean; allowReview?: boolean }): string[] {
  const errors: string[] = [];
  const production = options?.production !== false;
  if (!reference.id || !CATEGORIES.has(reference.category)) errors.push("schema");
  if (!Array.isArray(reference.modes) || !Array.isArray(reference.cities)) errors.push("schema");
  if (reference.category === "easter_egg") {
    if (reference.status !== "EASTER_EGG" || reference.allow_math !== false || reference.calculation_price_eur != null) errors.push("easter_egg_policy");
    return errors;
  }
  if (!CURRENCIES.has(reference.original_currency || "")) errors.push("currency");
  if (!(Number.isFinite(reference.calculation_price_eur) && Number(reference.calculation_price_eur) > 0)) errors.push("price");
  if (!reference.source_url || !isAllowedSourceUrl(reference.source_url)) errors.push("source");
  const expiry = Date.parse(reference.valid_until);
  if (!Number.isFinite(expiry) || expiry < now.getTime()) errors.push("expired");
  if (production && reference.status !== "VERIFIED") errors.push("status");
  if (!production && reference.status !== "VERIFIED" && !(options?.allowReview && reference.status === "REVIEW_REQUIRED")) errors.push("status");
  if (!reference.labels.en || !reference.labels.fr || !reference.labels["zh-Hans"]) errors.push("localization");
  return [...new Set(errors)];
}

export function productionEligibleReferences(catalog: V22Catalog, now = new Date()): V22Reference[] {
  return catalog.comparisons.filter((reference) => reference.category !== "easter_egg" && validateReference(reference, now, { production: true }).length === 0);
}

export function catalogReadiness(catalog: V22Catalog = CORE_CATALOG, now = new Date()) {
  const eligible = productionEligibleReferences(catalog, now);
  const has = (mode: Mode, category: V22Category, city?: string) => eligible.some((r) => r.modes.includes(mode) && r.category === category && (!city || r.cities.includes(city)));
  const kids = eligible.filter((r) => r.category === "kids" && r.modes.includes("kids"));
  const cities = ["paris", "london", "newyork"];
  const ready = has("normal", "luxury") && has("normal", "food") && has("simple", "food") && kids.length >= 3
    && cities.every((city) => has("normal", "city", city))
    && ["paris", "newyork"].every((city) => has("simple", "city", city));
  return { ready, eligible, eligibleCount: eligible.length, totalCount: catalog.comparisons.length };
}

export function resolveV22Set(context: V22Context, catalog: V22Catalog = CORE_CATALOG): V22Set | null {
  const production = context.environment !== "development" && context.environment !== "test";
  const pool = catalog.comparisons.filter((reference) => {
    const errors = validateReference(reference, new Date(), { production, allowReview: context.allowReviewRecords });
    return errors.length === 0 && reference.category !== "easter_egg";
  });
  if (production && !catalogReadiness(catalog).ready) return null;
  const city = normalizeCity(context.city);
  const seed = `${context.artworkId}|${context.mode}|${city}|${context.sessionId}|${context.surpriseCounter || 0}`;
  const excluded = new Set(context.excludeIds || []);
  const global = (categories: V22Category[]) => pool.filter((r) => r.modes.includes(context.mode) && categories.includes(r.category) && r.cities.includes("global"));
  const local = pool.filter((r) => r.modes.includes(context.mode) && r.category === "city" && !!city && r.cities.includes(city) && !r.cities.includes("global"));
  let picked: V22Reference[] = [];
  if (context.fixedIds?.length) {
    picked = context.fixedIds.map((id) => pool.find((reference) => reference.id === id)).filter((reference): reference is V22Reference => !!reference);
    if (!validFixedSet(picked, context.mode, city)) return null;
  } else if (context.mode === "normal") {
    picked = pickSlots([
      global(["luxury", "tech"]),
      global(["food", "everyday"]),
      local.length ? local : global(["pop", "tech", "everyday", "luxury"]),
    ], seed, excluded);
  } else if (context.mode === "simple") {
    const food = global(["food", "everyday"]).filter((r) => !SIMPLE_FORBIDDEN.has(r.id));
    const fallback = global(["food", "everyday", "tech"]).filter((r) => !SIMPLE_FORBIDDEN.has(r.id));
    picked = pickSlots([food, local.length ? local : fallback], seed, excluded);
  } else {
    const kids = pool.filter((r) => r.category === "kids" && r.modes.includes("kids") && (r.cities.includes("global") || (!!city && r.cities.includes(city))));
    picked = deterministicPick(kids, `${seed}|kids`, 3, excluded);
  }
  const required = context.mode === "simple" ? 2 : 3;
  if (picked.length !== required) return null;
  const rows = picked.map((reference) => rowFor(reference, context.estimatedEur, context.mode, context));
  applySinglePunchline(rows, picked, seed, context.mode, context.locale || "en");
  const easterEgg = maybeFounder(catalog, context, seed);
  return { rows, easterEgg, engineVersion: COMPARISON_ENGINE_V22_VERSION, hasPunchline: rows.some((row) => !!row.punchline) };
}

function validFixedSet(references: V22Reference[], mode: Mode, city: string): boolean {
  if (mode === "normal") return references.length === 3
    && ["luxury", "tech"].includes(references[0].category)
    && ["food", "everyday"].includes(references[1].category)
    && references[2].category === "city" && !!city && references[2].cities.includes(city);
  if (mode === "simple") return references.length === 2
    && ["food", "everyday"].includes(references[0].category) && !SIMPLE_FORBIDDEN.has(references[0].id)
    && references[1].category === "city" && !!city && references[1].cities.includes(city) && !SIMPLE_FORBIDDEN.has(references[1].id);
  return references.length === 3 && references.every((reference) => reference.category === "kids" && reference.modes.includes("kids"));
}

function rowFor(reference: V22Reference, estimatedEur: number, mode: Mode, context: V22Context): V22Row {
  const count = estimatedEur / Number(reference.calculation_price_eur);
  const locale = context.locale || "en";
  const humanized = humanizeCount(count, locale);
  const label = reference.labels[locale]!;
  return { id: reference.id, category: reference.category, icon: reference.emoji || "•", count, humanized, label, text: `${humanized} ${label}`, punchline: null };
}

function applySinglePunchline(rows: V22Row[], references: V22Reference[], seed: string, mode: Mode, locale: Locale) {
  const probability = mode === "kids" ? 80 : mode === "normal" ? 30 : 0;
  if (fnv1a(`${seed}|punchline-roll`) % 100 >= probability) return;
  const eligible = rows.filter((row) => {
    const source = references.find((r) => r.id === row.id);
    return !!matchingPunchline(source, row.count, locale);
  });
  if (!eligible.length) return;
  const selected = eligible[fnv1a(`${seed}|punchline-target`) % eligible.length];
  const source = references.find((r) => r.id === selected.id);
  selected.punchline = matchingPunchline(source, selected.count, locale);
}

function matchingPunchline(reference: V22Reference | undefined, count: number, locale: Locale): string | null {
  const match = reference?.punchlines?.find((p) => count >= (p.min_count ?? 0) && count < (p.max_count ?? Infinity));
  return match?.text[locale] || null;
}

function maybeFounder(catalog: V22Catalog, context: V22Context, seed: string): V22Row | null {
  if (fnv1a(`${seed}|founder`) % 100 !== 0) return null;
  const founder = catalog.comparisons.find((r) => r.id === "founder_meeting" && r.status === "EASTER_EGG" && r.allow_math === false && r.calculation_price_eur == null);
  if (!founder) return null;
  const locale = context.locale || "en";
  const text = founder.labels[locale];
  if (!text) return null;
  return { id: founder.id, category: "easter_egg", icon: founder.emoji || "☕", count: 1, humanized: "~1", label: text, text: `~1 ${text}`, punchline: null };
}

function pickSlots(slots: V22Reference[][], seed: string, excluded: Set<string>) {
  const result: V22Reference[] = [];
  slots.forEach((slot, index) => {
    const pick = deterministicPick(slot, `${seed}|slot-${index}`, 1, new Set([...excluded, ...result.map((r) => r.id)]))[0];
    if (pick) result.push(pick);
  });
  return result;
}

function deterministicPick(pool: V22Reference[], seed: string, count: number, excluded: Set<string>) {
  const preferred = pool.filter((r) => !excluded.has(r.id));
  const source = preferred.length >= Math.min(count, pool.length) ? preferred : pool;
  if (!source.length) return [];
  const start = fnv1a(seed) % source.length;
  return Array.from({ length: Math.min(count, source.length) }, (_, i) => source[(start + i) % source.length]);
}

export function humanizeCount(value: number, locale: Locale): string {
  const prefix = "~";
  if (!Number.isFinite(value) || value <= 0) return `${prefix}0`;
  let rounded: number;
  if (value < 1.5) rounded = 1;
  else if (value < 10) rounded = Math.round(value);
  else if (value < 100) rounded = Math.round(value / 5) * 5;
  else if (value < 1_000) rounded = Math.round(value / 50) * 50;
  else if (value < 1_000_000) rounded = Math.round(value / (value < 10_000 ? 100 : value < 100_000 ? 1_000 : 10_000)) * (value < 10_000 ? 100 : value < 100_000 ? 1_000 : 10_000);
  else if (value < 1_000_000_000) {
    const millions = Math.round(value / 1_000_000);
    return locale === "zh-Hans" ? `${prefix}${millions * 100}万` : locale === "fr" ? `${prefix}${millions} millions` : `${prefix}${millions} million`;
  } else {
    const billions = Math.round(value / 1_000_000_000);
    return locale === "zh-Hans" ? `${prefix}${billions * 10}亿` : locale === "fr" ? `${prefix}${billions} milliards` : `${prefix}${billions} billion`;
  }
  return `${prefix}${new Intl.NumberFormat(locale === "zh-Hans" ? "zh-CN" : locale === "fr" ? "fr-FR" : "en-US", { maximumFractionDigits: 0 }).format(rounded)}`;
}

export function fnv1a(value: string): number {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) { hash ^= value.charCodeAt(i); hash = Math.imul(hash, 16777619); }
  return hash >>> 0;
}

export function normalizeCity(city?: string | null): string {
  return (city || "").toLocaleLowerCase("en").replace(/[^a-z]/g, "").replace("newyorkcity", "newyork");
}

function isAllowedSourceUrl(value: string): boolean {
  try { const url = new URL(value); return url.protocol === "https:" && !["localhost", "127.0.0.1"].includes(url.hostname); } catch { return false; }
}
