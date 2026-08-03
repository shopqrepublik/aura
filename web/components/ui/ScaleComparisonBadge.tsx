import { resolveScaleComparison } from "@/lib/scaleComparison";
import type { Locale } from "@/lib/types";

// "Second h7 px3 rounded-full bg #F5F5F7 13px medium '≈ 1 Boeing 787'" per
// the design spec — but the text is now real, computed from the artwork's
// own estimate midpoint (see lib/scaleComparison.ts), not a hardcoded
// example. Renders nothing at all when there's no estimate — no estimate,
// no comparison, same rule PriceBadge already follows for the number itself.
export default function ScaleComparisonBadge({ low, high, locale }: { low: number | null; high: number | null; locale: Locale }) {
  const text = resolveScaleComparison(low, high, locale);
  if (!text) return null;

  return (
    <span className="h-7 px-3 rounded-full bg-[#F5F5F7] text-[13px] font-medium text-[#1D1D1F] flex items-center">
      {text}
    </span>
  );
}
