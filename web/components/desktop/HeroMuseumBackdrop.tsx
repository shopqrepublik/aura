import { proxyImageUrl } from "@/lib/visitPalette";
import { ORSAY_CLOCK_IMAGE_URL } from "@/lib/museumTheme";

// Round 6, Block 3b -- "the clock reads too big, ~full-bleed instead of
// confined to roughly 60-65% of the right side; that flattens depth."
// First attempt shrank the image's own physical box (104vw -> 83vw) --
// that put the image's own left edge inside the visible hero and created
// a hard vertical seam where the box simply ended (nothing gradient about
// it). Fixed by going the other way: keep the image itself large enough
// that its physical edge always stays off-canvas (118vw, shifted further
// right via -8vw so even the widened box's left edge clears x=0 at every
// tested viewport), and do the actual "confined to the right ~60-65%"
// shaping entirely through the mask below -- fully transparent through
// the first ~28% of the hero, then a smooth ramp. A gradient can't
// produce a seam; a box edge can.
//
// Same real asset throughout this project (Roman Eisele / Wikimedia CC
// BY-SA 4.0, backlit clock-face silhouette) -- not a different, richer
// full-architecture photo. Filters can push warmth, softness and
// legibility, not add detail (visible iron trusses, hanging lamp) that
// isn't in this specific photo.
//
// aria-hidden: purely decorative (spec §49) -- must not be announced.
export default function HeroMuseumBackdrop() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" style={{ zIndex: 0 }} aria-hidden="true">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={proxyImageUrl(ORSAY_CLOCK_IMAGE_URL, 1200)}
        alt=""
        fetchPriority="high"
        className="absolute select-none"
        style={{
          right: "-8vw",
          top: "-14vh",
          width: "min(118vw, 2150px)",
          height: "auto",
          opacity: 1,
          filter: "sepia(0.35) brightness(1.08) contrast(0.82) blur(13px)",
          // Round 6, Block 3c -- "the bridge is atmospheric light only,
          // there's no architectural presence in the middle third." The
          // glow layer in DesktopShell.tsx is untouched; this mask curve
          // is the only change, retuned to sit at the midpoint of each
          // named band (0-20%:0.05, 20-40%:0.08, 40-55%:0.11, 55-70%:0.18,
          // 70-100%:0.29) with stops placed at each band's center so CSS's
          // linear interpolation between them tracks those targets across
          // the full band, not just at one point in it -- a smooth ramp,
          // not a step function, so it reads as spatial continuity rather
          // than added detail or contrast.
          WebkitMaskImage:
            "linear-gradient(to right, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.05) 10%, rgba(0,0,0,0.08) 30%, rgba(0,0,0,0.11) 47.5%, rgba(0,0,0,0.18) 62.5%, rgba(0,0,0,0.29) 85%, rgba(0,0,0,0.29) 100%)",
          maskImage:
            "linear-gradient(to right, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.05) 10%, rgba(0,0,0,0.08) 30%, rgba(0,0,0,0.11) 47.5%, rgba(0,0,0,0.18) 62.5%, rgba(0,0,0,0.29) 85%, rgba(0,0,0,0.29) 100%)",
        }}
      />
    </div>
  );
}
