"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Heart } from "lucide-react";
import SegmentControl from "@/components/ui/SegmentControl";
import ArtworkIdentity from "@/components/ui/ArtworkIdentity";
import ProvenanceReveal from "@/components/ui/ProvenanceReveal";
import ViewingNote from "@/components/ui/ViewingNote";
import ListenButton from "@/components/ui/ListenButton";
import { resolveCardText, resolveTitle, isExcludedInKids } from "@/lib/artworks";
import { getArtworkValueReveal } from "@/lib/valueReveal";
import { tt } from "@/lib/i18n";
import { track, trackGoogleEvent } from "@/lib/analytics";
import { proxyImageUrl } from "@/lib/visitPalette";
import type { AppState } from "@/lib/app-state";

const viewedStoryKeys = new Set<string>();

function displayImageUrl(url: string): string {
  if (/^https?:\/\/(upload|commons)\.wikimedia\.org\//i.test(url)) {
    return proxyImageUrl(url, 1200);
  }
  return url;
}

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
  // Desktop hero reuses this real component as a static curated preview
  // (components/desktop/HeroPhonePreview.tsx) rather than forking its
  // markup. That preview isn't a real scan/read event, so it opts out of
  // artwork_card_opened/read_time tracking below -- default true keeps
  // every real mobile call site's behavior byte-for-byte unchanged.
  trackingEnabled = true,
}: {
  state: AppState;
  onSetMode: (mode: AppState["mode"]) => void;
  onBack: () => void;
  onAddToVisit: () => void;
  onToggleFavorite: () => void;
  onGoProgress: () => void;
  trackingEnabled?: boolean;
}) {
  const [imgError, setImgError] = useState(false);
  const artwork = state.currentArtwork;

  // Narration only exists for Normal mode (Top 20 launch scope, §10.4) --
  // Kids/Simple text is often deliberately different or redacted (see
  // content-policy work throughout lib/data/artworks.json), so playing the
  // Normal-mode script in another mode would leak content that mode is
  // meant to avoid.
  const audioUrl = state.mode === "normal" ? artwork?.audioUrl?.[state.locale] : undefined;

  // artwork_card_opened / artwork_card_read_time (§13) -- read_time_ms is
  // this project's north-star "meaningful attention time" metric (§3).
  // Uses state.cardOpenedAt (set once, in app-state.ts's recognizeFrame) as
  // the start time rather than a fresh Date.now() here, so this agrees with
  // ProgressScreen's live "focus minutes" stat, which reads the same field.
  // The cleanup fires exactly when this artwork's card stops being
  // rendered -- back to camera, on to progress, or a different artwork
  // replacing it -- so it measures actual mounted time, not a guess at
  // when the user "left".
  useEffect(() => {
    if (!trackingEnabled || !artwork || state.cardOpenedAt == null) return;
    const artworkId = artwork.id;
    const openedAt = state.cardOpenedAt;
    const storyKey = `${openedAt}:${artworkId}`;
    if (!viewedStoryKeys.has(storyKey)) {
      viewedStoryKeys.add(storyKey);
      trackGoogleEvent("story_viewed", { locale: state.locale, museum_slug: state.museumId || undefined, museum_city: state.museumCity || undefined, artwork_id: artworkId, recognition_mode: "catalog", catalog_status: "catalog", source_surface: "scanner" });
    }
    try {
      track("artwork_card_opened", { artwork_id: artworkId });
    } catch {
      // First-party analytics must never prevent GA story_viewed or card use.
    }
    return () => {
      track("artwork_card_read_time", { artwork_id: artworkId, read_time_ms: Date.now() - openedAt });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artwork?.id, state.cardOpenedAt, trackingEnabled]);

  if (!artwork) return null;

  const excluded = isExcludedInKids(artwork, state.mode);
  const { why, where, rarity } = resolveCardText(artwork, state.mode, state.locale);
  const title = resolveTitle(artwork, state.locale);
  const valueReveal = getArtworkValueReveal(artwork);
  const isAdded = state.added.has(artwork.id);
  const isFavorite = state.favorites.has(artwork.id);

  const revealKey = `${artwork.id}-${state.locale}`;
  const sectionEyebrow = "text-[10px] font-semibold tracking-[0.15em] uppercase text-[#696763]";

  return (
    <div className="w-full h-full bg-[#F7F3EC] flex flex-col overflow-y-auto scrollbar-none">
      <div className="shrink-0 relative">
        <div className="aspect-[4/3] w-full overflow-hidden bg-[#EDE8E1]">
          {!imgError ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={displayImageUrl(artwork.imageUrl)}
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

      <div
        className="rounded-t-[30px] -mt-4 relative z-10 flex-1 px-5 pt-7 pb-[32px]"
        style={{
          backgroundColor: "#FBF8F2",
          boxShadow: "0 -16px 45px rgba(22,19,15,0.09), inset 0 1px 0 rgba(255,255,255,0.80)",
        }}
      >
        <SegmentControl mode={state.mode} locale={state.locale} onChange={onSetMode} />

        <ArtworkIdentity
          key={`identity-${revealKey}`}
          artist={artwork.artist}
          artistFallback={tt("uncataloged_unknown_artist", state.locale)}
          title={title}
          year={artwork.year}
        />

        <ProvenanceReveal
          key={`reveal-${revealKey}`}
          valueReveal={valueReveal}
          accent={artwork.accent}
          comparableSalesCount={artwork.estimate.comparableSales?.length}
          inventoryNumber={artwork.inventoryNumber}
          locale={state.locale}
          mode={state.mode}
          museumCity={state.museumCity}
          artworkId={artwork.id}
          comparisonSessionId={state.visitId || String(state.startTime || "direct-session")}
          museumId={state.museumId}
        />

        {!excluded && (
          <>
            <section className="mt-5">
              <div className={sectionEyebrow}>{tt("why_it_matters_label", state.locale)}</div>
              <p className="mt-2 text-[16px] leading-[23px] tracking-[-0.01em] text-[#272622]">{why}</p>
            </section>
            <section className="mt-5">
              <div className={sectionEyebrow}>{tt("look_closer_label", state.locale)}</div>
              <ViewingNote text={where} accent={artwork.accent} />
            </section>
            {rarity && (
              <details className="mt-4 group">
                <summary className="cursor-pointer list-none text-[12px] font-semibold text-[#67635C]">
                  {tt("view_deeper_context", state.locale)}
                </summary>
                <p className="mt-2 text-[12px] leading-[17px] text-[#8A8A90] font-[450]">{rarity}</p>
              </details>
            )}
          </>
        )}

        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={onAddToVisit}
            className="w-full h-[54px] rounded-[14px] text-[16px] font-medium tracking-[-0.01em] bg-[#181714] text-[#FAF7F0] shadow-[0_7px_18px_rgba(20,18,15,0.12)] active:scale-[0.98] transition-transform"
          >
            {isAdded ? tt("added_check", state.locale) : tt("add_to_my_visit", state.locale)}
          </button>
          <div className="flex gap-3">
            {audioUrl && (
              <ListenButton
                key={`${artwork.id}-${state.locale}`}
                audioUrl={audioUrl}
                locale={state.locale}
                artworkId={artwork.id}
              />
            )}
            <button
              type="button"
              onClick={onToggleFavorite}
              aria-pressed={isFavorite}
              className="w-[44px] h-[44px] rounded-full bg-[rgba(24,23,20,0.055)] border border-[rgba(24,23,20,0.06)] flex items-center justify-center"
            >
              <Heart className={`w-4 h-4 ${isFavorite ? "fill-[#181714] text-[#181714]" : "text-[#181714]"}`} />
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
            className="w-full h-[50px] rounded-[14px] bg-[rgba(24,23,20,0.055)] border border-[rgba(24,23,20,0.06)] text-[#25231F] text-[15px] font-medium tracking-[-0.01em]"
          >
            {tt("scan_next_artwork", state.locale)}
          </button>
          {/* Direct route to Progress/Recap from the card itself, without
              first bouncing through Camera. */}
          <button
            type="button"
            onClick={onGoProgress}
            className="w-full text-center text-[13px] font-semibold text-[#67635C] pt-1"
          >
            {tt("view_visit_progress", state.locale)}
          </button>
        </div>
      </div>
    </div>
  );
}
