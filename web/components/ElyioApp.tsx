"use client";

import { useEffect, useRef } from "react";
import { useElyioApp, type AppState } from "@/lib/app-state";
import { useAuth } from "@/lib/useAuth";
import { identify, track, trackSessionStartedOnce } from "@/lib/analytics";
import { useIsDesktop } from "@/lib/useIsDesktop";
import { useMuseumDetection } from "@/lib/geolocation";
import { tt } from "@/lib/i18n";
import type { Locale } from "@/lib/types";
import HomeScreen from "@/components/screens/HomeScreen";
import CameraScreen from "@/components/screens/CameraScreen";
import CardScreen from "@/components/screens/CardScreen";
import UncatalogedCardScreen from "@/components/screens/UncatalogedCardScreen";
import ProgressScreen from "@/components/screens/ProgressScreen";
import RecapScreen from "@/components/screens/RecapScreen";
import DesktopShell from "@/components/desktop/DesktopShell";
import VisitToast from "@/components/ui/VisitToast";
import type { Artwork } from "@/lib/types";

// The real, working ELYIO app — state-machine driven, talks to the existing
// backend (lib/api.ts), same 5-screen flow and nav map as the old PWA
// (frontend/index.html data-nav attributes): Camera <-> Progress/Home,
// Card -> Camera, Progress -> Camera/Recap, Recap -> new visit.
//
// Extracted out of AppPage (desktop rebuild spec §22/§41/§42) so the exact
// same live screens/state render two ways from ONE tree: full-viewport on
// mobile, inside PhoneFrame.tsx on desktop -- never a forked copy of the
// business logic.
function AppScreens({
  state,
  seenArtworks,
  actions,
}: {
  state: AppState;
  seenArtworks: Artwork[];
  actions: ReturnType<typeof useElyioApp>["actions"];
}) {
  return (
    <>
      {state.screen === "home" && (
        <HomeScreen
          state={state}
          seenArtworks={seenArtworks}
          onStartVisit={actions.startVisit}
          onSetLocale={actions.setLocale}
        />
      )}
      {state.screen === "camera" && (
        <CameraScreen
          state={state}
          onCapture={actions.recognizeFrame}
          onGoProgress={() => actions.goto("progress")}
          onGoHome={() => actions.goto("home")}
        />
      )}
      {/* Phase 2 §2 -- Tier 1 (real catalog match) vs Tier 2 (recognized but
          not cataloged) are two different screens sharing the "card" slot,
          branched on which of currentArtwork/uncatalogedSighting app-state.ts
          set -- never the same component with fields blanked out (see
          UncatalogedCardScreen's doc comment for why). */}
      {state.screen === "card" && state.currentArtwork && (
        <CardScreen
          state={state}
          onSetMode={actions.setMode}
          onBack={() => actions.goto("camera")}
          onAddToVisit={actions.addToVisit}
          onToggleFavorite={actions.toggleFavorite}
          onGoProgress={() => actions.goto("progress")}
        />
      )}
      {state.screen === "card" && !state.currentArtwork && state.uncatalogedSighting && (
        <UncatalogedCardScreen
          state={state}
          onBack={() => actions.goto("camera")}
          onSetMode={actions.setMode}
          onAddToVisit={actions.addUncatalogedToVisit}
          onToggleFavorite={actions.toggleUncatalogedFavorite}
          onGoProgress={() => actions.goto("progress")}
        />
      )}
      {state.screen === "progress" && (
        <ProgressScreen
          state={state}
          seenArtworks={seenArtworks}
          onBack={() => actions.goto("camera")}
          onContinueScanning={() => actions.goto("camera")}
          onCompleteVisit={actions.completeVisit}
        />
      )}
      {state.screen === "recap" && (
        <RecapScreen state={state} seenArtworks={seenArtworks} onNewVisit={actions.newVisit} />
      )}
      <VisitToast
        state={state}
        seenArtworks={seenArtworks}
        onDismissAchievement={actions.dismissAchievementToast}
        onDismissMission={actions.dismissMissionToast}
      />
    </>
  );
}

// Lives at "/" (root) so an installed icon or a bare domain visit lands
// visitors straight in the working app, not the developer-facing design
// system — that one moved to /design (app/design/page.tsx).
//
// Below the desktop breakpoint (spec §39: <1100px, which covers today's
// mobile AND the not-yet-designed tablet range unchanged): the original
// full-viewport-on-phone / boxed-on-black-on-wider-screens behavior,
// byte-for-byte. At >=1100px: DesktopShell (desktop rebuild spec §68 Phase
// 1) instead of the black box. isDesktop starts `null` (see useIsDesktop)
// and the mobile branch is the fallback during that window, so a real
// mobile visitor never sees any flash of desktop layout — only a real
// desktop visitor briefly sees the old boxed layout for one paint before
// this resolves true.
export default function ElyioApp({
  directToScanner = false,
  initialLocale,
}: {
  directToScanner?: boolean;
  initialLocale?: Locale;
}) {
  const { state, seenArtworks, actions } = useElyioApp({ directToScanner, initialLocale });
  const { user } = useAuth();
  const isDesktop = useIsDesktop();
  const detection = useMuseumDetection({ enabled: directToScanner && !state.visitStarted });
  const startingVisit = useRef(false);
  const attributed = useRef(false);

  useEffect(() => {
    if (!directToScanner || state.visitStarted || startingVisit.current || !detection.museum) return;
    if (detection.status !== "detected" && detection.status !== "manual-confirmed") return;
    startingVisit.current = true;
    void actions.startVisit(
      detection.museum.id,
      detection.museum.name,
      detection.museum.city || detection.museum.region || null,
    );
  }, [actions, detection.museum, detection.status, directToScanner, state.visitStarted]);

  useEffect(() => {
    trackSessionStartedOnce({ locale: state.locale });
    track("app_opened", { locale: state.locale, display_mode: window.matchMedia?.("(display-mode: standalone)")?.matches ? "standalone" : "browser" });
  }, [state.locale]);

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    if (query.get("from") !== "organic" || attributed.current) return;
    attributed.current = true;
    const attribution = { traffic_source: "organic", landing_page: query.get("landing") || "unknown", landing_locale: query.get("locale") || state.locale };
    try { window.sessionStorage.setItem("elyio-organic-landing", JSON.stringify(attribution)); } catch { /* storage is optional */ }
    track("seo_begin_visit", attribution);
  }, [state.locale]);

  // Links every event fired after this point (visit_started onward, per
  // useAuth's SIGNED_IN-gated onboarding_completed) to the real Supabase
  // user_id. posthog-js merges the pre-login anonymous distinct_id (used
  // for e.g. language_selected on Home before sign-in) into this identity
  // automatically -- see lib/analytics.ts.
  useEffect(() => {
    if (user) identify(user.id);
  }, [user]);

  const screens = (
    <AppScreens
      state={state}
      seenArtworks={seenArtworks}
      actions={actions}
    />
  );

  // display:contents -- a landmark for the accessibility tree only. It
  // generates no box of its own, so it changes nothing about either
  // branch's actual layout (fixed/inset-0 sizing below, DesktopShell's own
  // layout) -- pixel-identical either way, just now reachable as <main>.
  // Round 6, Block 5 -- DesktopShell no longer takes the live screens tree
  // as children; its hero phone now renders HeroPhonePreview (a static
  // curated Card-screen reveal) instead, so `screens` isn't passed here at
  // all. Real mobile below is unaffected -- still the live AppScreens tree.
  if (isDesktop && !directToScanner) {
    return (
      <main style={{ display: "contents" }}>
        <DesktopShell locale={state.locale} onSetLocale={actions.setLocale} />
      </main>
    );
  }

  return (
    <main style={{ display: "contents" }}>
      <div className="fixed inset-0 flex items-center justify-center bg-[#111111] sm:p-6">
        <div className="relative w-full h-full sm:max-w-[430px] sm:h-[min(932px,100vh)] sm:rounded-[44px] sm:overflow-hidden bg-[#FAFAF9] sm:shadow-[0_40px_80px_rgba(0,0,0,0.5)]">
          {directToScanner && !state.visitStarted ? (
            <DirectScannerEntry
              locale={state.locale}
              detection={detection}
              onSelect={detection.confirmManually}
            />
          ) : screens}
        </div>
      </div>
    </main>
  );
}

function DirectScannerEntry({
  locale,
  detection,
  onSelect,
}: {
  locale: Locale;
  detection: ReturnType<typeof useMuseumDetection>;
  onSelect: (museumId?: string) => void;
}) {
  const resolvedAutomatically = detection.status === "detected";
  return (
    <section className="absolute inset-0 flex flex-col justify-end bg-[#0A0A0A] text-white" aria-label="Scanner setup">
      <div className="absolute inset-0 bg-[radial-gradient(100%_100%_at_50%_35%,#8FA8C8_0%,#4A5A85_52%,#151D2A_100%)] opacity-75" />
      <div className="relative z-10 p-6 pb-[max(28px,env(safe-area-inset-bottom))] bg-gradient-to-t from-black via-black/90 to-transparent">
        <div className="text-[11px] font-semibold tracking-[0.16em] uppercase text-white/65">ELYIO · {tt("select_museum_sheet_title", locale)}</div>
        <h1 className="mt-2 text-[25px] font-medium tracking-[-0.02em]">
          {resolvedAutomatically ? detection.museum?.name : detection.status === "checking" ? tt("museum_locating", locale) : tt("museum_select_prompt", locale)}
        </h1>
        {detection.status === "checking" && detection.museums.length === 0 ? null : !resolvedAutomatically ? (
          <div className="mt-4 max-h-[42vh] overflow-y-auto rounded-[16px] bg-white/10 backdrop-blur border border-white/15 p-2">
            {detection.museums.map((museum) => (
              <button
                key={museum.id}
                type="button"
                onClick={() => {
                  track("museum_selected", {
                    museum_id: museum.id,
                    experience_level: museum.experience_level,
                    city: museum.city,
                    source: "direct_scanner_entry",
                  });
                  onSelect(museum.id);
                }}
                className="w-full min-h-12 px-3 py-2 text-left rounded-[12px] hover:bg-white/10 active:bg-white/20"
              >
                <span className="block text-[14px] font-semibold">{museum.name}</span>
                <span className="block text-[12px] text-white/60">{museum.city || museum.region || museum.country_code}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
