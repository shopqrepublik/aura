import { hexToRgba } from "./cardReveal";
import { BACKEND_URL } from "./api";
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

/** Routes a Wikimedia image URL through our own backend's /v1/image-proxy
 * (server-side fetch + 512px resize + on-disk cache, see backend/app/main.py)
 * instead of loading it directly -- canvas.drawImage() refuses cross-origin
 * Wikimedia images outright even with img.crossOrigin set (confirmed live:
 * fetch(url, {mode:"cors"}) against the actual commons.wikimedia.org redirect
 * chain throws), because Wikimedia's CDN doesn't send a CORS header. Our own
 * backend re-serves the same bytes from an origin that does. */
function proxyImageUrl(url: string): string {
  return `${BACKEND_URL}/v1/image-proxy?url=${encodeURIComponent(url)}`;
}

/** Generic crossOrigin-anonymous image loader with a hard timeout -- the
 * export shouldn't hang indefinitely if the backend itself is slow/down
 * (this goes through our own proxy now, not raw Wikimedia, so the ~18s
 * hangs observed there shouldn't recur, but nothing guarantees it). */
function loadImage(url: string, timeoutMs = 8000): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    const timer = setTimeout(() => reject(new Error("image load timed out")), timeoutMs);
    img.onload = () => {
      clearTimeout(timer);
      resolve(img);
    };
    img.onerror = () => {
      clearTimeout(timer);
      reject(new Error("image load failed"));
    };
    img.src = url;
  });
}

/** object-fit: cover equivalent for canvas -- crops the source to the
 * destination's aspect ratio instead of stretching it, matching the
 * on-screen <img className="object-cover"> the real thumbnails use. */
function coverSourceRect(imgWidth: number, imgHeight: number, dstWidth: number, dstHeight: number) {
  const srcRatio = imgWidth / imgHeight;
  const dstRatio = dstWidth / dstHeight;
  let sx = 0, sy = 0, sw = imgWidth, sh = imgHeight;
  if (srcRatio > dstRatio) {
    sw = imgHeight * dstRatio;
    sx = (imgWidth - sw) / 2;
  } else {
    sh = imgWidth / dstRatio;
    sy = (imgHeight - sh) / 2;
  }
  return { sx, sy, sw, sh };
}

/** Canvas version of the on-screen artwork-thumbnail row (§14: "три
 * изображения, 120-150px высотой, ratio ~4:5, radius 8-10px") -- real
 * photos via the image proxy above, same position/size/radius/border the
 * on-screen thumbnails use. Falls back to the honest accent-color block
 * PER ITEM, only on a genuine proxy failure (network down, this specific
 * image genuinely missing) -- not the default path anymore.
 *
 * Loads all items CONCURRENTLY (network-bound, safe to parallelize) but
 * draws them SEQUENTIALLY afterward: ctx.save()/clip()/restore() share one
 * global context stack, and interleaving those calls across concurrently
 * awaited draws (if drawing itself were async, e.g. one `await
 * loadImage()` per item inside a Promise.all) would corrupt that shared
 * stack the moment two items' save/restore pairs overlap out of order.
 * Separating "fetch" from "draw" avoids that entirely while keeping the
 * network round-trips parallel. Returns the row's height so the caller's
 * y-accumulator can continue past it, same contract as before. */
export async function paintThumbnailsCanvas(
  ctx: CanvasRenderingContext2D,
  works: Array<{ imageUrl: string; accent: string }>,
  x: number,
  y: number,
  thumbHeight: number
): Promise<number> {
  const thumbWidth = thumbHeight * (4 / 5);
  const gap = 14;
  const radius = 22; // canvas-scale equivalent of the on-screen 8-10px at ~2.7x export ratio
  const items = works.slice(0, 3);

  const loaded = await Promise.all(
    items.map((work) => loadImage(proxyImageUrl(work.imageUrl)).catch(() => null))
  );

  items.forEach((work, i) => {
    const thumbX = x + i * (thumbWidth + gap);
    const img = loaded[i];
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(thumbX, y, thumbWidth, thumbHeight, radius);
    ctx.clip();
    if (img) {
      const { sx, sy, sw, sh } = coverSourceRect(img.naturalWidth, img.naturalHeight, thumbWidth, thumbHeight);
      ctx.drawImage(img, sx, sy, sw, sh, thumbX, y, thumbWidth, thumbHeight);
    } else {
      ctx.fillStyle = hexToRgba(work.accent, 0.9);
      ctx.fillRect(thumbX, y, thumbWidth, thumbHeight);
    }
    ctx.restore();
    ctx.strokeStyle = "rgba(255,255,255,0.22)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(thumbX, y, thumbWidth, thumbHeight, radius);
    ctx.stroke();
  });

  return thumbHeight;
}

/** Same real-photo-with-accent-fallback approach as paintThumbnailsCanvas
 * above, sized/positioned for the "Most valuable work" anchor instead of
 * the thumbnail row -- see recap-image.ts's call site. Single item, so no
 * concurrency-vs-canvas-state concern, but kept as a separate load-then-draw
 * pair for the same reason (consistency, and so a future caller that adds a
 * second item doesn't reintroduce the interleaving bug). */
export async function paintAnchorThumbnailCanvas(
  ctx: CanvasRenderingContext2D,
  work: { imageUrl: string; accent: string },
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
): Promise<void> {
  const img = await loadImage(proxyImageUrl(work.imageUrl)).catch(() => null);
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
  ctx.clip();
  if (img) {
    const { sx, sy, sw, sh } = coverSourceRect(img.naturalWidth, img.naturalHeight, width, height);
    ctx.drawImage(img, sx, sy, sw, sh, x, y, width, height);
  } else {
    ctx.fillStyle = work.accent || "#3A3A3A";
    ctx.fillRect(x, y, width, height);
  }
  ctx.restore();
  ctx.strokeStyle = "rgba(255,255,255,0.22)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
  ctx.stroke();
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
