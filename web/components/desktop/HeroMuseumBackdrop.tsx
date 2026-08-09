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
          top: "-6vh",
          width: "min(118vw, 2150px)",
          height: "auto",
          opacity: 1,
          filter: "sepia(0.35) brightness(1.08) contrast(0.82) blur(11px)",
          // Round 6, Block 5 -- the source photo's dial is centered
          // roughly where the phone itself now sits (confirmed by
          // inspecting the raw asset), so the phone already covers the
          // dial's hub -- correct per "clock's visual center behind the
          // phone." What was missing is the RING around that hub staying
          // visible past the phone's edges: it's a thin band once the
          // phone is this big, and at the old 13px blur it dissolved into
          // indistinct haze instead of reading as a clock. Blur eased to
          // 9px for more ring definition, and the 40-70% band (directly
          // flanking/above the phone) boosted well past the other rounds'
          // values so that ring actually registers.
          WebkitMaskImage:
            "linear-gradient(to right, rgba(0,0,0,0.07) 0%, rgba(0,0,0,0.07) 10%, rgba(0,0,0,0.12) 30%, rgba(0,0,0,0.18) 47.5%, rgba(0,0,0,0.26) 62.5%, rgba(0,0,0,0.34) 85%, rgba(0,0,0,0.34) 100%)",
          maskImage:
            "linear-gradient(to right, rgba(0,0,0,0.07) 0%, rgba(0,0,0,0.07) 10%, rgba(0,0,0,0.12) 30%, rgba(0,0,0,0.18) 47.5%, rgba(0,0,0,0.26) 62.5%, rgba(0,0,0,0.34) 85%, rgba(0,0,0,0.34) 100%)",
        }}
      />
    </div>
  );
}
