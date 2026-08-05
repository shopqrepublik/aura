import { tt } from "@/lib/i18n";
import { paintVisitPaletteCanvas, paintGrainCanvas, paintThumbnailsCanvas, paintAnchorThumbnailCanvas } from "@/lib/visitPalette";
import type { Artwork, Locale } from "@/lib/types";

// Generates the actual shareable PNG for the Recap screen — 1080x1920, per
// the visual-match rebuild §14 ("dark editorial collage" poster). This
// intentionally draws a SUBSET of what's on screen (poster content, not the
// interactive buttons/footer link) — a shared image should show the visit,
// not a picture of a "Share" button.
export const RECAP_IMAGE_WIDTH = 1080;
export const RECAP_IMAGE_HEIGHT = 1920;

const SANS_STACK = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', Inter, 'Helvetica Neue', sans-serif";
// Matches --font-editorial's actual registered family name (next/font
// self-hosts "Cormorant Garamond" -- confirmed live via document.fonts).
// Canvas text doesn't understand CSS custom properties, so the literal
// family name is needed here.
const SERIF_STACK = "'Cormorant Garamond', Georgia, serif";
const CREAM = "#F3E8D7";

// Draws `text` centered on `angleCenter` around the circle at (cx, cy) --
// canvas has no native equivalent of SVG's <textPath>. angle 0 = straight
// up from center (ctx.rotate is clockwise), matching the same top-arc
// convention CollectorsSeal.tsx's SVG path uses, so the exported PNG and
// the on-screen component read identically.
//
// Spaces each character by its OWN measured width (ctx.measureText), not
// by an equal angle per character -- an equal-angle version was tried
// first and produced a visibly uneven gap around "MILESTONE" (narrow
// letters like I got the same angular slot as wide ones, so the run
// visually drifted out of alignment with itself once bold+narrow letters
// mixed together). Real per-glyph widths is what SVG's textPath already
// does automatically; this just replicates that on canvas.
// Picks the largest font size (from `candidates`, descending) at which
// `text` still fits within `maxWidth` -- canvas has no native text-wrap, so
// this is the shrink-to-fit safety net for cumulative totals a very long
// visit could produce (the on-screen version wraps to a 2nd line instead;
// canvas text wrapping needs manual line-splitting, more code than this
// headline -- a handful of digits -- actually needs).
function fitFontSize(ctx: CanvasRenderingContext2D, text: string, font: string, weight: number, candidates: number[], maxWidth: number): number {
  for (const size of candidates) {
    ctx.font = `${weight} ${size}px ${font}`;
    if (ctx.measureText(text).width <= maxWidth) return size;
  }
  return candidates[candidates.length - 1];
}

function drawCircularText(ctx: CanvasRenderingContext2D, text: string, cx: number, cy: number, radius: number, angleCenter: number): void {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const chars = [...text];
  const widths = chars.map((ch) => ctx.measureText(ch).width);
  const totalAngle = widths.reduce((sum, w) => sum + w, 0) / radius;
  let angle = angleCenter - totalAngle / 2;
  for (let i = 0; i < chars.length; i++) {
    const charAngle = angle + widths[i] / 2 / radius;
    ctx.save();
    ctx.rotate(charAngle);
    ctx.translate(0, -radius);
    ctx.fillText(chars[i], 0, 0);
    ctx.restore();
    angle += widths[i] / radius;
  }
  ctx.restore();
}

export interface RecapImageData {
  locale: Locale;
  dateStr: string;
  worksCount: number;
  artistsCount: number;
  timeStr: string;
  hasAnyEstimate: boolean;
  reviewedCount: number;
  totalLow: number;
  totalHigh: number;
  mostValuable: Artwork | null;
  mostValuableHasEstimate: boolean;
  /** Precomputed via lib/artworks.ts's resolveTitle in RecapScreen.tsx --
   * this file doesn't import that module itself, keeping the same "pass
   * derived data in, don't recompute it here" convention the other
   * mostValuable* fields already use. */
  mostValuableTitle: string;
  isBillion: boolean;
  /** design-direction-v3.md §10 "Visit Palette" -- up to 3 accent hex colors
   * from the visit's most significant seen works (RecapScreen computes this
   * via lib/visitPalette.ts's buildVisitPalette, same ranking as
   * mostValuable above). Empty when nothing was seen. */
  paletteAccents: string[];
  /** Same works as paletteAccents is derived from, this time with the
   * imageUrl each needs to actually draw a real photo via the image proxy
   * (see visitPalette.ts's paintThumbnailsCanvas) -- a slim {imageUrl,
   * accent} projection, not the full Artwork, since that's all the canvas
   * painter needs. */
  paletteWorks: Array<{ imageUrl: string; accent: string }>;
}

// The artwork-thumbnail row and most-valuable block draw real photos here
// via our own backend's /v1/image-proxy endpoint (server-side fetch +
// resize + cache, see backend/app/main.py) -- canvas.drawImage() refuses
// cross-origin Wikimedia images outright even with img.crossOrigin set
// (confirmed live: fetch(url, {mode:"cors"}) against the actual
// commons.wikimedia.org redirect chain throws, because Wikimedia's CDN
// doesn't send a CORS header), so a same-origin-as-far-as-the-browser-cares
// proxy was the fix, not a DOM-rendering rewrite (html2canvas et al.) of
// the whole export. paintThumbnailsCanvas/paintAnchorThumbnailCanvas fall
// back to the honest accent-color block per item, but only when the proxy
// itself genuinely fails (network down, this specific image genuinely
// missing) -- that's the rare edge case now, not the default path.
export async function generateRecapImage(data: RecapImageData): Promise<Blob | null> {
  if (typeof document === "undefined") return null;

  // Cormorant Garamond is loaded via next/font on <html>, but canvas text
  // doesn't trigger font loading itself -- it silently falls back if the
  // face isn't ready yet. Every other screen in this app already renders
  // serif text before Recap is reachable, so in practice this resolves
  // instantly from cache, but awaiting it here makes correctness not
  // depend on navigation order.
  if (typeof document.fonts?.load === "function") {
    await document.fonts.load(`500 60px ${SERIF_STACK}`).catch(() => {});
  }

  const canvas = document.createElement("canvas");
  canvas.width = RECAP_IMAGE_WIDTH;
  canvas.height = RECAP_IMAGE_HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const W = RECAP_IMAGE_WIDTH;
  const H = RECAP_IMAGE_HEIGHT;
  const marginX = 64;

  // Visit Palette background — dark accent-tinted gradient + dark overlay +
  // grain, same layering as the on-screen version (lib/visitPalette.ts).
  paintVisitPaletteCanvas(ctx, data.paletteAccents, W, H);
  paintGrainCanvas(ctx, W, H);

  // Header: "MUSÉE D'ORSAY" / "PARIS · date" + cream circular "E" mark.
  ctx.fillStyle = "rgba(248,242,229,0.88)";
  ctx.font = `700 30px ${SANS_STACK}`;
  ctx.textBaseline = "alphabetic";
  ctx.fillText("MUSÉE D'ORSAY", marginX, 150);
  ctx.fillStyle = "rgba(248,242,229,0.55)";
  ctx.font = `500 26px ${SANS_STACK}`;
  ctx.fillText(`PARIS · ${data.dateStr}`.toUpperCase(), marginX, 190);

  ctx.beginPath();
  ctx.arc(W - marginX - 24, 145, 24, 0, Math.PI * 2);
  ctx.fillStyle = CREAM;
  ctx.fill();
  ctx.fillStyle = "#181714";
  ctx.font = `700 22px ${SANS_STACK}`;
  ctx.textAlign = "center";
  ctx.fillText("E", W - marginX - 24, 153);
  ctx.textAlign = "left";

  // "The Acquisition Poster" headline (§10/§14/§6) -- one big culmination
  // number, serif throughout. Kept as the same honest low-high RANGE the
  // rest of this app always shows rather than collapsing to a single
  // fabricated point figure the way the doc's literal "€3.8B" example does.
  const valueText = data.hasAnyEstimate
    ? `€${data.totalLow}–${data.totalHigh}M`
    : tt("pending_review", data.locale);
  const valueNote =
    data.hasAnyEstimate && data.reviewedCount < data.worksCount
      ? tt("value_seen_partial_note", data.locale)
          .replace("{n}", String(data.reviewedCount))
          .replace("{total}", String(data.worksCount))
      : null;

  let y = 290;
  ctx.fillStyle = "#F4EBDD";
  ctx.font = `500 48px ${SERIF_STACK}`;
  ctx.fillText(tt("you_saw_label", data.locale), marginX, y);

  const maxHeadlineWidth = W - marginX * 2;
  const headlineSize = data.hasAnyEstimate
    ? fitFontSize(ctx, valueText, SERIF_STACK, 500, [250, 220, 190, 150], maxHeadlineWidth)
    : 92;
  y += headlineSize * 0.82;
  ctx.fillStyle = CREAM;
  ctx.font = `500 ${headlineSize}px ${SERIF_STACK}`;
  ctx.fillText(valueText, marginX, y);

  y += 66;
  ctx.fillStyle = CREAM;
  ctx.globalAlpha = 0.92;
  ctx.font = `500 58px ${SERIF_STACK}`;
  ctx.fillText(
    data.hasAnyEstimate ? tt("in_estimated_market_value", data.locale) : tt("recap_value_pending_caption", data.locale),
    marginX,
    y
  );
  ctx.globalAlpha = 1;

  if (valueNote) {
    y += 36;
    ctx.fillStyle = "rgba(243,232,215,0.6)";
    ctx.font = `500 24px ${SANS_STACK}`;
    ctx.fillText(valueNote, marginX, y);
  }

  // Stats: three columns (serif value + sans uppercase label), not one
  // sentence -- §6 spec's pairing, mirrors the on-screen version.
  const worksLabel = data.worksCount === 1 ? tt("stat_work_one", data.locale) : tt("works_seen_count", data.locale).toLowerCase();
  const artistsLabel = data.artistsCount === 1 ? tt("stat_artist_one", data.locale) : tt("stat_artists", data.locale).toLowerCase();
  const statCols: Array<[string, string]> = [
    [String(data.worksCount), worksLabel],
    [String(data.artistsCount), artistsLabel],
    [data.timeStr, tt("stat_time", data.locale).toLowerCase()],
  ];
  y += 90;
  let statX = marginX;
  for (const [value, label] of statCols) {
    ctx.fillStyle = CREAM;
    ctx.font = `500 65px ${SERIF_STACK}`;
    ctx.fillText(value, statX, y);
    ctx.fillStyle = "rgba(243,232,215,0.75)";
    ctx.font = `600 24px ${SANS_STACK}`;
    ctx.fillText(label.toUpperCase(), statX, y + 34);
    statX += Math.max(ctx.measureText(value).width, 140) + 60;
  }

  // Artwork thumbnails -- real photos, via the image proxy (see this file's
  // own top-level comment for why that's needed at all).
  y += 70;
  const thumbHeight = 357; // ~132px on-screen * the ~2.7x export scale ratio this file already uses elsewhere
  await paintThumbnailsCanvas(ctx, data.paletteWorks, marginX, y, thumbHeight);
  y += thumbHeight;

  // Most valuable work, directly on the poster -- no white card (§14). Text
  // sits to the right of a small real-photo anchor (same image-proxy path
  // as the thumbnail row above, same accent-color fallback on a genuine
  // proxy failure).
  if (data.mostValuable) {
    y += 56;
    const anchorHeight = 194; // ~72px on-screen small thumbnail * this file's ~2.7x export ratio
    const anchorWidth = anchorHeight * (4 / 5);
    const anchorGap = 38;
    const anchorTop = y - 40;
    const radius = 22;
    await paintAnchorThumbnailCanvas(
      ctx,
      { imageUrl: data.mostValuable.imageUrl, accent: data.mostValuable.accent },
      marginX,
      anchorTop,
      anchorWidth,
      anchorHeight,
      radius
    );

    const textX = marginX + anchorWidth + anchorGap;
    ctx.fillStyle = "rgba(243,232,215,0.65)";
    ctx.font = `600 24px ${SANS_STACK}`;
    ctx.fillText(
      (data.mostValuableHasEstimate ? tt("most_valuable_today", data.locale) : tt("featured_today", data.locale)).toUpperCase(),
      textX,
      y
    );
    y += 54;
    ctx.fillStyle = CREAM;
    ctx.font = `500 46px ${SERIF_STACK}`;
    ctx.fillText(data.mostValuable.artist, textX, y);
    if (data.mostValuableTitle) {
      y += 42;
      ctx.fillStyle = "rgba(243,232,215,0.7)";
      ctx.font = `500 34px ${SERIF_STACK}`;
      ctx.fillText(data.mostValuableTitle, textX, y);
    }
    y += 44;
    ctx.fillStyle = "rgba(243,232,215,0.92)";
    ctx.font = `600 30px ${SANS_STACK}`;
    const estText = data.mostValuableHasEstimate
      ? `€${data.mostValuable.estimate.low}–${data.mostValuable.estimate.high}M EST.`
      : tt("estimate_pending", data.locale);
    ctx.fillText(estText, textX, y);
  }

  // Collector's Seal, only when it's genuinely earned (isBillion is computed
  // by the caller from the real summed estimate, not decorative) --
  // burgundy variant (matches the on-screen CollectorsSeal component, which
  // switched from graphite once the poster background went dark -- see
  // that component's doc comment).
  if (data.isBillion) {
    const radius = 110;
    const cx = marginX + radius;
    const cy = H - 250;

    ctx.fillStyle = "#681E1A";
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(242,213,189,0.22)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, radius - 6, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = "rgba(242,213,189,0.14)";
    ctx.beginPath();
    ctx.arc(cx, cy, radius - 12, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = "rgba(242,213,189,0.85)";
    ctx.font = `600 13px ${SANS_STACK}`;
    drawCircularText(ctx, "ELYIO · CULTURAL MILESTONE · PARIS", cx, cy, radius - 22, 0);

    ctx.textAlign = "center";
    ctx.fillStyle = "#F2D5BD";
    ctx.font = `700 30px ${SANS_STACK}`;
    ctx.fillText("€1B+", cx, cy - 6);
    ctx.fillStyle = "rgba(242,213,189,0.8)";
    ctx.font = `600 15px ${SANS_STACK}`;
    ctx.fillText("VISITOR", cx, cy + 20);
    // dateStr is "DD.MM.YYYY" (formatDate in RecapScreen.tsx) -- the seal
    // uses the same short "DD·MM·YY" form as the doc's own example
    // ("04·08·26"), matching the on-screen CollectorsSeal exactly.
    const [dd, mm, yyyy] = data.dateStr.split(".");
    ctx.fillStyle = "rgba(242,213,189,0.45)";
    ctx.font = `500 13px ${SANS_STACK}`;
    if (dd && mm && yyyy) ctx.fillText(`${dd}·${mm}·${yyyy.slice(-2)}`, cx, cy + 46);
    ctx.textAlign = "left";
  }

  // Footer tagline.
  ctx.fillStyle = "rgba(243,232,215,0.4)";
  ctx.font = `600 26px ${SANS_STACK}`;
  ctx.fillText("elyio.co / v1.0", marginX, H - 80);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/png");
  });
}
