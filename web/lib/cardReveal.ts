"use client";

import { useEffect, useState } from "react";

// Design-direction-v3 §6 "Три уровня интенсивности" — tier is read off the
// TOP of the estimate range (estimate.high), the same field lib/missions.ts
// and lib/recap-image.ts already treat as "the value" of a work elsewhere
// in this app (e.g. the Billion-badge threshold). A range that reaches into
// nine figures at all (>= €100M high) reads as exceptional even if its low
// end doesn't — there's no separate "low bound" or "midpoint" tier in the
// design doc to fall back on, so this is the literal, defensible reading of
// "Exceptional Work (€100M+)". Concretely: Van Gogh's Starry Night Over the
// Rhone (€95-130M) lands on Exceptional under this rule, not Major, because
// its high bound clears 100. Null estimate = no tier at all (Pending review
// state, no reveal drama to have a tier for).
export type PriceTier = "standard" | "major" | "exceptional";

export function getPriceTier(high: number | null): PriceTier | null {
  if (high == null) return null;
  if (high >= 100) return "exceptional";
  if (high >= 10) return "major";
  return "standard";
}

// v3 §4's exact gradient recipe operates on the artwork's own existing
// `accent` hex (already in the catalog, one per work) — no new color-
// extraction system, just a hex->rgba conversion so it can sit inside a
// CSS linear-gradient() at a specific opacity.
export function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const bigint = Number.parseInt(clean, 16);
  if (Number.isNaN(bigint)) return `rgba(17, 17, 17, ${alpha})`;
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// v3 §15 lists "reduced-motion" as a required state. No prior art for this
// in the codebase (grepped — nothing uses prefers-reduced-motion yet), so
// this is a new, minimal hook: true means skip the staged reveal and render
// the end state immediately, same principle as any other progressive-
// enhancement check already in this app (haptics, camera permission).
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);
  return reduced;
}
