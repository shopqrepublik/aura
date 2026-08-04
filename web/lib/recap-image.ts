import { tt } from "@/lib/i18n";
import { paintVisitPaletteCanvas, paintGrainCanvas, paintFragmentsCanvas } from "@/lib/visitPalette";
import type { Artwork, Locale } from "@/lib/types";

// Generates the actual shareable PNG for the Recap screen — 1080x1920, per
// the design system's "05 VISIT RECAP VIRAL" spec. This intentionally draws
// a SUBSET of what's on screen (stats, most-valuable card, branding) and
// skips the interactive buttons/footer link, the same split the original
// vanilla-JS canvas recap (frontend/app.js renderRecap()) used — a shared
// image should show the visit, not a picture of a "Share" button.
export const RECAP_IMAGE_WIDTH = 1080;
export const RECAP_IMAGE_HEIGHT = 1920;

const FONT_STACK = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', Inter, 'Helvetica Neue', sans-serif";

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
  isBillion: boolean;
  /** design-direction-v3.md §10 "Visit Palette" -- up to 3 accent hex colors
   * from the visit's most significant seen works (RecapScreen computes this
   * via lib/visitPalette.ts's buildVisitPalette, same ranking as
   * mostValuable above). Empty when nothing was seen. */
  paletteAccents: string[];
}

// The most-valuable card's thumbnail is always a solid accent-color block,
// never the artwork's real photo — matching both the design system's own
// "05 VISIT RECAP VIRAL" spec (thumb ... bg #FFD8A8, a color, not a photo)
// and the original vanilla-JS canvas recap (frontend/app.js), which did the
// same. This isn't a shortcut: every artwork's imageUrl is an http://
// commons.wikimedia.org/wiki/Special:FilePath/... redirect chain, and a
// canvas-safe crossOrigin="anonymous" <img> load of that chain fails in
// Chrome (verified live — the redirect hops don't carry
// Access-Control-Allow-Origin, only the final response does, which anonymous
// CORS mode rejects). A solid color block is the reliable choice, not a
// fallback for a rare failure.
export async function generateRecapImage(data: RecapImageData): Promise<Blob | null> {
  if (typeof document === "undefined") return null;

  const canvas = document.createElement("canvas");
  canvas.width = RECAP_IMAGE_WIDTH;
  canvas.height = RECAP_IMAGE_HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const W = RECAP_IMAGE_WIDTH;
  const H = RECAP_IMAGE_HEIGHT;
  const marginX = 64;

  // Visit Palette background — same muted accent-tint-over-neutral-base
  // layering as the on-screen version (lib/visitPalette.ts), plus grain and
  // abstract accent-color fragments standing in for the on-screen photo
  // collage (see paintFragmentsCanvas's doc comment for why this path can't
  // use the real photos).
  paintVisitPaletteCanvas(ctx, data.paletteAccents, W, H);
  paintFragmentsCanvas(ctx, data.paletteAccents, W, H);
  paintGrainCanvas(ctx, W, H);

  // Header: "ELYIO • date" + black circular "E" mark.
  ctx.fillStyle = "#8E8E93";
  ctx.font = `700 26px ${FONT_STACK}`;
  ctx.textBaseline = "alphabetic";
  ctx.fillText(`ELYIO • ${data.dateStr}`.toUpperCase(), marginX, 150);

  ctx.beginPath();
  ctx.arc(W - marginX - 24, 138, 24, 0, Math.PI * 2);
  ctx.fillStyle = "#111111";
  ctx.fill();
  ctx.fillStyle = "#FFFFFF";
  ctx.font = `700 22px ${FONT_STACK}`;
  ctx.textAlign = "center";
  ctx.fillText("E", W - marginX - 24, 146);
  ctx.textAlign = "left";

  // Title + subtitle.
  ctx.fillStyle = "#111111";
  ctx.font = `700 64px ${FONT_STACK}`;
  ctx.fillText(tt("my_visit_title", data.locale), marginX, 280);

  ctx.fillStyle = "#6E6E73";
  ctx.font = `500 34px ${FONT_STACK}`;
  ctx.fillText(
    `${data.worksCount} ${tt("works_seen_count", data.locale).toLowerCase()} • ${data.timeStr} • Musée d'Orsay`,
    marginX,
    334
  );

  // Stat rows: Works / Artists / Value seen / Time — mirrors the on-screen
  // list, including the honest "N of M works reviewed" note when the value
  // total only covers some of what was scanned.
  const valueText = data.hasAnyEstimate
    ? `€${data.totalLow}–${data.totalHigh}M`
    : tt("pending_review", data.locale);
  const valueNote =
    data.hasAnyEstimate && data.reviewedCount < data.worksCount
      ? tt("value_seen_partial_note", data.locale)
          .replace("{n}", String(data.reviewedCount))
          .replace("{total}", String(data.worksCount))
      : null;

  const rows: Array<[string, string, string | null]> = [
    [tt("works_seen_count", data.locale), String(data.worksCount), null],
    [tt("stat_artists", data.locale), String(data.artistsCount), null],
    [tt("stat_value_seen", data.locale), valueText, valueNote],
    [tt("stat_time", data.locale), data.timeStr, null],
  ];

  let y = 470;
  const rowH = 132;
  for (const [label, value, note] of rows) {
    ctx.strokeStyle = "rgba(0,0,0,0.1)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(marginX, y);
    ctx.lineTo(W - marginX, y);
    ctx.stroke();

    ctx.fillStyle = "#8E8E93";
    ctx.font = `600 28px ${FONT_STACK}`;
    ctx.fillText(label.toUpperCase(), marginX, y - 40);

    ctx.fillStyle = "#111111";
    ctx.font = `700 56px ${FONT_STACK}`;
    ctx.textAlign = "right";
    ctx.fillText(value, W - marginX, y - 30);
    ctx.textAlign = "left";

    if (note) {
      ctx.fillStyle = "#8E8E93";
      ctx.font = `500 24px ${FONT_STACK}`;
      ctx.textAlign = "right";
      ctx.fillText(note, W - marginX, y + 4);
      ctx.textAlign = "left";
    }

    y += rowH;
  }

  // Most valuable / featured card.
  if (data.mostValuable) {
    const cardY = y + 20;
    const cardH = 220;
    const cardX = marginX;
    const cardW = W - marginX * 2;

    ctx.save();
    ctx.shadowColor = "rgba(0,0,0,0.08)";
    ctx.shadowBlur = 24;
    ctx.shadowOffsetY = 8;
    ctx.fillStyle = "#FFFFFF";
    ctx.beginPath();
    ctx.roundRect(cardX, cardY, cardW, cardH, 28);
    ctx.fill();
    ctx.restore();

    const thumbSize = 148;
    const thumbX = cardX + 36;
    const thumbY = cardY + (cardH - thumbSize) / 2;
    ctx.fillStyle = data.mostValuable.accent || "#FFD8A8";
    ctx.beginPath();
    ctx.roundRect(thumbX, thumbY, thumbSize, thumbSize, 20);
    ctx.fill();

    const textX = thumbX + thumbSize + 32;
    ctx.fillStyle = "#8E8E93";
    ctx.font = `600 24px ${FONT_STACK}`;
    ctx.fillText(
      (data.mostValuableHasEstimate ? tt("most_valuable_today", data.locale) : tt("featured_today", data.locale)).toUpperCase(),
      textX,
      cardY + 78
    );

    ctx.fillStyle = "#111111";
    ctx.font = `700 34px ${FONT_STACK}`;
    const estText = data.mostValuableHasEstimate
      ? `€${data.mostValuable.estimate.low}–${data.mostValuable.estimate.high}M EST.`
      : tt("estimate_pending", data.locale);
    ctx.fillText(`${data.mostValuable.artist} • ${estText}`, textX, cardY + 126);

    y = cardY + cardH;
  }

  // Collector's Seal, only when it's genuinely earned (isBillion is computed
  // by the caller from the real summed estimate, not decorative) --
  // replaces the old flat red pill. Same circular-stamp design as the
  // on-screen CollectorsSeal component (graphite, double hairline ring, top
  // arc of circumference text, fixed non-localized stamp text -- see that
  // component's doc comment for why it isn't run through tt()).
  if (data.isBillion) {
    const radius = 110;
    const cx = marginX + radius;
    const cy = H - 250;

    ctx.fillStyle = "#1B1B1D";
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.16)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, radius - 6, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.beginPath();
    ctx.arc(cx, cy, radius - 12, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = "rgba(255,255,255,0.8)";
    ctx.font = `600 13px ${FONT_STACK}`;
    drawCircularText(ctx, "ELYIO · CULTURAL MILESTONE · PARIS", cx, cy, radius - 22, 0);

    ctx.textAlign = "center";
    ctx.fillStyle = "#FFFFFF";
    ctx.font = `700 30px ${FONT_STACK}`;
    ctx.fillText("€1B+", cx, cy - 6);
    ctx.fillStyle = "rgba(255,255,255,0.78)";
    ctx.font = `600 15px ${FONT_STACK}`;
    ctx.fillText("VISITOR", cx, cy + 20);
    // dateStr is "DD.MM.YYYY" (formatDate in RecapScreen.tsx) -- the seal
    // uses the same short "DD·MM·YY" form as the doc's own example
    // ("04·08·26"), matching the on-screen CollectorsSeal exactly.
    const [dd, mm, yyyy] = data.dateStr.split(".");
    ctx.fillStyle = "rgba(255,255,255,0.42)";
    ctx.font = `500 13px ${FONT_STACK}`;
    if (dd && mm && yyyy) ctx.fillText(`${dd}·${mm}·${yyyy.slice(-2)}`, cx, cy + 46);
    ctx.textAlign = "left";
  }

  // Footer tagline.
  ctx.fillStyle = "rgba(17,17,17,0.35)";
  ctx.font = `600 26px ${FONT_STACK}`;
  ctx.fillText("elyio.co / v1.0", marginX, H - 80);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/png");
  });
}
