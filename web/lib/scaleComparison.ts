import type { Locale, Mode, ValueReveal } from "./types";
import { isV22Requested, resolveV22Set, type V22Category } from "./comparisonEngineV22";
import {
  COMPARISON_ENGINE_VERSION,
  COMPARISON_REFERENCES,
  localPropertyReference,
  type ComparisonCategory,
  type ScaleAudience,
  type ScaleReference,
} from "./comparisonReferences";

export { COMPARISON_ENGINE_VERSION, COMPARISON_REFERENCES } from "./comparisonReferences";

export interface ScaleComparison {
  referenceId: string;
  category: ComparisonCategory | "FOUNDER_EASTER_EGG" | V22Category;
  engineVersion: string;
  monetary: boolean;
  icon: string;
  label: string;
  sentence: string;
  shortSentence: string;
  countLabel: string;
  source: string;
  punchline?: string;
}

export interface ScaleComparisonContext {
  city?: string | null;
  countryCode?: string | null;
  artworkId?: string | null;
  sessionId?: string | null;
  surpriseCounter?: number;
  excludeIds?: string[];
  fixedIds?: string[];
}

const CURRENCY_TO_USD: Record<string, number> = {
  USD_MILLION: 1,
  USD: 1 / 1_000_000,
  EUR_MILLION: 1.09,
  EUR: 1.09 / 1_000_000,
  GBP_MILLION: 1.29,
  GBP: 1.29 / 1_000_000,
};

export function resolveScaleComparisonForAmount(
  amountMillions: number,
  currency: string | undefined,
  locale: Locale,
  mode: Mode,
  context?: ScaleComparisonContext
): ScaleComparison | null {
  return resolveScaleComparisonsForAmount(amountMillions, currency, locale, mode, 1, context)[0] || null;
}

export function resolveScaleComparisonsForAmount(
  amountMillions: number,
  currency: string | undefined,
  locale: Locale,
  mode: Mode,
  limit?: number,
  context?: ScaleComparisonContext
): ScaleComparison[] {
  if (isV22Requested()) {
    const estimatedEur = toEurAmount(amountMillions, currency);
    if (estimatedEur != null) {
      const set = resolveV22Set({
        artworkId: context?.artworkId || `value-${amountMillions}`,
        estimatedEur,
        mode,
        city: context?.city,
        sessionId: context?.sessionId || "no-visit-session",
        surpriseCounter: context?.surpriseCounter,
        excludeIds: context?.excludeIds,
        locale,
        fixedIds: context?.fixedIds,
      });
      if (set) {
        return [...set.rows, ...(set.easterEgg ? [set.easterEgg] : [])].map((row) => ({
          referenceId: row.id,
          category: row.category,
          engineVersion: set.engineVersion,
          monetary: row.category !== "easter_egg",
          icon: row.icon,
          label: row.label,
          sentence: row.punchline ? `${row.text}. ${row.punchline}` : row.text,
          shortSentence: row.text,
          countLabel: row.humanized,
          source: row.category === "easter_egg" ? "ELYIO product easter egg; no monetary role." : "Verified V2.2 governed reference.",
          ...(row.punchline ? { punchline: row.punchline } : {}),
        }));
      }
    }
  }
  const amountUsdMillions = toUsdMillions(amountMillions, currency);
  if (amountUsdMillions == null || amountUsdMillions <= 0) return [];
  const audience: ScaleAudience = mode === "kids" ? "kids" : "adult";
  const localReference = mode === "kids" ? null : localPropertyReference(context?.city);
  const candidates = [...COMPARISON_REFERENCES, ...(localReference ? [localReference] : [])].filter(
    (reference) =>
      reference.active &&
      reference.allowedLocales.includes(locale) &&
      reference.ageSuitability.includes(audience) &&
      amountUsdMillions >= toUsdMillions(reference.usefulAmountMillions.min, reference.currency)! &&
      amountUsdMillions <= toUsdMillions(reference.usefulAmountMillions.max, reference.currency)! &&
      quantityIsUseful(amountUsdMillions, reference)
  );
  const rowLimit = limit ?? (mode === "normal" ? 3 : mode === "simple" ? 2 : 3);
  const ordered = orderReferences(candidates, context, amountUsdMillions);
  const monetaryRows = ordered.slice(0, rowLimit).map((reference): ScaleComparison | null => {
    const range = comparisonRange(amountUsdMillions, reference);
    if (!range) return null;
    return {
      referenceId: reference.id,
      category: reference.category,
      engineVersion: COMPARISON_ENGINE_VERSION,
      monetary: true,
      icon: iconFor(reference.category),
      label: reference.label[locale] || reference.label.en,
      sentence: sentenceFor(reference, range, locale, mode),
      shortSentence: shortSentenceFor(reference, range, locale, mode),
      countLabel: countLabelFor(range, reference, locale),
      source: reference.source,
    };
  }).filter((comparison): comparison is ScaleComparison => !!comparison);
  if (rowLimit >= 3 && monetaryRows.length === rowLimit && shouldShowFounderEasterEgg(context)) {
    monetaryRows[monetaryRows.length - 1] = founderEasterEgg(locale);
  }
  return monetaryRows;
}

function toEurAmount(amountMillions: number, currency: string | undefined): number | null {
  if (!Number.isFinite(amountMillions)) return null;
  const key = currency || "USD_MILLION";
  const unit = key.endsWith("_MILLION") ? 1_000_000 : 1;
  const code = key.replace("_MILLION", "");
  const toEur = code === "EUR" ? 1 : code === "USD" ? 1 / 1.09 : code === "GBP" ? 1.29 / 1.09 : null;
  return toEur == null ? null : amountMillions * unit * toEur;
}

export function resolveScaleComparisonSentence(
  low: number | null,
  high: number | null,
  locale: Locale,
  mode: "normal" | "simple"
): string | null {
  if (low == null || high == null) return null;
  const comparison = resolveScaleComparisonForAmount((low + high) / 2, "EUR_MILLION", locale, mode);
  return comparison?.sentence ?? null;
}

export function resolveKidsScaleComparison(low: number | null, high: number | null, locale: Locale): string | null {
  if (low == null || high == null) return null;
  const comparison = resolveScaleComparisonForAmount((low + high) / 2, "EUR_MILLION", locale, "kids");
  return comparison?.sentence ?? null;
}

export function resolveValueRevealScaleComparison(valueReveal: ValueReveal | null, locale: Locale, mode: Mode, context?: ScaleComparisonContext): ScaleComparison | null {
  if (!isResponsibleNumericEstimate(valueReveal)) return null;
  const numeric = valueRevealNumericContext(valueReveal);
  if (!numeric) return null;
  return resolveScaleComparisonForAmount(numeric.amountMillions, numeric.currency, locale, mode, context);
}

export function resolveValueRevealScaleComparisons(valueReveal: ValueReveal | null, locale: Locale, mode: Mode, context?: ScaleComparisonContext): ScaleComparison[] {
  if (!isResponsibleNumericEstimate(valueReveal)) return [];
  const numeric = valueRevealNumericContext(valueReveal);
  if (!numeric) return [];
  return resolveScaleComparisonsForAmount(numeric.amountMillions, numeric.currency, locale, mode, undefined, context);
}

export function isResponsibleNumericEstimate(valueReveal: ValueReveal | null): boolean {
  if (valueReveal?.mode === "ESTIMATED_VALUE") {
    return valueReveal.aggregateValueEligible === true
      && Number.isFinite(valueReveal.estimatedValue.low)
      && Number.isFinite(valueReveal.estimatedValue.high)
      && valueReveal.estimatedValue.low > 0
      && valueReveal.estimatedValue.high >= valueReveal.estimatedValue.low;
  }
  if (valueReveal?.mode === "AI_INDICATIVE_ESTIMATE") {
    const estimate = valueReveal.aiIndicativeEstimate;
    return valueReveal.indicativeAggregateEligible === true
      && estimate.version === "ai-indicative-estimate-v4"
      && estimate.currency === "EUR"
      && Number.isFinite(estimate.lowEur)
      && Number.isFinite(estimate.highEur)
      && estimate.lowEur > 0
      && estimate.highEur > estimate.lowEur
      && estimate.highEur <= 1_000_000_000;
  }
  return false;
}

export function valueRevealNumericContext(valueReveal: ValueReveal | null): { amountMillions: number; currency: string | undefined } | null {
  if (!valueReveal) return null;
  if (valueReveal.mode === "ESTIMATED_VALUE") {
    return {
      amountMillions: (valueReveal.estimatedValue.low + valueReveal.estimatedValue.high) / 2,
      currency: valueReveal.estimatedValue.currency === "EUR" ? "EUR_MILLION" : valueReveal.estimatedValue.currency,
    };
  }
  if (valueReveal.mode === "AI_INDICATIVE_ESTIMATE") {
    if (valueReveal.aiIndicativeEstimate.version !== "ai-indicative-estimate-v4") return null;
    if (valueReveal.aiIndicativeEstimate.highEur > 1_000_000_000) return null;
    return {
      amountMillions: ((valueReveal.aiIndicativeEstimate.lowEur + valueReveal.aiIndicativeEstimate.highEur) / 2) / 1_000_000,
      currency: "EUR_MILLION",
    };
  }
  if (valueReveal.mode === "MARKET_CONTEXT") {
    const number = valueReveal.marketContext.headlineNumber;
    if (typeof number === "number") return { amountMillions: number, currency: valueReveal.marketContext.currency };
    if (typeof number === "object" && number && typeof number.low === "number" && typeof number.high === "number") {
      return { amountMillions: (number.low + number.high) / 2, currency: valueReveal.marketContext.currency };
    }
    return null;
  }
  const optional = valueReveal.beyondMarket.optionalContext;
  if (!optional) return null;
  const match = optional.match(/([$€£])\s?([0-9]+(?:[.,][0-9]+)?)\s?M/i) || optional.match(/([0-9]+(?:[.,][0-9]+)?)\s?(?:million|millions)/i);
  if (!match) return null;
  const symbol = match[1]?.match(/[$€£]/) ? match[1] : "$";
  const numberText = match[2] || match[1];
  const number = Number(numberText.replace(",", "."));
  if (!Number.isFinite(number)) return null;
  const currency = symbol === "€" ? "EUR_MILLION" : symbol === "£" ? "GBP_MILLION" : "USD_MILLION";
  return { amountMillions: number, currency };
}

function orderReferences(candidates: ScaleReference[], context: ScaleComparisonContext | undefined, amountUsdMillions: number): ScaleReference[] {
  const seed = `${COMPARISON_ENGINE_VERSION}|${context?.artworkId || amountUsdMillions.toFixed(3)}|${context?.city || "global"}|${context?.countryCode || ""}`;
  const uniqueByCategory = new Map<ComparisonCategory, ScaleReference>();
  for (const candidate of [...candidates].sort((a, b) => stableHash(`${seed}|${a.id}`) - stableHash(`${seed}|${b.id}`))) {
    if (!uniqueByCategory.has(candidate.category)) uniqueByCategory.set(candidate.category, candidate);
  }
  const local = uniqueByCategory.get("PRIME_PROPERTY");
  const global = [...uniqueByCategory.values()].filter((reference) => reference.category !== "PRIME_PROPERTY");
  // A local row appears often enough to feel contextual, without making
  // property one of the same three rows on every artwork.
  if (!local) return global;
  return stableHash(`${seed}|local-property`) % 100 < 55 ? [local, ...global] : [...global, local];
}

function iconFor(category: ComparisonCategory): string {
  if (category === "LIGHT_PRIVATE_JET" || category === "LARGE_BUSINESS_JET" || category === "COMMERCIAL_AIRCRAFT") return "✈";
  if (category === "SUPERCAR") return "🏎";
  if (category === "PRIME_PROPERTY") return "⌂";
  if (category === "YACHT") return "◈";
  if (category === "SPACEFLIGHT") return "🚀";
  if (category === "LUXURY_HOLIDAY") return "☀";
  if (category === "LUXURY_HOTEL") return "▣";
  if (category === "PRIVATE_ISLAND") return "🏝";
  if (category === "EDUCATION") return "🎓";
  if (category === "ENTERTAINMENT_BUDGET") return "🎬";
  return "•";
}

function comparisonRange(amountUsdMillions: number, reference: ScaleReference): { low: number; high: number } | null {
  const lowUnit = toUsdMillions(reference.unitValueMillions.high, reference.currency);
  const highUnit = toUsdMillions(reference.unitValueMillions.low, reference.currency);
  if (!lowUnit || !highUnit) return null;
  const low = roundRangeCount(amountUsdMillions / lowUnit);
  const high = roundRangeCount(amountUsdMillions / highUnit);
  if (low <= 0 || high <= 0) return null;
  return { low: Math.min(low, high), high: Math.max(low, high) };
}

function sentenceFor(reference: ScaleReference, range: { low: number; high: number }, locale: Locale, mode: Mode): string {
  const count = countLabelFor(range, reference, locale);
  if (mode === "kids") {
    if (locale === "fr") return `Imagine cette somme : environ ${count}.`;
    if (locale === "zh-Hans") return `想象一下这个数字：大约相当于${count}。`;
    return `Imagine that much money: about ${count}.`;
  }
  if (mode === "simple") {
    if (locale === "fr") return `Pensez à environ ${count}.`;
    if (locale === "zh-Hans") return `可以想成大约${count}。`;
    return `Think of it as roughly ${count}.`;
  }
  if (locale === "fr") return `Pour situer l'échelle : environ ${count}.`;
  if (locale === "zh-Hans") return `作为量级参照：大约相当于${count}。`;
  return `For scale: roughly ${count}.`;
}

function shortSentenceFor(reference: ScaleReference, range: { low: number; high: number }, locale: Locale, mode: Mode): string {
  const count = countLabelFor(range, reference, locale);
  if (mode === "kids") {
    if (locale === "fr") return `Imagine : ${count}`;
    if (locale === "zh-Hans") return `想象一下：${count}`;
    return `Imagine: ${count}`;
  }
  if (locale === "fr") return `environ ${count}`;
  if (locale === "zh-Hans") return `约${count}`;
  return `roughly ${count}`;
}

function countLabelFor(range: { low: number; high: number }, reference: ScaleReference, locale: Locale): string {
  const label = reference.label[locale] || reference.label.en;
  if (range.low >= 1_000_000 || range.high >= 1_000_000) {
    const low = Math.max(1, Math.round(range.low / 1_000_000));
    const high = Math.max(low, Math.round(range.high / 1_000_000));
    if (locale === "fr") return low === high ? `${low} million de ${label}` : `${low} à ${high} millions de ${label}`;
    if (locale === "zh-Hans") return low === high ? `${low}百万个${label}` : `${low}到${high}百万个${label}`;
    return low === high ? `${low} million ${label}` : `${low}-${high} million ${label}`;
  }
  if (range.low >= 10_000 || range.high >= 10_000) {
    const low = formatLargeCount(range.low, locale);
    const high = formatLargeCount(range.high, locale);
    if (range.low === range.high) return `${low} ${label}`;
    if (locale === "fr") return `${low} à ${high} ${label}`;
    if (locale === "zh-Hans") return `${low}到${high}个${label}`;
    return `${low}-${high} ${label}`;
  }
  if (range.low === range.high) {
    if (range.low === 1) {
      if (locale === "fr") return `un ${label}`;
      if (locale === "zh-Hans") return `一架${label}`;
      return `one ${reference.singularLabel?.[locale] || label}`;
    }
    return `${range.low} ${label}`;
  }
  if (locale === "fr") return `${range.low} à ${range.high} ${label}`;
  if (locale === "zh-Hans") return `${range.low}到${range.high}个${label}`;
  return `${range.low}-${range.high} ${label}`;
}

function roundRangeCount(value: number): number {
  if (value < 1.4) return 1;
  if (value < 10) return Math.round(value);
  if (value < 50) return Math.round(value / 5) * 5;
  if (value < 200) return Math.round(value / 10) * 10;
  if (value < 1000) return Math.round(value / 25) * 25;
  if (value < 10_000) return Math.round(value / 500) * 500;
  if (value < 100_000) return Math.round(value / 5_000) * 5_000;
  if (value < 1_000_000) return Math.round(value / 50_000) * 50_000;
  return Math.round(value / 500_000) * 500_000;
}

function formatLargeCount(value: number, locale: Locale): string {
  const rounded = value >= 100_000 ? Math.round(value / 5_000) * 5_000 : value;
  if (locale === "zh-Hans") return String(rounded);
  return rounded.toLocaleString(locale === "fr" ? "fr-FR" : "en-US");
}

function toUsdMillions(amount: number, currency: string | undefined): number | null {
  const key = currency || "USD_MILLION";
  const multiplier = CURRENCY_TO_USD[key];
  if (!multiplier || !Number.isFinite(amount)) return null;
  return amount * multiplier;
}

function quantityIsUseful(amountUsdMillions: number, reference: ScaleReference): boolean {
  const range = comparisonRange(amountUsdMillions, reference);
  return !!range && range.low >= reference.usefulQuantity.min && range.high <= reference.usefulQuantity.max;
}

function stableHash(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  hash ^= hash >>> 16;
  hash = Math.imul(hash, 0x85ebca6b);
  hash ^= hash >>> 13;
  hash = Math.imul(hash, 0xc2b2ae35);
  hash ^= hash >>> 16;
  return hash >>> 0;
}

function shouldShowFounderEasterEgg(context?: ScaleComparisonContext): boolean {
  if (!context?.artworkId) return false;
  return stableHash(`${COMPARISON_ENGINE_VERSION}|founder|${context.artworkId}`) % 100 < 4;
}

function founderEasterEgg(locale: Locale): ScaleComparison {
  const copy = locale === "fr"
    ? "une rencontre avec le fondateur d’ELYIO — apparemment inestimable"
    : locale === "zh-Hans"
      ? "与 ELYIO 创始人见一次面——据说无价"
      : "one meeting with ELYIO’s founder — apparently priceless";
  return {
    referenceId: "elyio_founder_easter_egg_v1",
    category: "FOUNDER_EASTER_EGG",
    engineVersion: COMPARISON_ENGINE_VERSION,
    monetary: false,
    icon: "🤝",
    label: copy,
    sentence: copy,
    shortSentence: copy,
    countLabel: copy,
    source: "ELYIO product easter egg; no monetary reference or valuation role.",
  };
}
