"use client";

import { useElyioApp } from "@/lib/app-state";
import HomeScreen from "@/components/screens/HomeScreen";
import CameraScreen from "@/components/screens/CameraScreen";
import CardScreen from "@/components/screens/CardScreen";
import ProgressScreen from "@/components/screens/ProgressScreen";
import RecapScreen from "@/components/screens/RecapScreen";

// The real, working ELYIO app — state-machine driven, talks to the existing
// backend (lib/api.ts), same 5-screen flow and nav map as the old PWA
// (frontend/index.html data-nav attributes): Camera <-> Progress/Home,
// Card -> Camera, Progress -> Camera/Recap, Recap -> new visit.
//
// Lives at "/" (root) so an installed icon or a bare domain visit lands
// visitors straight in the working app, not the developer-facing design
// system — that one moved to /design (app/design/page.tsx).
//
// Rendered edge-to-edge on a phone; centered in a fixed mobile frame on
// wider viewports so it's testable from a desktop browser during `npm run
// dev` without a physical device.
export default function AppPage() {
  const { state, seenArtworks, actions } = useElyioApp();

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[#111111] sm:p-6">
      <div className="relative w-full h-full sm:max-w-[430px] sm:h-[min(932px,100vh)] sm:rounded-[44px] sm:overflow-hidden bg-[#FAFAF9] sm:shadow-[0_40px_80px_rgba(0,0,0,0.5)]">
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
        {state.screen === "card" && (
          <CardScreen
            state={state}
            onSetMode={actions.setMode}
            onBack={() => actions.goto("camera")}
            onAddToVisit={actions.addToVisit}
            onToggleFavorite={actions.toggleFavorite}
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
      </div>
    </div>
  );
}
