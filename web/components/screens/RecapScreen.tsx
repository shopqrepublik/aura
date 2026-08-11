"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { tt } from "@/lib/i18n";
import { artworkArtistDisplayName } from "@/lib/artist-display";
import { resolveTitle } from "@/lib/artworks";
import { generateRecapImage } from "@/lib/recap-image";
import { buildVisitPalette, visitPaletteBaseBackground, visitPaletteTintOverlayBackground, GRAIN_BACKGROUND_IMAGE } from "@/lib/visitPalette";
import { formatEstimatedValueRange, formatVisitValueHeadline, formatVisitValueSubtitle, getAggregateEligibleValue, getMostValuableArtwork, summarizeVisitValue } from "@/lib/valueReveal";
import { track } from "@/lib/analytics";
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

// Cream text-on-dark palette for this poster -- the visual-match rebuild's
// §14/§6 spec values, used at varying opacity for hierarchy rather than
// picking a different color per role.
const CREAM = "#F3E8D7";

// Editorial-collage placement for the background photo fragments (§14) --
// one spec per palette.works index, up to 3. Bleeds off the poster edges and
// alternates corners/rotation so it reads as loosely arranged clippings
// rather than a neat grid; sizes taper down (largest first) since
// palette.works is already ranked most-to-least significant. All three stay
// in the top ~55% of the frame -- the dark overlay above them (§14's own
// spec) fades from ~10% opaque at the top to ~94% by the bottom precisely so
// stats/thumbnails/buttons stay legible, which means a fragment placed any
// lower is fully hidden under that overlay before it ever reads as a photo.
const COLLAGE_FRAGMENTS: CSSProperties[] = [
  { width: "62%", height: "38%", top: "-6%", right: "-8%", transform: "rotate(3deg)", opacity: 0.4, mixBlendMode: "luminosity", filter: "grayscale(5%) contrast(108%)" },
  { width: "44%", height: "30%", top: "-4%", left: "-8%", transform: "rotate(-6deg)", opacity: 0.32, mixBlendMode: "luminosity", filter: "grayscale(5%) contrast(108%)" },
  { width: "32%", height: "24%", top: "30%", right: "-8%", transform: "rotate(8deg)", opacity: 0.28, mixBlendMode: "luminosity", filter: "grayscale(5%) contrast(108%)" },
];

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
    const id = window.setTimeout(() => setNow(Date.now()), 0);
    return () => window.clearTimeout(id);
  }, []);

  const artists = new Set(seenArtworks.map((a) => artworkArtistDisplayName(a, state.locale)));
  const valueSummary = summarizeVisitValue(seenArtworks);
  const totalLow = valueSummary.estimatedValueLow;
  const totalHigh = valueSummary.estimatedValueHigh;
  const hasAnyEstimate = valueSummary.hasEstimatedValue;

  // recap_generated (§13): fires once per mount, i.e. once per completed
  // visit that reaches this screen -- RecapScreen only ever mounts fresh
  // (page.tsx renders it conditionally on state.screen === "recap", and
  // newVisit() resets state entirely), so an empty deps array is correct
  // here, not a staleness risk.
  useEffect(() => {
    track("recap_generated", { works_count: seenArtworks.length, artists_count: artists.size });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const mins = now && state.startTime ? Math.max(1, Math.round((now - state.startTime) / 60000)) : 0;
  const timeStr = mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins}m`;

  const mostValuable = getMostValuableArtwork(seenArtworks);
  const mostValuableAggregate = mostValuable ? getAggregateEligibleValue(mostValuable) : null;

  const visitTimestamp = state.startTime ?? now;
  const dateStr = visitTimestamp ? formatDate(visitTimestamp) : "";

  // design-direction-v3.md §10 "Visit Palette" -- background for this whole
  // screen, derived from the same top-3-significant-works ranking used for
  // "Most valuable" above. Also supplies the on-screen thumbnail row's real
  // photos below. See lib/visitPalette.ts for the dark-poster rationale.
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
    hasAnyEstimate && valueSummary.estimatedValueArtworkCount < seenArtworks.length
      ? tt("value_seen_partial_note", state.locale)
          .replace("{n}", String(valueSummary.estimatedValueArtworkCount))
          .replace("{total}", String(seenArtworks.length))
      : null;

  const worksLabel = seenArtworks.length === 1 ? tt("stat_work_one", state.locale) : tt("works_seen_count", state.locale).toLowerCase();
  const artistsLabel = artists.size === 1 ? tt("stat_artist_one", state.locale) : tt("stat_artists", state.locale).toLowerCase();

  const headlineText = formatVisitValueHeadline(valueSummary, state.locale);
  const headlineSubtitle = formatVisitValueSubtitle(valueSummary, state.locale);
  // Discrete size steps, shifted into §6's "Recap value" clamp range
  // (70-92px) -- bigger than the Card-level Provenance Reveal price since
  // this is the poster's own culmination number, not a compact card figure.
  const headlineSize = headlineText.length > 10 ? 70 : headlineText.length > 7 ? 82 : 92;

  const [imageBusy, setImageBusy] = useState<"share" | "save" | null>(null);

  async function buildImage(): Promise<Blob | null> {
    return generateRecapImage({
      locale: state.locale,
      dateStr,
      worksCount: seenArtworks.length,
      artistsCount: artists.size,
      timeStr,
      hasAnyEstimate,
      reviewedCount: valueSummary.estimatedValueArtworkCount,
      totalLow,
      totalHigh,
      marketContextCount: valueSummary.marketContextCount,
      beyondMarketCount: valueSummary.beyondMarketCount,
      unvaluedCount: valueSummary.unvaluedCount,
      mostValuable,
      mostValuableHasEstimate: mostValuableAggregate != null,
      mostValuableValueText: mostValuableAggregate ? formatEstimatedValueRange(mostValuableAggregate) : null,
      mostValuableTitle: mostValuable ? resolveTitle(mostValuable, state.locale) : "",
      isBillion,
      paletteAccents: palette.accents,
      paletteWorks: palette.works.map((w) => ({ imageUrl: w.imageUrl, accent: w.accent })),
    });
  }

  async function handleShare() {
    setImageBusy("share");
    track("share_started");
    try {
      // Editorial share-sheet caption, not the old debug-log-style stat
      // dump -- reuses worksLabel (already singular/plural/locale-correct
      // via stat_work_one/works_seen_count, computed above) rather than
      // re-deriving that logic here, which is exactly how the old text
      // ended up ungrammatical in the first place: a second, separate
      // string nobody wired up to the same fix.
      const text = hasAnyEstimate
        ? tt("share_visit_with_value", state.locale)
            .replace("{count}", String(seenArtworks.length))
            .replace("{works}", worksLabel)
            .replace("{value}", headlineText)
        : tt("share_visit_pending", state.locale)
            .replace("{count}", String(seenArtworks.length))
            .replace("{works}", worksLabel)
            .replace("{value}", headlineText);
      const blob = await buildImage();
      const file = blob ? new File([blob], "elyio-visit-recap.png", { type: "image/png" }) : null;

      // Web Share Level 2 (files) has patchy cross-browser support even
      // where navigator.share itself exists — canShare({files}) is the
      // actual capability check, not just the presence of navigator.share.
      if (file && navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: "My ELYIO visit", text });
          track("share_completed", { method: "web_share_files" });
        } catch {
          // user cancelled the native share sheet — nothing to do
        }
        return;
      }

      if (navigator.share) {
        try {
          await navigator.share({ title: "My ELYIO visit", text });
          track("share_completed", { method: "web_share_text" });
        } catch {
          // user cancelled — nothing to do
        }
        return;
      }

      // No Web Share support at all (most desktop browsers): fall back to
      // the same download flow as the explicit "Save image" button.
      if (blob) {
        downloadBlob(blob);
        track("share_completed", { method: "download_fallback" });
      }
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
      {/* Visit Palette background -- dark editorial collage (visual-rebuild-
          contract.md §14): near-black base, then real cropped photo
          fragments from the 2-3 most significant seen works (low opacity,
          luminosity blend, soft radial mask so edges dissolve into the base
          rather than reading as pasted rectangles), then the same accent
          tint + dark overlay the contract specifies on top (fades to 94%
          opaque by the bottom so stats/thumbnails/buttons stay legible),
          then grain at ~3% opacity. Real <img> is safe here for the same
          reason the thumbnail row below is -- plain on-screen <img> has no
          canvas pixel read, so Wikimedia's CORS restriction (which only
          blocks canvas.drawImage) never applies. The PNG export
          (lib/recap-image.ts) has no photo layer -- see that file for why
          -- and stays an honest accent-color gradient instead.

          DELIBERATE DEVIATION from §14: the contract's own example collage
          mixes in museum-architecture fragments (its sample CSS references
          "orsay-clock-crop.jpg") alongside artwork crops. This intentionally
          uses ONLY crops of the works this specific visitor actually
          scanned, no generic building/clock photography. Architecture shots
          are identical for every visitor and add nothing to "what did I see
          today" -- the whole point of a personalized recap is that it's
          personalized. Do not "fix" this to match §14 literally in a future
          pass without raising it again; it's a considered exception, not an
          oversight. */}
      {/* min-h-full, not h-full, on the flex column below: h-full was a
          FIXED height (exactly one viewport), and this poster's own content
          -- header + headline + stats + thumbnails + most-valuable + footer
          -- is already taller than that in practice (not just with longer
          FR/ZH text, confirmed live on EN too). With shrink-0 on every
          child, a fixed-height flex column can't compress to fit, so it
          overflowed into the scrollable area below -- but the background
          div below was ALSO absolute+inset-0 sized against that same fixed
          one-viewport height (inset-0 sizes to the containing block's own
          box, never to scrollable content height), so it stopped short
          exactly where the overflow began. Below that line, the page's own
          white background showed through, which is why "Save image" (an
          8%-opacity fill) and "Start a new visit" (65%-opacity text) read
          as washed out while "Share your visit" (opaque solid cream)
          stayed fully visible regardless of what was behind it -- the
          reported bug. min-h-full lets this column grow taller than one
          viewport when content demands it instead of forcing an overflow;
          moving the background INSIDE it (as an absolutely-positioned
          first child, still painted behind everything else in DOM order)
          means inset-0 now sizes against this same content-driven height,
          so it always covers exactly as much as there is to scroll. */}
      {/* isolate (isolation: isolate) is load-bearing, not decorative: it
          makes this div establish its OWN stacking context, so the
          background's z-index:-1 below only needs to escape behind THIS
          div's own static-flow children (header, headline, stats,
          thumbnails, buttons) -- without it, a negative z-index with no
          nearby stacking-context boundary bubbles all the way up past
          this component's own ancestors, painting behind PhoneFrame's
          opaque white background too (confirmed live: the whole poster
          rendered as cream-on-white, unreadable, the second half of this
          same bug). */}
      <div className="relative isolate flex flex-col min-h-full pt-16 px-[44px] pb-12">
        {/* z-index: -1 is ALSO load-bearing (see the isolate comment above
            for why it's scoped correctly now): without it, this positioned
            (absolute) element paints AFTER all the static-flow siblings
            below it regardless of DOM order -- CSS stacking groups
            positioned elements together and paints that whole group on
            top of static content, so simply listing this div first was not
            enough once it moved inside the same flex column as those
            siblings (previously it was a sibling of the whole content
            block instead, where both sides of that pairing were
            themselves positioned, so DOM order alone correctly decided
            paint order). Confirmed live: without z-index:-1, the poster
            was a solid dark rectangle with every line of text and every
            button invisible underneath it -- the first half of this bug. */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none" style={{ zIndex: -1, backgroundImage: visitPaletteBaseBackground() }}>
          {palette.works.slice(0, 3).map((w, i) => (
            <img
              key={w.id}
              src={w.imageUrl}
              alt=""
              aria-hidden="true"
              className="absolute object-cover"
              style={{
                ...COLLAGE_FRAGMENTS[i],
                maskImage: "radial-gradient(ellipse at center, black 45%, transparent 78%)",
                WebkitMaskImage: "radial-gradient(ellipse at center, black 45%, transparent 78%)",
              }}
              // Purely decorative -- an intermittently-failing Wikimedia fetch
              // (observed live, same as the thumbnail row) should just leave
              // one fewer fragment rather than show a broken-image icon at low
              // opacity, so this hides the element instead of the solid-block
              // fallback the content thumbnails use.
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ))}
          <div className="absolute inset-0" style={{ backgroundImage: visitPaletteTintOverlayBackground(palette) }} />
          <div
            className="absolute inset-0 opacity-[0.03] mix-blend-overlay"
            style={{ backgroundImage: GRAIN_BACKGROUND_IMAGE, backgroundSize: "180px 180px" }}
          />
        </div>

        <div className="flex items-center justify-between shrink-0">
          <div>
            <div className="text-[10px] font-bold tracking-[0.18em] uppercase" style={{ color: "rgba(248,242,229,0.88)" }}>
              Musée d&apos;Orsay
            </div>
            <div className="text-[10px] font-medium tracking-[0.1em] uppercase mt-0.5" style={{ color: "rgba(248,242,229,0.55)" }}>
              Paris · {dateStr}
            </div>
          </div>
          <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold" style={{ background: CREAM, color: "#181714" }}>
            E
          </div>
        </div>

        {/* "The Acquisition Poster" (§10/§14/§6): "YOU SAW" intro, one big
            culmination number, then a serif supporting phrase -- kept as the
            same honest low-high RANGE the rest of this app always shows
            rather than collapsing to a single fabricated point figure the
            way the doc's literal "€3.8B" example does. */}
        <div className="mt-10 shrink-0">
          <div className="font-medium" style={{ fontFamily: "var(--font-editorial)", fontSize: 18, lineHeight: 1.1, color: "#F4EBDD" }}>
            {tt("you_saw_label", state.locale)}
          </div>
          <div
            className="mt-1 font-medium"
            style={
              hasAnyEstimate
                ? { fontFamily: "var(--font-editorial)", fontSize: headlineSize, letterSpacing: "-0.05em", lineHeight: 0.85, color: CREAM }
                : { fontFamily: "var(--font-editorial)", fontSize: 34, letterSpacing: "-0.02em", lineHeight: 1.1, color: CREAM }
            }
          >
            {headlineText}
          </div>
          <div className="mt-2 font-medium" style={{ fontFamily: "var(--font-editorial)", fontSize: 22, letterSpacing: "-0.01em", color: "#F3E8D7", opacity: 0.92 }}>
            {headlineSubtitle}
          </div>
          {valueNote && (
            <div className="text-[11px] mt-1.5" style={{ color: "rgba(243,232,215,0.6)" }}>
              {valueNote}
            </div>
          )}
        </div>

        {/* Stats: three columns, not one sentence -- §6 spec's serif value +
            sans uppercase label pairing. */}
        <div className="mt-8 flex gap-9 shrink-0">
          {[
            [String(seenArtworks.length), worksLabel],
            [String(artists.size), artistsLabel],
            [timeStr, tt("stat_time", state.locale).toLowerCase()],
          ].map(([value, label]) => (
            <div key={label}>
              <div className="font-medium tabular-nums" style={{ fontFamily: "var(--font-editorial)", fontSize: 24, lineHeight: 1.1, color: CREAM }}>
                {value}
              </div>
              <div className="mt-1 text-[9px] font-semibold tracking-[0.1em] uppercase" style={{ color: "rgba(243,232,215,0.75)" }}>
                {label}
              </div>
            </div>
          ))}
        </div>

        {/* Artwork thumbnails: real photos (§14 -- "три изображения, 120-150px
            высотой, ratio ~4:5, radius 8-10px, тонкая светлая border"). Real
            <img> is fine here (unlike the PNG export path further down) --
            no canvas pixel read involved, so Wikimedia's CORS restriction on
            canvas-loading these images never applies to plain on-screen
            display. Each falls back to a solid accent-color block on load
            failure, same convention CardScreen's own hero image already
            uses -- some of these commons.wikimedia.org URLs genuinely 404
            or fail intermittently (observed live), and a blank box reads as
            broken while an accent block reads as intentional. */}
        {palette.works.length > 0 && (
          <div className="mt-8 flex gap-3 shrink-0">
            {palette.works.map((w) => (
              <RecapThumbnail key={w.id} artwork={w} />
            ))}
          </div>
        )}

        {/* Most valuable work, directly on the poster -- no white SaaS card
            (§14: "Не помещать в большую белую SaaS-карточку"). */}
        {mostValuable && (
          <div className="mt-6 shrink-0 flex gap-3.5 items-start">
            {/* Visual anchor -- this block used to be bare text with nothing
                tying it to the artwork; a small thumbnail (same real-photo /
                accent-fallback convention as the row above) gives it the
                same visual weight as the rest of the poster. */}
            <RecapThumbnail artwork={mostValuable} size="small" />
            <div>
              <div className="text-[10px] font-semibold tracking-[0.13em] uppercase" style={{ color: "rgba(243,232,215,0.65)" }}>
                {tt("most_valuable_today", state.locale)}
              </div>
              <div className="mt-1.5 font-medium" style={{ fontFamily: "var(--font-editorial)", fontSize: 20, color: CREAM }}>
                {artworkArtistDisplayName(mostValuable, state.locale)}
              </div>
              <div className="text-[14px]" style={{ fontFamily: "var(--font-editorial)", color: "rgba(243,232,215,0.7)" }}>
                {resolveTitle(mostValuable, state.locale)}
              </div>
              <div className="mt-1 text-[13px] font-medium tabular-nums" style={{ color: "rgba(243,232,215,0.92)" }}>
                {mostValuableAggregate ? `${formatEstimatedValueRange(mostValuableAggregate)} EST.` : tt("estimate_pending", state.locale)}
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
            className="w-full h-[52px] rounded-[14px] text-[15px] font-semibold disabled:opacity-60"
            style={{ background: CREAM, color: "#181714", boxShadow: "0 8px 20px rgba(0,0,0,0.28)" }}
          >
            {imageBusy === "share" ? tt("generating_image", state.locale) : tt("share_your_visit", state.locale)}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={imageBusy !== null}
            className="w-full h-[52px] rounded-[14px] text-[15px] font-semibold disabled:opacity-60"
            style={{ background: "rgba(243,232,215,0.08)", border: "1px solid rgba(243,232,215,0.25)", color: CREAM }}
          >
            {imageBusy === "save" ? tt("generating_image", state.locale) : tt("save_image", state.locale)}
          </button>
          <button type="button" onClick={onNewVisit} className="w-full text-center text-[13px] font-semibold pt-1" style={{ color: "rgba(243,232,215,0.65)" }}>
            {tt("new_visit", state.locale)}
          </button>
          <p className="text-[11px] text-center pt-2" style={{ color: "rgba(243,232,215,0.4)" }}>
            elyio.co / v1.0
          </p>
        </div>
      </div>
    </div>
  );
}

function RecapThumbnail({ artwork, size = "large" }: { artwork: Artwork; size?: "large" | "small" }) {
  const [imgError, setImgError] = useState(false);
  // "small" is the Most Valuable block's visual anchor -- same 4:5 ratio and
  // rounding convention as the large thumbnail row, just sized to sit next
  // to a line of text instead of a full-width row.
  const height = size === "large" ? 132 : 72;
  const shared = { height, aspectRatio: "4 / 5", border: "1px solid rgba(255,255,255,0.18)" } as const;
  // The accent color is the CONTAINER's background, painted on the very
  // first frame -- not a separate branch swapped in only after onError.
  // Wikimedia's CDN doesn't always fail fast: observed live, one image took
  // ~18s to resolve as broken (hanging, not a quick 404/503), and onError
  // only fires once that resolution finally happens. A branch that renders
  // *either* the <img> *or* the fallback div left an empty bordered box for
  // that whole window -- nothing painted underneath the still-pending
  // <img> yet. Layering the real photo on top of the accent color instead
  // means there's never a moment with nothing to show: color from frame
  // one, replaced by the photo if/when it decodes, color remains if it
  // never does.
  return (
    <div className="rounded-[9px] shrink-0 overflow-hidden" style={{ ...shared, background: artwork.accent || "#3A3A3A" }}>
      {!imgError && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={artwork.imageUrl} alt="" className="w-full h-full object-cover" onError={() => setImgError(true)} />
      )}
    </div>
  );
}
