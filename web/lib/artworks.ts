import artworksJson from "./data/artworks.json";
import missionsJson from "./data/missions.json";
import stringsJson from "./data/strings.json";
import type { Artwork, Mission, UIStrings, Locale, Mode, LocalizedText } from "./types";

export const ARTWORKS = artworksJson as unknown as Artwork[];
export const MISSIONS = missionsJson as unknown as Mission[];
export const STRINGS = stringsJson as unknown as UIStrings;

const BY_ID = new Map(ARTWORKS.map((a) => [a.id, a]));

export function getArtwork(id: string): Artwork | undefined {
  return BY_ID.get(id);
}

export function t(key: keyof UIStrings, locale: Locale): string {
  const entry = STRINGS[key];
  return entry?.[locale] ?? entry?.en ?? key;
}

function pick(text: LocalizedText, locale: Locale): string {
  return text[locale] || text.en;
}

/**
 * Content policy (§ Kids mode), ported 1:1 from the old app.js renderCard()
 * logic, then extended to Simple mode on the same principle:
 *  - kidsModeExcluded works: no Kids content at all — caller must check
 *    `isExcludedInKids` and show the neutral message instead of calling this.
 *  - whyKids/whereKids/rarityKids: used only in kids mode, when present;
 *    every other work/field/mode falls back to the plain Normal text.
 *    Absence is normal, not a bug — most works only got a Kids rewrite for
 *    the specific field that actually needed one (e.g. Gauguin has whyKids
 *    but no whereKids, because only "why" touched colonial context).
 *  - whySimple/whereSimple/raritySimple: same fallback rule for Simple mode.
 *  - Kids always wins over Simple if both exist for a field (shouldn't
 *    normally co-occur as a choice — mode is a single select, not a stack —
 *    but this keeps precedence explicit rather than accidental).
 */
export function isExcludedInKids(artwork: Artwork, mode: Mode): boolean {
  return mode === "kids" && artwork.kidsModeExcluded === true;
}

function resolveModeText(normal: LocalizedText, kids: LocalizedText | undefined, simple: LocalizedText | undefined, mode: Mode): LocalizedText {
  if (mode === "kids" && kids) return kids;
  if (mode === "simple" && simple) return simple;
  return normal;
}

export function resolveCardText(artwork: Artwork, mode: Mode, locale: Locale) {
  const whySource = resolveModeText(artwork.why, artwork.whyKids, artwork.whySimple, mode);
  const whereSource = resolveModeText(artwork.where, artwork.whereKids, artwork.whereSimple, mode);
  const raritySource = resolveModeText(artwork.rarity, artwork.rarityKids, artwork.raritySimple, mode);
  return {
    why: pick(whySource, locale),
    where: pick(whereSource, locale),
    rarity: pick(raritySource, locale),
  };
}

export function resolveTitle(artwork: Artwork, locale: Locale): string {
  return pick(artwork.title, locale);
}

export function missionLabel(mission: Mission, locale: Locale): string {
  return mission[locale] || mission.en;
}
