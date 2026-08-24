"use client";

import { ArrowLeft, Heart } from "lucide-react";
import SegmentControl from "@/components/ui/SegmentControl";
import ProvenanceReveal from "@/components/ui/ProvenanceReveal";
import { tt } from "@/lib/i18n";
import { generatedValueReveal, quietNoTrustedContext } from "@/lib/generated-enrichment";
import type { AppState } from "@/lib/app-state";
import type { Mode } from "@/lib/types";

export default function UncatalogedCardScreen({
  state,
  onBack,
  onSetMode,
  onAddToVisit,
  onToggleFavorite,
  onGoProgress,
}: {
  state: AppState;
  onBack: () => void;
  onSetMode: (mode: Mode) => void;
  onAddToVisit: () => void;
  onToggleFavorite: () => void;
  onGoProgress: () => void;
}) {
  const sighting = state.uncatalogedSighting;
  if (!sighting) return null;

  const enrichment = sighting.enrichment;
  const localeContent = enrichment.content[state.locale] || enrichment.content.en;
  const content = localeContent[state.mode] || localeContent.normal;
  const artist = enrichment.displayArtist || sighting.artist || tt("uncataloged_unknown_artist", state.locale);
  const title = enrichment.displayTitle || sighting.title || tt("uncataloged_unknown_title", state.locale);
  const isAdded = state.uncatalogedAdded.has(sighting.id);
  const isFavorite = state.favorites.has(sighting.id);
  const valueReveal = sighting.valueReveal || generatedValueReveal(enrichment, state.locale);
  const metaLine = [enrichment.displayDate, enrichment.objectType, enrichment.movementOrPeriod]
    .filter(Boolean)
    .filter((value, index, values) => values.indexOf(value) === index)
    .join(" · ");

  return (
    <div className="w-full h-full bg-[#F7F3EC] flex flex-col overflow-y-auto scrollbar-none">
      <div className="shrink-0 relative aspect-[4/3] w-full overflow-hidden bg-[#EDE8E1]">
        {sighting.imageUrl ? (
          <img
            src={sighting.imageUrl}
            alt={title}
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 bg-[linear-gradient(105deg,#E7E1D6_0%,#DAD3C6_50%,#CFC7B8_100%)]" />
        )}
        <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/10" />
        <button
          type="button"
          onClick={onBack}
          aria-label="Back"
          className="absolute top-4 left-4 w-9 h-9 rounded-full bg-black/40 backdrop-blur flex items-center justify-center"
        >
          <ArrowLeft className="w-4 h-4 text-white" />
        </button>
        <button
          type="button"
          onClick={onToggleFavorite}
          aria-label="Favorite"
          className="absolute top-4 right-4 w-9 h-9 rounded-full bg-black/40 backdrop-blur flex items-center justify-center"
        >
          <Heart className={`w-4 h-4 ${isFavorite ? "text-[#F3D5C0] fill-[#F3D5C0]" : "text-white"}`} />
        </button>
      </div>

      <div
        className="rounded-t-[30px] -mt-4 relative z-10 flex-1 px-5 pt-5 pb-[32px]"
        style={{
          backgroundColor: "#FBF8F2",
          boxShadow: "0 -16px 45px rgba(22,19,15,0.09), inset 0 1px 0 rgba(255,255,255,0.80)",
        }}
      >
        <SegmentControl mode={state.mode} locale={state.locale} onChange={onSetMode} />

        <div className="mt-5 text-[11px] font-semibold tracking-[0.16em] uppercase text-[#696763]">
          {artist.toUpperCase()}
        </div>
        <h1
          className="mt-1 font-medium leading-[0.98] text-[#181714]"
          style={{ fontFamily: "var(--font-editorial)", fontSize: "clamp(30px, 7.7vw, 38px)", letterSpacing: 0 }}
        >
          {title}
        </h1>

        {metaLine && <p className="mt-2 text-[13px] leading-[18px] text-[#68665f]">{metaLine}</p>}

        <p className="mt-5 text-[19px] leading-[25px] text-[#24231F] font-medium tracking-[-0.01em]">{content.hook}</p>

        {valueReveal ? (
          <div>
            <ProvenanceReveal
              valueReveal={valueReveal}
              accent="#8C6A4C"
              inventoryNumber={sighting.id}
              locale={state.locale}
              mode={state.mode}
              museumCity={state.museumCity}
              artworkId={sighting.id}
            />
          </div>
        ) : (
          <p className="mt-4 text-[12px] leading-[17px] text-[#77736d]">{quietNoTrustedContext(state.locale)}</p>
        )}

        <Section label={tt("why_it_matters_label", state.locale)}>
          {content.whyItMatters}
        </Section>

        <div
          className="mt-5 rounded-[16px] px-4 py-3.5"
          style={{ background: "rgba(140,106,76,0.10)", borderLeft: "2px solid rgba(140,106,76,0.70)" }}
        >
          <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#696763]">
            {tt("look_closer_label", state.locale)}
          </div>
          <p className="mt-1.5 text-[16px] leading-[22px] text-[#272622]">{content.lookCloser}</p>
        </div>

        <Section label={state.locale === "fr" ? "Contexte" : state.locale === "zh-Hans" ? "背景" : "Context"}>
          {state.mode === "kids" && content.funFactOrMission ? content.funFactOrMission : content.deeperContext}
        </Section>

        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={onAddToVisit}
            className="w-full h-[54px] rounded-[14px] text-[16px] font-medium tracking-[-0.01em] bg-[#181714] text-[#FAF7F0] shadow-[0_7px_18px_rgba(20,18,15,0.12)] active:scale-[0.98] transition-transform"
          >
            {isAdded ? tt("added_check", state.locale) : tt("add_to_my_visit", state.locale)}
          </button>
          <button
            type="button"
            onClick={onBack}
            className="w-full h-[50px] rounded-[14px] bg-[rgba(24,23,20,0.055)] border border-[rgba(24,23,20,0.06)] text-[#25231F] text-[15px] font-medium tracking-[-0.01em]"
          >
            {tt("scan_next_artwork", state.locale)}
          </button>
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

function Section({ label, children }: { label: string; children: string }) {
  return (
    <div className="mt-5">
      <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#696763]">{label}</div>
      <p className="mt-2 text-[15px] leading-[21px] text-[#3E3A34]">{children}</p>
    </div>
  );
}
