"use client";

import { useEffect, useRef } from "react";
import CardScreen from "@/components/screens/CardScreen";
import { getArtwork } from "@/lib/artworks";
import type { AppState } from "@/lib/app-state";
import type { Locale } from "@/lib/types";

// Round 6, Block 5 -- "the phone feels like a navigation screen; this is
// the homepage, not the app dashboard." The hero phone used to render the
// SAME live AppScreens tree as real mobile (starting at Home), because
// the desktop rebuild's own convention has always been "reuse the real
// screens, never fork them." But Home is a dashboard, not a demo -- it
// sells nothing. The Card screen (photo + ArtworkIdentity + the
// ProvenanceReveal price/rarity reveal) is the actual "wow" moment, so
// that's the real screen reused here instead, fed a curated static state
// rather than live app-state -- same reuse principle, different real
// screen. Same canonical artwork Journey/Recap already use, so the hero
// phone previews the exact piece a visitor sees explained a few seconds
// of scroll later, not an arbitrary different one.
const HERO_PREVIEW_ARTWORK_ID = "orsay_rf_1975_19";

const noop = () => {};

// CardScreen is a full mobile screen (photo, then identity, then the
// price/rarity reveal, then more) scrollable internally via its own
// overflow-y-auto root -- built for a full 852px phone canvas. The hero
// stage is shorter than that, and this is a static, non-interactive
// preview (see pointerEvents:none where it's mounted), so it never gets a
// real scroll gesture to reach the reveal on its own. This scrolls the
// real component's own scroll container down programmatically on mount,
// past most of the photo, so the actual "wow" payoff -- ProvenanceReveal's
// price + rarity tier -- is what's visible, not just the top of the photo.
const REVEAL_SCROLL_OFFSET_PX = 230;

export default function HeroPhonePreview({ locale }: { locale: Locale }) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const artwork = getArtwork(HERO_PREVIEW_ARTWORK_ID);

  useEffect(() => {
    const scrollable = wrapperRef.current?.querySelector<HTMLElement>(".overflow-y-auto");
    if (scrollable) scrollable.scrollTop = REVEAL_SCROLL_OFFSET_PX;
  }, []);

  if (!artwork) return null;

  // A fixed, non-live snapshot -- "already scanned and revealed" -- not
  // wired to useElyioApp's real state machine, so nothing here is
  // clickable-for-real (onAddToVisit etc. are no-ops) and
  // trackingEnabled=false keeps this static marketing preview out of the
  // real artwork_card_opened/read_time analytics.
  const state: AppState = {
    screen: "card",
    locale,
    mode: "normal",
    visitId: null,
    visitStarted: true,
    startTime: null,
    seen: [artwork.id],
    favorites: new Set(),
    added: new Set(),
    currentArtwork: artwork,
    lastConfidence: 0.97,
    scanStatus: null,
    cardOpenedAt: null,
  };

  return (
    <div ref={wrapperRef} className="w-full h-full">
      <CardScreen
        state={state}
        onSetMode={noop}
        onBack={noop}
        onAddToVisit={noop}
        onToggleFavorite={noop}
        onGoProgress={noop}
        trackingEnabled={false}
      />
    </div>
  );
}
