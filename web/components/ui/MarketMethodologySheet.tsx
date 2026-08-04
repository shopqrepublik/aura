import BottomSheet from "./BottomSheet";
import { tt } from "@/lib/i18n";
import type { Locale } from "@/lib/types";

// design-direction-v3.md §3/§15: "View methodology" is an ADDITION to the
// always-visible disclaimer inside ProvenanceReveal, never a replacement --
// this sheet never repeats the disclaimer's mandatory §11 text verbatim
// (it's already permanently visible on the card), it only adds general
// process explanation plus a real comparable-sales count. It deliberately
// never shows `estimate.comparableSales` or `estimate.logic` text verbatim
// -- both are internal editorial-review metadata per lib/types.ts's own
// comment on the Estimate interface, not user-facing copy. `salesCount` is
// the one real, safe-to-show number derived from that data.
export default function MarketMethodologySheet({
  open,
  onClose,
  locale,
  salesCount,
}: {
  open: boolean;
  onClose: () => void;
  locale: Locale;
  salesCount?: number;
}) {
  return (
    <BottomSheet open={open} onClose={onClose}>
      <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#8A8A90] mb-2">
        {tt("methodology_sheet_title", locale)}
      </div>
      {!!salesCount && salesCount > 0 && (
        <p className="text-[13px] tabular-nums text-[#626267] mb-3">
          {tt(salesCount === 1 ? "comparable_sales_count_one" : "comparable_sales_count_other", locale).replace(
            "{n}",
            String(salesCount)
          )}
        </p>
      )}
      <p className="text-[15px] leading-[22px] text-[#1D1D1F]">{tt("methodology_sheet_body", locale)}</p>
    </BottomSheet>
  );
}
