"use client";

import ProgressRing from "@/components/ui/ProgressRing";
import { MISSIONS, missionLabel } from "@/lib/artworks";
import { tt, LOCALES } from "@/lib/i18n";
import type { AppState } from "@/lib/app-state";

// "01 MUSEUM HOME" — exact bg/pill/button/mission-card classNames mined from
// ELYIO-iPhone-WoW-Design-System.html. Missions reuse the REAL localized
// mission set ported from the old app (data.js) rather than the mockup's
// placeholder examples ("See 3 Monet" etc.) — those were illustrative, not a
// content requirement, and inventing new mission copy would violate "don't
// invent beyond spec" as much as ignoring real content would.
export default function HomeScreen({
  state,
  onStartVisit,
  onSetLocale,
}: {
  state: AppState;
  onStartVisit: () => void;
  onSetLocale: (locale: AppState["locale"]) => void;
}) {
  return (
    <div className="relative w-full h-full bg-[#F5F5F7] overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_0%,#E8E0D6_0%,#D6DDE8_40%,#C9CED6_100%)]" />
        <div className="absolute inset-0 bg-white/30 backdrop-blur-[2px]" />
      </div>

      <div className="relative z-10 pt-[56px] flex items-center justify-center gap-2">
        <div className="h-[28px] px-3 rounded-full bg-black/80 backdrop-blur-xl flex items-center gap-2 shadow-[0_4px_12px_rgba(0,0,0,0.15)]">
          <div className="w-2 h-2 rounded-full bg-[#30D158] shadow-[0_0_8px_#30D158]" />
          <span className="text-[12px] font-[600] text-white tracking-[-0.01em]">
            {tt("museum_detected", state.locale)}
          </span>
        </div>
        <select
          aria-label="Language"
          value={state.locale}
          onChange={(e) => onSetLocale(e.target.value as AppState["locale"])}
          className="h-[28px] px-2 rounded-full bg-white/70 backdrop-blur-xl text-[11px] font-semibold text-black/70 border border-black/[0.06]"
        >
          {LOCALES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.code === "zh-Hans" ? "中文" : l.code.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      <div className="relative z-10 flex flex-col items-center mt-[148px]">
        <button
          type="button"
          onClick={onStartVisit}
          className="w-[164px] h-[164px] rounded-full bg-black text-white flex flex-col items-center justify-center shadow-[0_20px_40px_rgba(0,0,0,0.25),inset_0_1px_0_rgba(255,255,255,0.15)] active:scale-[0.98] transition-transform"
        >
          <span className="text-[17px] font-semibold tracking-[-0.02em]">
            {state.visitStarted ? tt("visit_active_label", state.locale) : tt("start_visit_label", state.locale)}
          </span>
          <span className="text-[11px] opacity-60 mt-0.5 font-medium">{tt("tap_to_begin", state.locale)}</span>
        </button>
      </div>

      <div className="absolute bottom-0 left-0 right-0 z-10 p-3 pb-[34px] space-y-2.5">
        {MISSIONS.map((mission, i) => {
          const done = state.seen.length > i;
          return (
            <div
              key={mission.id}
              className="h-[64px] rounded-[16px] bg-white/90 backdrop-blur-2xl border border-black/[0.06] shadow-[0_8px_24px_rgba(0,0,0,0.06)] flex items-center px-4 gap-3"
            >
              <ProgressRing
                progress={done ? 1 : 0}
                radius={13}
                strokeWidth={3}
                size={32}
                progressColor="#111111"
                centerLabel={done ? "✓" : i + 1}
              />
              <div className="flex-1">
                <div className="text-[14px] font-semibold tracking-[-0.01em] leading-none">
                  {missionLabel(mission, state.locale)}
                </div>
                <div className="text-[12px] text-[#8E8E93] mt-1 font-medium">{done ? "1/1" : "0/1"}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
