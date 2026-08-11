"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Check } from "lucide-react";
import ProgressRing from "@/components/ui/ProgressRing";
import { ARTWORKS, MISSIONS, missionLabel } from "@/lib/artworks";
import { isMissionComplete } from "@/lib/missions";
import { formatVisitValueHeadline, formatVisitValueSubtitle, summarizeVisitValue } from "@/lib/valueReveal";
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
//
// visual-rebuild-contract.md §13/§22 "Progress page": this used to be a
// 4-cell KPI-dashboard grid (value/works/time/museum% as four identical
// stat blocks) -- the contract calls that out by name as one of the things
// that makes ELYIO read like a fintech app instead of a museum guide. Now
// it's one editorial-serif headline value (value seen) with one secondary
// line (works · time), the museum-% ring shrunk and moved to a corner
// marker instead of a competing stat cell, missions as a numbered editorial
// checklist instead of filled circle-badges, and the thumbnail row's
// ring-2/ring-offset-2 (a genuinely double outline) replaced by the same
// thin hairline border + accent bar convention the Recap thumbnails
// already use.
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
    const tick = () => setNow(Date.now());
    const initialId = window.setTimeout(tick, 0);
    const intervalId = window.setInterval(tick, 30000);
    return () => {
      window.clearTimeout(initialId);
      window.clearInterval(intervalId);
    };
  }, []);

  const valueSummary = summarizeVisitValue(seenArtworks);
  const valueSeen = formatVisitValueHeadline(valueSummary, state.locale);
  const valueSubtitle = formatVisitValueSubtitle(valueSummary, state.locale);

  const mins = now && state.startTime ? Math.max(1, Math.round((now - state.startTime) / 60000)) : 0;
  const pct = ARTWORKS.length ? Math.min(100, Math.round((seenArtworks.length / ARTWORKS.length) * 100)) : 0;
  // Same singular/plural convention RecapScreen's own stats row already
  // uses (lib/i18n.ts's stat_work_one / works_seen_count pair) -- one
  // secondary line here replaces what used to be two of the four KPI cells.
  const worksLabel = seenArtworks.length === 1 ? tt("stat_work_one", state.locale) : tt("works_seen_count", state.locale).toLowerCase();

  const focusMins = now && state.currentArtwork && state.cardOpenedAt
    ? Math.max(0.1, (now - state.cardOpenedAt) / 60000)
    : null;

  const nextMission = MISSIONS.find((m) => !isMissionComplete(m.id, state.seen)) ?? null;

  const thumbnails = seenArtworks.slice().reverse();

  return (
    <div className="w-full h-full bg-[#F7F3EC] overflow-y-auto scrollbar-none flex flex-col">
      <div className="px-6 pt-[60px] pb-[100px] flex-1">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={onBack}
            aria-label="Back"
            className="w-9 h-9 rounded-full bg-[rgba(24,23,20,0.055)] flex items-center justify-center"
          >
            <ArrowLeft className="w-4 h-4 text-[#181714]" />
          </button>
          <button type="button" onClick={onCompleteVisit} className="text-[13px] font-semibold text-[#67635C]">
            {tt("complete_visit", state.locale)}
          </button>
        </div>

        {/* Header row: label + a small corner ring instead of the old
            64px ring floating over a 4-cell grid -- museum-% is real
            context, not a stat that should visually compete with the
            headline value below it. */}
        <div className="mt-6 flex items-start justify-between">
          <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#67635C]">
            {tt("live_progress", state.locale)}
          </div>
          <ProgressRing
            progress={pct / 100}
            radius={16}
            strokeWidth={3}
            size={38}
            trackColor="rgba(24,23,20,0.08)"
            progressColor="#181714"
            centerLabel={<span className="text-[9px] font-semibold tabular-nums text-[#181714]">{pct}%</span>}
          />
        </div>

        {/* One editorial-serif headline value + one secondary line --
            replaces the old 2x2 KPI grid (value/works/time/museum% as four
            identical cells). Same "you saw €X in Y works" shape RecapScreen
            already uses, just sized for an in-progress stat instead of the
            final poster number. */}
        <div className="mt-3">
          <div
            className="font-medium leading-[0.9] text-[#181714]"
            style={{ fontFamily: "var(--font-editorial)", fontSize: "clamp(38px, 10vw, 48px)", letterSpacing: "-0.03em" }}
          >
            {valueSeen}
          </div>
          <div className="mt-1.5 text-[13px] text-[#67635C]">{valueSubtitle}</div>
          <div className="mt-3 text-[14px] font-medium text-[#302E29] tabular-nums">
            {seenArtworks.length} {worksLabel} · {mins}m
          </div>
        </div>

        <div className="h-px bg-[rgba(30,27,22,0.10)] mt-7" />

        {/* Missions: numbered editorial checklist -- filled circle-badges
            with a checkmark glyph read as a to-do app; a tabular index
            number that gives way to a thin checkmark on completion, with
            hairline row dividers, reads closer to a printed visit guide's
            own checklist. */}
        <div className="mt-6">
          <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#67635C]">
            {tt("missions_label", state.locale)}
          </div>
          <div className="mt-2.5">
            {MISSIONS.map((mission, i) => {
              const done = isMissionComplete(mission.id, state.seen);
              return (
                <div
                  key={mission.id}
                  className={`flex items-center gap-3 py-2.5 ${i > 0 ? "border-t border-[rgba(30,27,22,0.08)]" : ""}`}
                >
                  {done ? (
                    <Check className="w-3.5 h-3.5 shrink-0 text-[#181714]" strokeWidth={2.5} />
                  ) : (
                    <span className="w-3.5 shrink-0 text-[11px] tabular-nums text-[#8B867E]">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                  )}
                  <span className={`text-[13px] font-medium ${done ? "text-[#8B867E]" : "text-[#302E29]"}`}>
                    {missionLabel(mission, state.locale)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {thumbnails.length > 0 && (
          <div className="mt-6 flex gap-2.5 overflow-x-auto -mx-1 px-1 pb-2 scrollbar-none">
            {thumbnails.map((a) => {
              const active = a.id === state.currentArtwork?.id;
              return (
                <div
                  key={a.id}
                  className="relative w-[64px] h-[64px] rounded-[12px] bg-[#EDE6DA] shrink-0 overflow-hidden border border-[rgba(24,23,20,0.08)]"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={a.imageUrl} alt="" className="w-full h-full object-cover" />
                  {active && <div className="absolute bottom-1 left-1 right-1 h-[3px] rounded-full bg-[#181714]" />}
                </div>
              );
            })}
          </div>
        )}

        {state.currentArtwork && focusMins != null && (
          <div
            className="mt-6 rounded-[16px] p-4 flex items-center justify-between"
            style={{ backgroundColor: "#FBF8F2", border: "1px solid rgba(24,23,20,0.06)" }}
          >
            <div>
              <div className="text-[11px] uppercase tracking-[0.1em] text-[#67635C]">{tt("deep_focus", state.locale)}</div>
              <div className="text-[14px] font-medium text-[#181714] mt-1">
                {focusMins < 1
                  ? `< 1 min · ${state.currentArtwork.artist || tt("uncataloged_unknown_artist", state.locale)}`
                  : `${focusMins.toFixed(1)} min · ${state.currentArtwork.artist || tt("uncataloged_unknown_artist", state.locale)}`}
              </div>
            </div>
            <div className="w-10 h-10 rounded-full bg-[#EDE6DA] shrink-0" />
          </div>
        )}
      </div>

      {/* The "Next" bar below is still the strongest visual element on this
          screen and still reads as THE primary action -- that's correct,
          it's the main nudge to keep scanning. What changed is how loud it
          is: pure black, a 20px radius, and a 32px-blur shadow read as a
          promo banner, not a button in this app's own editorial system
          (compare CardScreen's primary button -- #181714 ink, 14px radius,
          a much quieter shadow). Same color/radius/shadow tokens as
          everywhere else now, just still full-width and bottom-anchored so
          it's not any less reachable. The actual way to reach Recap was
          ALSO a plain 13px gray text link in the top-right corner
          (onCompleteVisit, tt("complete_visit")) -- same visual weight as a
          "cancel" link and nowhere near where a first-time user's eye
          lands. Same class of regression as the Camera/Card navigation
          fixes: the handler existed, but nothing made it discoverable.
          This button doesn't replace the top-corner link (still there,
          still works) or the Next bar (still the right nudge for
          continuing to scan) -- it adds a second, equally-visible,
          always-available way to finish. */}
      <div className="sticky bottom-0 left-0 right-0 p-3 pb-9 space-y-3 bg-gradient-to-t from-[#F7F3EC] via-[#F7F3EC]/90 to-transparent">
        <button
          type="button"
          onClick={onContinueScanning}
          className="w-full h-[64px] rounded-[14px] flex items-center px-5 justify-between"
          style={{ background: "#181714", color: "#FAF7F0", boxShadow: "0 6px 16px rgba(16,15,13,0.13)" }}
        >
          <span className="text-left">
            <span className="block text-[10px] uppercase opacity-60">{tt("next_label", state.locale)}</span>
            <span className="block text-[14px] font-medium">
              {nextMission ? missionLabel(nextMission, state.locale) : tt("keep_exploring", state.locale)}
            </span>
          </span>
        </button>
        <button
          type="button"
          onClick={onCompleteVisit}
          className="w-full h-[50px] rounded-[14px] bg-[rgba(24,23,20,0.055)] border border-[rgba(24,23,20,0.06)] text-[#25231F] text-[15px] font-medium tracking-[-0.01em]"
        >
          {tt("complete_visit_button", state.locale)}
        </button>
      </div>
    </div>
  );
}
