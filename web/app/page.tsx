"use client";

import { useEffect } from "react";
import { useElyioApp, type AppState } from "@/lib/app-state";
import { useAuth } from "@/lib/useAuth";
import { identify } from "@/lib/analytics";
import { useIsDesktop } from "@/lib/useIsDesktop";
import HomeScreen from "@/components/screens/HomeScreen";
import CameraScreen from "@/components/screens/CameraScreen";
import CardScreen from "@/components/screens/CardScreen";
import UncatalogedCardScreen from "@/components/screens/UncatalogedCardScreen";
import ProgressScreen from "@/components/screens/ProgressScreen";
import RecapScreen from "@/components/screens/RecapScreen";
import DesktopShell from "@/components/desktop/DesktopShell";
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
          onAddToVisit={actions.addUncatalogedToVisit}
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
export default function AppPage() {
  const { state, seenArtworks, actions } = useElyioApp();
  const { user } = useAuth();
  const isDesktop = useIsDesktop();

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
  if (isDesktop) {
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
          {screens}
        </div>
      </div>
    </main>
  );
}
