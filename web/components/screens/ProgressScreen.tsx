"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Heart, ScanLine, Trophy } from "lucide-react";
import { artworkArtistDisplayName } from "@/lib/artist-display";
import { resolveTitle } from "@/lib/artworks";
import { tt } from "@/lib/i18n";
import { buildVisitGame, visitHeadline } from "@/lib/visit-game";
import type { AppState } from "@/lib/app-state";
import type { Artwork } from "@/lib/types";

const editorial = { fontFamily: "var(--font-editorial)" } as const;

export default function ProgressScreen({
  state,
  seenArtworks,
  onBack,
  onContinueScanning,
  onCompleteVisit,
}: {
  state: AppState;
  seenArtworks: Artwork[];
  onBack: () => void;
  onContinueScanning: () => void;
  onCompleteVisit: () => void;
}) {
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    const tick = () => setNow(Date.now());
    tick();
    const intervalId = window.setInterval(tick, 30000);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    trackProgressViewed(state, seenArtworks.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const game = buildVisitGame({
    locale: state.locale,
    museumName: state.museumName,
    museumCity: state.museumCity,
    startTime: state.startTime,
    now: now || state.lastActivityAt || state.startTime || 0,
    seenArtworks,
    favoriteIds: state.favorites,
    unlockedAchievements: state.unlockedAchievements,
  });
  const mission = game.primaryMission;
  const thumbnails = useMemo(() => seenArtworks.slice().reverse(), [seenArtworks]);
  const valueMoment = game.recap.valueMoment;
  const favorite = game.recap.favoriteArtwork;
  const unlocked = game.achievements.filter((a) => a.unlocked);

  return (
    <div className="w-full h-full bg-[#F7F3EC] overflow-y-auto scrollbar-none flex flex-col">
      <div className="px-6 pt-[max(20px,env(safe-area-inset-top))] pb-[116px] flex-1">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={onBack}
            aria-label="Back"
            className="w-9 h-9 rounded-full bg-[rgba(24,23,20,0.055)] flex items-center justify-center"
          >
            <ArrowLeft className="w-4 h-4 text-[#181714]" />
          </button>
          <button type="button" onClick={onCompleteVisit} className="text-[13px] font-semibold text-[#67635C]">
            {tt("complete_visit", state.locale)}
          </button>
        </div>

        <div className="mt-7">
          <div className="text-[11px] font-semibold tracking-[0.13em] uppercase text-[#67635C]">
            {state.museumName || tt("live_progress", state.locale)}
          </div>
          <h1
            className="mt-2 text-[#181714] font-medium leading-[0.95] tracking-[-0.035em]"
            style={{ ...editorial, fontSize: "clamp(40px, 12vw, 56px)" }}
          >
            {visitHeadline(state.museumName, state.locale, game.metrics.artworksCount <= 1)}
          </h1>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-2.5">
          <Stat value={String(game.metrics.artworksCount)} label={game.metrics.artworksCount === 1 ? tt("stat_work_one", state.locale) : tt("works_seen_count", state.locale)} />
          <Stat value={String(game.metrics.artistsCount)} label={game.metrics.artistsCount === 1 ? tt("stat_artist_one", state.locale) : tt("stat_artists", state.locale)} />
          <Stat value={game.metrics.durationLabel} label={tt("stat_time", state.locale)} />
        </div>

        {mission && (
          <section className="mt-7 rounded-[18px] p-4 bg-[#181714] text-[#F8F1E6]">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[10px] font-bold tracking-[0.14em] uppercase text-[#C8BFAF]">
                  {state.locale === "fr" ? "Prochaine mission" : state.locale === "zh-Hans" ? "下一个任务" : "Next mission"}
                </div>
                <div className="mt-1 text-[18px] font-semibold tracking-[-0.015em]">{mission.title}</div>
                <p className="mt-1 text-[12px] leading-[17px] text-[#D9D0BF]">{mission.description}</p>
              </div>
              <div className="text-right shrink-0">
                <div className="text-[22px] font-semibold tabular-nums">{mission.progress}/{mission.target}</div>
                <div className="text-[10px] uppercase tracking-[0.1em] text-[#C8BFAF]">{state.locale === "zh-Hans" ? "进度" : "progress"}</div>
              </div>
            </div>
            <div className="mt-3 h-1.5 rounded-full bg-white/12 overflow-hidden">
              <div className="h-full rounded-full bg-[#F3E8D7]" style={{ width: `${Math.min(100, (mission.progress / mission.target) * 100)}%` }} />
            </div>
          </section>
        )}

        <section className="mt-6 grid grid-cols-2 gap-3">
          <VisitMomentCard valueMoment={valueMoment} />
          <div className="rounded-[16px] bg-[#FBF8F2] border border-[rgba(24,23,20,0.06)] p-4 min-h-[132px]">
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#67635C]">
              <Heart className="w-3.5 h-3.5" />
              {state.locale === "fr" ? "Favori" : state.locale === "zh-Hans" ? "最爱" : "Favorite"}
            </div>
            {favorite ? (
              <>
                <div className="mt-3 text-[14px] font-semibold text-[#181714] leading-[17px]">{artworkArtistDisplayName(favorite, state.locale)}</div>
                <div className="mt-1 text-[13px] leading-[17px] text-[#67635C]" style={editorial}>{resolveTitle(favorite, state.locale)}</div>
              </>
            ) : (
              <p className="mt-3 text-[13px] leading-[18px] text-[#67635C]">
                {state.locale === "fr"
                  ? "Touchez le cœur sur une œuvre à retenir."
                  : state.locale === "zh-Hans"
                    ? "在想记住的作品上点心形。"
                    : "Heart the work you want to remember."}
              </p>
            )}
          </div>
        </section>

        <section className="mt-7">
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-bold tracking-[0.13em] uppercase text-[#67635C]">
              {state.locale === "fr" ? "Trophées" : state.locale === "zh-Hans" ? "成就" : "Achievements"}
            </div>
            <div className="text-[11px] tabular-nums text-[#8B867E]">{unlocked.length}/{game.achievements.length}</div>
          </div>
          <div className="mt-3 flex gap-2.5 overflow-x-auto pb-1 scrollbar-none">
            {game.achievements.slice(0, 8).map((achievement) => (
              <div
                key={achievement.id}
                className={`w-[112px] shrink-0 rounded-[14px] p-3 border ${
                  achievement.unlocked
                    ? "bg-[#181714] border-[#181714] text-[#F8F1E6]"
                    : "bg-[#FBF8F2] border-[rgba(24,23,20,0.07)] text-[#8B867E]"
                }`}
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[13px] font-bold ${
                  achievement.unlocked ? "bg-[#F3E8D7] text-[#181714]" : "bg-[rgba(24,23,20,0.06)] text-[#8B867E]"
                }`}>
                  {achievement.unlocked ? achievement.icon : "·"}
                </div>
                <div className="mt-2 text-[12px] font-semibold leading-[14px]">{achievement.title}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-7">
          <div className="text-[11px] font-bold tracking-[0.13em] uppercase text-[#67635C]">
            {state.locale === "fr" ? "Vos découvertes" : state.locale === "zh-Hans" ? "你的发现" : "Your discoveries"}
          </div>
          {thumbnails.length > 0 ? (
            <div className="mt-3 space-y-2.5">
              {thumbnails.map((artwork) => (
                <div key={artwork.id} className="flex items-center gap-3 rounded-[14px] bg-[#FBF8F2] border border-[rgba(24,23,20,0.06)] p-2.5">
                  <div className="w-12 h-12 rounded-[10px] bg-[#EDE6DA] overflow-hidden shrink-0" style={{ backgroundColor: artwork.accent || "#EDE6DA" }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={artwork.imageUrl} alt="" className="w-full h-full object-cover" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px] font-semibold text-[#181714] truncate">{artworkArtistDisplayName(artwork, state.locale)}</div>
                    <div className="text-[12px] text-[#67635C] truncate" style={editorial}>{resolveTitle(artwork, state.locale)}</div>
                  </div>
                  {state.favorites.has(artwork.id) && <Heart className="w-4 h-4 text-[#8C3328] fill-[#8C3328]" />}
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-3 rounded-[16px] bg-[#FBF8F2] border border-[rgba(24,23,20,0.06)] p-4 text-[13px] leading-[18px] text-[#67635C]">
              {state.locale === "fr"
                ? "Scannez votre première œuvre pour commencer votre visite."
                : state.locale === "zh-Hans"
                  ? "扫描第一件作品，开始你的参观。"
                  : "Scan your first artwork to start building your visit."}
            </div>
          )}
        </section>
      </div>

      <div className="sticky bottom-0 left-0 right-0 p-3 pb-[max(28px,env(safe-area-inset-bottom))] space-y-3 bg-gradient-to-t from-[#F7F3EC] via-[#F7F3EC]/92 to-transparent">
        <button
          type="button"
          onClick={onContinueScanning}
          className="w-full h-[60px] rounded-[14px] bg-[#181714] text-[#FAF7F0] flex items-center justify-center gap-2 text-[15px] font-semibold"
          style={{ boxShadow: "0 8px 22px rgba(16,15,13,0.16)" }}
        >
          <ScanLine className="w-4 h-4" />
          {tt("scan_next_artwork", state.locale)}
        </button>
        <button
          type="button"
          onClick={onCompleteVisit}
          className="w-full h-[50px] rounded-[14px] bg-[rgba(24,23,20,0.055)] border border-[rgba(24,23,20,0.06)] text-[#25231F] text-[15px] font-medium"
        >
          {tt("complete_visit_button", state.locale)}
        </button>
      </div>
    </div>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-[16px] bg-[#FBF8F2] border border-[rgba(24,23,20,0.06)] p-3">
      <div className="text-[26px] leading-none font-medium text-[#181714] tabular-nums" style={editorial}>{value}</div>
      <div className="mt-1.5 text-[10px] font-bold uppercase tracking-[0.1em] text-[#67635C]">{label}</div>
    </div>
  );
}

function VisitMomentCard({ valueMoment }: { valueMoment: ReturnType<typeof buildVisitGame>["recap"]["valueMoment"] }) {
  return (
    <div className="rounded-[16px] bg-[#FBF8F2] border border-[rgba(24,23,20,0.06)] p-4 min-h-[132px]">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#67635C]">
        <Trophy className="w-3.5 h-3.5" />
        {valueMoment.label}
      </div>
      {valueMoment.kind === "none" ? (
        <p className="mt-3 text-[13px] leading-[18px] text-[#67635C]">{valueMoment.subtitle}</p>
      ) : (
        <>
          <div className="mt-3 text-[24px] leading-none font-medium text-[#181714] tabular-nums" style={editorial}>{valueMoment.valueText}</div>
          <div className="mt-2 text-[12px] leading-[16px] text-[#67635C]">{valueMoment.subtitle}</div>
        </>
      )}
    </div>
  );
}

function trackProgressViewed(state: AppState, worksCount: number) {
  void import("@/lib/analytics").then(({ track }) => track("progress_viewed", { museum_id: state.museumId, works_count: worksCount }));
}
