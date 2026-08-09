"use client";

import { ArrowLeft } from "lucide-react";
import { tt } from "@/lib/i18n";
import type { AppState } from "@/lib/app-state";

// Phase 2 §2 -- Tier 2 minimal card. Stage 1 open recognition named a real
// artist/title, but it isn't in the reviewed catalog (no estimate, no
// why/where/rarity, no Kids/Simple text, no audio -- none of that exists
// for a work nobody has reviewed yet). This is a deliberately honest dead
// end, not a stripped-down CardScreen: no photo (we don't have one), no
// SegmentControl (Kids mode requires editorial review to exist at all, so
// there's nothing to switch to), no ProvenanceReveal/ListenButton/Add-to-
// visit (none of those have real data here either). Never reuses
// CardScreen's markup with fields blanked out -- that would risk a half-
// empty card reading as a bug rather than an honest boundary.
export default function UncatalogedCardScreen({
  state,
  onBack,
  onGoProgress,
}: {
  state: AppState;
  onBack: () => void;
  onGoProgress: () => void;
}) {
  const sighting = state.uncatalogedSighting;
  if (!sighting) return null;

  const artist = sighting.artist || tt("uncataloged_unknown_artist", state.locale);
  const title = sighting.title || tt("uncataloged_unknown_title", state.locale);

  return (
    <div className="w-full h-full bg-[#F7F3EC] flex flex-col overflow-y-auto scrollbar-none">
      <div className="shrink-0 relative aspect-[4/3] w-full overflow-hidden bg-[#EDE8E1]">
        <div className="absolute inset-0 bg-[linear-gradient(105deg,#E7E1D6_0%,#DAD3C6_50%,#CFC7B8_100%)]" />
        <button
          type="button"
          onClick={onBack}
          aria-label="Back"
          className="absolute top-4 left-4 w-9 h-9 rounded-full bg-black/40 backdrop-blur flex items-center justify-center"
        >
          <ArrowLeft className="w-4 h-4 text-white" />
        </button>
        <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 w-10 h-1 rounded-full bg-black/15" />
      </div>

      <div
        className="rounded-t-[30px] -mt-4 relative z-10 flex-1 px-5 pt-7 pb-[32px]"
        style={{
          backgroundColor: "#FBF8F2",
          boxShadow: "0 -16px 45px rgba(22,19,15,0.09), inset 0 1px 0 rgba(255,255,255,0.80)",
        }}
      >
        <div className="text-[11px] font-semibold tracking-[0.16em] uppercase text-[#696763]">
          {artist.toUpperCase()}
        </div>
        <h1
          className="mt-1 font-medium leading-[0.98] tracking-[-0.025em] text-[#181714]"
          style={{ fontFamily: "var(--font-editorial)", fontSize: "clamp(28px, 7.3vw, 34px)" }}
        >
          {title}
        </h1>

        <div
          className="mt-5 rounded-[16px] px-4 py-3.5"
          style={{ background: "rgba(24,23,20,0.045)", border: "1px solid rgba(24,23,20,0.06)" }}
        >
          <p className="text-[13px] leading-[19px] text-[#5E584F]">{tt("uncataloged_note", state.locale)}</p>
        </div>

        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={onBack}
            className="w-full h-[54px] rounded-[14px] text-[16px] font-medium tracking-[-0.01em] bg-[#181714] text-[#FAF7F0] shadow-[0_7px_18px_rgba(20,18,15,0.12)] active:scale-[0.98] transition-transform"
          >
            {tt("scan_next_artwork", state.locale)}
          </button>
          <button
            type="button"
            onClick={onGoProgress}
            className="w-full text-center text-[13px] font-semibold text-[#67635C] pt-1"
          >
            {tt("view_visit_progress", state.locale)}
          </button>
        </div>
      </div>
    </div>
  );
}
