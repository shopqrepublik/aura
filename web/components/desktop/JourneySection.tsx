import { getArtwork, resolveTitle } from "@/lib/artworks";
import { proxyImageUrl } from "@/lib/visitPalette";
import { getArtworkValueReveal } from "@/lib/valueReveal";
import ProvenanceReveal from "@/components/ui/ProvenanceReveal";
import { tt } from "@/lib/i18n";
import { artworkArtistDisplayName } from "@/lib/artist-display";
import type { Locale } from "@/lib/types";

// Round 6, Block 4 -- Journey is deliberately NOT hero language. The brief
// draws a hard line: hero = emotion (atmosphere, glow, one big scene),
// Journey = explanation (gallery wayfinding, calm information
// architecture). Concretely that means no glow, no gradients, no
// drop-shadows, no viewfinder-bracket/camera-app motifs -- a quiet framed
// "plate" + plain caption, the way a printed museum guide presents a
// figure, not an app feature card. All three chapters reuse the same real
// artwork (Starry Night Over the Rhone) so the section reads as one
// example encountered three ways, not three unrelated stock photos.
const JOURNEY_ARTWORK_ID = "orsay_rf_1975_19";

// Smaller than the hero-adjacent rounds' 180x112 -- Journey is capped at
// "max 15% of the hero's visual intensity," and part of reading as quiet
// information rather than a feature card is simply taking up less room.
const PLATE_W = 160;
const PLATE_H = 100;
const REVEAL_SOURCE_W = 340;
const REVEAL_SCALE = PLATE_W / REVEAL_SOURCE_W;

const NUMBER_STYLE = { fontSize: 11, fontWeight: 600, letterSpacing: "0.14em", color: "#9C9284" } as const;
const TITLE_STYLE = { fontFamily: "var(--font-editorial)", fontWeight: 400, fontSize: 22, lineHeight: 1.1, color: "var(--desktop-ink)" } as const;
const BODY_STYLE = { fontSize: 13, lineHeight: 1.65, color: "#716A61" } as const;
const CAPTION_STYLE = { fontSize: 10.5, color: "#9C9284", letterSpacing: "0.01em" } as const;

// Thin 1px rule instead of a gap -- "thin dividers" as the section's own
// separators, in place of the hero's gradients/glow.
const DIVIDER_STYLE = { borderLeft: "1px solid rgba(28,26,22,0.11)" } as const;

// A plain bordered frame ("printed, not digital") -- no radius worth
// naming, no shadow, a light desaturation instead of the hero's warmth.
function Plate({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="overflow-hidden"
      style={{ width: PLATE_W, height: PLATE_H, border: "1px solid rgba(28,26,22,0.14)", borderRadius: 3 }}
    >
      {children}
    </div>
  );
}

export default function JourneySection({ locale }: { locale: Locale }) {
  const artwork = getArtwork(JOURNEY_ARTWORK_ID);
  if (!artwork) return null;
  const title = resolveTitle(artwork, locale);
  const caption = `${artworkArtistDisplayName(artwork, locale)} — ${title}`;

  const steps = [
    {
      number: "01",
      title: tt("desktop_journey_scan_title", locale),
      body: tt("desktop_journey_scan_body", locale),
      plate: (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={proxyImageUrl(artwork.imageUrl)}
          alt=""
          className="w-full h-full object-cover"
          style={{ filter: "saturate(0.82) sepia(0.04)" }}
        />
      ),
    },
    {
      number: "02",
      title: tt("desktop_journey_understand_title", locale),
      body: tt("desktop_journey_understand_body", locale),
      plate: (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={proxyImageUrl(artwork.imageUrl)}
          alt={title}
          className="w-full h-full object-cover"
          style={{ filter: "saturate(0.82) sepia(0.04)" }}
        />
      ),
    },
    {
      number: "03",
      title: tt("desktop_journey_reveal_title", locale),
      body: tt("desktop_journey_reveal_body", locale),
      plate: (
        <div style={{ width: REVEAL_SOURCE_W, transform: `scale(${REVEAL_SCALE})`, transformOrigin: "top left", filter: "saturate(0.85)" }}>
          <div style={{ marginTop: -60 }}>
            <ProvenanceReveal
              valueReveal={getArtworkValueReveal(artwork)}
              accent={artwork.accent}
              comparableSalesCount={artwork.estimate.comparableSales?.length}
              inventoryNumber={artwork.inventoryNumber}
              locale={locale}
              mode="normal"
            />
          </div>
        </div>
      ),
    },
  ];

  return (
    // id: real scroll target for the header nav's "How it works"/
    // "Experience" links (DesktopHeader.tsx) -- both point here, there's
    // no separate section for either label yet.
    <section id="journey" style={{ padding: "48px 0 24px", borderTop: "1px solid rgba(28,26,22,0.08)" }}>
      <div className="mx-auto" style={{ width: "min(1200px, calc(100vw - 128px))" }}>
        <div className="text-[10px] font-semibold tracking-[0.18em] uppercase" style={{ color: "#9C9284", marginBottom: 40 }}>
          {tt("desktop_journey_eyebrow", locale)}
        </div>

        <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          {steps.map((step, i) => (
            <div key={step.number} style={i === 0 ? { paddingRight: 44 } : { ...DIVIDER_STYLE, padding: "0 44px" }}>
              <div style={NUMBER_STYLE}>{step.number}</div>
              <div style={{ ...TITLE_STYLE, marginTop: 2 }}>{step.title}</div>
              <p style={{ ...BODY_STYLE, marginTop: 4, maxWidth: 260 }}>{step.body}</p>
              <div style={{ marginTop: 18 }}>
                <Plate>{step.plate}</Plate>
                <div style={{ ...CAPTION_STYLE, marginTop: 4 }}>{caption}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
