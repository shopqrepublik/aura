"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles, EyeOff, MousePointerClick } from "lucide-react";
import PhoneFrame from "@/components/ui/PhoneFrame";
import HomeScreen from "@/components/screens/HomeScreen";
import CameraScreen from "@/components/screens/CameraScreen";
import CardScreen from "@/components/screens/CardScreen";
import ProgressScreen from "@/components/screens/ProgressScreen";
import RecapScreen from "@/components/screens/RecapScreen";
import { getArtwork } from "@/lib/artworks";
import { artworkArtistDisplayName } from "@/lib/artist-display";
import { tt } from "@/lib/i18n";
import type { AppState } from "@/lib/app-state";
import type { Artwork } from "@/lib/types";

// Desktop landing / design-system reference page, per the end of
// ELYIO-FINAL-PROMPT.md. Lives at /design, not "/" — the root route is the
// real working app (app/page.tsx), so an installed icon or a bare domain
// visit never lands here; this stays reachable for internal/dev use only.
// Structure and copy ported from the real markup
// embedded in ELYIO-iPhone-WoW-Design-System.html (extracted from its
// minified React bundle: nav ids/labels, hero copy, Principles/Palette
// sections, the 5 screens' id/label/note triples, dev-handoff block, and
// the IntersectionObserver scroll-spy with its exact rootMargin) — not
// re-imagined from the terse prose spec alone. Two deliberate departures
// from that reference:
//   1. Rebranded AURA -> ELYIO throughout, including the footer, which the
//      reference file itself had NOT rebranded yet.
//   2. The "Screens" grid embeds the REAL screen components (this app's
//      actual HomeScreen/CameraScreen/CardScreen/ProgressScreen/RecapScreen)
//      instead of the reference's separate inline demo components, so the
//      showcase can never visually drift from the working app. CameraScreen
//      runs in `preview` mode here so scrolling the page never triggers a
//      real camera-permission prompt. The Typography section's example
//      strings and the Screens demo artwork are pulled from a REAL curated
//      catalog entry (Renoir's Bal du moulin de la Galette) rather than the
//      reference's invented "€80–120M EST." example — this project's
//      estimates are null until an editor reviews them, and that rule holds
//      here too, including in the Recap demo (no fabricated billion badge).
const NAV_ITEMS = [
  { id: "principles", label: "Principles" },
  { id: "palette", label: "Palette" },
  { id: "type", label: "Type" },
  { id: "screens", label: "Screens" },
];

const PRINCIPLES = [
  {
    icon: Sparkles,
    title: "Content is Hero",
    desc: "Artwork first. UI retreats to 8% opacity until needed. No chrome competes with a Monet.",
  },
  {
    icon: EyeOff,
    title: "Invisible UI",
    desc: "Interface appears on intent, not on load. The camera is the navigation. Point is the click.",
  },
  {
    icon: MousePointerClick,
    title: "One Action Per Screen",
    desc: "Every view has a single, unmistakable verb. Start. Frame. Add. Continue. Share.",
  },
];

const PALETTE = [
  { hex: "#FAFAF9", name: "Canvas", role: "Background" },
  { hex: "#111111", name: "Ink", role: "Text" },
  { hex: "#000000", name: "Obsidian", role: "Primary" },
  { hex: "#F5F5F7", name: "Stone", role: "Card / Surface" },
  { hex: "#FF3B30", name: "Billion", role: "Accent" },
  { hex: "#FFF8E1", name: "Glow", role: "Eye highlight" },
];

const noop = () => {};
const noopAsync = async () => {};

// This module is evaluated once on the server and once again on the client,
// at genuinely different (if close) wall-clock moments, so DEMO_NOW itself
// is NOT identical between the two. That's fine: ProgressScreen/RecapScreen
// never read Date.now() (or anything derived from it) during their initial
// render — they only do so from an effect, after mount — so a differing
// DEMO_NOW here can't produce a hydration mismatch. A fixed historical
// constant was tried instead and rejected: it would make the "minutes ago"
// demo stat grow without bound the longer this page has existed, which is
// a worse, purely visual bug for a value that's meant to look like ~52m.
const DEMO_NOW = Date.now();

// Real catalog entry (Top 20 curated) — used for both the Typography
// section's example strings and the Card/Progress/Recap screen demos.
const DEMO_ARTWORK = getArtwork("orsay_rf_2739") as Artwork; // Renoir — Bal du moulin de la Galette
const DEMO_SEEN_IDS = ["orsay_rf_2739", "orsay_rf_1975_19", "orsay_rf_699"];
const DEMO_SEEN: Artwork[] = DEMO_SEEN_IDS.map((id) => getArtwork(id)).filter((a): a is Artwork => !!a);

// 11 highest-estimate catalog works, summed high-estimate crosses the real
// €1B threshold (~€1045M) -- for exercising the Collector's Seal + the
// widest headline size fitFontSize can pick, per recap-image.ts's own
// "isBillion" gate (never decorative, only shown past a genuine sum).
const DEMO_BILLION_IDS = [
  "orsay_rf_2511", "orsay_rf_1975_19", "orsay_rf_2765", "orsay_rf_1961_6",
  "orsay_rf_2739", "orsay_rf_1668", "orsay_rf_644", "orsay_rf_1951_42",
  "orsay_rf_1949_17", "orsay_rf_2718", "orsay_rf_1944_9",
];
const DEMO_BILLION_SEEN: Artwork[] = DEMO_BILLION_IDS.map((id) => getArtwork(id)).filter((a): a is Artwork => !!a);

function demoState(overrides: Partial<AppState>): AppState {
  return {
    screen: "home",
    locale: "en",
    mode: "normal",
    museumId: "orsay",
    visitId: null,
    visitStarted: false,
    startTime: DEMO_NOW - 52 * 60000,
    seen: DEMO_SEEN_IDS,
    favorites: new Set(),
    added: new Set([DEMO_ARTWORK.id]),
    catalogArtworks: {},
    currentArtwork: null,
    uncatalogedSighting: null,
    lastConfidence: 0.94,
    scanStatus: null,
    cardOpenedAt: null,
    ...overrides,
  };
}

const SCREEN_DEMOS = [
  {
    id: "home",
    label: "01 — MUSEUM HOME",
    note: "First-use state -- editorial exhibition-cover cover, no black circle, honest GPS dot next to the static museum name.",
    node: (
      <HomeScreen
        state={demoState({ seen: [] })}
        seenArtworks={[]}
        isAuthenticated={true}
        onStartVisit={noop}
        onSetLocale={noop}
        onSignInWithEmail={noopAsync}
        onSignInWithGoogle={noopAsync}
      />
    ),
  },
  {
    id: "home-continue",
    label: "01b — MUSEUM HOME · CONTINUE VISIT",
    note: "Returning-user state (§17) -- shown instead of the empty first-use hero once a visit is already in progress.",
    node: (
      <HomeScreen
        state={demoState({ visitStarted: true, seen: DEMO_SEEN_IDS })}
        seenArtworks={DEMO_SEEN}
        isAuthenticated={true}
        onStartVisit={noop}
        onSetLocale={noop}
        onSignInWithEmail={noopAsync}
        onSignInWithGoogle={noopAsync}
      />
    ),
  },
  {
    id: "camera",
    label: "02 — CAMERA",
    note: "Shutter: iOS camera haptic. Guide auto-scales to artwork ratio. Capture: 40ms white flash.",
    node: (
      <CameraScreen
        state={demoState({ screen: "camera" })}
        onCapture={noop}
        onGoProgress={noop}
        onGoHome={noop}
        preview
      />
    ),
  },
  {
    id: "camera-scanning",
    label: "02b — CAMERA · SCANNING",
    note: "Waiting UX for the real 3-6s /v1/recognize round trip (backend/scripts/latency_test.py) -- warm-gold breathing corners, rotating ring, 3-dot caption instead of a frozen screen.",
    node: (
      <CameraScreen
        state={demoState({ screen: "camera", scanStatus: "scanning" })}
        onCapture={noop}
        onGoProgress={noop}
        onGoHome={noop}
        preview
      />
    ),
  },
  {
    id: "card",
    label: "03 — ARTWORK CARD • HERO",
    note: "Explicit \"Scan next artwork\" + \"View visit progress\" buttons — no swipe/drag gesture exists. Value badge reveals once. Eye block fades in 240ms.",
    node: (
      <CardScreen
        state={demoState({ screen: "card", currentArtwork: DEMO_ARTWORK })}
        onSetMode={noop}
        onBack={noop}
        onAddToVisit={noop}
        onToggleFavorite={noop}
        onGoProgress={noop}
      />
    ),
  },
  {
    id: "progress",
    label: "04 — VISIT PROGRESS",
    note: "WatchOS-style ring. Live numbers. Thumbnails momentum scroll. Bottom sheet sticky.",
    node: (
      <ProgressScreen
        state={demoState({
          screen: "progress",
          currentArtwork: DEMO_ARTWORK,
          cardOpenedAt: DEMO_NOW - 4 * 60000,
        })}
        seenArtworks={DEMO_SEEN}
        onBack={noop}
        onContinueScanning={noop}
        onCompleteVisit={noop}
      />
    ),
  },
  {
    id: "recap",
    label: "05 — VISIT RECAP • VIRAL",
    note: "Native share sheet. Gradient mesh. Billion badge only fires past a real €1B threshold.",
    node: <RecapScreen state={demoState({ screen: "recap" })} seenArtworks={DEMO_SEEN} onNewVisit={noop} />,
  },
  {
    id: "recap-billion",
    label: "05b — VISIT RECAP · €1B+",
    note: "Widest headline size + Collector's Seal together -- checks the value/subtitle line gap at the largest fitFontSize candidate (recap-image.ts), not just the typical 3-work case.",
    node: <RecapScreen state={demoState({ screen: "recap" })} seenArtworks={DEMO_BILLION_SEEN} onNewVisit={noop} />,
  },
];

const TYPE_ROWS = [
  { label: "Title 28px Bold", sample: DEMO_ARTWORK.title.en, meta: "-0.03em / 700", size: "text-[24px] md:text-[28px] font-bold tracking-[-0.03em]" },
  { label: "Headline 22px", sample: tt("my_visit_title", "en"), meta: "-0.02em / 600", size: "text-[22px] font-semibold tracking-[-0.02em]" },
  { label: "Body 16px", sample: DEMO_ARTWORK.why.en, meta: "-0.011em / 450", size: "text-[16px] leading-[24px] font-[450] max-w-[520px]" },
  {
    label: "Caption 13px Upper",
    sample: `${artworkArtistDisplayName(DEMO_ARTWORK, "en").toUpperCase()} • ${tt("frame_artwork_fully", "en").toUpperCase()}`,
    meta: "0.12em / 600",
    size: "text-[11px] font-semibold tracking-[0.12em] uppercase",
  },
];

export default function LandingPage() {
  const [active, setActive] = useState("principles");
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActive(entry.target.id);
        });
      },
      { rootMargin: "-40% 0px -55% 0px" }
    );
    Object.values(sectionRefs.current).forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, []);

  function scrollToSection(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="min-h-screen bg-[#FAFAF9] text-[#111111] selection:bg-black selection:text-white antialiased overflow-x-clip">
      <div className="sticky top-0 z-[100] backdrop-blur-[20px] bg-[#FAFAF9]/80 border-b border-black/[0.06]">
        <div className="mx-auto max-w-[1280px] px-4 md:px-10 h-[48px] flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="text-[14px] font-bold tracking-[-0.02em]">ELYIO</div>
            <div className="hidden md:flex items-center gap-1 p-1 rounded-full bg-[#F5F5F7] border border-black/[0.04]">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  onClick={(e) => {
                    e.preventDefault();
                    scrollToSection(item.id);
                  }}
                  className={`px-3.5 h-7 rounded-full text-[12px] font-semibold transition-all flex items-center ${
                    active === item.id ? "bg-white shadow-[0_1px_6px_rgba(0,0,0,0.08)] text-black" : "text-[#8E8E93] hover:text-black"
                  }`}
                >
                  {item.label}
                </a>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 text-[11px] font-medium text-[#8E8E93]">
              <div className="w-1.5 h-1.5 rounded-full bg-[#30D158]" /> Design System v1.0
            </div>
            <div className="h-7 px-3 rounded-full bg-black text-white text-[11px] font-semibold flex items-center tracking-wide">
              iPhone 15 Pro • 390px
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-[1280px] px-4 md:px-10 pt-12 md:pt-28 pb-10">
        <div className="max-w-[760px]">
          <div className="inline-flex items-center gap-2 h-7 px-3 rounded-full bg-white border border-black/10 shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
            <div className="w-4 h-4 rounded-full bg-black text-white flex items-center justify-center text-[9px] font-bold">E</div>
            <span className="text-[11px] font-semibold tracking-widest uppercase">ELYIO — Point. Discover. Understand.</span>
          </div>
          <h1 className="mt-8 text-[38px] md:text-[68px] font-bold leading-[0.9] tracking-[-0.05em] text-balance">
            Design System
            <br />
            <span className="text-[#8E8E93] font-[600]">iPhone-like,</span>
            <br />
            WoW, minimal.
          </h1>
          <p className="mt-6 text-[18px] md:text-[20px] leading-[28px] tracking-[-0.015em] text-[#6E6E73] font-[450] max-w-[520px]">
            A premium interactive showcase for the museum app. Built like Apple ships hardware: content is hero, UI is invisible, one verb per screen.
          </p>
          <div className="mt-8 flex items-center gap-3">
            <div className="text-[11px] font-semibold uppercase tracking-widest text-[#8E8E93]">5 screens • 54px radius • SF Pro feel</div>
            <div className="h-[1px] w-12 bg-black/10" />
            <div className="text-[11px] font-medium text-[#8E8E93]">Linear.app + Apple editorial</div>
          </div>
        </div>
      </div>

      <section
        id="principles"
        ref={(el) => {
          sectionRefs.current.principles = el;
        }}
        className="mx-auto max-w-[1280px] px-4 md:px-10 py-12 md:py-24 scroll-mt-[48px]"
      >
        <div className="flex items-baseline justify-between mb-8">
          <h2 className="text-[28px] font-bold tracking-[-0.03em]">Principles</h2>
          <span className="text-[11px] font-semibold tracking-[0.14em] uppercase text-[#8E8E93]">03 Rules</span>
        </div>
        <div className="grid md:grid-cols-3 gap-3 md:gap-4">
          {PRINCIPLES.map((p) => (
            <div key={p.title} className="rounded-[20px] bg-white border border-black/[0.06] p-5 md:p-6 shadow-[0_8px_24px_rgba(0,0,0,0.04)]">
              <div className="w-9 h-9 rounded-full bg-[#F5F5F7] flex items-center justify-center mb-5">
                <p.icon className="w-4 h-4" />
              </div>
              <div className="text-[16px] font-semibold tracking-[-0.01em]">{p.title}</div>
              <div className="mt-2 text-[14px] leading-[20px] text-[#6E6E73] font-[450]">{p.desc}</div>
            </div>
          ))}
        </div>
      </section>

      <section
        id="palette"
        ref={(el) => {
          sectionRefs.current.palette = el;
        }}
        className="mx-auto max-w-[1280px] px-4 md:px-10 py-12 md:py-20 scroll-mt-[48px] border-t border-black/[0.06]"
      >
        <div className="flex items-baseline justify-between mb-8">
          <h2 className="text-[28px] font-bold tracking-[-0.03em]">Palette</h2>
          <span className="text-[11px] font-semibold tracking-[0.14em] uppercase text-[#8E8E93]">6 Swatches</span>
        </div>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {PALETTE.map((sw) => (
            <div key={sw.hex} className="rounded-[16px] bg-white border border-black/[0.06] p-3">
              <div className="aspect-square rounded-[12px] border border-black/[0.06]" style={{ background: sw.hex }} />
              <div className="mt-3 text-[12px] font-semibold">{sw.name}</div>
              <div className="text-[11px] font-medium text-[#8E8E93]">{sw.role}</div>
              <div className="mt-1 text-[11px] font-mono text-black/50">{sw.hex}</div>
            </div>
          ))}
        </div>
      </section>

      <section
        id="type"
        ref={(el) => {
          sectionRefs.current.type = el;
        }}
        className="mx-auto max-w-[1280px] px-4 md:px-10 py-12 md:py-20 scroll-mt-[48px] border-t border-black/[0.06]"
      >
        <div className="flex items-baseline justify-between mb-8">
          <h2 className="text-[28px] font-bold tracking-[-0.03em]">Typography</h2>
          <span className="text-[11px] font-semibold tracking-[0.14em] uppercase text-[#8E8E93]">SF Pro • Inter</span>
        </div>
        <div className="rounded-[20px] bg-white border border-black/[0.06] divide-y divide-black/[0.06] overflow-hidden">
          {TYPE_ROWS.map((row) => (
            <div key={row.label} className="p-5 md:p-8 flex flex-col md:flex-row md:items-baseline justify-between gap-2">
              <div className="text-[11px] font-semibold uppercase tracking-widest text-[#8E8E93] w-[140px] shrink-0">{row.label}</div>
              <div className={row.size}>{row.sample}</div>
              <div className="text-[12px] text-[#8E8E93] font-mono hidden md:block">{row.meta}</div>
            </div>
          ))}
        </div>
      </section>

      <section
        id="screens"
        ref={(el) => {
          sectionRefs.current.screens = el;
        }}
        className="border-t border-black/[0.06] bg-white/60 backdrop-blur overflow-x-clip"
      >
        <div className="mx-auto max-w-[1280px] px-4 md:px-10 py-12 md:py-28">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12 md:mb-16">
            <div>
              <div className="text-[11px] font-semibold tracking-[0.18em] uppercase text-[#8E8E93]">iPhone 15 Pro • 390×852</div>
              <h2 className="mt-3 text-[32px] md:text-[44px] font-bold tracking-[-0.04em] leading-[0.95] text-balance">
                5 Screens in
                <br />
                iPhone frames
              </h2>
            </div>
            <div className="max-w-[360px] text-[14px] leading-[20px] text-[#6E6E73] font-[450]">
              Each frame lifts on hover. Same components as the working app — no separate mockup to drift out of sync.
            </div>
          </div>

          <div className="sticky top-[48px] z-20 px-1 py-2.5 bg-[#FAFAF9]/90 backdrop-blur-xl border-y md:border md:rounded-full border-black/[0.06] md:w-fit flex gap-1 overflow-x-auto scrollbar-none max-w-full">
            {SCREEN_DEMOS.map((s) => (
              <a
                key={s.id}
                href={`#screen-${s.id}`}
                onClick={(e) => {
                  e.preventDefault();
                  document.getElementById(`screen-${s.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
                }}
                className="whitespace-nowrap px-3.5 h-7 rounded-full text-[12px] font-semibold bg-white border border-black/10 shadow-sm hover:bg-black hover:text-white transition-colors flex items-center"
              >
                {s.label.split("—")[1]?.trim() || s.label}
              </a>
            ))}
          </div>

          <div className="mt-10 md:mt-16 grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-x-16 md:gap-y-28 place-items-center">
            {SCREEN_DEMOS.map((s) => (
              <div key={s.id} id={`screen-${s.id}`} className="scroll-mt-[120px] w-full flex justify-center">
                <PhoneFrame label={s.label} note={s.note}>
                  {s.node}
                </PhoneFrame>
              </div>
            ))}
          </div>

          <div className="mt-20 md:mt-28 rounded-[24px] bg-black text-white p-6 md:p-12 flex flex-col md:flex-row justify-between gap-8">
            <div>
              <div className="text-[11px] tracking-[0.18em] uppercase font-semibold opacity-60">Developer handoff</div>
              <div className="mt-4 text-[24px] font-bold tracking-[-0.03em] leading-[26px] max-w-[420px]">
                Build like iPhone.
                <br />
                No navigation chrome. Camera as cursor. Value as status.
              </div>
            </div>
            <div className="grid grid-cols-2 gap-8 text-[13px] leading-[18px] font-[450] opacity-80 max-w-[420px]">
              <div>
                <span className="text-white font-semibold">Motion:</span> spring(0.16,1,0.3,1) 600ms. All lifts use transform only.
              </div>
              <div>
                <span className="text-white font-semibold">Blur:</span> backdrop-blur-2xl 40px. Never compete with art.
              </div>
              <div>
                <span className="text-white font-semibold">Radius:</span> 54px phone, 24px cards, full buttons. 16px inner.
              </div>
              <div>
                <span className="text-white font-semibold">Shadow:</span> layered 50/100 and 20/40. No hard edges.
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-black/[0.06] py-10">
        <div className="mx-auto max-w-[1280px] px-4 md:px-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-2 text-[11px] font-medium text-[#8E8E93]">
          <div>ELYIO Design System • Built for designer → developer handoff</div>
          <div className="hidden md:block">FAFAF9 • 390px • 54px • Lucide • elyio.co</div>
        </div>
      </footer>
    </div>
  );
}
