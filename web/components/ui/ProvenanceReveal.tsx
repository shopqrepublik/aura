"use client";

import { useEffect, useState } from "react";
import { haptics } from "@/lib/haptics";
import { hexToRgba, getPriceTier, usePrefersReducedMotion } from "@/lib/cardReveal";
import { GRAIN_BACKGROUND_IMAGE } from "@/lib/visitPalette";
import { resolveScaleComparisonSentence, resolveKidsScaleComparison } from "@/lib/scaleComparison";
import { tt } from "@/lib/i18n";
import MarketMethodologySheet from "./MarketMethodologySheet";
import type { Locale, Mode } from "@/lib/types";

// Visual-match rebuild: sizes now sit in the editorial-serif clamp range
// the brief specifies (48-62px) instead of the earlier sans-serif 42-52px
// scale -- same three-tier hierarchy design-direction-v3.md §6 asks for,
// just re-expressed in the new type system.
const PRICE_SIZE_PX: Record<"standard" | "major" | "exceptional", number> = {
  standard: 48,
  major: 55,
  exceptional: 62,
};

const TINT_OPACITY: Record<"standard" | "major" | "exceptional", number> = {
  standard: 0.05,
  major: 0.07,
  exceptional: 0.09,
};

// Motion timings, visual-match brief §19 "Price reveal" (Variant 2) --
// same five-stage choreography design-direction-v3.md §5 already specified
// (pause -> card enters -> price shows its low bound -> resolves to the
// full range -> evidence fades in), just pinned to these exact ms values.
// Read as a sequential chain: each stage's number is the delay AFTER the
// previous stage fires, not an absolute timestamp -- this keeps the total
// (~1120ms for a Standard/Major reveal) inside the original spec's stated
// ~900-1100ms budget for the whole sequence, and matches how this
// component's timers were already structured before this pass (only the
// exact numbers changed, not the chain shape).
const PAUSE_MS = 140;
const CARD_ENTER_MS = 520; // also the CSS transition duration below
const PRICE_LOW_MS = 180;
const FULL_RANGE_MS = 160;
const EVIDENCE_MS = 120;
// design-direction-v3.md §6: Exceptional tier gets a longer pause before
// revealing -- kept as an addition to the pause stage specifically (not
// applied to any other stage), same rule Phase 1 already implemented.
const EXCEPTIONAL_PAUSE_BONUS_MS = 200;

export default function ProvenanceReveal({
  low,
  high,
  accent,
  comparableSalesCount,
  inventoryNumber,
  locale,
  mode,
}: {
  low: number | null;
  high: number | null;
  accent: string;
  comparableSalesCount?: number;
  inventoryNumber: string;
  locale: Locale;
  mode: Mode;
}) {
  const hasEstimate = low != null && high != null;
  const tier = getPriceTier(high);
  const reducedMotion = usePrefersReducedMotion();
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  const [containerVisible, setContainerVisible] = useState(reducedMotion);
  const [priceStage, setPriceStage] = useState<"low" | "full">(reducedMotion ? "full" : "low");
  const [evidenceVisible, setEvidenceVisible] = useState(reducedMotion);

  useEffect(() => {
    if (reducedMotion) return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    const entranceDelay = PAUSE_MS + (tier === "exceptional" ? EXCEPTIONAL_PAUSE_BONUS_MS : 0);
    timers.push(setTimeout(() => setContainerVisible(true), entranceDelay));

    if (hasEstimate) {
      // Price shows its low bound the moment the card is visible (no
      // count-up -- it just jumps straight to `€{low}M`), holds there for
      // PRICE_LOW_MS, then resolves to the full range FULL_RANGE_MS later.
      // The single medium haptic fires exactly here, at full-range-resolve,
      // and only for Major/Exceptional (Standard stays silent -- design-
      // direction-v3.md §6, unchanged by this motion pass).
      const fullPriceAt = entranceDelay + PRICE_LOW_MS + FULL_RANGE_MS;
      timers.push(
        setTimeout(() => {
          setPriceStage("full");
          if (tier === "major" || tier === "exceptional") haptics.impactMedium();
        }, fullPriceAt)
      );
      timers.push(setTimeout(() => setEvidenceVisible(true), fullPriceAt + EVIDENCE_MS));
    } else {
      timers.push(setTimeout(() => setEvidenceVisible(true), entranceDelay + PRICE_LOW_MS));
    }

    return () => timers.forEach(clearTimeout);
  }, [reducedMotion, tier, hasEstimate]);

  const kidsBump = mode === "kids" ? 0.02 : 0;
  const tintOpacity = (tier ? TINT_OPACITY[tier] : TINT_OPACITY.standard) + kidsBump;

  const analogy = !hasEstimate
    ? null
    : mode === "kids"
      ? resolveKidsScaleComparison(low, high, locale)
      : resolveScaleComparisonSentence(low, high, locale, mode === "simple" ? "simple" : "normal");

  const priceSize = tier ? PRICE_SIZE_PX[tier] : PRICE_SIZE_PX.standard;
  const priceText = hasEstimate
    ? priceStage === "low"
      ? `€${low}M`
      : `€${low}–${high}M`
    : tt("pending_review", locale);

  return (
    <div
      className="mt-6 rounded-[22px] transition-all"
      style={{
        // Auction Paper: warm base + accent tint blended in via the same
        // hexToRgba layering technique lib/visitPalette.ts already
        // established (kept consistent rather than introducing color-mix()
        // as a second blending method in the same codebase).
        backgroundColor: "#EDE6DA",
        backgroundImage: `linear-gradient(145deg, ${hexToRgba(accent, tintOpacity)}, #F1EBE1 47%, ${hexToRgba(accent, tintOpacity * 0.6)})`,
        border: "1px solid rgba(45, 39, 31, 0.12)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.55), 0 14px 35px rgba(37,31,24,0.075)",
        padding: "24px 22px 22px",
        opacity: containerVisible ? 1 : 0,
        transform: containerVisible ? "translateY(0) scale(1)" : "translateY(10px) scale(0.985)",
        transitionDuration: `${CARD_ENTER_MS}ms`,
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      {/* Same self-contained SVG-noise grain visitPalette.ts already built
          for the Recap background, reused here at a much subtler opacity
          for the paper's own texture -- one grain technique, not two. */}
      <div
        className="relative"
        style={{
          backgroundImage: GRAIN_BACKGROUND_IMAGE,
          backgroundSize: "180px 180px",
          margin: "-24px -22px -22px",
          padding: "24px 22px 22px",
          borderRadius: 22,
          opacity: 1,
        }}
      >
      <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#65625d]">
        {tt("market_context_label", locale)}
      </div>

      {hasEstimate && !!comparableSalesCount && comparableSalesCount > 0 && (
        <div className="mt-1 text-[11px] leading-[15px] tabular-nums text-[#77736d]">
          {tt(comparableSalesCount === 1 ? "comparable_sales_count_one" : "comparable_sales_count_other", locale).replace(
            "{n}",
            String(comparableSalesCount)
          )}
        </div>
      )}

      {/* Serif, tabular-nums price. Phase 1 found tabular-nums produced a
          visible mid-digit gap combined with tight tracking on this app's
          SANS system-font-fallback stack (no SF Pro Display on Windows).
          That root cause doesn't apply here: Cormorant Garamond is an
          embedded webfont via next/font, not a fallback-dependent system
          font, so the brief's tabular-nums requirement is restored --
          verified visually before shipping, see the Step 1 screenshot. */}
      <div
        className="mt-6 font-medium leading-[0.88] text-[#161512]"
        style={
          hasEstimate
            ? {
                fontFamily: "var(--font-editorial)",
                fontSize: `clamp(${priceSize - 6}px, 13vw, ${priceSize}px)`,
                letterSpacing: "-0.055em",
                fontVariantNumeric: "lining-nums tabular-nums",
              }
            : { fontFamily: "var(--font-sans)", fontSize: 22, letterSpacing: "-0.01em" }
        }
      >
        {priceText}
      </div>
      {hasEstimate && <p className="mt-2.5 text-[12px] leading-[16px] text-[#68655f]">{tt("estimated_market_range", locale)}</p>}
      {!hasEstimate && <p className="mt-2.5 text-[12px] leading-[16px] text-[#68655f]">{tt("reveal_pending_review_note", locale)}</p>}

      {tier === "exceptional" && (
        <div className="mt-4 py-2 border-t border-b border-[rgba(45,39,31,0.14)] flex items-center justify-between">
          <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#6B211D]">
            {tt("exceptional_market_tier", locale)}
          </span>
          <span className="text-[11px] tabular-nums text-[#8B867E]">{inventoryNumber}</span>
        </div>
      )}

      <div className="transition-opacity duration-300 ease-out" style={{ opacity: evidenceVisible ? 1 : 0 }}>
        {analogy && (
          <>
            <div className="mt-5 h-px bg-[rgba(45,39,31,0.14)]" />
            <p className="mt-5 text-[14px] font-medium text-[#24231f] leading-[20px]">{analogy}</p>
          </>
        )}

        <p className="mt-[18px] text-[11px] leading-[16px] text-[#66635e]">
          {tt("estimate_disclaimer", locale)}{" "}
          <button
            type="button"
            onClick={() => setMethodologyOpen(true)}
            className="underline underline-offset-2 text-[#181714] font-medium"
          >
            {tt("view_methodology", locale)} →
          </button>
        </p>
      </div>
      </div>

      <MarketMethodologySheet
        open={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
        locale={locale}
        salesCount={hasEstimate ? comparableSalesCount : undefined}
      />
    </div>
  );
}
