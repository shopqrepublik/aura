import { paintGrainCanvas, paintVisitPaletteCanvas, proxyImageUrl } from "@/lib/visitPalette";
import type { Artwork, Locale } from "@/lib/types";
import type { VisitValueMoment } from "@/lib/visit-game";

export const RECAP_IMAGE_WIDTH = 1080;
export const RECAP_IMAGE_HEIGHT = 1920;

const SANS_STACK = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', Inter, 'Helvetica Neue', sans-serif";
const SERIF_STACK = "'Cormorant Garamond', Georgia, serif";
const CREAM = "#F3E8D7";
const INK = "#181714";

export interface RecapImageData {
  locale: Locale;
  museumName: string;
  museumLocation: string;
  headline: string;
  dateStr: string;
  worksCount: number;
  artistsCount: number;
  timeStr: string;
  favoriteArtwork: Artwork | null;
  heroArtwork: Artwork | null;
  favoriteArtist: string;
  favoriteTitle: string;
  valueMoment: VisitValueMoment;
  achievementTitle: string;
  achievementIcon: string;
  paletteAccents: string[];
  paletteWorks: Array<{ imageUrl: string; accent: string }>;
}

export async function generateRecapImage(data: RecapImageData): Promise<Blob | null> {
  if (typeof document === "undefined") return null;
  if (typeof document.fonts?.load === "function") {
    await document.fonts.load(`500 80px ${SERIF_STACK}`).catch(() => {});
    await document.fonts.load(`700 36px ${SANS_STACK}`).catch(() => {});
  }

  const canvas = document.createElement("canvas");
  canvas.width = RECAP_IMAGE_WIDTH;
  canvas.height = RECAP_IMAGE_HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const W = RECAP_IMAGE_WIDTH;
  const H = RECAP_IMAGE_HEIGHT;
  const margin = 72;

  paintVisitPaletteCanvas(ctx, data.paletteAccents, W, H);
  await paintHero(ctx, data, W, H);
  paintGrainCanvas(ctx, W, H);

  ctx.fillStyle = "rgba(8,7,6,0.18)";
  ctx.fillRect(0, 0, W, H);

  drawHeader(ctx, data, margin);
  drawHeadline(ctx, data, margin);
  drawStats(ctx, data, margin);
  drawFavorite(ctx, data, margin);
  drawValueMoment(ctx, data, margin);
  drawAchievement(ctx, data, margin);
  drawFooter(ctx, margin, W, H);

  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), "image/png"));
}

async function paintHero(ctx: CanvasRenderingContext2D, data: RecapImageData, width: number, height: number): Promise<void> {
  const artwork = data.favoriteArtwork || data.heroArtwork;
  const heroHeight = 820;
  if (artwork?.imageUrl) {
    try {
      const url = /^https?:\/\/(upload|commons)\.wikimedia\.org\//i.test(artwork.imageUrl)
        ? proxyImageUrl(artwork.imageUrl, 1600)
        : artwork.imageUrl;
      const img = await loadImage(url, 7000);
      drawCover(ctx, img, 0, 0, width, heroHeight);
      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, "rgba(8,7,6,0.08)");
      gradient.addColorStop(0.38, "rgba(8,7,6,0.25)");
      gradient.addColorStop(0.58, "rgba(8,7,6,0.76)");
      gradient.addColorStop(1, "rgba(8,7,6,0.98)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);
      return;
    } catch {
      // Fall through to editorial fallback.
    }
  }

  const accent = artwork?.accent || data.paletteAccents[0] || "#725E47";
  const g = ctx.createRadialGradient(width * 0.25, height * 0.12, 40, width * 0.5, height * 0.24, width * 0.8);
  g.addColorStop(0, accent);
  g.addColorStop(0.55, "#2E302A");
  g.addColorStop(1, "#0E0D0B");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(243,232,215,0.10)";
  ctx.lineWidth = 2;
  for (let i = 0; i < 9; i++) {
    ctx.beginPath();
    ctx.ellipse(width * 0.5, 310 + i * 18, 340 - i * 20, 90 + i * 7, -0.08, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawHeader(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  ctx.fillStyle = "rgba(248,242,229,0.88)";
  ctx.font = `700 28px ${SANS_STACK}`;
  ctx.textBaseline = "alphabetic";
  fillFitText(ctx, data.museumName.toUpperCase(), margin, 130, 760, 28, SANS_STACK, 700);
  ctx.fillStyle = "rgba(248,242,229,0.58)";
  ctx.font = `600 23px ${SANS_STACK}`;
  const location = [data.museumLocation, data.dateStr].filter(Boolean).join(" · ");
  fillFitText(ctx, location.toUpperCase(), margin, 168, 720, 23, SANS_STACK, 600);

  ctx.beginPath();
  ctx.arc(RECAP_IMAGE_WIDTH - margin - 28, 128, 28, 0, Math.PI * 2);
  ctx.fillStyle = CREAM;
  ctx.fill();
  ctx.fillStyle = INK;
  ctx.font = `800 23px ${SANS_STACK}`;
  ctx.textAlign = "center";
  ctx.fillText("E", RECAP_IMAGE_WIDTH - margin - 28, 137);
  ctx.textAlign = "left";
}

function drawHeadline(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  ctx.fillStyle = CREAM;
  const lines = wrapText(ctx, data.headline.toUpperCase(), RECAP_IMAGE_WIDTH - margin * 2, 84, SERIF_STACK, 500);
  let y = 310;
  for (const line of lines.slice(0, 3)) {
    ctx.font = `500 84px ${SERIF_STACK}`;
    ctx.fillText(line, margin, y);
    y += 82;
  }
}

function drawStats(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  const y = 625;
  const colW = 290;
  const stats = [
    [String(data.worksCount), statLabel("artworks", data.locale, data.worksCount)],
    [String(data.artistsCount), statLabel("artists", data.locale, data.artistsCount)],
    [data.timeStr.toUpperCase(), statLabel("time", data.locale, 2)],
  ];
  for (let i = 0; i < stats.length; i++) {
    const x = margin + i * colW;
    ctx.fillStyle = "rgba(243,232,215,0.12)";
    roundRect(ctx, x, y, colW - 24, 132, 24);
    ctx.fill();
    ctx.fillStyle = CREAM;
    ctx.font = `500 58px ${SERIF_STACK}`;
    ctx.fillText(stats[i][0], x + 24, y + 64);
    ctx.fillStyle = "rgba(243,232,215,0.70)";
    ctx.font = `700 20px ${SANS_STACK}`;
    ctx.fillText(stats[i][1].toUpperCase(), x + 24, y + 102);
  }
}

function drawFavorite(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  if (!data.favoriteArtist && !data.favoriteTitle) return;
  const y = 835;
  ctx.fillStyle = "rgba(243,232,215,0.66)";
  ctx.font = `700 22px ${SANS_STACK}`;
  ctx.fillText((data.favoriteArtwork ? favoriteLabel(data.locale) : highlightLabel(data.locale)).toUpperCase(), margin, y);
  ctx.fillStyle = CREAM;
  ctx.font = `500 50px ${SERIF_STACK}`;
  fillFitText(ctx, data.favoriteArtist, margin, y + 62, 820, 50, SERIF_STACK, 500);
  ctx.fillStyle = "rgba(243,232,215,0.72)";
  ctx.font = `500 36px ${SERIF_STACK}`;
  fillFitText(ctx, data.favoriteTitle, margin, y + 108, 840, 36, SERIF_STACK, 500);
}

function drawValueMoment(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  if (data.valueMoment.kind === "none") return;
  const y = 1085;
  ctx.fillStyle = CREAM;
  roundRect(ctx, margin, y, RECAP_IMAGE_WIDTH - margin * 2, 230, 28);
  ctx.fill();
  ctx.fillStyle = INK;
  ctx.font = `800 21px ${SANS_STACK}`;
  ctx.fillText(data.valueMoment.label.toUpperCase(), margin + 34, y + 48);
  ctx.font = `500 86px ${SERIF_STACK}`;
  fillFitText(ctx, data.valueMoment.valueText, margin + 34, y + 133, RECAP_IMAGE_WIDTH - margin * 2 - 68, 86, SERIF_STACK, 500);
  ctx.fillStyle = "rgba(24,23,20,0.66)";
  ctx.font = `600 25px ${SANS_STACK}`;
  fillFitText(ctx, data.valueMoment.subtitle, margin + 34, y + 179, RECAP_IMAGE_WIDTH - margin * 2 - 68, 25, SANS_STACK, 600);
}

function drawAchievement(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  if (!data.achievementTitle) return;
  const y = 1380;
  ctx.fillStyle = "rgba(243,232,215,0.10)";
  roundRect(ctx, margin, y, RECAP_IMAGE_WIDTH - margin * 2, 150, 28);
  ctx.fill();
  ctx.strokeStyle = "rgba(243,232,215,0.18)";
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(margin + 64, y + 75, 38, 0, Math.PI * 2);
  ctx.fillStyle = CREAM;
  ctx.fill();
  ctx.fillStyle = INK;
  ctx.font = `800 28px ${SANS_STACK}`;
  ctx.textAlign = "center";
  ctx.fillText(data.achievementIcon || "✓", margin + 64, y + 84);
  ctx.textAlign = "left";
  ctx.fillStyle = "rgba(243,232,215,0.65)";
  ctx.font = `700 20px ${SANS_STACK}`;
  ctx.fillText(achievementLabel(data.locale).toUpperCase(), margin + 126, y + 60);
  ctx.fillStyle = CREAM;
  ctx.font = `700 38px ${SANS_STACK}`;
  fillFitText(ctx, data.achievementTitle.toUpperCase(), margin + 126, y + 106, 760, 38, SANS_STACK, 700);
}

function drawFooter(ctx: CanvasRenderingContext2D, margin: number, width: number, height: number): void {
  ctx.fillStyle = CREAM;
  ctx.font = `700 24px ${SANS_STACK}`;
  ctx.fillText("ELYIO", margin, height - 142);
  ctx.fillStyle = "rgba(243,232,215,0.58)";
  ctx.font = `600 26px ${SANS_STACK}`;
  ctx.fillText("Point. Discover. Understand.", margin, height - 104);
  ctx.fillStyle = "rgba(243,232,215,0.42)";
  ctx.font = `600 24px ${SANS_STACK}`;
  ctx.fillText("elyio.co", margin, height - 66);
  ctx.strokeStyle = "rgba(243,232,215,0.12)";
  ctx.beginPath();
  ctx.moveTo(margin, height - 186);
  ctx.lineTo(width - margin, height - 186);
  ctx.stroke();
}

function statLabel(kind: "artworks" | "artists" | "time", locale: Locale, count: number): string {
  if (kind === "time") return locale === "fr" ? "exploration" : locale === "zh-Hans" ? "探索" : "exploring";
  if (kind === "artworks") {
    if (locale === "fr") return count === 1 ? "œuvre" : "œuvres";
    if (locale === "zh-Hans") return "作品";
    return count === 1 ? "artwork" : "artworks";
  }
  if (locale === "fr") return count === 1 ? "artiste" : "artistes";
  if (locale === "zh-Hans") return "艺术家";
  return count === 1 ? "artist" : "artists";
}

function favoriteLabel(locale: Locale): string {
  if (locale === "fr") return "votre favori";
  if (locale === "zh-Hans") return "你的最爱";
  return "your favorite";
}

function highlightLabel(locale: Locale): string {
  if (locale === "fr") return "moment fort";
  if (locale === "zh-Hans") return "亮点";
  return "highlight";
}

function achievementLabel(locale: Locale): string {
  if (locale === "fr") return "trophée";
  if (locale === "zh-Hans") return "成就";
  return "achievement";
}

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

function drawCover(ctx: CanvasRenderingContext2D, img: HTMLImageElement, x: number, y: number, w: number, h: number): void {
  const srcRatio = img.width / img.height;
  const dstRatio = w / h;
  let sx = 0;
  let sy = 0;
  let sw = img.width;
  let sh = img.height;
  if (srcRatio > dstRatio) {
    sw = img.height * dstRatio;
    sx = (img.width - sw) / 2;
  } else {
    sh = img.width / dstRatio;
    sy = (img.height - sh) / 2;
  }
  ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
}

function fillFitText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  size: number,
  font: string,
  weight: number
): void {
  if (!text) return;
  let fontSize = size;
  while (fontSize > 18) {
    ctx.font = `${weight} ${fontSize}px ${font}`;
    if (ctx.measureText(text).width <= maxWidth) break;
    fontSize -= 2;
  }
  ctx.fillText(text, x, y);
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number, size: number, font: string, weight: number): string[] {
  ctx.font = `${weight} ${size}px ${font}`;
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (ctx.measureText(candidate).width <= maxWidth || !line) {
      line = candidate;
    } else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
