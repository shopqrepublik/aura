"use client";

import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import ProgressRing from "@/components/ui/ProgressRing";
import { ARTWORKS, MISSIONS, missionLabel } from "@/lib/artworks";
import { isMissionComplete } from "@/lib/missions";
import { tt } from "@/lib/i18n";
import type { AppState } from "@/lib/app-state";
import type { Artwork } from "@/lib/types";

// "04 VISIT PROGRESS - Live Progress" — ported the stat math (value seen /
// works / time / museum %) from the old app.js renderProgress(): estimates
// are null for unreviewed works, so the total is only ever a sum of REAL
// non-null estimates, "Pending review" otherwise — never an invented number.
// Deep focus and the "Next" suggestion are new to ELYIO (no equivalent in
// the old frontend) but stay on the same rule: Deep focus only renders when
// there is a real measured dwell time (cardOpenedAt), and "Next"/the
// mission list below both use lib/missions.ts's real per-mission
// completion check (has the user actually scanned a work that satisfies
// this specific mission?) rather than the old placeholder that just
// marked mission N done once N works had been scanned, regardless of
// which ones.
export default function ProgressScreen({
  state,
  seenArtworks,
  onBack,
  onContinueScanning,
  onCompleteVisit,
}: {
  state: AppState;
  seenArtworks: Artwork[];
  onBack: () => void;
  onContinueScanning: () => void;
  onCompleteVisit: () => void;
}) {
  // `now` starts null so the very first client render matches the server's
  // (neither ever calls Date.now() during render) — it's only ever set from
  // inside an effect, i.e. after hydration. Without this, "mins"/"focusMins"
  // below would read a different wall-clock value on the server than on the
  // client and React would throw a hydration mismatch the moment this
  // component is part of the initial paint (e.g. the landing page's Screens
  // showcase, which mounts it immediately instead of after user navigation).
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  const totalLow = seenArtworks.reduce((sum, a) => sum + (a.estimate.low || 0), 0);
  const totalHigh = seenArtworks.reduce((sum, a) => sum + (a.estimate.high || 0), 0);
  const hasEstimate = seenArtworks.length > 0 && totalHigh > 0;
  const valueSeen = hasEstimate ? `€${totalLow}–${totalHigh}M` : tt("pending_review", state.locale);

  const mins = now && state.startTime ? Math.max(1, Math.round((now - state.startTime) / 60000)) : 0;
  const pct = ARTWORKS.length ? Math.min(100, Math.round((seenArtworks.length / ARTWORKS.length) * 100)) : 0;

  const focusMins = now && state.currentArtwork && state.cardOpenedAt
    ? Math.max(0.1, (now - state.cardOpenedAt) / 60000)
    : null;

  const nextMission = MISSIONS.find((m) => !isMissionComplete(m.id, state.seen)) ?? null;

  const thumbnails = seenArtworks.slice().reverse();

  return (
    <div className="w-full h-full bg-[#FAFAF9] overflow-y-auto scrollbar-none flex flex-col">
      <div className="px-6 pt-[60px] pb-[100px] flex-1">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={onBack}
            aria-label="Back"
            className="w-9 h-9 rounded-full bg-black/[0.06] flex items-center justify-center"
          >
            <ArrowLeft className="w-4 h-4 text-black" />
          </button>
          <button type="button" onClick={onCompleteVisit} className="text-[13px] font-semibold text-[#8E8E93]">
            {tt("complete_visit", state.locale)}
          </button>
        </div>

        <div className="relative mt-5">
          <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#8E8E93]">
            {tt("live_progress", state.locale)}
          </div>

          <div className="absolute -top-2 -right-2 w-16 h-16">
            <ProgressRing
              progress={pct / 100}
              radius={26}
              strokeWidth={4}
              size={64}
              centerLabel={<span className="text-[12px] font-bold">{pct}%</span>}
            />
          </div>

          <div className="grid grid-cols-2 gap-6 mt-6 max-w-[70%]">
            <div>
              <div className="text-[28px] font-bold tracking-[-0.04em] text-[#111] tabular-nums">{valueSeen}</div>
              <div className="text-[11px] uppercase tracking-[0.08em] text-[#8E8E93] mt-1">
                {tt("stat_value_seen", state.locale)}
              </div>
            </div>
            <div>
              <div className="text-[28px] font-bold tracking-[-0.04em] text-[#111] tabular-nums">
                {seenArtworks.length}
              </div>
              <div className="text-[11px] uppercase tracking-[0.08em] text-[#8E8E93] mt-1">
                {tt("stat_works", state.locale)}
              </div>
            </div>
            <div>
              <div className="text-[28px] font-bold tracking-[-0.04em] text-[#111] tabular-nums">{mins}m</div>
              <div className="text-[11px] uppercase tracking-[0.08em] text-[#8E8E93] mt-1">
                {tt("stat_time", state.locale)}
              </div>
            </div>
            <div>
              <div className="text-[28px] font-bold tracking-[-0.04em] text-[#111] tabular-nums">{pct}%</div>
              <div className="text-[11px] uppercase tracking-[0.08em] text-[#8E8E93] mt-1">
                {tt("stat_museum", state.locale)}
              </div>
            </div>
          </div>
        </div>

        <div className="h-[1px] bg-black/10 mt-8" />

        <div className="mt-6">
          <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#8E8E93]">
            {tt("missions_label", state.locale)}
          </div>
          <div className="mt-3 space-y-2">
            {MISSIONS.map((mission) => {
              const done = isMissionComplete(mission.id, state.seen);
              return (
                <div key={mission.id} className="flex items-center gap-3">
                  <div
                    className={`w-5 h-5 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold ${
                      done ? "bg-[#111] text-white" : "bg-black/[0.08] text-[#8E8E93]"
                    }`}
                  >
                    {done ? "✓" : ""}
                  </div>
                  <span className={`text-[13px] font-medium ${done ? "text-[#111] line-through" : "text-[#3C3C43]"}`}>
                    {missionLabel(mission, state.locale)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {thumbnails.length > 0 && (
          <div className="mt-6 flex gap-3 overflow-x-auto -mx-1 px-1 pb-2 scrollbar-none">
            {thumbnails.map((a) => {
              const active = a.id === state.currentArtwork?.id;
              return (
                <div
                  key={a.id}
                  className={`relative w-[72px] h-[72px] rounded-[16px] bg-[#E8E8E8] shrink-0 overflow-hidden ${
                    active ? "ring-2 ring-black ring-offset-2" : ""
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={a.imageUrl} alt="" className="w-full h-full object-cover" />
                  {active && (
                    <div className="absolute bottom-1 left-1 right-1 h-1 rounded-full bg-black/70" />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {state.currentArtwork && focusMins != null && (
          <div className="mt-6 rounded-[20px] bg-white border border-black/[0.06] shadow-sm p-4 flex items-center justify-between">
            <div>
              <div className="text-[12px] uppercase tracking-[0.08em] text-[#8E8E93]">
                {tt("deep_focus", state.locale)}
              </div>
              <div className="text-[14px] font-semibold text-[#111] mt-1">
                {focusMins < 1
                  ? `< 1 min · ${state.currentArtwork.artist}`
                  : `${focusMins.toFixed(1)} min · ${state.currentArtwork.artist}`}
              </div>
            </div>
            <div className="w-10 h-10 rounded-full bg-[#F5F5F7] shrink-0" />
          </div>
        )}
      </div>

      {/* The black "Next" bar below is the strongest visual element on this
          screen, and reads as THE primary action -- easy to mistake for the
          only path forward. The actual way to reach Recap was a plain
          13px gray text link in the top-right corner (onCompleteVisit,
          tt("complete_visit")), the same visual weight as a "cancel" link
          and nowhere near the bottom CTA a first-time user's eye lands on.
          Same class of regression as the Camera/Card navigation fixes: the
          handler existed, but nothing made it discoverable. This button
          doesn't replace the top-corner link (still there, still works) or
          the Next bar (still the right nudge for continuing to scan) -- it
          adds a second, equally-visible, always-available way to finish. */}
      <div className="sticky bottom-0 left-0 right-0 p-3 pb-9 space-y-3 bg-gradient-to-t from-[#FAFAF9] via-[#FAFAF9]/90 to-transparent">
        <button
          type="button"
          onClick={onContinueScanning}
          className="w-full h-[72px] rounded-[20px] bg-black text-white flex items-center px-5 justify-between shadow-[0_16px_32px_rgba(0,0,0,0.22)]"
        >
          <span className="text-left">
            <span className="block text-[11px] uppercase opacity-60">{tt("next_label", state.locale)}</span>
            <span className="block text-[15px] font-semibold">
              {nextMission ? missionLabel(nextMission, state.locale) : tt("keep_exploring", state.locale)}
            </span>
          </span>
        </button>
        <button
          type="button"
          onClick={onCompleteVisit}
          className="w-full h-[50px] rounded-full bg-[#F5F5F7] text-[#111] text-[15px] font-semibold tracking-[-0.01em]"
        >
          {tt("complete_visit_button", state.locale)}
        </button>
      </div>
    </div>
  );
}
