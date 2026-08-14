"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Download, Heart, Share2, Trophy } from "lucide-react";
import { artworkArtistDisplayName } from "@/lib/artist-display";
import { resolveTitle } from "@/lib/artworks";
import { tt } from "@/lib/i18n";
import { generateRecapImage } from "@/lib/recap-image";
import { buildVisitGame, visitHeadline } from "@/lib/visit-game";
import { buildVisitPalette } from "@/lib/visitPalette";
import { track } from "@/lib/analytics";
import type { AppState } from "@/lib/app-state";
import type { Artwork } from "@/lib/types";

const editorial = { fontFamily: "var(--font-editorial)" } as const;

function formatDate(ts: number): string {
  const d = new Date(ts);
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
}

export default function RecapScreen({
  state,
  seenArtworks,
  onNewVisit,
}: {
  state: AppState;
  seenArtworks: Artwork[];
  onNewVisit: () => void;
}) {
  const [now, setNow] = useState<number | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewBlob, setPreviewBlob] = useState<Blob | null>(null);
  const [imageBusy, setImageBusy] = useState<"preview" | "share" | "save" | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    const id = window.setTimeout(() => setNow(Date.now()), 0);
    return () => window.clearTimeout(id);
  }, []);

  const game = buildVisitGame({
    locale: state.locale,
    museumName: state.museumName,
    museumCity: state.museumCity,
    startTime: state.startTime,
    now: now || state.completedAt || state.lastActivityAt || state.startTime || 0,
    seenArtworks,
    favoriteIds: state.favorites,
    unlockedAchievements: state.unlockedAchievements,
  });
  const dateStr = formatDate(state.startTime ?? now ?? state.completedAt ?? state.lastActivityAt ?? 0);
  const palette = buildVisitPalette(seenArtworks);
  const favorite = game.recap.favoriteArtwork;
  const heroArtwork = game.recap.heroArtwork;
  const achievement = game.recap.topAchievement;
  const valueMoment = game.recap.valueMoment;

  useEffect(() => {
    track("recap_generated", {
      works_count: game.metrics.artworksCount,
      artists_count: game.metrics.artistsCount,
      museum_id: state.museumId,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function buildImage(): Promise<Blob | null> {
    return generateRecapImage({
      locale: state.locale,
      museumName: state.museumName || "ELYIO",
      museumLocation: state.museumCity || "",
      headline: visitHeadline(state.museumName, state.locale, game.metrics.artworksCount <= 1),
      dateStr,
      worksCount: game.metrics.artworksCount,
      artistsCount: game.metrics.artistsCount,
      timeStr: game.metrics.durationLabel,
      favoriteArtwork: favorite,
      heroArtwork,
      favoriteArtist: favorite ? artworkArtistDisplayName(favorite, state.locale) : heroArtwork ? artworkArtistDisplayName(heroArtwork, state.locale) : "",
      favoriteTitle: favorite ? resolveTitle(favorite, state.locale) : heroArtwork ? resolveTitle(heroArtwork, state.locale) : "",
      valueMoment,
      achievementTitle: achievement?.title || "",
      achievementIcon: achievement?.icon || "",
      paletteAccents: palette.accents,
      paletteWorks: palette.works.map((w) => ({ imageUrl: w.imageUrl, accent: w.accent })),
    });
  }

  async function ensurePreview(): Promise<Blob | null> {
    if (previewBlob) return previewBlob;
    setImageBusy("preview");
    try {
      const blob = await buildImage();
      if (blob) {
        setPreviewBlob(blob);
        setPreviewUrl(await blobToDataUrl(blob));
        track("share_card_viewed", { works_count: game.metrics.artworksCount, museum_id: state.museumId });
      }
      return blob;
    } finally {
      setImageBusy(null);
    }
  }

  async function openPreview() {
    const blob = await ensurePreview();
    if (blob) setShowPreview(true);
  }

  async function handleShare() {
    setImageBusy("share");
    track("share_clicked", { works_count: game.metrics.artworksCount, museum_id: state.museumId });
    track("share_started", { works_count: game.metrics.artworksCount, museum_id: state.museumId });
    try {
      const blob = await ensurePreview();
      const text = shareText(state, game);
      const file = blob ? new File([blob], "elyio-visit-trophy.png", { type: "image/png" }) : null;
      if (file && navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: "ELYIO", text });
          track("share_completed", { method: "web_share_files" });
        } catch {
          // Native share sheet cancellation is not an error.
        }
        return;
      }
      if (navigator.share) {
        try {
          await navigator.share({ title: "ELYIO", text });
          track("share_completed", { method: "web_share_text" });
        } catch {
          // Native share sheet cancellation is not an error.
        }
        return;
      }
      if (blob) {
        downloadBlob(blob);
        track("share_completed", { method: "download_fallback" });
      }
    } finally {
      setImageBusy(null);
    }
  }

  async function handleSave() {
    setImageBusy("save");
    try {
      const blob = await ensurePreview();
      if (blob) {
        downloadBlob(blob);
        track("share_saved", { works_count: game.metrics.artworksCount, museum_id: state.museumId });
      }
    } finally {
      setImageBusy(null);
    }
  }

  function downloadBlob(blob: Blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "elyio-visit-trophy.png";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="relative w-full h-full overflow-y-auto scrollbar-none bg-[#11100E] text-[#F6EBDD]">
      <div className="relative min-h-full px-6 pt-[max(24px,env(safe-area-inset-top))] pb-[max(28px,env(safe-area-inset-bottom))] overflow-hidden">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: "radial-gradient(circle at 20% 0%, rgba(168,126,76,0.28), transparent 36%), linear-gradient(145deg,#12100E 0%,#29362F 52%,#0E0D0B 100%)" }}
        />
        {heroArtwork && (
          <div className="absolute inset-x-0 top-0 h-[46%] opacity-[0.28] pointer-events-none overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={heroArtwork.imageUrl}
              alt=""
              data-image-source-type={heroArtwork.imageSourceType || "UNKNOWN"}
              data-image-source-id={heroArtwork.imageSourceId || ""}
              className="w-full h-full object-cover grayscale-[15%] contrast-110"
            />
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#11100E]/35 to-[#11100E]" />
          </div>
        )}

        <div className="relative z-10">
          <div className="flex items-center justify-between">
            <div className="text-[19px] tracking-[0.18em] font-medium" style={editorial}>ELYIO</div>
            <div className="w-8 h-8 rounded-full bg-[#F3E8D7] text-[#181714] flex items-center justify-center text-[12px] font-bold">E</div>
          </div>

          <div className="mt-[64px]">
            <div className="text-[12px] font-bold tracking-[0.15em] uppercase text-[#C8BFAF]">
              {state.museumName || "ELYIO"}
            </div>
            <h1 className="mt-2 font-medium leading-[0.9] tracking-[-0.035em]" style={{ ...editorial, fontSize: "clamp(42px, 12vw, 60px)" }}>
              {visitHeadline(state.museumName, state.locale, game.metrics.artworksCount <= 1)}
            </h1>
          </div>

          <div className="mt-7 grid grid-cols-3 gap-3">
            <RecapStat value={String(game.metrics.artworksCount)} label={game.metrics.artworksCount === 1 ? tt("stat_work_one", state.locale) : tt("works_seen_count", state.locale)} />
            <RecapStat value={String(game.metrics.artistsCount)} label={game.metrics.artistsCount === 1 ? tt("stat_artist_one", state.locale) : tt("stat_artists", state.locale)} />
            <RecapStat value={game.metrics.durationLabel} label={tt("stat_time", state.locale)} />
          </div>

          {(favorite || heroArtwork) && (
            <section className="mt-8 rounded-[20px] border border-white/12 bg-white/[0.055] overflow-hidden">
              {heroArtwork && (
                <div className="aspect-[4/3] bg-[#2F3730] overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={heroArtwork.imageUrl}
                    alt=""
                    data-image-source-type={heroArtwork.imageSourceType || "UNKNOWN"}
                    data-image-source-id={heroArtwork.imageSourceId || ""}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="p-4">
                <div className="flex items-center gap-2 text-[10px] font-bold tracking-[0.14em] uppercase text-[#C8BFAF]">
                  <Heart className="w-3.5 h-3.5" />
                  {favorite ? (state.locale === "fr" ? "Votre favori" : state.locale === "zh-Hans" ? "你的最爱" : "Your favorite") : (state.locale === "fr" ? "Moment fort" : state.locale === "zh-Hans" ? "亮点" : "Highlight")}
                </div>
                <div className="mt-2 text-[20px] font-medium" style={editorial}>
                  {favorite ? artworkArtistDisplayName(favorite, state.locale) : heroArtwork ? artworkArtistDisplayName(heroArtwork, state.locale) : ""}
                </div>
                <div className="text-[15px] text-[#D8CFBE]" style={editorial}>
                  {favorite ? resolveTitle(favorite, state.locale) : heroArtwork ? resolveTitle(heroArtwork, state.locale) : ""}
                </div>
              </div>
            </section>
          )}

          {valueMoment.kind !== "none" && (
            <section className="mt-5 rounded-[18px] bg-[#F3E8D7] text-[#181714] p-4">
              <div className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#605649]">{valueMoment.label}</div>
              <div className="mt-1 font-medium leading-none tabular-nums" style={{ ...editorial, fontSize: "clamp(38px, 12vw, 54px)" }}>{valueMoment.valueText}</div>
              <div className="mt-2 text-[13px] leading-[18px] text-[#4B453D]">{valueMoment.subtitle}</div>
            </section>
          )}

          {achievement && (
            <section className="mt-5 rounded-[18px] border border-[#F3E8D7]/22 bg-[#F3E8D7]/8 p-4 flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-[#F3E8D7] text-[#181714] flex items-center justify-center text-[18px] font-bold">
                {achievement.icon || <Trophy className="w-5 h-5" />}
              </div>
              <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.13em] text-[#C8BFAF]">{state.locale === "fr" ? "Trophée" : state.locale === "zh-Hans" ? "成就" : "Achievement"}</div>
                <div className="mt-1 text-[18px] font-semibold">{achievement.title}</div>
              </div>
            </section>
          )}

          <div className="mt-8 space-y-3">
            <button
              type="button"
              onClick={openPreview}
              disabled={imageBusy !== null}
              className="w-full h-[54px] rounded-[15px] bg-[#F3E8D7] text-[#181714] text-[15px] font-semibold flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Share2 className="w-4 h-4" />
              {imageBusy === "preview" ? tt("generating_image", state.locale) : tt("share_your_visit", state.locale)}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={imageBusy !== null}
              className="w-full h-[50px] rounded-[15px] bg-white/[0.07] border border-white/15 text-[#F3E8D7] text-[14px] font-semibold flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Download className="w-4 h-4" />
              {imageBusy === "save" ? tt("generating_image", state.locale) : tt("save_image", state.locale)}
            </button>
            <button type="button" onClick={onNewVisit} className="w-full text-center text-[13px] font-semibold pt-1 text-[#C8BFAF]">
              {tt("new_visit", state.locale)}
            </button>
            <p className="text-[11px] text-center pt-2 text-[#8A8172]">Point. Discover. Understand. · elyio.co</p>
          </div>
        </div>
      </div>

      {showPreview && previewUrl && (
        <div className="fixed inset-0 z-[90] bg-[#11100E]/96 px-5 pt-[max(20px,env(safe-area-inset-top))] pb-[max(20px,env(safe-area-inset-bottom))] flex flex-col">
          <div className="flex items-center justify-between text-[#F3E8D7]">
            <button type="button" onClick={() => setShowPreview(false)} className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="text-[12px] font-bold uppercase tracking-[0.14em]">{state.locale === "fr" ? "Carte souvenir" : state.locale === "zh-Hans" ? "分享卡片" : "Share card"}</div>
            <div className="w-10" />
          </div>
          <div className="mt-4 flex-1 min-h-0 flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={previewUrl} alt="ELYIO visit recap" className="max-h-full max-w-full rounded-[18px] shadow-[0_18px_60px_rgba(0,0,0,0.38)]" />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={handleShare}
              disabled={imageBusy !== null}
              className="h-[52px] rounded-[14px] bg-[#F3E8D7] text-[#181714] text-[15px] font-semibold disabled:opacity-60"
            >
              {imageBusy === "share" ? tt("generating_image", state.locale) : state.locale === "fr" ? "Partager" : state.locale === "zh-Hans" ? "分享" : "Share"}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={imageBusy !== null}
              className="h-[52px] rounded-[14px] bg-white/[0.08] border border-white/15 text-[#F3E8D7] text-[15px] font-semibold disabled:opacity-60"
            >
              {imageBusy === "save" ? tt("generating_image", state.locale) : tt("save_image", state.locale)}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function RecapStat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-[16px] bg-white/[0.075] border border-white/12 px-3 py-3">
      <div className="text-[27px] leading-none font-medium tabular-nums" style={editorial}>{value}</div>
      <div className="mt-2 text-[9px] font-bold uppercase tracking-[0.11em] text-[#C8BFAF]">{label}</div>
    </div>
  );
}

function shareText(state: AppState, game: ReturnType<typeof buildVisitGame>): string {
  const museum = state.museumName || "ELYIO";
  const works = game.metrics.artworksCount;
  const artists = game.metrics.artistsCount;
  if (state.locale === "fr") return `${works} ${works === 1 ? "œuvre" : "œuvres"}, ${artists} ${artists === 1 ? "artiste" : "artistes"} — ${museum} — ELYIO`;
  if (state.locale === "zh-Hans") return `${museum}：${works}件作品，${artists}位艺术家 — ELYIO`;
  return `${works} ${works === 1 ? "artwork" : "artworks"}, ${artists} ${artists === 1 ? "artist" : "artists"} — ${museum} — ELYIO`;
}
