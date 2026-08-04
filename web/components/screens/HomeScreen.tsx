"use client";

import { useState } from "react";
import ProgressRing from "@/components/ui/ProgressRing";
import { MISSIONS, missionLabel } from "@/lib/artworks";
import { tt, LOCALES } from "@/lib/i18n";
import { useMuseumDetection } from "@/lib/geolocation";
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
  const { status: museumStatus, confirmManually } = useMuseumDetection();
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div className="relative w-full h-full bg-[#F5F5F7] overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_0%,#E8E0D6_0%,#D6DDE8_40%,#C9CED6_100%)]" />
        <div className="absolute inset-0 bg-white/30 backdrop-blur-[2px]" />
      </div>

      <div className="relative z-10 pt-[56px] flex items-center justify-center gap-2">
        <div className="relative">
          {/* Chip is only a <button> (tappable) in the "manual-prompt"
              state -- otherwise it's just a status readout. This is the
              honest fallback for §4.1's "GPS/geofence OR manual, both
              valid" -- we never block the app on a missing/denied/out-of-
              range GPS fix, we just stop claiming we detected something we
              didn't. "manual-confirmed" gets its own color (not green) so
              it never reads as a GPS-verified detection it isn't. */}
          {museumStatus === "manual-prompt" ? (
            <button
              type="button"
              onClick={() => setShowConfirm((v) => !v)}
              className="h-[28px] px-3 rounded-full bg-black/80 backdrop-blur-xl flex items-center gap-2 shadow-[0_4px_12px_rgba(0,0,0,0.15)]"
            >
              <div className="w-2 h-2 rounded-full bg-white/40" />
              <span className="text-[12px] font-[600] text-white tracking-[-0.01em]">
                {tt("museum_select_prompt", state.locale)}
              </span>
            </button>
          ) : (
            <div className="h-[28px] px-3 rounded-full bg-black/80 backdrop-blur-xl flex items-center gap-2 shadow-[0_4px_12px_rgba(0,0,0,0.15)]">
              <div
                className={`w-2 h-2 rounded-full ${
                  museumStatus === "detected"
                    ? "bg-[#30D158] shadow-[0_0_8px_#30D158]"
                    : museumStatus === "manual-confirmed"
                      ? "bg-[#0A84FF] shadow-[0_0_8px_#0A84FF]"
                      : "bg-white/40 animate-pulse"
                }`}
              />
              <span className="text-[12px] font-[600] text-white tracking-[-0.01em]">
                {museumStatus === "detected"
                  ? tt("museum_detected", state.locale)
                  : museumStatus === "manual-confirmed"
                    ? tt("museum_confirmed_manual", state.locale)
                    : tt("museum_locating", state.locale)}
              </span>
            </div>
          )}

          {showConfirm && (
            <div className="absolute top-[36px] left-1/2 -translate-x-1/2 w-[220px] rounded-[16px] bg-white shadow-[0_12px_32px_rgba(0,0,0,0.2)] p-3 z-20">
              <p className="text-[13px] font-semibold text-[#111] text-center leading-[18px]">
                {tt("museum_confirm_question", state.locale)}
              </p>
              <div className="mt-2.5 flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowConfirm(false)}
                  className="flex-1 h-[32px] rounded-full bg-[#F5F5F7] text-[12px] font-semibold text-black"
                >
                  {tt("museum_confirm_not_now", state.locale)}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    confirmManually();
                    setShowConfirm(false);
                  }}
                  className="flex-1 h-[32px] rounded-full bg-black text-[12px] font-semibold text-white"
                >
                  {tt("museum_confirm_yes", state.locale)}
                </button>
              </div>
            </div>
          )}
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
