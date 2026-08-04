"use client";

import { useEffect, useState } from "react";
import { haptics } from "@/lib/haptics";
import { hexToRgba, getPriceTier, usePrefersReducedMotion } from "@/lib/cardReveal";
import { resolveScaleComparisonSentence, resolveKidsScaleComparison } from "@/lib/scaleComparison";
import { tt } from "@/lib/i18n";
import MarketMethodologySheet from "./MarketMethodologySheet";
import type { Locale, Mode } from "@/lib/types";

const PRICE_SIZE_PX: Record<"standard" | "major" | "exceptional", number> = {
  standard: 42,
  major: 48,
  exceptional: 52,
};

const TINT_OPACITY: Record<"standard" | "major" | "exceptional", number> = {
  standard: 0.05,
  major: 0.07,
  exceptional: 0.09,
};

// design-direction-v3.md §3-6: replaces the old PriceBadge pill + separate
// ScaleComparisonBadge pill with a single "Auction Paper" document. Two
// invariants that must never regress, called out explicitly in this
// project's rollout plan for this redesign:
//  1. The §11 disclaimer text is ALWAYS rendered here, in full, never
//     hidden behind "View methodology" -- that link is a genuine addition
//     (more process detail + a real comp-sale count), not a replacement.
//  2. No estimate (low/high both null) never fabricates a tier, a price, or
//     an animation to reveal -- it renders a plain, honest "Pending review"
//     variant instead, same rule PriceBadge always followed.
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
    // reducedMotion=true is already handled by each piece of state's
    // initial value (useState(reducedMotion) etc. above) -- nothing to
    // synchronously set here in that case.
    if (reducedMotion) return;

    const timers: ReturnType<typeof setTimeout>[] = [];

    // Frame 3 "Pause" then Frame 4 "Provenance Reveal enters" (design-
    // direction-v3.md §5): the pause already covers frames 1-3 elapsing in
    // ArtworkIdentity, so this component's own mount-relative delay is the
    // full ~520ms. Exceptional tier gets an extra, deliberately longer
    // pause per §6 ("увеличенная пауза перед раскрытием").
    const entranceDelay = 520 + (tier === "exceptional" ? 200 : 0);
    timers.push(setTimeout(() => setContainerVisible(true), entranceDelay));

    if (hasEstimate) {
      // Frame 5 "Price resolves": low bound shown first, then morphs to the
      // full range ~160ms later, with the single medium haptic firing at
      // that exact moment for Major/Exceptional tiers only (§6 -- Standard
      // gets no haptic at all).
      const fullPriceAt = entranceDelay + 200 + 160;
      timers.push(
        setTimeout(() => {
          setPriceStage("full");
          if (tier === "major" || tier === "exceptional") haptics.impactMedium();
        }, fullPriceAt)
      );
      // Frame 6 "Evidence appears" -- comps, disclaimer, analogy, methodology.
      timers.push(setTimeout(() => setEvidenceVisible(true), fullPriceAt + 120));
    } else {
      // No number to resolve -- just let the pending-review card settle in.
      timers.push(setTimeout(() => setEvidenceVisible(true), entranceDelay + 160));
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
      className="mt-6 rounded-[18px] p-4 transition-all"
      style={{
        backgroundColor: "#F4F1EB",
        backgroundImage: `linear-gradient(135deg, ${hexToRgba(accent, tintOpacity)}, rgba(244,241,235,0.96) 48%)`,
        border: "1px solid rgba(17,17,17,0.08)",
        boxShadow: "0 12px 30px rgba(0,0,0,0.055)",
        opacity: containerVisible ? 1 : 0,
        transform: containerVisible ? "translateY(0) scale(1)" : "translateY(10px) scale(0.985)",
        transitionDuration: "520ms",
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      <div className="text-[10px] font-semibold tracking-[0.12em] uppercase text-[#8A8A90]">
        {tt("market_context_label", locale)}
      </div>

      {hasEstimate && !!comparableSalesCount && comparableSalesCount > 0 && (
        <div className="mt-1 text-[11px] tabular-nums text-[#626267]">
          {tt(comparableSalesCount === 1 ? "comparable_sales_count_one" : "comparable_sales_count_other", locale).replace(
            "{n}",
            String(comparableSalesCount)
          )}
        </div>
      )}

      <div
        className="mt-3 font-semibold text-[#111111] leading-[1.15]"
        // whiteSpace: nowrap prevents the browser from treating "€95–130M"
        // as breakable at any character (it has no spaces, so without this
        // it can wrap at an arbitrary point).
        //
        // Deliberately NOT using font-variant-numeric: tabular-nums here,
        // even though design-direction-v3.md §3/§13 specifies it: tested
        // live, tabular-nums combined with this size's -0.045em tracking
        // renders a visible gap mid-number on this font stack's fallback
        // (observed as "€95–1 30M" -- confirmed by toggling tabular-nums
        // off, which fixed it outright; the DOM text itself was always the
        // correct, unbroken string "€95–130M", so this was a pure
        // rendering artifact, not a data or logic bug). Since ELYIO is a
        // PWA, not iOS-exclusive, this fallback rendering matters for real
        // users, not just this test environment -- a readable price beats
        // spec-perfect column alignment nobody is comparing against
        // another row here anyway (it's one number, not a table).
        //
        // "Pending review" is plain text, not a number -- rendering it at
        // the same 40-52px tier-scale price size (observed live: it
        // visually overlapped the line below it, and thematically there's
        // no number to convey scale/drama for, so it doesn't deserve that
        // treatment) -- it gets a calm, fixed, much smaller size instead,
        // with normal (not -0.045em) letter-spacing, which is far too tight
        // for real words at any size.
        style={
          hasEstimate
            ? { fontSize: priceSize, letterSpacing: "-0.045em", whiteSpace: "nowrap" }
            : { fontSize: 22, letterSpacing: "-0.01em" }
        }
      >
        {priceText}
      </div>
      {hasEstimate && (
        <p className="mt-1 text-[13px] text-[#626267]">{tt("estimated_market_range", locale)}</p>
      )}
      {!hasEstimate && (
        <p className="mt-1 text-[13px] text-[#626267]">{tt("reveal_pending_review_note", locale)}</p>
      )}

      {tier === "exceptional" && (
        <div className="mt-3 py-2 border-t border-b border-[rgba(17,17,17,0.09)] flex items-center justify-between">
          <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#6F1D1B]">
            {tt("exceptional_market_tier", locale)}
          </span>
          <span className="text-[11px] tabular-nums text-[#8A8A90]">{inventoryNumber}</span>
        </div>
      )}

      <div
        className="transition-opacity duration-300 ease-out"
        style={{ opacity: evidenceVisible ? 1 : 0 }}
      >
        {analogy && (
          <>
            <div className="mt-3 h-px bg-[rgba(17,17,17,0.09)]" />
            <p className="mt-3 text-[15px] font-medium text-[#1D1D1F] leading-[21px]">{analogy}</p>
          </>
        )}

        {/* Invariant: this text is ALWAYS visible here, never hidden behind
            "View methodology" -- that link only adds more detail. */}
        <p className="mt-3 text-[11.5px] leading-[16px] text-[#626267]">
          {tt("estimate_disclaimer", locale)}{" "}
          <button
            type="button"
            onClick={() => setMethodologyOpen(true)}
            className="underline underline-offset-2 text-[#111111] font-medium"
          >
            {tt("view_methodology", locale)} →
          </button>
        </p>
      </div>

      <MarketMethodologySheet
        open={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
        locale={locale}
        // Only ever pass this through when there's an actual estimate to
        // back it. Some null-estimate works (eg Monet's Women in the
        // Garden) still carry a `comparableSales` array -- but there it
        // documents candidate comps the editor considered and REJECTED as
        // not transferable, not evidence supporting a number. Showing a
        // count in that case would falsely imply a supported range exists.
        salesCount={hasEstimate ? comparableSalesCount : undefined}
      />
    </div>
  );
}
