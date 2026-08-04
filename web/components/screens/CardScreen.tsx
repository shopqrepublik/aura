"use client";

import { useState } from "react";
import { ArrowLeft, Heart } from "lucide-react";
import SegmentControl from "@/components/ui/SegmentControl";
import PriceBadge from "@/components/ui/PriceBadge";
import ScaleComparisonBadge from "@/components/ui/ScaleComparisonBadge";
import EyeBlock from "@/components/ui/EyeBlock";
import ListenButton from "@/components/ui/ListenButton";
import { resolveCardText, resolveTitle, isExcludedInKids } from "@/lib/artworks";
import { resolveKidsScaleComparison } from "@/lib/scaleComparison";
import { tt } from "@/lib/i18n";
import type { AppState } from "@/lib/app-state";

// "03 ARTWORK CARD HERO" — exact classNames mined from the HTML reference.
// Content policy (Kids mode) ported 1:1 from the old app.js renderCard():
// kidsModeExcluded works show the neutral message and hide Where/Rarity
// entirely instead of falling back to Normal text; everything else uses
// whyKids/whereKids when present, else the plain why/where. See
// lib/artworks.ts (isExcludedInKids / resolveCardText) for the shared logic
// — this component never duplicates that decision.
export default function CardScreen({
  state,
  onSetMode,
  onBack,
  onAddToVisit,
  onToggleFavorite,
}: {
  state: AppState;
  onSetMode: (mode: AppState["mode"]) => void;
  onBack: () => void;
  onAddToVisit: () => void;
  onToggleFavorite: () => void;
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
  const isKids = state.mode === "kids";
  const kidsComparison = isKids
    ? resolveKidsScaleComparison(artwork.estimate.low, artwork.estimate.high, state.locale)
    : null;

  return (
    <div className="w-full h-full bg-[#F5F5F7] flex flex-col overflow-y-auto scrollbar-none">
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

        <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#8E8E93]">
          {artwork.artist.toUpperCase()}
        </div>
        <h1 className="mt-1 text-[22px] font-bold leading-[24px] tracking-[-0.03em] text-[#111]">{title}</h1>
        <p className="mt-1 text-[14px] text-[#6E6E73] font-[450]">{artwork.year}</p>

        <div className="mt-4 flex items-center gap-2">
          <PriceBadge low={artwork.estimate.low} high={artwork.estimate.high} locale={state.locale} />
          {/* Kids mode gets its own sentence-style comparison below instead
              of this terse pill — a kid-facing "≈ 2 long-range private
              jets" reads as a dry fact, not the "Хватило бы на X" story
              tone the rest of Kids content uses. */}
          {!isKids && <ScaleComparisonBadge low={artwork.estimate.low} high={artwork.estimate.high} locale={state.locale} />}
        </div>
        {kidsComparison && (
          <p className="mt-2 text-[13px] font-semibold text-[#1D1D1F]">{kidsComparison}</p>
        )}

        {excluded ? (
          <p className="mt-5 text-[16px] leading-[24px] tracking-[-0.011em] text-[#1D1D1F] font-[450]">
            {/* Per-artwork override: most exclusions (eg L'Origine du monde)
                use the generic "switch to Normal mode" string below, but a
                work can supply its own neutral message when the exclusion
                reason isn't "content can't be shown" (eg a difficult
                personal/biographical subject) -- see kidsExclusionMessage
                on Artwork and Camille Monet on her deathbed for the first
                case. */}
            {artwork.kidsExclusionMessage
              ? artwork.kidsExclusionMessage[state.locale] || artwork.kidsExclusionMessage.en
              : tt("kids_mode_excluded", state.locale)}
          </p>
        ) : (
          <>
            <p className="mt-5 text-[16px] leading-[24px] tracking-[-0.011em] text-[#1D1D1F] font-[450]">{why}</p>
            <EyeBlock text={where} />
            <p className="mt-4 text-[12px] leading-[17px] text-[#8E8E93] font-[450]">{rarity}</p>
          </>
        )}

        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={onAddToVisit}
            className={`w-full h-[50px] rounded-full text-[15px] font-semibold tracking-[-0.01em] shadow-[0_8px_20px_rgba(0,0,0,0.18)] active:scale-[0.98] transition-transform ${
              isAdded ? "bg-black text-white" : "bg-black text-white"
            }`}
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
              easy to miss on a first real visit. The old vanilla app had
              exactly this same icon PLUS an explicit labeled button
              (frontend/index.html #btnScanNext); the ELYIO redesign kept
              only the icon and dropped the label, which is what actually
              left people stuck on this screen with no visible way to
              continue. This button is the reliable, always-visible path;
              the icon is a bonus shortcut, not the only way out. */}
          <button
            type="button"
            onClick={onBack}
            className="w-full h-[50px] rounded-full bg-[#F5F5F7] text-[#111] text-[15px] font-semibold tracking-[-0.01em]"
          >
            {tt("scan_next_artwork", state.locale)}
          </button>
        </div>
      </div>
    </div>
  );
}
