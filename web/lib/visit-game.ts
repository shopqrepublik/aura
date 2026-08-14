import { artworkArtistDisplayName } from "./artist-display";
import { resolveTitle } from "./artworks";
import { valueRevealNumericContext } from "./scaleComparison";
import {
  formatEstimatedValueRange,
  formatValueRevealHeadline,
  getAggregateEligibleValue,
  getIndicativeEligibleValue,
  getArtworkValueReveal,
  summarizeVisitValue,
} from "./valueReveal";
import type { Artwork, Locale } from "./types";

export interface VisitGameInput {
  locale: Locale;
  museumName: string | null;
  museumCity: string | null;
  startTime: number | null;
  now: number;
  seenArtworks: Artwork[];
  favoriteIds: Set<string>;
  unlockedAchievements?: Record<string, number>;
}

export interface VisitMetricSummary {
  artworksCount: number;
  artistsCount: number;
  durationMinutes: number;
  durationLabel: string;
  favoriteCount: number;
  curatedCount: number;
}

export interface VisitMission {
  id: string;
  type: string;
  title: string;
  description: string;
  progress: number;
  target: number;
  completed: boolean;
}

export interface VisitAchievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  unlocked: boolean;
  unlockedAt: number | null;
}

export interface VisitValueMoment {
  kind: "reviewed_estimate" | "indicative_total" | "market_context" | "none";
  label: string;
  valueText: string;
  trophyText?: string;
  subtitle: string;
  artwork: Artwork | null;
  aggregateEligible: boolean;
}

export interface VisitRecapHighlights {
  favoriteArtwork: Artwork | null;
  heroArtwork: Artwork | null;
  valueMoment: VisitValueMoment;
  topAchievement: VisitAchievement | null;
  mostRepresentedArtist: string | null;
  mostExploredPeriod: string | null;
}

export interface VisitGameSummary {
  metrics: VisitMetricSummary;
  primaryMission: VisitMission | null;
  secondaryMissions: VisitMission[];
  missions: VisitMission[];
  achievements: VisitAchievement[];
  completedMissionIds: string[];
  unlockedAchievementIds: string[];
  recap: VisitRecapHighlights;
}

type PeriodKey = "renaissance" | "impressionist" | "modern" | "ancient" | "medieval";

const UNKNOWN_ARTIST = new Set(["", "unknown artist", "artiste inconnu", "未知艺术家", "unknown"]);

export function buildVisitGame(input: VisitGameInput): VisitGameSummary {
  const metrics = buildMetrics(input);
  const periodCounts = countPeriods(input.seenArtworks);
  const categoryCounts = countCategories(input.seenArtworks);
  const missions = buildMissions(input, metrics, periodCounts, categoryCounts);
  const achievements = buildAchievements(input, metrics, periodCounts);
  const completedMissionIds = missions.filter((m) => m.completed).map((m) => m.id);
  const unlockedAchievementIds = achievements.filter((a) => a.unlocked).map((a) => a.id);
  const incomplete = missions.filter((m) => !m.completed);
  return {
    metrics,
    primaryMission: incomplete[0] ?? null,
    secondaryMissions: incomplete.slice(1, 3),
    missions,
    achievements,
    completedMissionIds,
    unlockedAchievementIds,
    recap: buildRecapHighlights(input, metrics, achievements, periodCounts),
  };
}

export function visitDisplayMuseumName(museumName: string | null | undefined, locale: Locale): string {
  return museumName || (locale === "fr" ? "votre musée" : locale === "zh-Hans" ? "您的博物馆" : "your museum");
}

export function visitHeadline(museumName: string | null | undefined, locale: Locale, shortVisit = false): string {
  const museum = visitDisplayMuseumName(museumName, locale);
  if (locale === "fr") return shortVisit ? `MA DÉCOUVERTE AU ${museum}` : `MA VISITE AU ${museum}`;
  if (locale === "zh-Hans") return shortVisit ? `我的${museum}发现` : `我的${museum}参观`;
  return shortVisit ? `MY ${museum.toUpperCase()} DISCOVERY` : `MY ${museum.toUpperCase()} VISIT`;
}

export function formatDuration(minutes: number, locale: Locale): string {
  const safe = Math.max(1, Math.round(minutes));
  if (safe >= 60) {
    const h = Math.floor(safe / 60);
    const m = safe % 60;
    if (locale === "zh-Hans") return m ? `${h}小时${m}分` : `${h}小时`;
    return m ? `${h}h ${m}m` : `${h}h`;
  }
  if (locale === "zh-Hans") return `${safe}分`;
  return `${safe}m`;
}

export function artistKey(artwork: Artwork, locale: Locale): string | null {
  const artist = artworkArtistDisplayName(artwork, locale).trim();
  if (UNKNOWN_ARTIST.has(artist.toLowerCase())) return null;
  return artist;
}

function buildMetrics(input: VisitGameInput): VisitMetricSummary {
  const uniqueArtists = new Set(input.seenArtworks.map((a) => artistKey(a, input.locale)).filter((v): v is string => !!v));
  const durationMinutes = input.startTime ? Math.max(1, Math.round((input.now - input.startTime) / 60000)) : 1;
  return {
    artworksCount: input.seenArtworks.length,
    artistsCount: uniqueArtists.size,
    durationMinutes,
    durationLabel: formatDuration(durationMinutes, input.locale),
    favoriteCount: input.favoriteIds.size,
    curatedCount: input.seenArtworks.filter((a) => isFullCurated(a)).length,
  };
}

function buildMissions(
  input: VisitGameInput,
  metrics: VisitMetricSummary,
  periodCounts: Record<PeriodKey, number>,
  categoryCounts: Record<string, number>
): VisitMission[] {
  const locale = input.locale;
  const missions: VisitMission[] = [
    mission("scan_3", "SCAN_COUNT", missionTitle("scan_3", locale), missionDescription("scan_3", locale), metrics.artworksCount, 3),
    mission("unique_artists_3", "UNIQUE_ARTISTS", missionTitle("unique_artists_3", locale), missionDescription("unique_artists_3", locale), metrics.artistsCount, 3),
    mission("favorite_1", "FAVORITE", missionTitle("favorite_1", locale), missionDescription("favorite_1", locale), metrics.favoriteCount, 1),
    mission("scan_5", "SCAN_COUNT", missionTitle("scan_5", locale), missionDescription("scan_5", locale), metrics.artworksCount, 5),
    mission("unique_artists_5", "UNIQUE_ARTISTS", missionTitle("unique_artists_5", locale), missionDescription("unique_artists_5", locale), metrics.artistsCount, 5),
    mission("curated_3", "CURATED_DISCOVERY", missionTitle("curated_3", locale), missionDescription("curated_3", locale), metrics.curatedCount, 3),
    mission("scan_10", "SCAN_COUNT", missionTitle("scan_10", locale), missionDescription("scan_10", locale), metrics.artworksCount, 10),
  ];

  if (periodCounts.renaissance > 0) {
    missions.splice(3, 0, mission("renaissance_3", "PERIOD_EXPLORER", missionTitle("renaissance_3", locale), missionDescription("renaissance_3", locale), periodCounts.renaissance, 3));
  }
  if (periodCounts.impressionist > 0) {
    missions.splice(3, 0, mission("impressionist_3", "PERIOD_EXPLORER", missionTitle("impressionist_3", locale), missionDescription("impressionist_3", locale), periodCounts.impressionist, 3));
  }
  const exploredCategories = Object.values(categoryCounts).filter((count) => count > 0).length;
  if (exploredCategories > 0) {
    missions.push(mission("explorer_3", "EXPLORER", missionTitle("explorer_3", locale), missionDescription("explorer_3", locale), exploredCategories, 3));
  }
  if (metrics.artistsCount > 0) {
    missions.push(mission("new_artist", "NEW_ARTIST", missionTitle("new_artist", locale), missionDescription("new_artist", locale), metrics.artistsCount, metrics.artistsCount + 1));
  }
  return missions;
}

function buildAchievements(input: VisitGameInput, metrics: VisitMetricSummary, periodCounts: Record<PeriodKey, number>): VisitAchievement[] {
  const summary = summarizeVisitValue(input.seenArtworks);
  const biggest = findBiggestMarketContext(input.seenArtworks, input.locale);
  const defs = [
    achievement("first_discovery", "◎", "First Discovery", "First artwork added.", metrics.artworksCount >= 1),
    achievement("curious_eye", "◐", "Curious Eye", "You discovered 5 artworks.", metrics.artworksCount >= 5),
    achievement("ten_masterpieces", "◆", "10 Masterpieces", "You discovered 10 artworks.", metrics.artworksCount >= 10),
    achievement("artist_explorer", "✦", "Artist Explorer", "You met 5 different artists.", metrics.artistsCount >= 5),
    achievement("new_favorite", "♥", "New Favorite", "You chose a favorite artwork.", metrics.favoriteCount >= 1),
    achievement("renaissance_explorer", "R", "Renaissance Explorer", "You found 5 Renaissance works.", periodCounts.renaissance >= 5),
    achievement("impressionist_trail", "I", "Impressionist Trail", "You followed 5 Impressionist or modern works.", periodCounts.impressionist >= 5),
    achievement("deep_dive", "◌", "Deep Dive", "You spent meaningful time exploring.", metrics.durationMinutes >= 30 || metrics.artworksCount >= 5),
    achievement("billion_euro_visitor", "€", "Billion Euro Visitor", "Your ELYIO indicative total starts above €1B.", summary.hasIndicativeValue && summary.indicativeValueLow >= 1000),
    achievement("market_giant", "M", "Market Giant", "You encountered a nine-figure market benchmark.", Math.max(biggest?.amountMillions ?? 0, summary.indicativeValueHigh) >= 100),
    achievement("museum_explorer", "E", "Museum Explorer", "You built a real museum visit.", metrics.artworksCount >= 3),
  ];
  return defs.map((a) => localizeAchievement(a, input.locale, input.unlockedAchievements?.[a.id] ?? null));
}

function buildRecapHighlights(
  input: VisitGameInput,
  metrics: VisitMetricSummary,
  achievements: VisitAchievement[],
  periodCounts: Record<PeriodKey, number>
): VisitRecapHighlights {
  const favoriteArtwork = latestFavorite(input.seenArtworks, input.favoriteIds);
  const valueMoment = buildValueMoment(input.seenArtworks, input.locale);
  const achievement = achievements.find((a) => a.unlocked && a.id === "billion_euro_visitor")
    || achievements.find((a) => a.unlocked && a.id === "ten_masterpieces")
    || achievements.find((a) => a.unlocked && a.id === "impressionist_trail")
    || achievements.find((a) => a.unlocked && a.id === "renaissance_explorer")
    || achievements.find((a) => a.unlocked && a.id === "artist_explorer")
    || achievements.find((a) => a.unlocked && a.id === "curious_eye")
    || achievements.find((a) => a.unlocked && a.id === "museum_explorer")
    || achievements.find((a) => a.unlocked && a.id === "market_giant")
    || achievements.find((a) => a.unlocked)
    || null;
  return {
    favoriteArtwork,
    heroArtwork: favoriteArtwork || valueMoment.artwork || input.seenArtworks[0] || null,
    valueMoment,
    topAchievement: achievement,
    mostRepresentedArtist: mostRepresentedArtist(input.seenArtworks, input.locale),
    mostExploredPeriod: topPeriod(periodCounts, input.locale),
  };
}

function buildValueMoment(artworks: Artwork[], locale: Locale): VisitValueMoment {
  const summary = summarizeVisitValue(artworks);
  if (summary.hasIndicativeValue) {
    return {
      kind: "indicative_total",
      label: valueLabel("indicative_total", locale),
      valueText: formatEstimatedValueRange({
        low: summary.indicativeValueLow,
        high: summary.indicativeValueHigh,
        currency: summary.indicativeValueCurrency,
      }),
      trophyText: formatTrophyValue(summary.indicativeValueLow, summary.indicativeValueHigh, summary.indicativeValueCurrency),
      subtitle: valueSubtitle("indicative_total", locale),
      artwork: getMostIndicativeArtwork(artworks),
      aggregateEligible: true,
    };
  }
  if (summary.hasEstimatedValue) {
    return {
      kind: "reviewed_estimate",
      label: valueLabel("reviewed_estimate", locale),
      valueText: formatEstimatedValueRange({
        low: summary.estimatedValueLow,
        high: summary.estimatedValueHigh,
        currency: summary.estimatedValueCurrency,
      }),
      trophyText: formatTrophyValue(summary.estimatedValueLow, summary.estimatedValueHigh, summary.estimatedValueCurrency),
      subtitle: valueSubtitle("reviewed_estimate", locale),
      artwork: getMostAggregateArtwork(artworks),
      aggregateEligible: true,
    };
  }
  const biggest = findBiggestMarketContext(artworks, locale);
  if (biggest) {
    return {
      kind: "market_context",
      label: valueLabel("market_context", locale),
      valueText: biggest.valueText,
      subtitle: biggest.subtitle,
      artwork: biggest.artwork,
      aggregateEligible: false,
    };
  }
  return {
    kind: "none",
    label: valueLabel("none", locale),
    valueText: "",
    subtitle: valueSubtitle("none", locale),
    artwork: null,
    aggregateEligible: false,
  };
}

function formatTrophyValue(lowMillions: number, highMillions: number, currency: string): string {
  const midpoint = (lowMillions + highMillions) / 2;
  const prefix = currency === "EUR" ? "€" : `${currency} `;
  if (!Number.isFinite(midpoint) || midpoint <= 0) return "";
  if (midpoint >= 1000) return `${prefix}${Number((midpoint / 1000).toFixed(midpoint >= 9500 ? 0 : 1)).toString().replace(/\.0$/, "")}B`;
  if (midpoint >= 100) return `${prefix}${Math.round(midpoint / 10) * 10}M`;
  if (midpoint >= 10) return `${prefix}${Math.round(midpoint)}M`;
  return `${prefix}${Number(midpoint.toFixed(1))}M`;
}

function findBiggestMarketContext(artworks: Artwork[], locale: Locale): { amountMillions: number; valueText: string; subtitle: string; artwork: Artwork } | null {
  let best: { amountMillions: number; valueText: string; subtitle: string; artwork: Artwork } | null = null;
  for (const artwork of artworks) {
    const reveal = getArtworkValueReveal(artwork);
    if (!reveal || reveal.mode === "ESTIMATED_VALUE") continue;
    const numeric = valueRevealNumericContext(reveal);
    if (!numeric) continue;
    const valueText = formatValueRevealHeadline(reveal, locale);
    const artist = artistKey(artwork, locale) || resolveTitle(artwork, locale);
    const subtitle = reveal.mode === "MARKET_CONTEXT"
      ? marketSubtitle(artist, locale)
      : beyondSubtitle(artist, locale);
    if (!best || numeric.amountMillions > best.amountMillions) {
      best = { amountMillions: numeric.amountMillions, valueText, subtitle, artwork };
    }
  }
  return best;
}

function getMostAggregateArtwork(artworks: Artwork[]): Artwork | null {
  let best: Artwork | null = null;
  let bestValue = Number.NEGATIVE_INFINITY;
  for (const artwork of artworks) {
    const aggregate = getAggregateEligibleValue(artwork);
    if (!aggregate) continue;
    if (aggregate.high > bestValue) {
      best = artwork;
      bestValue = aggregate.high;
    }
  }
  return best;
}

function getMostIndicativeArtwork(artworks: Artwork[]): Artwork | null {
  let best: Artwork | null = null;
  let bestValue = Number.NEGATIVE_INFINITY;
  for (const artwork of artworks) {
    const aggregate = getIndicativeEligibleValue(artwork);
    if (!aggregate) continue;
    if (aggregate.high > bestValue) {
      best = artwork;
      bestValue = aggregate.high;
    }
  }
  return best;
}

function latestFavorite(artworks: Artwork[], favoriteIds: Set<string>): Artwork | null {
  for (let i = artworks.length - 1; i >= 0; i--) {
    if (favoriteIds.has(artworks[i].id)) return artworks[i];
  }
  return null;
}

function isFullCurated(artwork: Artwork): boolean {
  return !artwork.needsEditorialReview && !String(artwork.editorialStatus || "").includes("fallback");
}

function mission(id: string, type: string, title: string, description: string, progress: number, target: number): VisitMission {
  const safeProgress = Math.max(0, Math.min(progress, target));
  return { id, type, title, description, progress: safeProgress, target, completed: progress >= target };
}

function achievement(id: string, icon: string, title: string, description: string, unlocked: boolean): VisitAchievement {
  return { id, icon, title, description, unlocked, unlockedAt: null };
}

function localizeAchievement(achievement: VisitAchievement, locale: Locale, unlockedAt: number | null): VisitAchievement {
  return {
    ...achievement,
    title: achievementTitle(achievement.id, locale),
    description: achievementDescription(achievement.id, locale),
    unlockedAt: achievement.unlocked ? unlockedAt : null,
  };
}

function countPeriods(artworks: Artwork[]): Record<PeriodKey, number> {
  const counts: Record<PeriodKey, number> = { renaissance: 0, impressionist: 0, modern: 0, ancient: 0, medieval: 0 };
  for (const artwork of artworks) {
    const text = searchText(artwork);
    if (/(renaissance|léonard|leonardo|titian|tiziano|raphael|antonello|xvie|xvi|15[0-9]{2}|16[0-2][0-9])/.test(text)) counts.renaissance += 1;
    if (/(impression|post-impression|monet|renoir|degas|cézanne|cezanne|gauguin|manet|van gogh|seurat|pissarro|morisot|sisley)/.test(text)) counts.impressionist += 1;
    if (/(picasso|moderne|modern|cubis|xxe|xx|19[0-9]{2})/.test(text)) counts.modern += 1;
    if (/(egypt|roman|greek|antiqu|dynasty|pharaoh|bce|av\\. j\\.-c|avant jésus|古埃及|古希腊|古罗马)/.test(text)) counts.ancient += 1;
    if (/(medieval|moyen âge|gothic|romanesk|xii|xiii|xiv|中世纪)/.test(text)) counts.medieval += 1;
  }
  return counts;
}

function countCategories(artworks: Artwork[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const artwork of artworks) {
    const text = searchText(artwork);
    const category = /sculpt|marble|bronze|statue/.test(text)
      ? "sculpture"
      : /vase|bowl|armor|armour|jewelry|tapestry|ceramic|porcelain|object/.test(text)
        ? "object"
        : /painting|canvas|oil|portrait|landscape/.test(text)
          ? "painting"
          : "artwork";
    counts[category] = (counts[category] || 0) + 1;
  }
  return counts;
}

function searchText(artwork: Artwork): string {
  return [
    artwork.artist,
    artwork.rawArtist,
    artwork.year,
    artwork.rawYear,
    artwork.priority,
    artwork.editorialStatus,
    artwork.title.en,
    artwork.title.fr,
    artwork.title["zh-Hans"],
    artwork.why?.en,
    artwork.where?.en,
    artwork.rarity?.en,
  ].filter(Boolean).join(" ").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function mostRepresentedArtist(artworks: Artwork[], locale: Locale): string | null {
  const counts = new Map<string, number>();
  for (const artwork of artworks) {
    const artist = artistKey(artwork, locale);
    if (!artist) continue;
    counts.set(artist, (counts.get(artist) || 0) + 1);
  }
  let best: string | null = null;
  let bestCount = 1;
  for (const [artist, count] of counts) {
    if (count > bestCount) {
      best = artist;
      bestCount = count;
    }
  }
  return best;
}

function topPeriod(counts: Record<PeriodKey, number>, locale: Locale): string | null {
  let best: PeriodKey | null = null;
  let bestCount = 1;
  for (const [period, count] of Object.entries(counts) as Array<[PeriodKey, number]>) {
    if (count > bestCount) {
      best = period;
      bestCount = count;
    }
  }
  return best ? periodLabel(best, locale) : null;
}

function periodLabel(period: PeriodKey, locale: Locale): string {
  const labels: Record<PeriodKey, Record<Locale, string>> = {
    renaissance: { en: "Renaissance", fr: "Renaissance", "zh-Hans": "文艺复兴" },
    impressionist: { en: "Impressionist", fr: "impressionniste", "zh-Hans": "印象派" },
    modern: { en: "modern", fr: "moderne", "zh-Hans": "现代艺术" },
    ancient: { en: "ancient", fr: "antique", "zh-Hans": "古代艺术" },
    medieval: { en: "medieval", fr: "médiévale", "zh-Hans": "中世纪" },
  };
  return labels[period][locale];
}

function missionTitle(id: string, locale: Locale): string {
  const map: Record<string, Record<Locale, string>> = {
    scan_3: { en: "Discover 3 artworks", fr: "Découvrez 3 œuvres", "zh-Hans": "发现3件作品" },
    scan_5: { en: "Curious Eye", fr: "Regard curieux", "zh-Hans": "好奇之眼" },
    scan_10: { en: "10 Masterpieces", fr: "10 chefs-d'œuvre", "zh-Hans": "10件杰作" },
    unique_artists_3: { en: "Meet 3 artists", fr: "Rencontrez 3 artistes", "zh-Hans": "认识3位艺术家" },
    unique_artists_5: { en: "Artist Explorer", fr: "Explorateur d'artistes", "zh-Hans": "艺术家探索者" },
    favorite_1: { en: "Choose a favorite", fr: "Choisissez un favori", "zh-Hans": "选出最喜欢的一件" },
    curated_3: { en: "Find curated highlights", fr: "Trouvez des temps forts", "zh-Hans": "发现精选亮点" },
    renaissance_3: { en: "Renaissance Explorer", fr: "Explorateur Renaissance", "zh-Hans": "文艺复兴探索者" },
    impressionist_3: { en: "Impressionist Trail", fr: "Parcours impressionniste", "zh-Hans": "印象派路线" },
    explorer_3: { en: "Explore 3 kinds of art", fr: "Explorez 3 types d'œuvres", "zh-Hans": "探索3类艺术" },
    new_artist: { en: "Meet a new artist", fr: "Rencontrez un nouvel artiste", "zh-Hans": "认识一位新艺术家" },
  };
  return map[id]?.[locale] || map[id]?.en || id;
}

function missionDescription(id: string, locale: Locale): string {
  const map: Record<string, Record<Locale, string>> = {
    scan_3: { en: "Add two more discoveries to unlock your first visit trophy.", fr: "Ajoutez deux découvertes pour débloquer votre premier trophée.", "zh-Hans": "再加入两件发现，解锁第一个参观奖章。" },
    scan_5: { en: "Build a visit worth remembering.", fr: "Construisez une visite qui reste en mémoire.", "zh-Hans": "让这次参观更值得记住。" },
    scan_10: { en: "Turn this into a serious museum story.", fr: "Transformez la visite en vrai parcours.", "zh-Hans": "把参观变成一段真正的博物馆故事。" },
    unique_artists_3: { en: "Find works by different makers.", fr: "Cherchez des œuvres d'artistes différents.", "zh-Hans": "寻找不同创作者的作品。" },
    unique_artists_5: { en: "Broaden the voices in your visit.", fr: "Élargissez les voix de votre visite.", "zh-Hans": "让你的参观遇见更多创作者。" },
    favorite_1: { en: "Heart the work you would show a friend.", fr: "Marquez l'œuvre que vous montreriez à un ami.", "zh-Hans": "收藏一件你想给朋友看的作品。" },
    curated_3: { en: "Collect a few ELYIO highlights.", fr: "Collectionnez quelques temps forts ELYIO.", "zh-Hans": "收集几件 ELYIO 精选亮点。" },
    renaissance_3: { en: "Follow another work from the Renaissance.", fr: "Trouvez une autre œuvre de la Renaissance.", "zh-Hans": "再找一件文艺复兴作品。" },
    impressionist_3: { en: "Follow light, color, and modern brushwork.", fr: "Suivez la lumière, la couleur et la touche moderne.", "zh-Hans": "追寻光、色彩与现代笔触。" },
    explorer_3: { en: "Mix paintings, objects, sculptures, or periods.", fr: "Mêlez peintures, objets, sculptures ou périodes.", "zh-Hans": "看看绘画、器物、雕塑或不同时代。" },
    new_artist: { en: "Scan something by someone you have not met yet.", fr: "Scannez une œuvre d'un artiste encore inédit pour vous.", "zh-Hans": "扫描一件来自新创作者的作品。" },
  };
  return map[id]?.[locale] || map[id]?.en || "";
}

function achievementTitle(id: string, locale: Locale): string {
  const map: Record<string, Record<Locale, string>> = {
    first_discovery: { en: "First Discovery", fr: "Première découverte", "zh-Hans": "第一件发现" },
    curious_eye: { en: "Curious Eye", fr: "Regard curieux", "zh-Hans": "好奇之眼" },
    ten_masterpieces: { en: "10 Masterpieces", fr: "10 chefs-d'œuvre", "zh-Hans": "10件杰作" },
    artist_explorer: { en: "Artist Explorer", fr: "Explorateur d'artistes", "zh-Hans": "艺术家探索者" },
    new_favorite: { en: "New Favorite", fr: "Nouveau favori", "zh-Hans": "新的最爱" },
    renaissance_explorer: { en: "Renaissance Explorer", fr: "Explorateur Renaissance", "zh-Hans": "文艺复兴探索者" },
    impressionist_trail: { en: "Impressionist Trail", fr: "Parcours impressionniste", "zh-Hans": "印象派路线" },
    deep_dive: { en: "Deep Dive", fr: "Immersion", "zh-Hans": "深度探索" },
    billion_euro_visitor: { en: "Billion Euro Visitor", fr: "Visiteur milliardaire", "zh-Hans": "十亿欧元访客" },
    market_giant: { en: "Market Giant", fr: "Géant du marché", "zh-Hans": "市场巨作" },
    museum_explorer: { en: "Museum Explorer", fr: "Explorateur du musée", "zh-Hans": "博物馆探索者" },
  };
  return map[id]?.[locale] || map[id]?.en || id;
}

function achievementDescription(id: string, locale: Locale): string {
  const map: Record<string, Record<Locale, string>> = {
    first_discovery: { en: "You added your first artwork.", fr: "Vous avez ajouté votre première œuvre.", "zh-Hans": "你加入了第一件作品。" },
    curious_eye: { en: "You discovered 5 artworks.", fr: "Vous avez découvert 5 œuvres.", "zh-Hans": "你发现了5件作品。" },
    ten_masterpieces: { en: "You discovered 10 artworks.", fr: "Vous avez découvert 10 œuvres.", "zh-Hans": "你发现了10件作品。" },
    artist_explorer: { en: "You met 5 different artists.", fr: "Vous avez rencontré 5 artistes différents.", "zh-Hans": "你认识了5位不同艺术家。" },
    new_favorite: { en: "You chose a work to remember.", fr: "Vous avez choisi une œuvre à retenir.", "zh-Hans": "你选出了一件值得记住的作品。" },
    renaissance_explorer: { en: "You followed 5 Renaissance works.", fr: "Vous avez suivi 5 œuvres Renaissance.", "zh-Hans": "你看了5件文艺复兴作品。" },
    impressionist_trail: { en: "You followed 5 Impressionist or modern works.", fr: "Vous avez suivi 5 œuvres impressionnistes ou modernes.", "zh-Hans": "你看了5件印象派或现代作品。" },
    deep_dive: { en: "You spent meaningful time exploring.", fr: "Vous avez vraiment pris le temps d'explorer.", "zh-Hans": "你认真探索了一段时间。" },
    billion_euro_visitor: { en: "Your reviewed range crossed €1B.", fr: "Votre fourchette évaluée dépasse 1 Md€.", "zh-Hans": "你的已评估区间超过10亿欧元。" },
    market_giant: { en: "You encountered a nine-figure market benchmark.", fr: "Vous avez croisé un repère de marché à neuf chiffres.", "zh-Hans": "你遇见了九位数级别的市场参照。" },
    museum_explorer: { en: "You built a real museum visit.", fr: "Vous avez construit une vraie visite.", "zh-Hans": "你完成了一次真正的博物馆参观。" },
  };
  return map[id]?.[locale] || map[id]?.en || "";
}

function valueLabel(kind: VisitValueMoment["kind"], locale: Locale): string {
  if (kind === "indicative_total") {
    if (locale === "fr") return "VALEUR TOTALE VUE";
    if (locale === "zh-Hans") return "已观看估计总值";
    return "TOTAL VALUE VIEWED";
  }
  if (kind === "reviewed_estimate") {
    if (locale === "fr") return "FOURCHETTE ÉVALUÉE RENCONTRÉE";
    if (locale === "zh-Hans") return "已评估市场区间";
    return "REVIEWED MARKET RANGE ENCOUNTERED";
  }
  if (kind === "market_context") {
    if (locale === "fr") return "PLUS GRAND MOMENT DE MARCHÉ";
    if (locale === "zh-Hans") return "最强市场瞬间";
    return "BIGGEST MARKET MOMENT";
  }
  if (locale === "fr") return "MOMENT À RETENIR";
  if (locale === "zh-Hans") return "值得记住的一刻";
  return "MOMENT TO REMEMBER";
}

function valueSubtitle(kind: VisitValueMoment["kind"], locale: Locale): string {
  if (kind === "indicative_total") {
    if (locale === "fr") return "estimation indicative ELYIO";
    if (locale === "zh-Hans") return "ELYIO 参考估计";
    return "ELYIO indicative estimate";
  }
  if (kind === "reviewed_estimate") {
    if (locale === "fr") return "fourchette agrégée uniquement pour les œuvres éligibles";
    if (locale === "zh-Hans") return "仅汇总符合条件的已评估作品";
    return "aggregate range for eligible reviewed works only";
  }
  if (locale === "fr") return "aucun total de valeur inventé";
  if (locale === "zh-Hans") return "没有虚构总价值";
  return "no invented total value";
}

function marketSubtitle(artist: string, locale: Locale): string {
  if (locale === "fr") return `${artist} · repère de marché artiste`;
  if (locale === "zh-Hans") return `${artist} · 艺术家市场参照`;
  return `${artist} artist-market benchmark`;
}

function beyondSubtitle(artist: string, locale: Locale): string {
  if (locale === "fr") return `${artist} · contexte seulement`;
  if (locale === "zh-Hans") return `${artist} · 仅作背景参照`;
  return `${artist} context only`;
}
