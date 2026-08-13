"use client";

import { useEffect, useMemo, useState } from "react";
import { preload } from "react-dom";
import { ArrowRight, ChevronDown, Download, X } from "lucide-react";
import { MISSIONS, missionLabel } from "@/lib/artworks";
import { isMissionComplete } from "@/lib/missions";
import { tt, LOCALES } from "@/lib/i18n";
import { useMuseumDetection } from "@/lib/geolocation";
import { proxyImageUrl } from "@/lib/visitPalette";
import { formatVisitValueHeadline, summarizeVisitValue } from "@/lib/valueReveal";
import { ORSAY_CLOCK_IMAGE_URL as HERO_IMAGE_URL } from "@/lib/museumTheme";
import { usePwaInstall } from "@/lib/pwaInstall";
import { track } from "@/lib/analytics";
import type { AppState } from "@/lib/app-state";
import type { Artwork } from "@/lib/types";
import type { Museum } from "@/lib/api";

// Home Screen Redesign -- "the cover of the ELYIO experience", not a
// dashboard. Rebuilds the visual layer only; three pieces of real logic are
// carried over unchanged from the previous implementation:
//   1. useMuseumDetection() (lib/geolocation.ts) -- the 4-state GPS/geofence
//      hook itself is untouched. Its honesty (green=GPS-detected,
//      grey=unconfirmed, blue=manually-confirmed, pulsing=locating) now
//      lives in a small dot next to the static "MUSÉE D'ORSAY" label instead
//      of a whole colored pill, per explicit instruction not to let a
//      statically-styled museum name silently read as "confirmed" regardless
//      of real GPS state.
//   2. isMissionComplete() (lib/missions.ts) against real state.seen -- only
//      the numbering (editorial "01/02/03" instead of ProgressRing circles)
//      and card materials changed.
//   3. state.visitStarted / state.seen, already tracked by useElyioApp --
//      "Continue visit" (§17) is a new READ of this existing state, not a
//      new storage mechanism.
const MISSION_EYEBROW_KEY: Record<string, string> = {
  m1: "mission_eyebrow_m1",
  m2: "mission_eyebrow_m2",
  m3: "mission_eyebrow_m3",
};

const editorial = { fontFamily: "var(--font-editorial)" } as const;

const FEATURED_MUSEUM_IDS = new Set([
  "louvre",
  "orsay",
  "orangerie",
  "versailles",
  "museofile_m5044", // Musée Rodin
  "museofile_m5043", // Musée Picasso Paris
  "museofile_m5055", // Musée du quai Branly - Jacques Chirac
  "museofile_m1111", // Petit Palais
  "museofile_m1104", // Musée Carnavalet
  "museofile_m5025", // Musée de l'Armée
  "museofile_m5005", // Musée Guimet
  "museofile_m5003", // Musée de Cluny
]);

function normalizedMuseumText(value: string | null | undefined): string {
  return (value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function museumLocationLabel(museum: Museum | null): string {
  if (!museum) return "Paris";
  if (museum.city && museum.region) return `${museum.city} · ${museum.region}`;
  return museum.city || museum.region || "France";
}

function museumExperienceKey(museum: Museum | null): string {
  return museum?.experience_level === "CURATED" ? "museum_curated_label" : "museum_ai_guide_label";
}

export default function HomeScreen({
  state,
  seenArtworks,
  onStartVisit,
  onSetLocale,
}: {
  state: AppState;
  seenArtworks: Artwork[];
  // Phase 2 §1 -- takes the resolved museum id (detected via GPS or
  // manually confirmed from useMuseumDetection below) instead of assuming
  // a single hardcoded museum.
  onStartVisit: (museumId: string, museumName?: string | null, museumCity?: string | null) => void;
  onSetLocale: (locale: AppState["locale"]) => void;
}) {
  const { status: museumStatus, museums, museum, confirmManually } = useMuseumDetection();
  const activeMuseum = museum ?? museums[0] ?? null;
  const activeMuseumName = activeMuseum?.name ?? "";
  const [showConfirm, setShowConfirm] = useState(false);
  const [showMuseumSheet, setShowMuseumSheet] = useState(false);
  const [museumSearch, setMuseumSearch] = useState("");
  const [iosInstallDismissed, setIosInstallDismissed] = useState(() =>
    typeof window !== "undefined" ? window.localStorage.getItem("elyio-ios-install-dismissed") === "1" : false
  );
  const { canPromptInstall, installed, isIosSafari, promptInstall } = usePwaInstall();

  // LCP element on mobile (Lighthouse-flagged) -- hoists a <link
  // rel="preload" as="image" fetchPriority="high"> into <head> via React
  // 19's resource-preloading API, same URL as the actual hero <img> below
  // so the browser dedupes the preload against the real fetch instead of
  // downloading it twice.
  preload(proxyImageUrl(HERO_IMAGE_URL), { as: "image", fetchPriority: "high" });

  const isReturning = state.visitStarted;
  const shouldShowIosInstallHint = isIosSafari && !installed && !iosInstallDismissed;
  const activeMuseumLocation = museumLocationLabel(activeMuseum);
  const activeMuseumExperience = tt(museumExperienceKey(activeMuseum), state.locale);
  const featuredMuseums = useMemo(() => {
    const featured = museums.filter((m) => FEATURED_MUSEUM_IDS.has(m.id));
    const idWeight = (id: string) => Array.from(FEATURED_MUSEUM_IDS).indexOf(id);
    return featured.sort((a, b) => idWeight(a.id) - idWeight(b.id)).slice(0, 12);
  }, [museums]);
  const visibleMuseums = useMemo(() => {
    const query = normalizedMuseumText(museumSearch.trim());
    const source = query
      ? museums.filter((m) => {
          const haystack = normalizedMuseumText(
            [m.name, m.common_name, m.city, m.department, m.region, m.external_id].filter(Boolean).join(" ")
          );
          return haystack.includes(query);
        })
      : museums.filter((m) => !FEATURED_MUSEUM_IDS.has(m.id));
    return source.slice(0, 80);
  }, [museums, museumSearch]);

  useEffect(() => {
    if (shouldShowIosInstallHint) track("pwa_ios_instructions_shown");
  }, [shouldShowIosInstallHint]);

  const valueText = formatVisitValueHeadline(summarizeVisitValue(seenArtworks), state.locale);
  const worksLabel =
    seenArtworks.length === 1 ? tt("stat_work_one", state.locale) : tt("works_seen_count", state.locale).toLowerCase();

  const statusText =
    museumStatus === "detected"
      ? tt("museum_detected", state.locale).replace("{museum}", museum?.name ?? "")
      : museumStatus === "manual-confirmed"
        ? tt("museum_confirmed_manual", state.locale).replace("{museum}", museum?.name ?? "")
        : museumStatus === "manual-prompt"
          ? tt("museum_select_prompt", state.locale)
          : tt("museum_locating", state.locale);

  const dotClass =
    museumStatus === "detected"
      ? "bg-[#30D158] shadow-[0_0_6px_#30D158]"
      : museumStatus === "manual-confirmed"
        ? "bg-[#0A84FF] shadow-[0_0_6px_#0A84FF]"
        : museumStatus === "manual-prompt"
          ? "bg-[#8B867E]"
          : "bg-[#8B867E] animate-pulse";

  return (
    <div className="relative w-full h-full bg-[#F7F3EC] overflow-y-auto scrollbar-none">
      {/* Hero: museum image, warm editorial overlay, subtle grain -- §1 */}
      <div className="absolute top-0 left-0 right-0 h-[300px] overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={proxyImageUrl(HERO_IMAGE_URL)}
          alt=""
          fetchPriority="high"
          className="w-full h-full object-cover"
          style={{ filter: "saturate(0.72) contrast(0.92) brightness(0.96)" }}
        />
        {/* Legibility scrim -- independent of the photo's own local
            brightness (this crop has a bright sky behind the clock face
            right where the wordmark/title sit), guarantees the cream text
            above always has a dark ground under it instead of hoping the
            photo happens to be dark there. */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(10,9,7,0.62) 0%, rgba(10,9,7,0.44) 35%, rgba(10,9,7,0.22) 70%, rgba(10,9,7,0) 92%)",
          }}
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(20,26,29,0.14) 0%, rgba(29,31,29,0.20) 28%, rgba(247,243,236,0.90) 62%, #F7F3EC 82%)",
          }}
        />
      </div>

      {/* Top navigation -- §3 */}
      <div className="relative z-10 flex items-center justify-between px-6 pt-[max(20px,env(safe-area-inset-top))]">
        <div
          style={{ ...editorial, textShadow: "0 1px 8px rgba(0,0,0,0.45)" }}
          className="text-[20px] font-medium tracking-[0.18em] text-[#F5EBDD]"
        >
          ELYIO
        </div>
        <select
          aria-label="Language"
          value={state.locale}
          onChange={(e) => {
            const locale = e.target.value as AppState["locale"];
            track("language_selected", { locale });
            onSetLocale(locale);
          }}
          className="h-[36px] px-3 rounded-[12px] bg-[rgba(247,243,236,0.88)] border border-white/25 text-[12px] font-medium text-[#181714]"
        >
          {LOCALES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.code === "zh-Hans" ? "中文" : l.code.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      {/* Museum identity -- static name, honest GPS dot preserved -- §3, requirement 1 */}
      <div className="relative z-10 mt-[30px] px-6">
        <button
          type="button"
          onClick={() => setShowMuseumSheet(true)}
          className="flex items-center gap-2"
        >
          {/* Lighthouse tap-target audit: the visual dot stays 7x7 (it's a
              status indicator, not meant to look like a button), but the
              actual hit area grows to the 24x24 WCAG 2.5.8 minimum via
              negative margin -- the box lays out as if it were still 7x7
              (same -8.5px margin on all sides pulls the extra 17px back out
              of the surrounding flex gap), so nothing around it shifts,
              only the invisible clickable/tappable region grows. */}
          <span
            role="button"
            tabIndex={0}
            aria-label={statusText}
            onClick={(e) => {
              e.stopPropagation();
              if (museumStatus === "manual-prompt") setShowConfirm((v) => !v);
            }}
            className="shrink-0 flex items-center justify-center"
            style={{ width: 24, height: 24, margin: "-8.5px" }}
          >
            <span className={`w-[7px] h-[7px] rounded-full ${dotClass}`} />
          </span>
          <div className="text-left" style={{ textShadow: "0 1px 6px rgba(0,0,0,0.4)" }}>
            <div className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[rgba(247,241,230,0.92)]">
              {activeMuseumName.toUpperCase()}
            </div>
            <div className="text-[11px] font-medium text-[rgba(247,241,230,0.68)]">
              {activeMuseumLocation.toUpperCase()}
            </div>
          </div>
          <ChevronDown
            className="w-[14px] h-[14px] text-[rgba(247,241,230,0.68)]"
            style={{ filter: "drop-shadow(0 1px 4px rgba(0,0,0,0.4))" }}
          />
        </button>
        <span className="sr-only" role="status">
          {statusText}
        </span>

        {showConfirm && (
          <div className="absolute top-[54px] left-6 w-[240px] rounded-[16px] bg-[#FDFBF7] shadow-[0_12px_32px_rgba(0,0,0,0.2)] p-3 z-30">
            <p className="text-[13px] font-semibold text-[#181714] text-center leading-[18px]">
              {tt("museum_confirm_question", state.locale).replace("{museum}", activeMuseumName)}
            </p>
            <div className="mt-2.5 flex gap-2">
              <button
                type="button"
                onClick={() => setShowConfirm(false)}
                className="flex-1 h-[32px] rounded-full bg-[#EDE6DA] text-[12px] font-semibold text-[#181714]"
              >
                {tt("museum_confirm_not_now", state.locale)}
              </button>
              <button
                type="button"
                onClick={() => {
                  confirmManually();
                  setShowConfirm(false);
                }}
                className="flex-1 h-[32px] rounded-full bg-[#181714] text-[12px] font-semibold text-white"
              >
                {tt("museum_confirm_yes", state.locale)}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Hero statement -- first-use (§4/§5) or Continue-visit (§17) */}
      {isReturning ? (
        // Clears the hero image/scrim entirely rather than overlapping it --
        // unlike the first-use headline, nothing here needs the cover-page
        // drama, so it's simpler to guarantee contrast by sitting fully on
        // the warm canvas below the image.
        <div className="relative z-10 mt-[160px] px-6 max-w-[330px]">
          <div
            style={{ textShadow: "0 1px 2px rgba(0,0,0,0.4), 0 1px 6px rgba(0,0,0,0.25)" }}
            className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[#8B867E]"
          >
            {tt("welcome_back_label", state.locale)}
          </div>
          <h1
            style={editorial}
            className="mt-2 text-[clamp(30px,8vw,38px)] leading-[1.05] font-medium tracking-[-0.03em] text-[#181714]"
          >
            {tt("continue_visit_heading", state.locale)}
          </h1>
          {seenArtworks.length > 0 && (
            <p className="mt-2 text-[15px] leading-[21px] text-[#4F4C46]">
              {tt("continue_visit_stat", state.locale)
                .replace("{n}", String(seenArtworks.length))
                .replace("{works}", worksLabel)
                .replace("{value}", valueText)}
            </p>
          )}
        </div>
      ) : (
        <div className="relative z-10 mt-[24px] px-6 max-w-[330px]">
          <h1
            style={{ ...editorial, textShadow: "0 2px 16px rgba(0,0,0,0.5), 0 1px 4px rgba(0,0,0,0.45)" }}
            className="text-[clamp(42px,11.5vw,56px)] leading-[0.94] font-medium tracking-[-0.035em] text-[#F5EBDD]"
          >
            {tt("home_hero_title", state.locale)}
          </h1>
          <p
            // Lighthouse/axe color-contrast audit flagged this paragraph
            // (title above is large-text, clears WCAG's more lenient 3:1;
            // this is 16px body text needing 4.5:1). First attempt used a
            // semi-transparent backdrop (rgba(...,0.34)) -- axe's contrast
            // checker resolves an element's effective background by walking
            // CSS `background-color` up the DOM ANCESTOR chain, which can't
            // see the hero photo (a sibling <img>, not a CSS background on
            // any ancestor); a translucent backdrop just made axe keep
            // walking up to <body>'s cream background, so it still failed.
            // A fully OPAQUE backdrop + fully opaque text color removes that
            // ambiguity outright -- axe now has a real, unambiguous pair of
            // solid colors, ~16:1 by the WCAG formula, well past 4.5:1.
            style={{
              textShadow: "0 1px 2px rgba(0,0,0,0.5)",
              background: "#141210",
              borderRadius: 10,
              padding: "6px 10px",
              margin: "20px -10px 0",
            }}
            className="text-[16px] leading-[23px] text-[#F5EBDD] max-w-[325px] inline-block"
          >
            {tt("home_hero_subtitle", state.locale)}
          </p>
        </div>
      )}

      {/* Primary CTA -- §7, no black circle. Starts an anonymous/local visit
          immediately: server-side visit persistence remains best-effort in
          app-state.ts, but recognition and progress must not wait for
          account creation. */}
      <div className="relative z-10 mt-[28px] px-6">
        <button
          type="button"
          onClick={() => {
            if (activeMuseum) onStartVisit(activeMuseum.id, activeMuseum.name, activeMuseum.city || activeMuseum.region || null);
          }}
          className="w-full h-[58px] px-5 rounded-[14px] bg-[#181714] text-[#FAF6ED] flex items-center justify-between shadow-[0_9px_24px_rgba(21,18,14,0.16)] active:scale-[0.985] transition-transform"
        >
          <span className="text-[16px] font-medium tracking-[-0.01em]">
            {isReturning ? tt("continue_visit_button", state.locale) : tt("start_visit_label", state.locale)}
          </span>
          <ArrowRight className="w-[18px] h-[18px]" />
        </button>
      </div>

      {(canPromptInstall || shouldShowIosInstallHint) && (
        <div
          className="relative z-10 mt-3 mx-6 rounded-[16px] px-4 py-3 flex items-start gap-3"
          style={{
            background: "rgba(253,251,247,0.92)",
            border: "1px solid rgba(34,29,23,0.10)",
            boxShadow: "0 10px 26px rgba(25,21,16,0.10)",
          }}
        >
          <div className="mt-0.5 w-8 h-8 rounded-[10px] bg-[#181714] text-[#FAF6ED] flex items-center justify-center shrink-0">
            <Download className="w-4 h-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[13px] font-semibold tracking-[-0.01em] text-[#181714]">
              {shouldShowIosInstallHint ? tt("pwa_ios_install_title", state.locale) : tt("pwa_install_title", state.locale)}
            </div>
            <p className="mt-1 text-[12px] leading-[17px] text-[#67635C]">
              {shouldShowIosInstallHint ? tt("pwa_ios_install_body", state.locale) : tt("pwa_install_body", state.locale)}
            </p>
            {canPromptInstall && (
              <button
                type="button"
                onClick={promptInstall}
                className="mt-2 h-[32px] px-3 rounded-full bg-[#181714] text-[#FAF6ED] text-[12px] font-semibold active:scale-[0.98] transition-transform"
              >
                {tt("pwa_install_action", state.locale)}
              </button>
            )}
          </div>
          {shouldShowIosInstallHint && (
            <button
              type="button"
              aria-label={tt("pwa_install_dismiss", state.locale)}
              onClick={() => {
                window.localStorage.setItem("elyio-ios-install-dismissed", "1");
                setIosInstallDismissed(true);
              }}
              className="w-8 h-8 rounded-full flex items-center justify-center text-[#67635C] active:scale-[0.96] transition-transform"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {/* Today's visit -- §7 */}
      <div
        className="relative z-10 mt-[24px] mx-6 rounded-[18px] px-4 py-3.5 flex items-center justify-between"
        style={{
          background: "rgba(247,243,236,0.86)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(255,255,255,0.32)",
          boxShadow: "0 12px 30px rgba(25,21,16,0.10)",
        }}
      >
        <div>
          <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#67635C]">
            {tt("home_todays_visit_label", state.locale)}
          </div>
          <div style={editorial} className="mt-1 text-[19px] font-medium text-[#181714]">
            {activeMuseumName}
          </div>
          <div className="text-[13px] text-[#67635C]">
            {tt("home_museum_context", state.locale)
              .replace("{city}", activeMuseum?.city || "France")
              .replace("{experience}", activeMuseumExperience)}
          </div>
        </div>
        <div className="w-[54px] h-[54px] rounded-[10px] overflow-hidden shrink-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={proxyImageUrl(HERO_IMAGE_URL)}
            alt=""
            className="w-full h-full object-cover scale-[2.2]"
            style={{ filter: "saturate(0.72) contrast(0.92) brightness(0.9)" }}
          />
        </div>
      </div>

      {/* Today's missions -- §8/§9, one editorial paper block, not 3 cards */}
      <div className="relative z-10 mt-[42px] px-6 pb-[max(28px,env(safe-area-inset-bottom))]">
        <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#67635C]">
          {tt("home_todays_missions_label", state.locale)}
        </div>
        <div className="mt-1 text-[14px] leading-[20px] text-[#77736C]">
          {tt("home_missions_subtitle", state.locale)}
        </div>
        <div
          className="mt-4 rounded-[22px] px-5"
          style={{
            background: "#FDFBF7",
            border: "1px solid rgba(34,29,23,0.08)",
            boxShadow: "0 12px 32px rgba(32,27,21,0.055)",
          }}
        >
          {MISSIONS.map((mission, i) => {
            const done = isMissionComplete(mission.id, state.seen);
            return (
              <div
                key={mission.id}
                className={`py-[18px] flex items-center gap-3 ${
                  i < MISSIONS.length - 1 ? "border-b border-[rgba(30,27,22,0.09)]" : ""
                }`}
              >
                <div
                  style={editorial}
                  className={`text-[23px] leading-[24px] font-medium tabular-nums shrink-0 ${
                    done ? "text-[#181714]" : "text-[#A19B91]"
                  }`}
                >
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[9px] font-semibold tracking-[0.13em] uppercase text-[#8B867E]">
                    {tt(MISSION_EYEBROW_KEY[mission.id], state.locale)}
                  </div>
                  <div className="mt-0.5 text-[15px] leading-[21px] font-medium tracking-[-0.01em] text-[#272520]">
                    {missionLabel(mission, state.locale)}
                  </div>
                </div>
                <div className="text-[11px] tabular-nums text-[#8B867E] shrink-0">{done ? "1/1" : "0/1"}</div>
              </div>
            );
          })}
        </div>
        <div className="mt-4 text-[10px] text-[#A19B91]">Photo: R. Eisele · CC BY-SA 4.0</div>
        <div className="mt-1.5 text-[10px] text-[#A19B91]">{tt("privacy_footer_note", state.locale)}</div>
      </div>

      {/* Museum selector sheet -- scalable France-wide directory. */}
      {showMuseumSheet && (
        <div className="fixed inset-0 z-40 flex items-end" onClick={() => setShowMuseumSheet(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div
            className="relative z-10 w-full max-h-[82vh] rounded-t-[24px] bg-[#FDFBF7] p-5 pb-[max(24px,env(safe-area-inset-bottom))] overflow-y-auto scrollbar-none"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[#67635C]">
              {tt("select_museum_sheet_title", state.locale)}
            </div>
            <input
              value={museumSearch}
              onChange={(e) => setMuseumSearch(e.target.value)}
              placeholder={tt("museum_search_placeholder", state.locale)}
              className="mt-3 w-full h-[42px] rounded-[14px] bg-[#F3EDE4] border border-[rgba(30,27,22,0.08)] px-3 text-[14px] text-[#181714] outline-none"
            />

            {!museumSearch.trim() && featuredMuseums.length > 0 && (
              <div className="mt-5">
                <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#8B867E] mb-1">
                  {tt("museum_featured_label", state.locale)}
                </div>
                {featuredMuseums.map((m) => (
                  <MuseumRow
                    key={m.id}
                    museum={m}
                    locale={state.locale}
                    onSelect={() => {
                      track("museum_selected", {
                        museum_id: m.id,
                        experience_level: m.experience_level,
                        city: m.city,
                        source: "featured",
                      });
                      confirmManually(m.id);
                      setShowMuseumSheet(false);
                    }}
                  />
                ))}
              </div>
            )}

            <div className="mt-5">
              <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#8B867E] mb-1">
                {tt("museum_results_label", state.locale)}
              </div>
              {visibleMuseums.length === 0 ? (
                <div className="py-5 text-[13px] text-[#67635C]">{tt("museum_no_results", state.locale)}</div>
              ) : (
                visibleMuseums.map((m) => (
                  <MuseumRow
                    key={m.id}
                    museum={m}
                    locale={state.locale}
                    onSelect={() => {
                      track("museum_selected", {
                        museum_id: m.id,
                        experience_level: m.experience_level,
                        city: m.city,
                        source: museumSearch.trim() ? "search" : "results",
                      });
                      confirmManually(m.id);
                      setShowMuseumSheet(false);
                    }}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MuseumRow({ museum, locale, onSelect }: { museum: Museum; locale: AppState["locale"]; onSelect: () => void }) {
  const curated = museum.experience_level === "CURATED";
  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full flex items-center justify-between gap-3 py-3 border-b border-[rgba(30,27,22,0.09)] text-left"
    >
      <span className="min-w-0">
        <span style={editorial} className="block text-[16px] leading-[19px] font-medium text-[#181714]">
          {museum.name}
        </span>
        <span className="mt-0.5 block text-[12px] leading-[16px] text-[#67635C]">
          {[museum.city, museum.department].filter(Boolean).join(" · ") || museum.region || "France"}
        </span>
      </span>
      <span className={`shrink-0 text-[10px] font-semibold ${curated ? "text-[#181714]" : "text-[#0A6A5A]"}`}>
        {tt(curated ? "museum_curated_label" : "museum_ai_guide_label", locale)}
      </span>
    </button>
  );
}
