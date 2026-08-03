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
 * logic:
 *  - kidsModeExcluded works: no Kids content at all — caller must check
 *    `isExcludedInKids` and show the neutral message instead of calling this.
 *  - whyKids/whereKids: used only in kids mode, when present; every other
 *    work and mode falls back to the plain why/where.
 *  - rarity is never mode-specific.
 */
export function isExcludedInKids(artwork: Artwork, mode: Mode): boolean {
  return mode === "kids" && artwork.kidsModeExcluded === true;
}

export function resolveCardText(artwork: Artwork, mode: Mode, locale: Locale) {
  const whySource = mode === "kids" && artwork.whyKids ? artwork.whyKids : artwork.why;
  const whereSource = mode === "kids" && artwork.whereKids ? artwork.whereKids : artwork.where;
  return {
    why: pick(whySource, locale),
    where: pick(whereSource, locale),
    rarity: pick(artwork.rarity, locale),
  };
}

export function resolveTitle(artwork: Artwork, locale: Locale): string {
  return pick(artwork.title, locale);
}

export function missionLabel(mission: Mission, locale: Locale): string {
  return mission[locale] || mission.en;
}
