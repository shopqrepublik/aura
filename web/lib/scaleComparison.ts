import type { Locale, Mode, ValueReveal } from "./types";

export type ScaleAudience = "adult" | "kids";

export interface ScaleReference {
  id: string;
  label: Record<Locale, string>;
  unitValueMillions: { low: number; high: number };
  currency: "USD_MILLION" | "EUR_MILLION";
  source: string;
  methodology: string;
  lastReviewedDate: string;
  allowedLocales: Locale[];
  ageSuitability: ScaleAudience[];
  usefulAmountMillions: { min: number; max: number };
}

export interface ScaleComparison {
  referenceId: string;
  label: string;
  sentence: string;
  shortSentence: string;
  countLabel: string;
  source: string;
}

export const SCALE_REFERENCES: ScaleReference[] = [
  {
    id: "wide_body_aircraft",
    label: {
      en: "modern wide-body aircraft",
      fr: "avion long-courrier moderne",
      "zh-Hans": "大型现代宽体客机",
    },
    unitValueMillions: { low: 110, high: 140 },
    currency: "USD_MILLION",
    source: "Editorial benchmark from recent wide-body aircraft market/list-price ranges; reviewed as a scale analogy, not a purchase quote.",
    methodology: "Use for nine-figure art-market context where one or several aircraft communicates magnitude.",
    lastReviewedDate: "2026-08-13",
    allowedLocales: ["en", "fr", "zh-Hans"],
    ageSuitability: ["adult", "kids"],
    usefulAmountMillions: { min: 80, max: 600 },
  },
  {
    id: "ferrari_class_supercar",
    label: {
      en: "Ferrari-class supercars",
      fr: "supercars de type Ferrari",
      "zh-Hans": "法拉利级别超跑",
    },
    unitValueMillions: { low: 0.35, high: 0.45 },
    currency: "USD_MILLION",
    source: "Editorial benchmark from current high-end supercar order-of-magnitude pricing.",
    methodology: "Use rounded ranges only; never exact car counts.",
    lastReviewedDate: "2026-08-13",
    allowedLocales: ["en", "fr", "zh-Hans"],
    ageSuitability: ["adult", "kids"],
    usefulAmountMillions: { min: 5, max: 250 },
  },
  {
    id: "central_paris_apartment",
    label: {
      en: "prime central-Paris apartments",
      fr: "appartements haut de gamme au centre de Paris",
      "zh-Hans": "巴黎市中心高端公寓",
    },
    unitValueMillions: { low: 2.5, high: 4.5 },
    currency: "EUR_MILLION",
    source: "Editorial benchmark using central Paris luxury-apartment order-of-magnitude pricing.",
    methodology: "Use ranges to communicate urban real-estate scale without implying exact valuation.",
    lastReviewedDate: "2026-08-13",
    allowedLocales: ["en", "fr", "zh-Hans"],
    ageSuitability: ["adult"],
    usefulAmountMillions: { min: 8, max: 250 },
  },
  {
    id: "luxury_yacht",
    label: {
      en: "50-metre luxury yachts",
      fr: "yachts de luxe de 50 mètres",
      "zh-Hans": "50米级豪华游艇",
    },
    unitValueMillions: { low: 25, high: 45 },
    currency: "USD_MILLION",
    source: "Editorial benchmark from specialist yacht-build cost ranges.",
    methodology: "Use for mid/high eight-figure art-market context.",
    lastReviewedDate: "2026-08-13",
    allowedLocales: ["en", "fr", "zh-Hans"],
    ageSuitability: ["adult"],
    usefulAmountMillions: { min: 20, max: 180 },
  },
  {
    id: "football_transfer",
    label: {
      en: "elite football transfer fees",
      fr: "transferts de football de très haut niveau",
      "zh-Hans": "顶级足球转会费",
    },
    unitValueMillions: { low: 70, high: 120 },
    currency: "EUR_MILLION",
    source: "Editorial benchmark from recent elite European football transfer-fee ranges.",
    methodology: "Use only as a broad cultural scale comparison.",
    lastReviewedDate: "2026-08-13",
    allowedLocales: ["en", "fr", "zh-Hans"],
    ageSuitability: ["adult"],
    usefulAmountMillions: { min: 50, max: 250 },
  },
  {
    id: "ice_cream",
    label: {
      en: "ice creams",
      fr: "glaces",
      "zh-Hans": "冰淇淋",
    },
    unitValueMillions: { low: 0.000004, high: 0.000006 },
    currency: "EUR_MILLION",
    source: "Editorial everyday-price benchmark for children's scale copy.",
    methodology: "Use only rounded million-level quantities.",
    lastReviewedDate: "2026-08-13",
    allowedLocales: ["en", "fr", "zh-Hans"],
    ageSuitability: ["kids"],
    usefulAmountMillions: { min: 1, max: 80 },
  },
];

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
  mode: Mode
): ScaleComparison | null {
  const amountUsdMillions = toUsdMillions(amountMillions, currency);
  if (amountUsdMillions == null || amountUsdMillions <= 0) return null;
  const audience: ScaleAudience = mode === "kids" ? "kids" : "adult";
  const candidates = SCALE_REFERENCES.filter(
    (reference) =>
      reference.allowedLocales.includes(locale) &&
      reference.ageSuitability.includes(audience) &&
      amountUsdMillions >= toUsdMillions(reference.usefulAmountMillions.min, reference.currency)! &&
      amountUsdMillions <= toUsdMillions(reference.usefulAmountMillions.max, reference.currency)!
  );
  const reference = pickReference(amountUsdMillions, candidates, mode);
  if (!reference) return null;
  const range = comparisonRange(amountUsdMillions, reference);
  if (!range) return null;
  return {
    referenceId: reference.id,
    label: reference.label[locale] || reference.label.en,
    sentence: sentenceFor(reference, range, locale, mode),
    shortSentence: shortSentenceFor(reference, range, locale, mode),
    countLabel: countLabelFor(range, reference, locale),
    source: reference.source,
  };
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

export function resolveValueRevealScaleComparison(valueReveal: ValueReveal | null, locale: Locale, mode: Mode): ScaleComparison | null {
  const numeric = valueRevealNumericContext(valueReveal);
  if (!numeric) return null;
  return resolveScaleComparisonForAmount(numeric.amountMillions, numeric.currency, locale, mode);
}

export function valueRevealNumericContext(valueReveal: ValueReveal | null): { amountMillions: number; currency: string | undefined } | null {
  if (!valueReveal) return null;
  if (valueReveal.mode === "ESTIMATED_VALUE") {
    return {
      amountMillions: (valueReveal.estimatedValue.low + valueReveal.estimatedValue.high) / 2,
      currency: valueReveal.estimatedValue.currency === "EUR" ? "EUR_MILLION" : valueReveal.estimatedValue.currency,
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

function pickReference(amountUsdMillions: number, candidates: ScaleReference[], mode: Mode): ScaleReference | null {
  if (candidates.length === 0) return null;
  if (mode === "kids") {
    return candidates.find((candidate) => candidate.id === "ferrari_class_supercar")
      || candidates.find((candidate) => candidate.id === "wide_body_aircraft")
      || candidates[0];
  }
  if (amountUsdMillions >= 80) {
    return candidates.find((candidate) => candidate.id === "wide_body_aircraft") || candidates[0];
  }
  if (amountUsdMillions >= 15) {
    return candidates.find((candidate) => candidate.id === "ferrari_class_supercar")
      || candidates.find((candidate) => candidate.id === "central_paris_apartment")
      || candidates[0];
  }
  return candidates.find((candidate) => candidate.id === "central_paris_apartment") || candidates[0];
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
  if (range.low === range.high) {
    if (range.low === 1) {
      if (locale === "fr") return `un ${label}`;
      if (locale === "zh-Hans") return `一架${label}`;
      return `one ${label}`;
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
  return Math.round(value / 25) * 25;
}

function toUsdMillions(amount: number, currency: string | undefined): number | null {
  const key = currency || "USD_MILLION";
  const multiplier = CURRENCY_TO_USD[key];
  if (!multiplier || !Number.isFinite(amount)) return null;
  return amount * multiplier;
}
