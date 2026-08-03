import type { Locale, LocalizedText } from "./types";

// "Scale comparison" badge — real logic driven by the artwork's own
// estimate midpoint, not a hardcoded example. Values below are approximate,
// sourced reference points (not invented): Paris apartment price/m² from
// 2025-2026 market data (~€9,700-10,450/m²), Boeing 787-9 list price
// (~$295M), private jet ranges (Cessna/Gulfstream, $5M-75M), superyacht
// ranges (€25-50M at 50m new-build, ~€250M+ at 100m+ custom build) — all
// approximate and meant to be updated as real prices move, same spirit as
// the artwork estimates themselves: illustrative, not exact.

interface ComparisonObject {
  id: string;
  valueEur: number; // in EUR, same unit as Artwork.estimate (millions) x1e6 handled by caller
  label: LocalizedText;
}

// Values in EUR millions, matching Artwork.estimate.low/high's unit.
const ADULT_OBJECTS: ComparisonObject[] = [
  { id: "paris_apartment", valueEur: 0.5, label: { en: "Paris apartment", fr: "appartement parisien", "zh-Hans": "巴黎公寓" } },
  { id: "light_jet", valueEur: 5, label: { en: "light private jet", fr: "jet privé léger", "zh-Hans": "轻型私人飞机" } },
  { id: "superyacht_50m", valueEur: 35, label: { en: "50-metre superyacht", fr: "superyacht de 50 mètres", "zh-Hans": "50米超级游艇" } },
  { id: "heavy_jet", valueEur: 65, label: { en: "long-range private jet", fr: "jet privé long-courrier", "zh-Hans": "远程私人飞机" } },
  { id: "superyacht_100m", valueEur: 250, label: { en: "100-metre superyacht", fr: "superyacht de 100 mètres", "zh-Hans": "100米超级游艇" } },
  { id: "boeing_787", valueEur: 270, label: { en: "Boeing 787", fr: "Boeing 787", "zh-Hans": "波音787客机" } },
];

// Kids table: deliberately NOT a reuse of the adult list — a 6-year-old has
// no intuition for "a private jet" as a unit, but absolutely has one for
// ice cream, LEGO, bikes and rollercoasters. Values are everyday-knowledge
// approximations (not independently sourced the way the adult table's
// big-ticket items were, since these are common consumer prices, not
// specialist market data).
const KIDS_OBJECTS: ComparisonObject[] = [
  { id: "ice_cream", valueEur: 0.000004, label: { en: "ice cream scoop", fr: "boule de glace", "zh-Hans": "一球冰淇淋" } },
  { id: "lego_set", valueEur: 0.00006, label: { en: "LEGO set", fr: "boîte de LEGO", "zh-Hans": "一套乐高" } },
  { id: "bicycle", valueEur: 0.0002, label: { en: "bicycle", fr: "vélo", "zh-Hans": "自行车" } },
  { id: "theme_park_day", valueEur: 0.0006, label: { en: "family day at a theme park", fr: "journée en famille dans un parc d'attractions", "zh-Hans": "一次家庭主题乐园之旅" } },
  { id: "backyard_pool", valueEur: 0.04, label: { en: "backyard swimming pool", fr: "piscine de jardin", "zh-Hans": "自家后院游泳池" } },
  { id: "rollercoaster", valueEur: 12, label: { en: "real rollercoaster", fr: "vrais grand huit", "zh-Hans": "一座真正的过山车" } },
];

function roundNicely(n: number): number {
  if (n < 10) return Math.round(n);
  if (n < 50) return Math.round(n / 5) * 5;
  if (n < 200) return Math.round(n / 10) * 10;
  return Math.round(n / 25) * 25;
}

/** Largest-value object whose implied count is still >= 1 — avoids ever
 * landing on an awkward "0.2 Boeing 787s" by walking down to a smaller,
 * more countable object instead of always picking the closest order of
 * magnitude regardless of direction. */
function pickComparison(midpointEur: number, objects: ComparisonObject[]): { object: ComparisonObject; count: number } | null {
  const sorted = [...objects].sort((a, b) => b.valueEur - a.valueEur);
  for (const obj of sorted) {
    const count = midpointEur / obj.valueEur;
    if (count >= 1) return { object: obj, count: roundNicely(count) };
  }
  // Artwork smaller than even the smallest object -- fall back to it anyway
  // (only reachable in principle; our real catalog never estimates this low).
  const smallest = sorted[sorted.length - 1];
  return smallest ? { object: smallest, count: Math.max(1, roundNicely(midpointEur / smallest.valueEur)) } : null;
}

function pick(text: LocalizedText, locale: Locale): string {
  return text[locale] || text.en;
}

function pluralize(count: number, singular: string, locale: Locale): string {
  if (locale !== "en") return singular; // FR/ZH labels below are written to work unchanged with a leading count
  return count === 1 ? singular : `${singular}s`;
}

/** Adult "≈ N object" badge text. Returns null when there's no estimate --
 * no estimate means no comparison, same rule as the price badge itself. */
export function resolveScaleComparison(low: number | null, high: number | null, locale: Locale): string | null {
  if (low == null || high == null) return null;
  const midpoint = (low + high) / 2;
  const result = pickComparison(midpoint, ADULT_OBJECTS);
  if (!result) return null;
  const label = pluralize(result.count, pick(result.object.label, locale), locale);
  return `≈ ${result.count} ${label}`;
}

/** Kids "Enough for N object!" sentence. Same null rule as the adult
 * version -- no estimate, no comparison, no exceptions. */
export function resolveKidsScaleComparison(low: number | null, high: number | null, locale: Locale): string | null {
  if (low == null || high == null) return null;
  const midpoint = (low + high) / 2;
  const result = pickComparison(midpoint, KIDS_OBJECTS);
  if (!result) return null;
  const label = pluralize(result.count, pick(result.object.label, locale), locale);
  const templates: Record<Locale, (count: number, label: string) => string> = {
    en: (c, l) => `That's enough for ${c} ${l}!`,
    fr: (c, l) => `De quoi s'offrir ${c} ${l} !`,
    "zh-Hans": (c, l) => `这些钱够买 ${c} 个${l}啦！`,
  };
  return templates[locale](result.count, label);
}
