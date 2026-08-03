"use client";

import { useEffect, useState } from "react";
import { tt } from "@/lib/i18n";
import type { AppState } from "@/lib/app-state";
import type { Artwork } from "@/lib/types";

// Deterministic, Intl-free formatter — `toLocaleDateString` is one of the
// causes React's hydration-mismatch error explicitly calls out (ICU data can
// differ between the Node server and the browser); this never depends on
// locale data, only on the timestamp itself.
function formatDate(ts: number): string {
  const d = new Date(ts);
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
}

// "05 VISIT RECAP VIRAL" — stat math and the most-valuable/favorite fallback
// ported 1:1 from the old app.js renderRecap() (canvas version): favorite
// artwork, else first seen, always shown if anything was seen; its own
// estimate line reads "Estimate pending review" per-item when null rather
// than hiding the card, exactly like the old app. The mockup's "4.7 km • 3
// floors • 87% focused" subtitle is NOT reproduced — there is no GPS or
// attention sensor behind those numbers, so showing them would be exactly
// the kind of fabricated figure this project has repeatedly ruled out
// (see estimate handling). The subtitle here uses only real counted stats.
export default function RecapScreen({
  state,
  seenArtworks,
  onNewVisit,
}: {
  state: AppState;
  seenArtworks: Artwork[];
  onNewVisit: () => void;
}) {
  // `now` starts null so the first client render matches the server's exactly
  // (neither ever calls Date.now() during render) — see the same pattern and
  // rationale in ProgressScreen.tsx. Only set from an effect, i.e. after
  // hydration, which is what makes this safe for a component that can be
  // part of the initial SSR paint (the landing page's Screens showcase).
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
  }, []);

  const artists = new Set(seenArtworks.map((a) => a.artist));
  const totalLow = seenArtworks.reduce((s, a) => s + (a.estimate.low || 0), 0);
  const totalHigh = seenArtworks.reduce((s, a) => s + (a.estimate.high || 0), 0);
  const hasAnyEstimate = seenArtworks.some((a) => a.estimate.high != null);

  const mins = now && state.startTime ? Math.max(1, Math.round((now - state.startTime) / 60000)) : 0;
  const timeStr = mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins}m`;

  const favArt = seenArtworks.find((a) => state.favorites.has(a.id)) ?? seenArtworks[0] ?? null;
  const withEstimate = seenArtworks.filter((a) => a.estimate.high != null);
  const mostValuable = withEstimate.length
    ? withEstimate.slice().sort((a, b) => (b.estimate.high ?? 0) - (a.estimate.high ?? 0))[0]
    : favArt;

  const visitTimestamp = state.startTime ?? now;
  const dateStr = visitTimestamp ? formatDate(visitTimestamp) : "";

  const isBillion = totalHigh >= 1000;

  async function handleShare() {
    const text = `${seenArtworks.length} works • ${artists.size} artists • ${timeStr} at Musée d'Orsay — ELYIO`;
    if (navigator.share) {
      try {
        await navigator.share({ title: "My ELYIO visit", text });
      } catch {
        // user cancelled the native share sheet — nothing to do
      }
    }
  }

  return (
    <div
      className="w-full h-full flex flex-col pt-16 pb-9 px-6 overflow-y-auto scrollbar-none"
      style={{ background: "linear-gradient(180deg, #FFFFFF 0%, #F5F5F7 55%, #EDEEF2 100%)" }}
    >
      <div className="flex items-center justify-between shrink-0">
        <span className="text-[10px] font-bold tracking-[0.18em] uppercase text-[#8E8E93]">
          ELYIO • {dateStr}
        </span>
        <div className="w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-[10px] font-bold">
          E
        </div>
      </div>

      <div className="mt-8 shrink-0">
        <h1 className="text-[24px] font-bold tracking-[-0.04em] leading-[26px] text-[#111]">
          {tt("my_visit_title", state.locale)}
        </h1>
        <p className="mt-1 text-[13px] font-medium text-[#6E6E73]">
          {`${seenArtworks.length} ${tt("works_seen_count", state.locale).toLowerCase()} • ${timeStr} • Musée d'Orsay`}
        </p>
      </div>

      <div className="mt-8 space-y-4 shrink-0">
        {[
          [tt("works_seen_count", state.locale), String(seenArtworks.length)],
          [tt("stat_artists", state.locale), String(artists.size)],
          [tt("stat_value_seen", state.locale), hasAnyEstimate ? `€${totalLow}–${totalHigh}M` : tt("pending_review", state.locale)],
          [tt("stat_time", state.locale), timeStr],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between items-baseline border-b border-black/10 pb-4">
            <span className="text-[13px] font-semibold uppercase tracking-widest text-[#8E8E93]">{label}</span>
            <span className="text-[22px] font-bold tracking-[-0.03em] text-[#111] tabular-nums">{value}</span>
          </div>
        ))}
      </div>

      {mostValuable && (
        <div className="mt-6 flex gap-3 p-3 rounded-[14px] bg-white border border-black/5 shadow-sm shrink-0">
          <div className="w-12 h-12 rounded-[10px] shrink-0 overflow-hidden bg-[#FFD8A8]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={mostValuable.imageUrl} alt="" className="w-full h-full object-cover" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-[0.08em] text-[#8E8E93]">
              {mostValuable.estimate.high != null ? tt("most_valuable_today", state.locale) : tt("featured_today", state.locale)}
            </div>
            <div className="text-[13px] font-semibold text-[#111] mt-0.5">
              {mostValuable.artist} •{" "}
              {mostValuable.estimate.high != null
                ? `€${mostValuable.estimate.low}–${mostValuable.estimate.high}M EST.`
                : tt("estimate_pending", state.locale)}
            </div>
          </div>
        </div>
      )}

      <div className="mt-auto space-y-3 pt-8 shrink-0">
        {isBillion && (
          <div className="w-fit px-3.5 py-2 rounded-full bg-[#FF3B30] text-white text-[12px] font-bold tracking-wide shadow-[0_8px_20px_rgba(255,59,48,0.35)] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
            {tt("billion_euro_visitor", state.locale)}
          </div>
        )}
        <button
          type="button"
          onClick={handleShare}
          className="w-full h-[52px] rounded-full bg-black text-white text-[15px] font-semibold shadow-[0_8px_20px_rgba(0,0,0,0.18)]"
        >
          {tt("share_your_visit", state.locale)}
        </button>
        <button type="button" onClick={onNewVisit} className="w-full text-center text-[13px] font-semibold text-[#8E8E93] pt-1">
          {tt("new_visit", state.locale)}
        </button>
        <p className="text-[11px] text-[#8E8E93] text-center pt-2">elyio.co / v1.0</p>
      </div>
    </div>
  );
}
