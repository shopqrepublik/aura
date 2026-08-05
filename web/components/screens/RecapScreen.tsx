"use client";

import { useEffect, useState } from "react";
import { tt } from "@/lib/i18n";
import { generateRecapImage } from "@/lib/recap-image";
import { buildVisitPalette, visitPaletteCssBackground, GRAIN_BACKGROUND_IMAGE, FRAGMENT_LAYOUT } from "@/lib/visitPalette";
import CollectorsSeal from "@/components/ui/CollectorsSeal";
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

  // design-direction-v3.md §10 "Visit Palette" -- background for this whole
  // screen, derived from the same top-3-significant-works ranking used for
  // "Most valuable" above. See lib/visitPalette.ts for the muting rationale.
  const palette = buildVisitPalette(seenArtworks);

  // €1000M = €1B. Real threshold against the real summed estimate — with
  // all 101 catalog works' estimate.high summing to ~€2.94B, this is
  // reachable but only by deliberately scanning roughly the museum's top
  // ten most valuable works in one visit (cumulative total crosses €1B
  // around the 11th-priciest work) — a rare, deliberately-earned badge, not
  // a routine one.
  const isBillion = totalHigh >= 1000;

  // Honest partial-coverage note: when SOME but not all scanned works have
  // a reviewed estimate, the €low–highM total silently covers only the
  // reviewed subset (`.reduce` treats null as 0) — this makes that visible
  // instead of letting the number read as "everything you scanned".
  const valueNote =
    hasAnyEstimate && withEstimate.length < seenArtworks.length
      ? tt("value_seen_partial_note", state.locale)
          .replace("{n}", String(withEstimate.length))
          .replace("{total}", String(seenArtworks.length))
      : null;

  const worksLabel = seenArtworks.length === 1 ? tt("stat_work_one", state.locale) : tt("works_seen_count", state.locale).toLowerCase();
  const artistsLabel = artists.size === 1 ? tt("stat_artist_one", state.locale) : tt("stat_artists", state.locale).toLowerCase();

  const headlineText = hasAnyEstimate ? `€${totalLow}–${totalHigh}M` : tt("pending_review", state.locale);
  // Discrete size steps (not a fluid clamp -- this codebase doesn't use
  // clamp() elsewhere, so this stays consistent with ProvenanceReveal's own
  // tiered price sizing rather than introducing a new technique).
  const headlineSize = headlineText.length > 10 ? 44 : headlineText.length > 7 ? 56 : 68;

  const [imageBusy, setImageBusy] = useState<"share" | "save" | null>(null);

  async function buildImage(): Promise<Blob | null> {
    return generateRecapImage({
      locale: state.locale,
      dateStr,
      worksCount: seenArtworks.length,
      artistsCount: artists.size,
      timeStr,
      hasAnyEstimate,
      reviewedCount: withEstimate.length,
      totalLow,
      totalHigh,
      mostValuable,
      mostValuableHasEstimate: mostValuable?.estimate.high != null,
      isBillion,
      paletteAccents: palette.accents,
    });
  }

  async function handleShare() {
    setImageBusy("share");
    try {
      const text = `${seenArtworks.length} works • ${artists.size} artists • ${timeStr} at Musée d'Orsay — ELYIO`;
      const blob = await buildImage();
      const file = blob ? new File([blob], "elyio-visit-recap.png", { type: "image/png" }) : null;

      // Web Share Level 2 (files) has patchy cross-browser support even
      // where navigator.share itself exists — canShare({files}) is the
      // actual capability check, not just the presence of navigator.share.
      if (file && navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: "My ELYIO visit", text });
        } catch {
          // user cancelled the native share sheet — nothing to do
        }
        return;
      }

      if (navigator.share) {
        try {
          await navigator.share({ title: "My ELYIO visit", text });
        } catch {
          // user cancelled — nothing to do
        }
        return;
      }

      // No Web Share support at all (most desktop browsers): fall back to
      // the same download flow as the explicit "Save image" button.
      if (blob) downloadBlob(blob);
    } finally {
      setImageBusy(null);
    }
  }

  async function handleSave() {
    setImageBusy("save");
    try {
      const blob = await buildImage();
      if (blob) downloadBlob(blob);
    } finally {
      setImageBusy(null);
    }
  }

  function downloadBlob(blob: Blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "elyio-visit-recap.png";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="relative w-full h-full overflow-y-auto scrollbar-none">
      {/* Visit Palette background layer -- muted accent gradient + grain +
          cropped photo fragments, all behind the content below. Real <img>
          fragments are fine here (unlike the PNG export path) since this is
          live DOM, not a canvas pixel read -- see lib/visitPalette.ts. */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none" style={{ backgroundImage: visitPaletteCssBackground(palette) }}>
        <div
          className="absolute inset-0 opacity-[0.05] mix-blend-overlay"
          style={{ backgroundImage: GRAIN_BACKGROUND_IMAGE, backgroundSize: "180px 180px" }}
        />
        {palette.works.map((w, i) => {
          const layout = FRAGMENT_LAYOUT[i];
          if (!layout) return null;
          return (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={w.id}
              src={w.imageUrl}
              alt=""
              aria-hidden="true"
              className="absolute object-cover rounded-[24px] opacity-[0.12]"
              style={{
                top: layout.top,
                left: layout.left,
                right: layout.right,
                width: layout.width,
                height: layout.height,
                transform: `rotate(${layout.rotate}deg)`,
              }}
            />
          );
        })}
      </div>

      <div className="relative flex flex-col h-full pt-16 pb-9 px-6">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <div className="text-[10px] font-bold tracking-[0.18em] uppercase text-[#8E8E93]">Musée d&apos;Orsay</div>
          <div className="text-[10px] font-medium tracking-[0.1em] uppercase text-[#B4B4B8] mt-0.5">Paris · {dateStr}</div>
        </div>
        <div className="w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-[10px] font-bold">
          E
        </div>
      </div>

      {/* "The Acquisition Poster" (design-direction-v3.md §10): one big
          culmination number, not four identical bordered cells. Kept as the
          same honest low-high RANGE the rest of this app always shows
          (ProvenanceReveal, the old "Value seen" row) rather than collapsing
          to a single fabricated point figure the way the doc's literal
          "€3.8B" example does -- a range is the real data; a single number
          would imply false precision this project has repeatedly ruled out
          (see estimate handling everywhere else). Font size steps down for
          longer strings instead of shrinking indefinitely or overflowing;
          wrapping (no nowrap) is the safety net for extreme cumulative
          totals a very long visit could produce. */}
      <div className="mt-10 shrink-0">
        <div className="text-[11px] font-bold tracking-[0.14em] uppercase text-[#8E8E93]">
          {tt("you_saw_label", state.locale)}
        </div>
        <div
          className="mt-1 font-bold text-[#111]"
          style={
            hasAnyEstimate
              ? { fontSize: headlineSize, letterSpacing: "-0.025em", lineHeight: 0.98 }
              : { fontSize: 26, letterSpacing: "-0.01em", lineHeight: 1.2 }
          }
        >
          {headlineText}
        </div>
        <div className="mt-2 text-[13px] font-medium text-[#6E6E73] uppercase tracking-[0.02em] max-w-[280px]">
          {hasAnyEstimate ? tt("in_estimated_market_value", state.locale) : tt("recap_value_pending_caption", state.locale)}
        </div>
        {valueNote && <div className="text-[11px] text-[#8E8E93] mt-1">{valueNote}</div>}
      </div>

      <div className="mt-6 text-[13px] font-semibold text-[#6E6E73] shrink-0">
        {`${seenArtworks.length} ${worksLabel} · ${artists.size} ${artistsLabel} · ${timeStr}`}
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
        {isBillion && <CollectorsSeal timestamp={visitTimestamp} locale={state.locale} />}
        <button
          type="button"
          onClick={handleShare}
          disabled={imageBusy !== null}
          className="w-full h-[52px] rounded-full bg-black text-white text-[15px] font-semibold shadow-[0_8px_20px_rgba(0,0,0,0.18)] disabled:opacity-60"
        >
          {imageBusy === "share" ? tt("generating_image", state.locale) : tt("share_your_visit", state.locale)}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={imageBusy !== null}
          className="w-full h-[52px] rounded-full bg-[#F5F5F7] text-[#111] text-[15px] font-semibold disabled:opacity-60"
        >
          {imageBusy === "save" ? tt("generating_image", state.locale) : tt("save_image", state.locale)}
        </button>
        <button type="button" onClick={onNewVisit} className="w-full text-center text-[13px] font-semibold text-[#8E8E93] pt-1">
          {tt("new_visit", state.locale)}
        </button>
        <p className="text-[11px] text-[#8E8E93] text-center pt-2">elyio.co / v1.0</p>
      </div>
      </div>
    </div>
  );
}
