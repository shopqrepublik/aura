
// ELYIO Comparison Engine v2.2 — Implementation
// Deterministic, no AI generation, truthful math

const ENGINE_VERSION = "2.2";

// FNV-1a hash for deterministic selection
function fnv1a(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// Humanize counts — no fake precision
function humanizeCount(count, locale = "en") {
  if (count < 1.5) return "~1";
  if (count < 10) return `~${Math.round(count)}`;
  if (count < 100) {
    const r = Math.round(count / 5) * 5;
    return `~${r}`;
  }
  if (count < 1000) {
    const r = Math.round(count / 50) * 50;
    return `~${r.toLocaleString(locale)}`;
  }
  if (count < 1000000) {
    const r = Math.round(count / 100) * 100;
    if (r >= 1000) return `~${(r/1000).toFixed(r%1000===0?0:1)}k`.replace('.0k','k');
    return `~${r.toLocaleString(locale)}`;
  }
  // millions
  const millions = count / 1e6;
  if (millions < 100) {
    const rounded = Math.round(millions * 10) / 10;
    return `~${rounded} million`;
  }
  return `~${Math.round(millions)} million`;
}

function formatComparison(count, comparison, locale="en") {
  const human = humanizeCount(count, locale);
  return `${comparison.emoji || ""} ${human} ${comparison.name_en}`.trim();
}

// Pool selectors
function getEligible(catalog, {mode, city, categoryFilter}) {
  return catalog.comparisons.filter(c => {
    if (c.is_easter_egg || c.category === "easter_egg") return false;
    if (categoryFilter && !categoryFilter.includes(c.category)) return false;
    if (mode && !c.modes.includes(mode)) return false;
    // City logic v2.2: city-specific only in its city, global allowed everywhere
    if (c.cities.includes("global")) return true;
    if (city && c.cities.includes(city)) return true;
    if (!city) return false; // if city-specific and no city match, exclude
    return false;
  });
}

function getCityEligible(catalog, mode, city) {
  if (!city) return [];
  return catalog.comparisons.filter(c => {
    if (c.is_easter_egg) return false;
    if (!c.modes.includes(mode)) return false;
    return c.cities.includes(city) && !c.cities.includes("global");
  });
}

function deterministicPick(pool, seedStr, count, excludeIds = []) {
  if (pool.length === 0) return [];
  let filtered = pool.filter(c => !excludeIds.includes(c.id));
  if (filtered.length === 0) filtered = pool;
  const hash = fnv1a(seedStr);
  const start = hash % filtered.length;
  const result = [];
  for (let i = 0; i < count && i < filtered.length; i++) {
    result.push(filtered[(start + i) % filtered.length]);
  }
  return result;
}

// Main selector per spec
function selectComparisons(catalog, {artworkId, estimatedEur, mode, city, sessionId, excludeIds = []}) {
  const seedBase = `${artworkId}|${mode}|${city}|${sessionId}`;
  let selected = [];

  if (mode === "normal") {
    const luxuryPool = getEligible(catalog, {mode, city, categoryFilter: ["luxury", "tech"]});
    const foodPool = getEligible(catalog, {mode, city, categoryFilter: ["food", "everyday"]});
    const cityPool = getCityEligible(catalog, mode, city);
    const fallbackPool = getEligible(catalog, {mode, city, categoryFilter: ["pop", "tech", "everyday", "luxury"]});

    const a = deterministicPick(luxuryPool, seedBase+"|A", 1, excludeIds)[0];
    const b = deterministicPick(foodPool, seedBase+"|B", 1, [...excludeIds, a?.id].filter(Boolean))[0];
    let cPool = cityPool.length > 0 ? cityPool : fallbackPool;
    const c = deterministicPick(cPool, seedBase+"|C", 1, [...excludeIds, a?.id, b?.id].filter(Boolean))[0];
    selected = [a,b,c].filter(Boolean);
  } else if (mode === "simple") {
    const foodPool = getEligible(catalog, {mode, city, categoryFilter: ["food", "everyday"]});
    const universalPool = getEligible(catalog, {mode, city, categoryFilter: ["food", "everyday", "tech", "city", "luxury"]});
    const a = deterministicPick(foodPool, seedBase+"|A", 1, excludeIds)[0];
    const b = deterministicPick(universalPool, seedBase+"|B", 1, [...excludeIds, a?.id].filter(Boolean))[0];
    selected = [a,b].filter(Boolean);
  } else if (mode === "kids") {
    const kidsPool = catalog.comparisons.filter(c => c.category === "kids" && !c.is_easter_egg);
    // deterministic 3
    selected = deterministicPick(kidsPool, seedBase+"|KIDS", 3, excludeIds);
  }

  // Calculate counts
  const results = selected.map(comp => {
    const price = comp.calculation_price_eur;
    if (!price || price <= 0) return null;
    const rawCount = estimatedEur / price;
    return {
      id: comp.id,
      emoji: comp.emoji,
      name_en: comp.name_en,
      name_ru: comp.name_ru,
      count: rawCount,
      humanized: humanizeCount(rawCount),
      formatted_en: formatComparison(rawCount, comp),
      punchline: selectPunchline(comp, rawCount),
      category: comp.category
    };
  }).filter(Boolean);

  // Easter egg 1% roll — deterministic per session too
  const easterRoll = fnv1a(seedBase+"|EASTER") % 100;
  let easterEgg = null;
  if (easterRoll === 0) { // 1%
    const founder = catalog.comparisons.find(c => c.id === "founder_meeting");
    if (founder) {
      easterEgg = {
        id: founder.id,
        emoji: "☕️",
        line_en: "One meeting with ELYIO's founder — Apparently priceless.",
        line_ru: "Встреча с фаундером ELYIO — Бесценно, но очень дорого.",
        is_easter_egg: true
      };
    }
  }

  return { results, easterEgg, seed: seedBase, engineVersion: ENGINE_VERSION };
}

function selectPunchline(comp, count) {
  if (!comp.punchlines) return null;
  // find matching range
  for (const p of comp.punchlines) {
    const min = p.min_count ?? 0;
    const max = p.max_count ?? Infinity;
    if (count >= min && count < max) return p;
  }
  return null;
}

function surpriseMe(catalog, prevState) {
  const {artworkId, estimatedEur, mode, city, sessionId, prevIds} = prevState;
  // new seed with surprise counter
  const newSessionId = sessionId + "|surprise|" + (prevState.surpriseCount || 1);
  const next = selectComparisons(catalog, {
    artworkId, estimatedEur, mode, city, sessionId: newSessionId, excludeIds: prevIds
  });
  // ensure no immediate repeat — if overlap, shift
  if (prevIds && next.results.some(r => prevIds.includes(r.id))) {
    // pick again with +1 offset
    return selectComparisons(catalog, {
      artworkId, estimatedEur, mode, city, sessionId: newSessionId + "|2", excludeIds: prevIds
    });
  }
  return {...next, surpriseCount: (prevState.surpriseCount||0)+1};
}

// Landing fixed demo
function getLandingDemo(catalog, demoSeed) {
  const results = [];
  for (const demo of demoSeed.demos) {
    const comps = demo.comparison_ids.map(id => catalog.comparisons.find(c => c.id === id)).filter(Boolean);
    const calculated = comps.map(comp => {
      const raw = demo.estimated_eur / (comp.calculation_price_eur || 1);
      return {
        id: comp.id,
        formatted_en: formatComparison(raw, comp),
        punchline: selectPunchline(comp, raw),
        humanized: humanizeCount(raw)
      };
    });
    results.push({...demo, calculated});
  }
  return results;
}

// Export for Node / browser
if (typeof module !== "undefined") module.exports = { fnv1a, humanizeCount, selectComparisons, surpriseMe, getLandingDemo, ENGINE_VERSION };
