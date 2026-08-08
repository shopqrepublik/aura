import { ArrowRight } from "lucide-react";
import { getArtwork } from "@/lib/artworks";
import { proxyImageUrl } from "@/lib/visitPalette";
import CollectorsSeal from "@/components/ui/CollectorsSeal";
import { tt } from "@/lib/i18n";
import type { Locale } from "@/lib/types";

// Same real 11-work set app/design/page.tsx's own showcase already uses to
// demonstrate the real "isBillion" milestone state (sums to a real
// ~€1045M, genuinely crossing the €1B threshold RecapScreen.tsx gates
// CollectorsSeal on). Kept real through the round-4 art-direction pass
// despite that round's prompt asking for the reference mockup's literal
// "€3.8B / 37 works / 14 artists / 2h 14m" -- those are invented figures
// (RecapScreen.tsx's own comment: the entire 101-work catalog only sums to
// ~€2.94B, so €3.8B isn't reachable with any real subset of it), and the
// original desktop-rebuild brief's own §74 explicitly lists "claim market
// valuation data that does not exist" under "what MUST NOT happen." "Time
// spent" stays dropped -- there's no real elapsed time for a static
// marketing demo to report.
const RECAP_DEMO_IDS = [
  "orsay_rf_2511", "orsay_rf_1975_19", "orsay_rf_2765", "orsay_rf_1961_6",
  "orsay_rf_2739", "orsay_rf_1668", "orsay_rf_644", "orsay_rf_1951_42",
  "orsay_rf_1949_17", "orsay_rf_2718", "orsay_rf_1944_9",
];

export default function RecapStrip({ locale }: { locale: Locale }) {
  const works = RECAP_DEMO_IDS.map((id) => getArtwork(id)).filter((w): w is NonNullable<typeof w> => !!w);
  if (works.length === 0) return null;

  const artists = new Set(works.map((w) => w.artist));
  const totalLow = works.reduce((s, w) => s + (w.estimate.low || 0), 0);
  const totalHigh = works.reduce((s, w) => s + (w.estimate.high || 0), 0);
  const heroWork = works[0];

  return (
    // Top padding tightened 18->10 -- combined with JourneySection's own
    // bottom padding (14px), that's a 24px Journey-bottom-to-Recap-top
    // gap, matching the requested 18-24px range instead of round 4's ~40px.
    <section style={{ padding: "10px 0 38px" }}>
      <div
        className="mx-auto relative overflow-hidden rounded-[16px]"
        style={{ width: "calc(100% - 56px)", maxWidth: 1500, minHeight: 154 }}
      >
        <div className="absolute inset-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={proxyImageUrl(heroWork.imageUrl, 1200)} alt="" className="w-full h-full object-cover" />
          {/* Lighter than round 3 (was rgba(...,.92)/(...,.84)) -- round 3
              read as a near-opaque banner instead of a luminous painting
              with legible texture underneath, per feedback. */}
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(90deg, rgba(16,26,32,0.83), rgba(21,30,34,0.77))" }}
          />
        </div>

        <div className="relative z-10 flex items-center justify-between gap-8 px-10 py-7 flex-wrap">
          <div>
            <div className="text-[9px] font-semibold tracking-[0.16em] uppercase" style={{ color: "rgba(239,226,206,0.8)" }}>
              {tt("desktop_recap_eyebrow", locale)}
            </div>
            <div style={{ fontFamily: "var(--font-editorial)", fontSize: 42, lineHeight: 0.95, color: "#EFE2CE" }}>
              {tt("desktop_recap_you_saw", locale)} €{totalLow}–{totalHigh}M {tt("desktop_recap_of_art", locale)}
            </div>
            <p className="mt-1 text-[13px]" style={{ color: "rgba(243,232,215,0.72)" }}>
              {tt("desktop_recap_sub", locale)}
            </p>
          </div>

          <div className="flex items-center gap-7">
            <div>
              <div style={{ fontFamily: "var(--font-editorial)", fontSize: 34, lineHeight: 1, color: "#F0E4D2" }}>{works.length}</div>
              <div className="text-[8px] uppercase tracking-[0.12em]" style={{ color: "rgba(240,228,210,0.66)" }}>
                {tt("works_seen_count", locale)}
              </div>
            </div>
            <div>
              <div style={{ fontFamily: "var(--font-editorial)", fontSize: 34, lineHeight: 1, color: "#F0E4D2" }}>{artists.size}</div>
              <div className="text-[8px] uppercase tracking-[0.12em]" style={{ color: "rgba(240,228,210,0.66)" }}>
                {tt("stat_artists", locale)}
              </div>
            </div>
            {/* timestamp=null: static marketing demo, not a real visit --
                see JourneySection/RecapStrip's own file comments for why
                a fake Date.now() isn't used here either. */}
            <CollectorsSeal timestamp={null} locale={locale} size={96} />
            <button
              type="button"
              className="h-[44px] px-5 rounded-[12px] flex items-center gap-2 text-[13px] font-medium shrink-0"
              style={{
                background: "rgba(16,21,22,0.18)",
                border: "1px solid rgba(240,230,214,0.28)",
                color: "#F3E7D4",
              }}
            >
              {tt("desktop_recap_view", locale)}
              <ArrowRight className="w-[14px] h-[14px]" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
