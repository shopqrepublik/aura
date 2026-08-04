"use client";

import { useState } from "react";
import { ArrowLeft, Heart } from "lucide-react";
import SegmentControl from "@/components/ui/SegmentControl";
import ArtworkIdentity from "@/components/ui/ArtworkIdentity";
import ProvenanceReveal from "@/components/ui/ProvenanceReveal";
import ViewingNote from "@/components/ui/ViewingNote";
import ListenButton from "@/components/ui/ListenButton";
import { resolveCardText, resolveTitle, isExcludedInKids } from "@/lib/artworks";
import { tt } from "@/lib/i18n";
import type { AppState } from "@/lib/app-state";

// "The Curated Reveal" (design-direction-v3.md) -- Observe -> Reveal stages
// for the Artwork Card. Content policy (Kids mode) is unchanged from before
// this redesign: kidsModeExcluded works still show the neutral message and
// hide Where/Rarity entirely instead of falling back to Normal text, and
// the price/ProvenanceReveal block is still shown regardless of exclusion
// (excluding a work hides its description, not its market context) --
// see lib/artworks.ts (isExcludedInKids / resolveCardText) for the shared
// logic this component never duplicates.
//
// ArtworkIdentity and ProvenanceReveal are both keyed by `${artwork.id}-
// ${locale}` (not by `mode`) so the staged reveal animation plays once per
// artwork/language, not on every Normal/Simple/Kids tab switch -- switching
// modes after the reveal has already played just updates the visible text
// in place, same remount-avoidance convention ListenButton already uses.
export default function CardScreen({
  state,
  onSetMode,
  onBack,
  onAddToVisit,
  onToggleFavorite,
  onGoProgress,
}: {
  state: AppState;
  onSetMode: (mode: AppState["mode"]) => void;
  onBack: () => void;
  onAddToVisit: () => void;
  onToggleFavorite: () => void;
  onGoProgress: () => void;
}) {
  const [imgError, setImgError] = useState(false);
  const artwork = state.currentArtwork;

  // Narration only exists for Normal mode (Top 20 launch scope, §10.4) --
  // Kids/Simple text is often deliberately different or redacted (see
  // content-policy work throughout lib/data/artworks.json), so playing the
  // Normal-mode script in another mode would leak content that mode is
  // meant to avoid.
  const audioUrl = state.mode === "normal" ? artwork?.audioUrl?.[state.locale] : undefined;

  if (!artwork) return null;

  const excluded = isExcludedInKids(artwork, state.mode);
  const { why, where, rarity } = resolveCardText(artwork, state.mode, state.locale);
  const title = resolveTitle(artwork, state.locale);
  const isAdded = state.added.has(artwork.id);
  const isFavorite = state.favorites.has(artwork.id);

  const exclusionMessage = artwork.kidsExclusionMessage
    ? artwork.kidsExclusionMessage[state.locale] || artwork.kidsExclusionMessage.en
    : tt("kids_mode_excluded", state.locale);

  const revealKey = `${artwork.id}-${state.locale}`;

  return (
    <div className="w-full h-full bg-[#FAFAF8] flex flex-col overflow-y-auto scrollbar-none">
      <div className="shrink-0 relative">
        <div className="aspect-[4/3] w-full overflow-hidden bg-[#EDE8E1]">
          {!imgError ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={artwork.imageUrl}
              alt={title}
              className="w-full h-full object-cover"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="w-full h-full relative">
              <div className="absolute inset-0 bg-[linear-gradient(105deg,#FFD8A8_0%,#FFA98E_18%,#7BA7D9_42%,#2B4A7A_68%,#E8B86D_100%)]" />
            </div>
          )}
          <div className="absolute bottom-3 right-3 px-2 py-1 rounded-full bg-black/70 text-[10px] font-semibold text-white tracking-widest">
            4:3 • SCAN
          </div>
        </div>
        <button
          type="button"
          onClick={onBack}
          aria-label="Back"
          className="absolute top-4 left-4 w-9 h-9 rounded-full bg-black/40 backdrop-blur flex items-center justify-center"
        >
          <ArrowLeft className="w-4 h-4 text-white" />
        </button>
        <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 w-10 h-1 rounded-full bg-black/15" />
      </div>

      <div className="bg-white rounded-t-[24px] -mt-4 relative z-10 flex-1 px-5 pt-7 pb-[32px]">
        <SegmentControl mode={state.mode} locale={state.locale} onChange={onSetMode} />

        <ArtworkIdentity
          key={`identity-${revealKey}`}
          artist={artwork.artist}
          title={title}
          year={artwork.year}
          hookText={excluded ? exclusionMessage : why}
        />

        <ProvenanceReveal
          key={`reveal-${revealKey}`}
          low={artwork.estimate.low}
          high={artwork.estimate.high}
          accent={artwork.accent}
          comparableSalesCount={artwork.estimate.comparableSales?.length}
          inventoryNumber={artwork.inventoryNumber}
          locale={state.locale}
          mode={state.mode}
        />

        {!excluded && (
          <>
            <ViewingNote text={where} accent={artwork.accent} />
            <p className="mt-4 text-[12px] leading-[17px] text-[#8A8A90] font-[450]">{rarity}</p>
          </>
        )}

        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={onAddToVisit}
            className="w-full h-[50px] rounded-full text-[15px] font-semibold tracking-[-0.01em] bg-black text-white shadow-[0_8px_20px_rgba(0,0,0,0.18)] active:scale-[0.98] transition-transform"
          >
            {isAdded ? tt("added_check", state.locale) : tt("add_to_my_visit", state.locale)}
          </button>
          <div className="flex gap-3">
            {audioUrl && <ListenButton key={`${artwork.id}-${state.locale}`} audioUrl={audioUrl} locale={state.locale} />}
            <button
              type="button"
              onClick={onToggleFavorite}
              aria-pressed={isFavorite}
              className="w-[44px] h-[44px] rounded-full bg-[#F5F5F7] flex items-center justify-center"
            >
              <Heart className={`w-4 h-4 ${isFavorite ? "fill-black text-black" : "text-black"}`} />
            </button>
          </div>
          {/* The only other way off this screen is the small back-arrow
              overlaid on the photo (top-left) -- an icon with no label,
              easy to miss on a first real visit. This button is the
              reliable, always-visible path; the icon is a bonus shortcut,
              not the only way out. */}
          <button
            type="button"
            onClick={onBack}
            className="w-full h-[50px] rounded-full bg-[#F5F5F7] text-[#111] text-[15px] font-semibold tracking-[-0.01em]"
          >
            {tt("scan_next_artwork", state.locale)}
          </button>
          {/* Direct route to Progress/Recap from the card itself, without
              first bouncing through Camera. */}
          <button
            type="button"
            onClick={onGoProgress}
            className="w-full text-center text-[13px] font-semibold text-[#8E8E93] pt-1"
          >
            {tt("view_visit_progress", state.locale)}
          </button>
        </div>
      </div>
    </div>
  );
}
