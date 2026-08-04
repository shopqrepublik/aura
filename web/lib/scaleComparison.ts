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
  // Only needed for locales that actually inflect for plural. English
  // pluralizes automatically (+s, see pickLabel); zh-Hans never inflects
  // (Chinese has no grammatical plural) so `label` alone is always correct
  // there; French DOES inflect, so any object missing labelPlural.fr would
  // silently render the wrong grammatical number for any count other than
  // 1 -- this was a real, live bug (surfaced while testing ProvenanceReveal
  // in French: "2 jet privé long-courrier" instead of "2 jets privés long-
  // courriers") before labelPlural existed.
  labelPlural?: LocalizedText;
}

// Values in EUR millions, matching Artwork.estimate.low/high's unit.
const ADULT_OBJECTS: ComparisonObject[] = [
  {
    id: "paris_apartment",
    valueEur: 0.5,
    label: { en: "Paris apartment", fr: "appartement parisien", "zh-Hans": "巴黎公寓" },
    labelPlural: { en: "", fr: "appartements parisiens", "zh-Hans": "" },
  },
  {
    id: "light_jet",
    valueEur: 5,
    label: { en: "light private jet", fr: "jet privé léger", "zh-Hans": "轻型私人飞机" },
    labelPlural: { en: "", fr: "jets privés légers", "zh-Hans": "" },
  },
  {
    id: "superyacht_50m",
    valueEur: 35,
    label: { en: "50-metre superyacht", fr: "superyacht de 50 mètres", "zh-Hans": "50米超级游艇" },
    labelPlural: { en: "", fr: "superyachts de 50 mètres", "zh-Hans": "" },
  },
  {
    id: "heavy_jet",
    valueEur: 65,
    label: { en: "long-range private jet", fr: "jet privé long-courrier", "zh-Hans": "远程私人飞机" },
    labelPlural: { en: "", fr: "jets privés long-courriers", "zh-Hans": "" },
  },
  {
    id: "superyacht_100m",
    valueEur: 250,
    label: { en: "100-metre superyacht", fr: "superyacht de 100 mètres", "zh-Hans": "100米超级游艇" },
    labelPlural: { en: "", fr: "superyachts de 100 mètres", "zh-Hans": "" },
  },
  {
    id: "boeing_787",
    valueEur: 270,
    label: { en: "Boeing 787", fr: "Boeing 787", "zh-Hans": "波音787客机" },
    // Model name -- doesn't inflect in French (or English) regardless of count.
  },
];

// Kids table: deliberately NOT a reuse of the adult list — a 6-year-old has
// no intuition for "a private jet" as a unit, but absolutely has one for
// ice cream, LEGO, bikes and rollercoasters. Small-item values are
// everyday-knowledge approximations (not independently sourced the way the
// adult table's big-ticket items were, since these are common consumer
// prices, not specialist market data). The two big-ticket items
// (trampoline_park, rollercoaster) ARE sourced: a standard trampoline park
// (25,000-40,000 sq ft) runs ~$1.5-3M per industry cost guides, and a major
// theme-park rollercoaster is commonly cited in the $10-15M range.
// trampoline_park exists specifically to fill the gap between backyard_pool
// and rollercoaster -- without it, a €2-8M work (Cabanel, Ingres tier)
// landed on 50-140 backyard pools, which reads as flat/uncountable rather
// than a vivid, graspable comparison.
const KIDS_OBJECTS: ComparisonObject[] = [
  {
    id: "ice_cream",
    valueEur: 0.000004,
    label: { en: "ice cream scoop", fr: "boule de glace", "zh-Hans": "一球冰淇淋" },
    labelPlural: { en: "", fr: "boules de glace", "zh-Hans": "" },
  },
  {
    id: "lego_set",
    valueEur: 0.00006,
    label: { en: "LEGO set", fr: "boîte de LEGO", "zh-Hans": "一套乐高" },
    labelPlural: { en: "", fr: "boîtes de LEGO", "zh-Hans": "" },
  },
  {
    id: "bicycle",
    valueEur: 0.0002,
    label: { en: "bicycle", fr: "vélo", "zh-Hans": "自行车" },
    labelPlural: { en: "", fr: "vélos", "zh-Hans": "" },
  },
  {
    id: "theme_park_day",
    valueEur: 0.0006,
    label: {
      en: "family day at a theme park",
      fr: "journée en famille dans un parc d'attractions",
      "zh-Hans": "一次家庭主题乐园之旅",
    },
    labelPlural: { en: "", fr: "journées en famille dans un parc d'attractions", "zh-Hans": "" },
  },
  {
    id: "backyard_pool",
    valueEur: 0.04,
    label: { en: "backyard swimming pool", fr: "piscine de jardin", "zh-Hans": "自家后院游泳池" },
    labelPlural: { en: "", fr: "piscines de jardin", "zh-Hans": "" },
  },
  {
    id: "trampoline_park",
    valueEur: 2,
    label: { en: "trampoline park", fr: "parc de trampolines", "zh-Hans": "一座蹦床乐园" },
    labelPlural: { en: "", fr: "parcs de trampolines", "zh-Hans": "" },
  },
  {
    id: "rollercoaster",
    valueEur: 12,
    label: { en: "real rollercoaster", fr: "vrais grand huit", "zh-Hans": "一座真正的过山车" },
    // "grand huit" is an invariant colloquial compound in French -- doesn't
    // take a regular plural form, singular text is used at any count.
  },
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

/** Picks the grammatically correct form of an object's label for the given
 * count and locale: zh-Hans never inflects, en pluralizes with a plain "+s"
 * (every EN label here is a regular noun phrase, no irregulars in this
 * list), fr uses the object's explicit labelPlural when count != 1 and one
 * exists (falls back to the singular for the handful of invariant terms
 * like "Boeing 787" or "grand huit" that were never given one). */
function pickLabel(object: ComparisonObject, count: number, locale: Locale): string {
  const singular = pick(object.label, locale);
  if (count === 1) return singular;
  if (locale === "zh-Hans") return singular;
  if (locale === "en") return `${singular}s`;
  if (locale === "fr" && object.labelPlural?.fr) return object.labelPlural.fr;
  return singular;
}

/** Normal/Simple mode analogy sentence for ProvenanceReveal (design-
 * direction-v3 §2/§8 — "not a pill", a plain sentence):
 *  - Normal: "Comparable to approximately {count} {object}"
 *  - Simple: "That is about the price of {count} {object}"
 * Both share the exact same object table and math as each other -- v3's
 * Simple-mode example ("two large private planes" vs Normal's "two long-
 * range private jets") differs only in sentence framing, not in which real
 * object gets picked, so this reuses ADULT_OBJECTS rather than inventing a
 * parallel Simple-only comparison table. Kids mode keeps its own dedicated
 * table/template (resolveKidsScaleComparison, below) -- unrelated to this.
 * Null estimate -> null, same rule as everywhere else this data appears. */
export function resolveScaleComparisonSentence(
  low: number | null,
  high: number | null,
  locale: Locale,
  mode: "normal" | "simple"
): string | null {
  if (low == null || high == null) return null;
  const midpoint = (low + high) / 2;
  const result = pickComparison(midpoint, ADULT_OBJECTS);
  if (!result) return null;
  const label = pickLabel(result.object, result.count, locale);
  const templates: Record<"normal" | "simple", Record<Locale, (c: number, l: string) => string>> = {
    normal: {
      en: (c, l) => `Comparable to approximately ${c} ${l}`,
      fr: (c, l) => `Comparable à environ ${c} ${l}`,
      "zh-Hans": (c, l) => `大约相当于 ${c} 个${l}`,
    },
    simple: {
      en: (c, l) => `That is about the price of ${c} ${l}`,
      fr: (c, l) => `C'est à peu près le prix de ${c} ${l}`,
      "zh-Hans": (c, l) => `差不多是 ${c} 个${l}的价格`,
    },
  };
  return templates[mode][locale](result.count, label);
}

/** Kids "Enough for N object!" sentence. Same null rule as the adult
 * version -- no estimate, no comparison, no exceptions. */
export function resolveKidsScaleComparison(low: number | null, high: number | null, locale: Locale): string | null {
  if (low == null || high == null) return null;
  const midpoint = (low + high) / 2;
  const result = pickComparison(midpoint, KIDS_OBJECTS);
  if (!result) return null;
  const label = pickLabel(result.object, result.count, locale);
  const templates: Record<Locale, (count: number, label: string) => string> = {
    en: (c, l) => `That's enough for ${c} ${l}!`,
    fr: (c, l) => `De quoi s'offrir ${c} ${l} !`,
    "zh-Hans": (c, l) => `这些钱够买 ${c} 个${l}啦！`,
  };
  return templates[locale](result.count, label);
}
