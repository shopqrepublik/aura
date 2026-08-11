import { ARTWORKS } from "./artworks";
import { getAggregateEligibleValue } from "./valueReveal";
import type { Artwork } from "./types";

/**
 * Real, structured completion checks for the 3 launch missions (missions.json
 * stays pure localized copy -- this is where "did the user actually do the
 * thing" lives, keyed by mission id so the two callers -- HomeScreen's
 * per-mission list and ProgressScreen's "Next" CTA -- share one source of
 * truth instead of each re-deriving it).
 *
 * m1 "dots or dabs" (pointillism/divisionism): keyed off Artwork.techniqueTag,
 * not a free-text match against why/where/rarity copy. Audited against the
 * full 101-work catalog: Georges Seurat's The Circus (orsay_rf_2511) is the
 * ONLY work that is genuinely pointillist by technique. Claude Monet's Poppy
 * Field has editorial copy that uses "dot-like brushwork" language, but
 * that's Impressionist broken color, not pointillism -- deliberately not
 * tagged, since stretching the tag to include it would make "dots or dabs"
 * true for most Impressionist works in the catalog and the mission
 * meaningless. This means m1 currently has exactly one valid target work --
 * narrow, but real, not invented. Revisit if more pointillist/divisionist
 * works are added to the catalog later.
 *
 * m2 "self-portrait": keyed off Artwork.isSelfPortrait. Exactly 2 works in
 * the catalog qualify by title: Van Gogh's Self-portrait (Sept 1889,
 * orsay_rf_1949_17) and Gauguin's Self-portrait with hat (orsay_rf_1966_7).
 *
 * m3 "most valuable work" (originally worded "...in this room"): the
 * `hall` field is null on all 101 catalog works with zero exceptions -- a
 * room-scoped mission cannot be implemented against current data, so this
 * falls back to "most valuable work in the whole collection" (missions.json
 * copy updated to match, room reference removed) rather than a "priciest
 * thing scanned this visit" self-comparison, which would be vacuously true
 * the instant any single work with a real estimate is scanned and wouldn't
 * actually be a mission. Computed through the central aggregate-eligible
 * value rule, EXCLUDING ids already claimed by m1/m2 -- without that exclusion this
 * resolves to Seurat's The Circus (EUR140M, the catalog's actual highest
 * estimate), the same work as m1, which would let one scan silently
 * complete two of the three missions at once.
 */

const POINTILLISM_IDS = ARTWORKS.filter((a) => a.techniqueTag === "pointillism").map((a) => a.id);
const SELF_PORTRAIT_IDS = ARTWORKS.filter((a) => a.isSelfPortrait === true).map((a) => a.id);

const claimedByOtherMissions = new Set<string>([...POINTILLISM_IDS, ...SELF_PORTRAIT_IDS]);

function computeMostValuableId(): string | null {
  let best: Artwork | null = null;
  for (const a of ARTWORKS) {
    const aggregate = getAggregateEligibleValue(a);
    if (!aggregate) continue;
    if (claimedByOtherMissions.has(a.id)) continue;
    const bestAggregate = best ? getAggregateEligibleValue(best) : null;
    if (!bestAggregate || aggregate.high > bestAggregate.high) best = a;
  }
  return best?.id ?? null;
}

const mostValuableId = computeMostValuableId();

const MISSION_TARGET_IDS: Record<string, string[]> = {
  m1: POINTILLISM_IDS,
  m2: SELF_PORTRAIT_IDS,
  m3: mostValuableId ? [mostValuableId] : [],
};

/** Every work id that would satisfy the given mission, if scanned. */
export function missionTargetIds(missionId: string): string[] {
  return MISSION_TARGET_IDS[missionId] ?? [];
}

/** Has the user actually scanned a work that satisfies this mission? */
export function isMissionComplete(missionId: string, seenIds: string[]): boolean {
  const targets = MISSION_TARGET_IDS[missionId];
  if (!targets || targets.length === 0) return false;
  return targets.some((id) => seenIds.includes(id));
}
