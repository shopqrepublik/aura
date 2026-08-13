"use client";

import { useEffect } from "react";
import { buildVisitGame } from "@/lib/visit-game";
import type { AppState } from "@/lib/app-state";
import type { Artwork } from "@/lib/types";

export default function VisitToast({
  state,
  seenArtworks,
  onDismissAchievement,
  onDismissMission,
}: {
  state: AppState;
  seenArtworks: Artwork[];
  onDismissAchievement: () => void;
  onDismissMission: () => void;
}) {
  const game = buildVisitGame({
    locale: state.locale,
    museumName: state.museumName,
    museumCity: state.museumCity,
    startTime: state.startTime,
    now: state.lastActivityAt || state.startTime || 0,
    seenArtworks,
    favoriteIds: state.favorites,
    unlockedAchievements: state.unlockedAchievements,
  });
  const achievement = state.achievementToast
    ? game.achievements.find((a) => a.id === state.achievementToast)
    : null;
  const mission = !achievement && state.missionToast
    ? game.missions.find((m) => m.id === state.missionToast)
    : null;

  useEffect(() => {
    if (!achievement && !mission) return;
    const id = window.setTimeout(() => {
      if (achievement) onDismissAchievement();
      if (mission) onDismissMission();
    }, 3200);
    return () => window.clearTimeout(id);
  }, [achievement, mission, onDismissAchievement, onDismissMission]);

  if (!achievement && !mission) return null;

  const title = achievement?.title || mission?.title || "";
  const body = achievement?.description || mission?.description || "";
  const eyebrow = achievement
    ? state.locale === "fr"
      ? "Trophée débloqué"
      : state.locale === "zh-Hans"
        ? "成就已解锁"
        : "Achievement unlocked"
    : state.locale === "fr"
      ? "Mission terminée"
      : state.locale === "zh-Hans"
        ? "任务完成"
        : "Mission complete";
  const icon = achievement?.icon || "✓";

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-[92px] z-[80] flex justify-center px-4">
      <div
        className="pointer-events-auto w-full max-w-[390px] rounded-[18px] px-4 py-3 flex items-center gap-3"
        style={{ background: "rgba(24,23,20,0.94)", color: "#F8F1E6", boxShadow: "0 18px 42px rgba(0,0,0,0.26)" }}
      >
        <div className="w-10 h-10 rounded-full bg-[#F3E8D7] text-[#181714] flex items-center justify-center text-[18px] font-bold shrink-0">
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.14em] text-[#C8BFAF]">{eyebrow}</div>
          <div className="mt-0.5 text-[14px] font-semibold truncate">{title}</div>
          <div className="mt-0.5 text-[12px] leading-[16px] text-[#D8CFBE] line-clamp-2">{body}</div>
        </div>
        <button
          type="button"
          onClick={achievement ? onDismissAchievement : onDismissMission}
          className="shrink-0 text-[12px] font-semibold text-[#F3E8D7]"
        >
          OK
        </button>
      </div>
    </div>
  );
}
