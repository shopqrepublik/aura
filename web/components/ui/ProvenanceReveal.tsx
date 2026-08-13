"use client";

import { useEffect, useState } from "react";
import { haptics } from "@/lib/haptics";
import { hexToRgba, getPriceTier, usePrefersReducedMotion } from "@/lib/cardReveal";
import { GRAIN_BACKGROUND_IMAGE } from "@/lib/visitPalette";
import { resolveValueRevealScaleComparison } from "@/lib/scaleComparison";
import { formatValueRevealHeadline } from "@/lib/valueReveal";
import { tt } from "@/lib/i18n";
import MarketMethodologySheet from "./MarketMethodologySheet";
import type { Locale, Mode, ValueReveal } from "@/lib/types";

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
  valueReveal,
  accent,
  comparableSalesCount,
  inventoryNumber,
  locale,
  mode,
}: {
  valueReveal: ValueReveal | null;
  accent: string;
  comparableSalesCount?: number;
  inventoryNumber: string;
  locale: Locale;
  mode: Mode;
}) {
  const hasEstimate = valueReveal?.mode === "ESTIMATED_VALUE" && valueReveal.aggregateValueEligible;
  const estimate = hasEstimate ? valueReveal.estimatedValue : null;
  const tier = getPriceTier(estimate?.high ?? null);
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

  const analogy = resolveValueRevealScaleComparison(valueReveal, locale, mode);

  const priceSize = tier ? PRICE_SIZE_PX[tier] : PRICE_SIZE_PX.standard;
  const priceText = estimate
    ? priceStage === "low"
      ? `€${estimate.low}M`
      : formatValueRevealHeadline(valueReveal, locale)
    : formatValueRevealHeadline(valueReveal, locale);
  const revealLabel = valueReveal?.mode === "ESTIMATED_VALUE"
    ? tt("estimated_value_label", locale)
    : valueReveal?.mode === "MARKET_CONTEXT"
      ? tt("market_context_label", locale)
      : valueReveal?.mode === "BEYOND_MARKET"
        ? tt("beyond_market_label", locale)
        : tt("market_context_label", locale);
  const supportingText = valueReveal?.mode === "ESTIMATED_VALUE"
    ? tt("estimated_market_range", locale)
    : valueReveal?.mode === "MARKET_CONTEXT"
      ? valueReveal.marketContext.explanation
      : valueReveal?.mode === "BEYOND_MARKET"
        ? valueReveal.beyondMarket.explanation
        : tt("reveal_pending_review_note", locale);
  const disclaimerText = valueReveal?.mode === "ESTIMATED_VALUE"
    ? valueReveal.estimatedValue.disclaimer || tt("estimate_disclaimer", locale)
    : valueReveal?.mode === "MARKET_CONTEXT"
      ? valueReveal.marketContext.disclaimer || tt("market_context_disclaimer", locale)
      : valueReveal?.mode === "BEYOND_MARKET"
        ? valueReveal.beyondMarket.disclaimer || tt("beyond_market_disclaimer", locale)
        : tt("reveal_pending_review_note", locale);
  const methodBody = valueReveal?.mode === "MARKET_CONTEXT"
    ? valueReveal.marketContext.relationshipToArtwork
    : valueReveal?.mode === "BEYOND_MARKET"
      ? valueReveal.beyondMarket.institutionalLegalContext
      : undefined;
  const optionalContext = valueReveal?.mode === "BEYOND_MARKET" ? cleanVisitorText(valueReveal.beyondMarket.optionalContext) : null;
  const cleanedSupportingText = cleanVisitorText(supportingText);
  const cleanedDisclaimerText = cleanVisitorText(disclaimerText);

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
        {revealLabel}
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
            : valueReveal?.mode === "MARKET_CONTEXT"
              ? {
                  fontFamily: "var(--font-editorial)",
                  fontSize: "clamp(42px, 12vw, 62px)",
                  letterSpacing: "-0.035em",
                  fontVariantNumeric: "lining-nums tabular-nums",
                }
              : { fontFamily: "var(--font-sans)", fontSize: 22, letterSpacing: "-0.01em" }
        }
      >
        {priceText}
      </div>
      <p className="mt-2.5 text-[12px] leading-[16px] text-[#68655f]">{cleanedSupportingText}</p>
      {valueReveal?.mode === "MARKET_CONTEXT" && (
        <p className="mt-2 text-[11px] leading-[15px] font-semibold uppercase tracking-[0.08em] text-[#6B211D]">
          {tt("not_artwork_value_label", locale)}
        </p>
      )}
      {analogy && (
        <div className="mt-4 rounded-[16px] bg-white/40 px-3.5 py-3 border border-[rgba(45,39,31,0.08)]">
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#65625d]">
            {locale === "fr" ? "Pour situer" : locale === "zh-Hans" ? "作为参照" : "For scale"}
          </div>
          <p className="mt-1.5 text-[16px] leading-[21px] font-semibold text-[#24231f]">{analogy.shortSentence}</p>
        </div>
      )}
      {optionalContext && (
        <div className="mt-4 rounded-[14px] bg-white/35 px-3 py-2.5 border border-[rgba(45,39,31,0.08)]">
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#65625d]">
            {locale === "fr" ? "Pour situer" : locale === "zh-Hans" ? "作为参照" : "For scale"}
          </div>
          <p className="mt-1 text-[12px] leading-[16px] text-[#3A3731]">{optionalContext}</p>
        </div>
      )}

      {tier === "exceptional" && (
        <div className="mt-4 py-2 border-t border-b border-[rgba(45,39,31,0.14)] flex items-center justify-between">
          <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#6B211D]">
            {tt("exceptional_market_tier", locale)}
          </span>
          <span className="text-[11px] tabular-nums text-[#8B867E]">{inventoryNumber}</span>
        </div>
      )}

      <div className="transition-opacity duration-300 ease-out" style={{ opacity: evidenceVisible ? 1 : 0 }}>
        <p className="mt-[18px] text-[11px] leading-[16px] text-[#66635e]">
          {cleanedDisclaimerText}{" "}
          <button
            type="button"
            onClick={() => setMethodologyOpen(true)}
            className="underline underline-offset-2 text-[#181714] font-medium"
          >
            {tt(hasEstimate ? "view_methodology" : "view_value_context", locale)} →
          </button>
        </p>
      </div>
      </div>

      <MarketMethodologySheet
        open={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
        locale={locale}
        salesCount={hasEstimate ? comparableSalesCount : undefined}
        body={methodBody}
      />
    </div>
  );
}

function cleanVisitorText(value: string | null | undefined): string {
  if (!value) return "";
  if (/[{}[\]"]|source_ids|catalog_version|review_status/.test(value)) {
    try {
      const parsed = JSON.parse(value) as Record<string, unknown>;
      return [parsed.label, parsed.explanation].filter((x): x is string => typeof x === "string").join(". ");
    } catch {
      return value
        .replace(/"source_ids"\s*:\s*\[[^\]]*\],?/g, "")
        .replace(/[{}[\]"]/g, "")
        .replace(/\b(number|currency|label|explanation)\s*:/g, "")
        .trim();
    }
  }
  return value;
}
