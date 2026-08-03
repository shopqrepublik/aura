"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import BottomSheet from "./BottomSheet";
import { tt } from "@/lib/i18n";
import type { Locale } from "@/lib/types";

// "Price Badge: black pill €80–120M EST. as StockX tag, tap (i) opens
// bottom-sheet disclaimer" — full disclaimer text is the §11 mandatory
// wording, ported verbatim from the old artwork card (see lib/i18n.ts
// estimate_disclaimer). Estimates are null for almost every work in the
// catalog until an editor reviews them (§8.4) — never invent a number here.
export default function PriceBadge({ low, high, locale }: { low: number | null; high: number | null; locale: Locale }) {
  const [open, setOpen] = useState(false);
  const hasEstimate = low != null && high != null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="h-7 px-3 rounded-full bg-black text-white flex items-center gap-1.5 text-[12px] font-semibold"
      >
        <span>{hasEstimate ? `€${low}–${high}M EST.` : "Pending review"}</span>
        <Info className="w-3 h-3 opacity-60" />
      </button>

      <BottomSheet open={open} onClose={() => setOpen(false)}>
        <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#8E8E93] mb-2">
          {tt("indicative_estimate", locale)}
        </div>
        <p className="text-[15px] leading-[22px] text-[#1D1D1F]">{tt("estimate_disclaimer", locale)}</p>
      </BottomSheet>
    </>
  );
}
