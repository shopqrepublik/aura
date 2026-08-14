import { paintGrainCanvas, proxyImageUrl } from "@/lib/visitPalette";
import type { Artwork, Locale } from "@/lib/types";
import type { VisitValueMoment } from "@/lib/visit-game";

export const RECAP_IMAGE_WIDTH = 1080;
export const RECAP_IMAGE_HEIGHT = 1920;

const SANS_STACK = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', Inter, 'Helvetica Neue', sans-serif";
const SERIF_STACK = "'Cormorant Garamond', Georgia, serif";
const CREAM = "#F6E9D4";
const INK = "#11100E";
const GOLD = "#D8B56D";
const GOLD_SOFT = "#E7CA83";

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

  paintTrophyBackground(ctx, W, H);
  await paintHero(ctx, data, W);
  paintGrainCanvas(ctx, W, H);

  ctx.fillStyle = "rgba(8,7,6,0.16)";
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

async function paintHero(ctx: CanvasRenderingContext2D, data: RecapImageData, width: number): Promise<void> {
  const artwork = data.favoriteArtwork || data.heroArtwork;
  const heroX = 86;
  const heroY = 520;
  const heroW = width - 172;
  const heroH = 570;
  if (artwork?.imageUrl) {
    try {
      const url = /^https?:\/\/(upload|commons)\.wikimedia\.org\//i.test(artwork.imageUrl)
        ? proxyImageUrl(artwork.imageUrl, 1600)
        : artwork.imageUrl;
      const img = await loadImage(url, 7000);
      ctx.save();
      roundRect(ctx, heroX, heroY, heroW, heroH, 34);
      ctx.clip();
      drawCover(ctx, img, heroX, heroY, heroW, heroH);
      const shade = ctx.createLinearGradient(0, heroY, 0, heroY + heroH);
      shade.addColorStop(0, "rgba(0,0,0,0.04)");
      shade.addColorStop(0.68, "rgba(0,0,0,0.04)");
      shade.addColorStop(1, "rgba(0,0,0,0.42)");
      ctx.fillStyle = shade;
      ctx.fillRect(heroX, heroY, heroW, heroH);
      ctx.restore();
      ctx.strokeStyle = "rgba(216,181,109,0.48)";
      ctx.lineWidth = 2;
      roundRect(ctx, heroX, heroY, heroW, heroH, 34);
      ctx.stroke();
      return;
    } catch {
      // Fall through to editorial fallback.
    }
  }

  const accent = artwork?.accent || data.paletteAccents[0] || "#725E47";
  const g = ctx.createRadialGradient(width * 0.48, heroY + 190, 40, width * 0.5, heroY + 250, heroW * 0.75);
  g.addColorStop(0, accent);
  g.addColorStop(0.55, "#383028");
  g.addColorStop(1, "#171310");
  ctx.fillStyle = g;
  roundRect(ctx, heroX, heroY, heroW, heroH, 34);
  ctx.fill();
  ctx.fillStyle = "rgba(246,233,212,0.08)";
  ctx.beginPath();
  ctx.arc(heroX + 220, heroY + 190, 118, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(246,233,212,0.20)";
  ctx.lineWidth = 26;
  ctx.beginPath();
  ctx.moveTo(heroX + 130, heroY + 440);
  ctx.bezierCurveTo(heroX + 310, heroY + 230, heroX + 560, heroY + 570, heroX + 770, heroY + 260);
  ctx.stroke();
  ctx.strokeStyle = "rgba(216,181,109,0.35)";
  ctx.lineWidth = 2;
  for (let i = 0; i < 8; i++) {
    ctx.beginPath();
    ctx.ellipse(width * 0.5, heroY + 270 + i * 14, 300 - i * 22, 72 + i * 6, -0.08, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function paintTrophyBackground(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  const base = ctx.createLinearGradient(0, 0, width, height);
  base.addColorStop(0, "#080706");
  base.addColorStop(0.42, "#18130D");
  base.addColorStop(1, "#050505");
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, width, height);

  const glow = ctx.createRadialGradient(width * 0.55, height * 0.16, 20, width * 0.5, height * 0.18, width * 0.75);
  glow.addColorStop(0, "rgba(216,181,109,0.34)");
  glow.addColorStop(0.36, "rgba(124,86,42,0.17)");
  glow.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, width, height);
}

function drawHeader(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  ctx.fillStyle = GOLD_SOFT;
  ctx.font = `700 30px ${SANS_STACK}`;
  ctx.textBaseline = "alphabetic";
  ctx.fillText("ELYIO", margin, 112);
  ctx.fillStyle = "rgba(246,233,212,0.62)";
  ctx.font = `600 24px ${SANS_STACK}`;
  ctx.fillText("Point. Discover. Understand.", margin, 150);

  ctx.fillStyle = "rgba(216,181,109,0.92)";
  ctx.strokeStyle = "rgba(216,181,109,0.36)";
  ctx.lineWidth = 2;
  roundRect(ctx, RECAP_IMAGE_WIDTH - margin - 96, 74, 96, 96, 48);
  ctx.stroke();
  ctx.font = `800 33px ${SANS_STACK}`;
  ctx.textAlign = "center";
  ctx.fillText("E", RECAP_IMAGE_WIDTH - margin - 48, 134);
  ctx.textAlign = "left";
}

function drawHeadline(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  ctx.fillStyle = "rgba(246,233,212,0.72)";
  ctx.font = `700 23px ${SANS_STACK}`;
  fillFitText(ctx, data.museumName.toUpperCase(), margin, 238, 880, 23, SANS_STACK, 700);
  ctx.fillStyle = CREAM;
  const headlineSize = data.headline.length > 42 ? 62 : 80;
  const lines = wrapText(ctx, data.headline.toUpperCase(), RECAP_IMAGE_WIDTH - margin * 2, headlineSize, SERIF_STACK, 500);
  let y = 326;
  for (const line of lines.slice(0, 3)) {
    ctx.font = `500 ${headlineSize}px ${SERIF_STACK}`;
    ctx.fillText(line, margin, y);
    y += headlineSize * 0.95;
  }
}

function drawStats(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  const y = 1148;
  const colW = 290;
  const stats = [
    [String(data.worksCount), statLabel("artworks", data.locale, data.worksCount)],
    [String(data.artistsCount), statLabel("artists", data.locale, data.artistsCount)],
    [data.timeStr.toUpperCase(), statLabel("time", data.locale, 2)],
  ];
  for (let i = 0; i < stats.length; i++) {
    const x = margin + i * colW;
    ctx.fillStyle = "rgba(216,181,109,0.095)";
    roundRect(ctx, x, y, colW - 24, 138, 24);
    ctx.fill();
    ctx.strokeStyle = "rgba(216,181,109,0.20)";
    ctx.stroke();
    ctx.fillStyle = GOLD_SOFT;
    ctx.font = `500 60px ${SERIF_STACK}`;
    fillFitText(ctx, stats[i][0], x + 24, y + 68, colW - 68, 60, SERIF_STACK, 500);
    ctx.fillStyle = "rgba(246,233,212,0.70)";
    ctx.font = `700 20px ${SANS_STACK}`;
    ctx.fillText(stats[i][1].toUpperCase(), x + 24, y + 108);
  }
}

function drawFavorite(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  if (!data.favoriteArtist && !data.favoriteTitle) return;
  const y = 1318;
  ctx.fillStyle = GOLD;
  ctx.font = `700 22px ${SANS_STACK}`;
  ctx.fillText((data.favoriteArtwork ? favoriteLabel(data.locale) : highlightLabel(data.locale)).toUpperCase(), margin, y);
  ctx.fillStyle = CREAM;
  ctx.font = `500 44px ${SERIF_STACK}`;
  fillFitText(ctx, data.favoriteArtist, margin, y + 56, 850, 44, SERIF_STACK, 500);
  ctx.fillStyle = "rgba(246,233,212,0.74)";
  ctx.font = `500 34px ${SERIF_STACK}`;
  fillFitText(ctx, data.favoriteTitle, margin, y + 100, 850, 34, SERIF_STACK, 500);
}

function drawValueMoment(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  if (data.valueMoment.kind === "none") return;
  const y = 1468;
  ctx.fillStyle = "rgba(216,181,109,0.98)";
  roundRect(ctx, margin, y, RECAP_IMAGE_WIDTH - margin * 2, 214, 28);
  ctx.fill();
  ctx.fillStyle = INK;
  ctx.font = `800 21px ${SANS_STACK}`;
  ctx.fillText(data.valueMoment.label.toUpperCase(), margin + 34, y + 48);
  ctx.font = `500 82px ${SERIF_STACK}`;
  fillFitText(ctx, data.valueMoment.valueText, margin + 34, y + 126, RECAP_IMAGE_WIDTH - margin * 2 - 68, 82, SERIF_STACK, 500);
  ctx.fillStyle = "rgba(24,23,20,0.66)";
  ctx.font = `600 25px ${SANS_STACK}`;
  fillFitText(ctx, data.valueMoment.subtitle, margin + 34, y + 172, RECAP_IMAGE_WIDTH - margin * 2 - 68, 25, SANS_STACK, 600);
}

function drawAchievement(ctx: CanvasRenderingContext2D, data: RecapImageData, margin: number): void {
  if (!data.achievementTitle) return;
  const y = 1714;
  ctx.fillStyle = "rgba(246,233,212,0.07)";
  roundRect(ctx, margin, y, RECAP_IMAGE_WIDTH - margin * 2, 118, 28);
  ctx.fill();
  ctx.strokeStyle = "rgba(216,181,109,0.24)";
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(margin + 58, y + 59, 36, 0, Math.PI * 2);
  ctx.fillStyle = GOLD_SOFT;
  ctx.fill();
  ctx.fillStyle = INK;
  ctx.font = `800 28px ${SANS_STACK}`;
  ctx.textAlign = "center";
  ctx.fillText(data.achievementIcon || "✓", margin + 58, y + 68);
  ctx.textAlign = "left";
  ctx.fillStyle = "rgba(216,181,109,0.84)";
  ctx.font = `700 20px ${SANS_STACK}`;
  ctx.fillText(achievementLabel(data.locale).toUpperCase(), margin + 116, y + 48);
  ctx.fillStyle = CREAM;
  ctx.font = `700 34px ${SANS_STACK}`;
  fillFitText(ctx, data.achievementTitle.toUpperCase(), margin + 116, y + 90, 780, 34, SANS_STACK, 700);
}

function drawFooter(ctx: CanvasRenderingContext2D, margin: number, width: number, height: number): void {
  ctx.fillStyle = "rgba(246,233,212,0.72)";
  ctx.font = `700 22px ${SANS_STACK}`;
  ctx.fillText("ELYIO", margin, height - 34);
  ctx.fillStyle = "rgba(216,181,109,0.70)";
  ctx.font = `600 24px ${SANS_STACK}`;
  ctx.fillText("elyio.co", width - margin - 110, height - 34);
  ctx.strokeStyle = "rgba(216,181,109,0.16)";
  ctx.beginPath();
  ctx.moveTo(margin, height - 66);
  ctx.lineTo(width - margin, height - 66);
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
