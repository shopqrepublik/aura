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

const BASE_STOPS = ["#FFFFFF", "#F5F5F7", "#EDEEF2"];

// Deliberately restrained opacities -- design-direction-v3.md explicitly
// rules out a vivid poster background for Recap ("Ни Bank Statement, ни
// яркий Spotify Wrapped"), the same anti-vividness constraint Phase 1
// applied to the Provenance Reveal tint (5-9%). These run a little higher
// (10-18%) since the Visit Palette is a full-bleed background rather than
// a small card, but stay far short of a saturated poster wash.
const TINT_OPACITIES = [0.18, 0.14, 0.1];

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

/** CSS background-image value: a muted accent-tint gradient layered over the
 * existing neutral 3-stop base (same base RecapScreen always used), as two
 * comma-separated linear-gradient layers -- no per-pixel color math needed
 * on the CSS side. */
export function visitPaletteCssBackground(palette: VisitPalette): string {
  const base = `linear-gradient(180deg, ${BASE_STOPS[0]} 0%, ${BASE_STOPS[1]} 55%, ${BASE_STOPS[2]} 100%)`;
  if (palette.accents.length === 0) return base;
  const [a, b, c] = palette.accents;
  const [oa, ob, oc] = TINT_OPACITIES;
  const tint = `linear-gradient(160deg, ${hexToRgba(a, oa)} 0%, ${hexToRgba(b, ob)} 46%, ${hexToRgba(c, oc)} 100%)`;
  return `${tint}, ${base}`;
}

/** Canvas equivalent of the two CSS gradient layers above -- same stops,
 * same opacities, drawn as two sequential fillRect passes so the exported
 * PNG's background matches the on-screen version. Takes the accent list
 * directly (not a full VisitPalette) since the canvas export path never
 * touches the works' photos -- see FRAGMENT_LAYOUT's doc comment below for
 * why. */
export function paintVisitPaletteCanvas(
  ctx: CanvasRenderingContext2D,
  accents: string[],
  width: number,
  height: number
): void {
  const base = ctx.createLinearGradient(0, 0, 0, height);
  base.addColorStop(0, BASE_STOPS[0]);
  base.addColorStop(0.55, BASE_STOPS[1]);
  base.addColorStop(1, BASE_STOPS[2]);
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, width, height);

  if (accents.length === 0) return;
  const [a, b, c] = accents;
  const [oa, ob, oc] = TINT_OPACITIES;
  const tint = ctx.createLinearGradient(width * 0.15, 0, width * 0.85, height);
  tint.addColorStop(0, hexToRgba(a, oa));
  tint.addColorStop(0.46, hexToRgba(b, ob));
  tint.addColorStop(1, hexToRgba(c, oc));
  ctx.fillStyle = tint;
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
    imageData.data[i + 3] = 14; // ~5.5% alpha, matches the on-screen grain's 0.05 opacity
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

/** Canvas stand-in for the on-screen "cropped photo fragments" collage --
 * abstract translucent rotated rounded rects in each work's accent color,
 * NOT real photos. See this file's export comment on FRAGMENT_LAYOUT: the
 * PNG export already can't canvas-load these artworks' commons.wikimedia.org
 * images (crossOrigin fails partway through their redirect chain), so this
 * reuses generateRecapImage's existing solid-accent-color-block technique
 * rather than inventing a new one. */
export function paintFragmentsCanvas(ctx: CanvasRenderingContext2D, accents: string[], width: number, height: number): void {
  const shapes: Array<{ x: number; y: number; w: number; h: number; rotate: number }> = [
    { x: width * 0.72, y: height * 0.06, w: 340, h: 430, rotate: 8 },
    { x: -80, y: height * 0.4, w: 300, h: 400, rotate: -6 },
    { x: width * 0.78, y: height * 0.7, w: 280, h: 360, rotate: 4 },
  ];
  accents.slice(0, 3).forEach((accent, i) => {
    const shape = shapes[i];
    if (!shape) return;
    ctx.save();
    ctx.translate(shape.x + shape.w / 2, shape.y + shape.h / 2);
    ctx.rotate((shape.rotate * Math.PI) / 180);
    ctx.fillStyle = hexToRgba(accent, 0.1);
    ctx.beginPath();
    ctx.roundRect(-shape.w / 2, -shape.h / 2, shape.w, shape.h, 32);
    ctx.fill();
    ctx.restore();
  });
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

// design-direction-v3.md §10.5: "2-3 cropped fragments картин как музейный
// коллаж". On-screen this uses the works' real imageUrl (plain <img>
// elements, no canvas pixel read involved). The PNG export path
// (recap-image.ts) deliberately does NOT do the same with real photos: this
// codebase already established, in generateRecapImage's own most-valuable
// thumbnail, that a canvas-safe crossOrigin="anonymous" load of these
// commons.wikimedia.org URLs fails (the redirect chain doesn't carry
// Access-Control-Allow-Origin on every hop) -- so the export instead reuses
// that file's existing solid-accent-color-block technique for its
// "fragments", not a new workaround.
export const FRAGMENT_LAYOUT: Array<{ top: string; left?: string; right?: string; width: number; height: number; rotate: number }> = [
  { top: "4%", right: "-8%", width: 220, height: 280, rotate: 8 },
  { top: "38%", left: "-10%", width: 200, height: 260, rotate: -6 },
  { top: "68%", right: "-6%", width: 180, height: 230, rotate: 4 },
];
