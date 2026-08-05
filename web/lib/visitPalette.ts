import { hexToRgba } from "./cardReveal";
import type { Artwork } from "./types";

// design-direction-v3.md §10 "Recap v3 / Visit Palette": the Recap poster's
// background is built from the 3 most significant seen works, using the
// SAME existing `accent` catalog field Phase 1's Provenance Reveal already
// uses -- not a new dominant-color-extraction system.
//
// "Significant" reuses the ranking RecapScreen already computes for its
// "Most valuable work" card: estimate.high descending, works without a
// reviewed estimate ranked after those with one, scan order as tiebreaker.
export function pickPaletteWorks(seenArtworks: Artwork[]): Artwork[] {
  const withEstimate = seenArtworks.filter((a) => a.estimate.high != null);
  const withoutEstimate = seenArtworks.filter((a) => a.estimate.high == null);
  const ranked = [
    ...withEstimate.slice().sort((a, b) => (b.estimate.high ?? 0) - (a.estimate.high ?? 0)),
    ...withoutEstimate,
  ];
  return ranked.slice(0, 3);
}

// Visual-match rebuild §14: "тёмный editorial collage", not the earlier
// light 3-stop gradient. Base is a near-black warm charcoal (not pure
// black -- the brief's own dark-mode tokens elsewhere in this app use a
// slightly warm off-black, e.g. --color-ink #181714, so this stays
// consistent with that choice rather than reaching for neutral #000).
const DARK_BASE_STOPS = ["#1A1D21", "#131518", "#0D0E10"];

// Accent tint opacities run much higher than the old light-background
// version (was 10-18%) -- muted colors need more presence to read at all
// against a near-black ground. Still nowhere near a saturated wash: these
// are layered UNDER the dark overlay below, which itself fades to 94%
// opaque by the bottom of the frame.
const DARK_TINT_OPACITIES = [0.4, 0.28, 0.16];

// §14's own overlay spec, verbatim: transparent at the top (lets the
// artwork-derived tint/imagery read) to near-opaque at the bottom (keeps
// stats/thumbnails/buttons legible over whatever's behind them).
const DARK_OVERLAY_STOPS: Array<[number, string]> = [
  [0, "rgba(10,19,28,0.10)"],
  [0.5, "rgba(18,20,20,0.55)"],
  [1, "rgba(21,20,18,0.94)"],
];

export interface VisitPalette {
  /** Up to 3 accent hex colors, in significance order. Empty when nothing seen. */
  accents: string[];
  works: Artwork[];
}

export function buildVisitPalette(seenArtworks: Artwork[]): VisitPalette {
  const works = pickPaletteWorks(seenArtworks);
  const raw = works.map((w) => w.accent).filter(Boolean);
  if (raw.length === 0) return { accents: [], works };
  // Repeat the last known accent to still cover 3 gradient stops when fewer
  // than 3 works were seen, so the gradient's direction/shape stays
  // consistent regardless of visit length.
  const filled = [raw[0], raw[1] ?? raw[0], raw[2] ?? raw[raw.length - 1]];
  return { accents: filled, works };
}

/** CSS background-image value for just the near-black base gradient -- no
 * tint, no overlay. Split out from the old combined
 * `visitPaletteCssBackground` so the on-screen version can sandwich the real
 * photo-fragment collage (RecapScreen.tsx) between this base and the tint
 * overlay below; the canvas export (paintVisitPaletteCanvas) has no such
 * photo layer and keeps painting all three in one pass. */
export function visitPaletteBaseBackground(): string {
  return `linear-gradient(180deg, ${DARK_BASE_STOPS[0]} 0%, ${DARK_BASE_STOPS[1]} 55%, ${DARK_BASE_STOPS[2]} 100%)`;
}

/** CSS background-image value for the accent tint + §14 dark overlay only
 * (no base) -- painted on screen on top of the photo-fragment collage so the
 * fragments read as tinted/legible rather than full-color cutouts pasted on
 * the poster. */
export function visitPaletteTintOverlayBackground(palette: VisitPalette): string {
  const overlay = `linear-gradient(180deg, ${DARK_OVERLAY_STOPS.map(([p, c]) => `${c} ${p * 100}%`).join(", ")})`;
  if (palette.accents.length === 0) return overlay;
  const [a, b, c] = palette.accents;
  const [oa, ob, oc] = DARK_TINT_OPACITIES;
  const tint = `linear-gradient(180deg, ${hexToRgba(a, oa)} 0%, ${hexToRgba(b, ob)} 45%, ${hexToRgba(c, oc)} 100%)`;
  return `${overlay}, ${tint}`;
}

/** Canvas equivalent of the three CSS gradient layers above -- same stops,
 * same opacities, drawn as sequential fillRect passes (base first, overlay
 * painted LAST so it's the topmost layer, matching the CSS stacking order)
 * so the exported PNG's background matches the on-screen version. Takes
 * the accent list directly (not a full VisitPalette) since the canvas
 * export path never touches the works' photos -- see
 * paintThumbnailBlocksCanvas's doc comment below for why. */
export function paintVisitPaletteCanvas(
  ctx: CanvasRenderingContext2D,
  accents: string[],
  width: number,
  height: number
): void {
  const base = ctx.createLinearGradient(0, 0, 0, height);
  base.addColorStop(0, DARK_BASE_STOPS[0]);
  base.addColorStop(0.55, DARK_BASE_STOPS[1]);
  base.addColorStop(1, DARK_BASE_STOPS[2]);
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, width, height);

  if (accents.length > 0) {
    const [a, b, c] = accents;
    const [oa, ob, oc] = DARK_TINT_OPACITIES;
    const tint = ctx.createLinearGradient(0, 0, 0, height);
    tint.addColorStop(0, hexToRgba(a, oa));
    tint.addColorStop(0.45, hexToRgba(b, ob));
    tint.addColorStop(1, hexToRgba(c, oc));
    ctx.fillStyle = tint;
    ctx.fillRect(0, 0, width, height);
  }

  const overlay = ctx.createLinearGradient(0, 0, 0, height);
  DARK_OVERLAY_STOPS.forEach(([p, c]) => overlay.addColorStop(p, c));
  ctx.fillStyle = overlay;
  ctx.fillRect(0, 0, width, height);
}

/** Canvas equivalent of the on-screen grain overlay -- a small tile of
 * random low-alpha pixels, tiled across the whole canvas via a repeating
 * pattern (cheaper than per-pixel noise across the full 1080x1920 export). */
export function paintGrainCanvas(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  const tileSize = 64;
  const tile = document.createElement("canvas");
  tile.width = tileSize;
  tile.height = tileSize;
  const tctx = tile.getContext("2d");
  if (!tctx) return;
  const imageData = tctx.createImageData(tileSize, tileSize);
  for (let i = 0; i < imageData.data.length; i += 4) {
    const v = Math.floor(Math.random() * 255);
    imageData.data[i] = v;
    imageData.data[i + 1] = v;
    imageData.data[i + 2] = v;
    imageData.data[i + 3] = 8; // ~3% alpha, matches §14's "grain: 2-3%"
  }
  tctx.putImageData(imageData, 0, 0);
  const pattern = ctx.createPattern(tile, "repeat");
  if (!pattern) return;
  ctx.save();
  // Matches the on-screen grain's mix-blend-mode: overlay -- plain alpha
  // blending would just wash the background out instead of texturing it.
  ctx.globalCompositeOperation = "overlay";
  ctx.fillStyle = pattern;
  ctx.fillRect(0, 0, width, height);
  ctx.restore();
}

/** Canvas stand-in for the on-screen artwork-thumbnail row (§14: "три
 * изображения, 120-150px высотой, ratio ~4:5, radius 8-10px"): real photos
 * on screen (see RecapScreen.tsx), solid accent-color blocks here, at the
 * SAME position/size/radius/border the real thumbnails use -- tested live
 * via fetch(url, {mode:"cors"}) against the actual commons.wikimedia.org
 * redirect chain: it throws (confirmed CORS-blocked, not just the earlier
 * <img crossorigin> test), so this remains the honest choice, not a
 * shortcut. Returns the row's height so the caller's y-accumulator can
 * continue past it. */
export function paintThumbnailBlocksCanvas(
  ctx: CanvasRenderingContext2D,
  accents: string[],
  x: number,
  y: number,
  thumbHeight: number
): number {
  const thumbWidth = thumbHeight * (4 / 5);
  const gap = 14;
  const radius = 22; // canvas-scale equivalent of the on-screen 8-10px at ~2.7x export ratio
  accents.slice(0, 3).forEach((accent, i) => {
    const thumbX = x + i * (thumbWidth + gap);
    ctx.fillStyle = hexToRgba(accent, 0.9);
    ctx.beginPath();
    ctx.roundRect(thumbX, y, thumbWidth, thumbHeight, radius);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.22)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(thumbX, y, thumbWidth, thumbHeight, radius);
    ctx.stroke();
  });
  return thumbHeight;
}

// Self-contained SVG fractal-noise grain, inlined as a data URI -- no
// external asset, matches the doc's "лёгкое grain" over the palette
// background. Used at low opacity with mix-blend-mode: overlay on-screen.
const GRAIN_SVG =
  "<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'>" +
  "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/>" +
  "<feColorMatrix type='matrix' values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.35 0'/></filter>" +
  "<rect width='100%' height='100%' filter='url(%23n)'/></svg>";

export const GRAIN_BACKGROUND_IMAGE = `url("data:image/svg+xml,${GRAIN_SVG}")`;
