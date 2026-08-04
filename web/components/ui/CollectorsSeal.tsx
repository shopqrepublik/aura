"use client";

import { useEffect, useState } from "react";
import { haptics } from "@/lib/haptics";
import { tt } from "@/lib/i18n";
import { usePrefersReducedMotion } from "@/lib/cardReveal";
import type { Locale } from "@/lib/types";

function formatSealDate(ts: number | null): string {
  if (ts == null) return "";
  const d = new Date(ts);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yy = String(d.getFullYear()).slice(-2);
  return `${dd}·${mm}·${yy}`;
}

// design-direction-v3.md §11 "Billion Euro Visitor: Collector's Seal" --
// replaces the old flat red pill badge. Circular stamp, double thin
// hairline, graphite fill (the doc's "основной вариант" / primary variant;
// the burgundy variant it also mentions has no stated trigger distinct from
// graphite, so this implements the one the spec actually gives selection
// criteria for, rather than inventing a rule for a second variant).
//
// The seal's own text ("ELYIO · CULTURAL MILESTONE · PARIS", "€1B+
// VISITOR") is fixed, not run through tt() -- the doc gives no localized
// variants, and it reads as a physical museum stamp (like the "ELYIO"
// brand mark and "elyio.co / v1.0" footer elsewhere on this screen), not
// interface copy. The accessible name IS localized via the existing
// billion_euro_visitor string, so screen readers still get the real
// language for the milestone.
//
// Fires its single medium haptic once, on mount -- RecapScreen only renders
// this component at all when isBillion is true, and only mounts once per
// visit, so "once per mount" already satisfies the doc's "без пульса после
// появления" (no repeat pulse after the initial stamp).
export default function CollectorsSeal({ timestamp, locale }: { timestamp: number | null; locale: Locale }) {
  const reducedMotion = usePrefersReducedMotion();
  const [stamped, setStamped] = useState(reducedMotion);

  useEffect(() => {
    if (reducedMotion) {
      haptics.impactMedium();
      return;
    }
    const t = setTimeout(() => {
      setStamped(true);
      haptics.impactMedium();
    }, 30);
    return () => clearTimeout(t);
  }, [reducedMotion]);

  const size = 88;
  const pathId = "collectors-seal-ring";
  const dateStr = formatSealDate(timestamp);

  return (
    <div
      role="img"
      aria-label={tt("billion_euro_visitor", locale)}
      className="shrink-0"
      style={{
        width: size,
        height: size,
        opacity: stamped ? 1 : 0,
        transform: stamped ? "scale(1) rotate(0deg)" : "scale(1.08) rotate(-2deg)",
        transitionProperty: "opacity, transform",
        transitionDuration: "420ms",
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      <svg width={size} height={size} viewBox="0 0 88 88">
        <defs>
          {/* Top-half arc only (left rim -> top -> right rim), not a full
              circle: a full-circle path with startOffset 50% centers text
              on the OPPOSITE side of the path's start, which for a path
              starting at 9 o'clock sweeping clockwise lands the center at
              3 o'clock and wraps the string over both the top and bottom --
              wrong for a stamp. A semicircle keeps the text cleanly arced
              across the top, which is the actual coin/stamp convention. */}
          <path id={pathId} d="M 14,44 A 30,30 0 0,1 74,44" />
        </defs>

        {/* Base fill + double thin hairline ring, approximating the doc's
            "blind emboss/deboss" as a soft two-tone edge rather than a
            bright fill -- no red per §12 (graphite is not a milestone-red
            context, burgundy is reserved and unused here). */}
        <circle cx="44" cy="44" r="42" fill="#1B1B1D" />
        <circle cx="44" cy="44" r="42" fill="none" stroke="rgba(0,0,0,0.35)" strokeWidth="1" />
        <circle cx="44" cy="44" r="37.5" fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="1" />
        <circle cx="44" cy="44" r="34" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />

        <text fill="rgba(255,255,255,0.8)" fontSize="5.4" fontWeight="600" letterSpacing="1.4">
          <textPath href={`#${pathId}`} startOffset="50%" textAnchor="middle">
            ELYIO · CULTURAL MILESTONE · PARIS
          </textPath>
        </text>

        <text x="44" y="41" textAnchor="middle" fill="#FFFFFF" fontSize="10.5" fontWeight="700" letterSpacing="-0.02em">
          €1B+
        </text>
        <text x="44" y="52" textAnchor="middle" fill="rgba(255,255,255,0.78)" fontSize="6" fontWeight="600" letterSpacing="0.08em">
          VISITOR
        </text>
        {dateStr && (
          <text x="44" y="65" textAnchor="middle" fill="rgba(255,255,255,0.42)" fontSize="5" fontWeight="500" letterSpacing="0.03em">
            {dateStr}
          </text>
        )}
      </svg>
    </div>
  );
}
