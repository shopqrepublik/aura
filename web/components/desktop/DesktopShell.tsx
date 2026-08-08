"use client";

import { Smartphone, Download, ArrowRight } from "lucide-react";
import PhoneFrame from "@/components/ui/PhoneFrame";
import HeroMuseumBackdrop from "./HeroMuseumBackdrop";
import DesktopHeader from "./DesktopHeader";
import JourneySection from "./JourneySection";
import RecapStrip from "./RecapStrip";
import { tt } from "@/lib/i18n";
import type { Locale } from "@/lib/types";

// Round 6, Block 3 -- "phone as object" composition pass. Round 4's
// clamp(560,59vh,650) was tuned to keep Journey+Recap in the same
// screenshot, but it left the phone stage's own max-height (height minus
// header) too short to ever reach the stage's own width clamp -- the
// phone was rendering height-bound, silently well under its intended
// width. Raising the floor/ceiling here is what actually lets the bigger
// phone in PHONE_STAGE below render at its real size instead of getting
// squeezed by a hero that's too short for it.
const HERO_HEIGHT = "clamp(636px, 62vh, 700px)";
const HEADER_HEIGHT = 72;
// -8px buffer (was -24px when the phone stage had its own 24px bottom
// padding) -- round 5 dropped that padding to let the phone's bottom
// actually meet the hero/journey boundary, so it can use nearly all the
// remaining vertical room instead of stopping short of it.
const PHONE_STAGE_MAX_HEIGHT = `calc(${HERO_HEIGHT} - ${HEADER_HEIGHT}px - 8px)`;

export default function DesktopShell({
  locale,
  onSetLocale,
  children,
}: {
  locale: Locale;
  onSetLocale: (locale: Locale) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="relative" style={{ background: "var(--desktop-canvas)" }}>
      <section className="relative overflow-hidden" style={{ height: HERO_HEIGHT }}>
        <HeroMuseumBackdrop />
        {/* This div is the ACTUAL root cause round 4's opacity/filter
            tuning kept failing to fix "architecture almost invisible."
            The earlier version ended its `background` shorthand in a
            trailing solid color (", #F5EFE4"). Per the CSS background
            shorthand spec, a trailing color-only layer becomes THIS
            element's own background-color, painted BEHIND the gradient
            but still WITHIN this div -- so everywhere the radial gradient
            itself went transparent (most of the hero outside a small
            hotspot near the center, especially the left and bottom), this
            div rendered an OPAQUE ivory panel, fully hiding
            HeroMuseumBackdrop underneath regardless of that component's
            own values. No trailing color here now -- this is purely a
            semi-transparent wash (never fully opaque, floors at 0.06 at
            the far edge, never 0) that lets the photo underneath show
            through everywhere. The solid canvas fill lives ONLY on the
            outer wrapper two lines up (`background: var(--desktop-canvas)`),
            never mixed into this layer. */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse at 70% 32%, rgba(255,248,229,0.58) 0%, rgba(246,239,226,0.34) 42%, rgba(245,239,228,0.16) 68%, rgba(245,239,228,0.06) 100%)",
          }}
        />

        {/* Round 6, Block 3b -- the "one museum scene, not two columns"
            fix. Shrinking HeroMuseumBackdrop above left the middle third
            of the hero (between the headline's right edge and the
            phone's left edge) as flat, uncovered canvas color -- there's
            no clock detail in the source photo to reveal there even at
            higher opacity, so the fix isn't "more clock," it's a separate
            atmosphere: a soft warm haze with no hard edges, sitting on
            TOP of the ivory wash (not under it) so the wash doesn't
            bleach its warmth out. Centered between the two columns and
            heavily blurred -- this is what a visitor's eye reads as
            "warm light filling the room" instead of "gap between two
            panels." */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse 640px 520px at 58% 60%, rgba(233,199,146,0.30) 0%, rgba(233,199,146,0.16) 45%, rgba(233,199,146,0) 78%)",
            filter: "blur(38px)",
          }}
        />

        <div className="relative flex flex-col" style={{ height: "100%" }}>
          <DesktopHeader locale={locale} onSetLocale={onSetLocale} />

          {/* Round 6, Block 3 -- alignItems changed stretch -> center. The
              old approach stretched both columns to the full hero height
              and anchored each internally (text via padding-top, phone via
              justify-content:flex-end); that's what made the hero read as
              two independent columns instead of one scene. Centering both
              on the same row means the text block and the phone now share
              one visual mid-line -- they read as occupying the same
              space, not stacked against opposite edges of it. Gap tightened
              50-100 -> 40-80 to pull them into a single composition instead
              of two separated panels. */}
          <div
            className="relative z-10 mx-auto grid"
            style={{
              width: "min(1480px, calc(100vw - 96px))",
              flex: 1,
              minHeight: 0,
              gridTemplateColumns: "minmax(560px, 1fr) minmax(420px, 0.82fr)",
              gap: "clamp(40px, 4.5vw, 80px)",
              alignItems: "center",
            }}
          >
            <div style={{ maxWidth: 600 }}>
              <div
                className="text-[11px] font-semibold tracking-[0.16em] uppercase text-[var(--desktop-secondary)]"
                style={{ marginBottom: 20 }}
              >
                MUSÉE D&apos;ORSAY · PARIS
              </div>
              {/* Round 6, Block 2 -- target break is "A different / way to
                  see / the museum." at the 1728px reference viewport.
                  Deployment hotfix -- maxWidth was a fixed 465px, tuned
                  only against 1728px. The font grows via its own
                  clamp(88px,6vw,118px), so at 1920px+ the same fixed box
                  wrapped one word short and orphaned "the" onto its own
                  line (4 lines instead of 3). maxWidth now scales at the
                  same 6vw rate the font already does (27vw is the ratio
                  465/1728 was already sitting at, so 1728px itself is
                  unaffected) -- this only moves the wrap boundary, no
                  font/size/weight/spacing/color values changed. */}
              <h1
                style={{
                  fontFamily: "var(--font-editorial)",
                  maxWidth: "clamp(430px, 27vw, 520px)",
                  fontSize: "clamp(88px, 6vw, 118px)",
                  lineHeight: 0.9,
                  fontWeight: 300,
                  letterSpacing: "-0.045em",
                  color: "#191815",
                }}
              >
                {tt("home_hero_title", locale)}
              </h1>
              <p style={{ maxWidth: 430, marginTop: 22, fontSize: 18, fontWeight: 400, lineHeight: 1.5, color: "#5E584F" }}>
                {tt("home_hero_subtitle", locale)}
              </p>

              <button
                type="button"
                className="flex items-center justify-between"
                style={{
                  width: 328,
                  height: 56,
                  marginTop: 22,
                  padding: "0 20px",
                  borderRadius: 13,
                  background: "#171714",
                  color: "#FAF7F0",
                  fontSize: 16,
                  fontWeight: 500,
                  boxShadow: "0 11px 26px rgba(28,23,17,0.13)",
                }}
              >
                {tt("start_visit_label", locale)}
                <ArrowRight className="w-[18px] h-[18px]" />
              </button>

              <div className="grid" style={{ gridTemplateColumns: "auto auto", gap: 26, marginTop: 14 }}>
                <div className="flex items-center gap-3">
                  <div
                    className="rounded-full flex items-center justify-center shrink-0"
                    style={{
                      width: 38,
                      height: 38,
                      background: "rgba(248,243,234,0.68)",
                      border: "1px solid rgba(35,31,26,0.10)",
                    }}
                  >
                    <Smartphone className="w-[16px] h-[16px]" />
                  </div>
                  <div>
                    <div className="text-[13px] font-medium text-[var(--desktop-ink)]" style={{ lineHeight: 1.3 }}>
                      {tt("desktop_open_on_phone", locale)}
                    </div>
                    <div className="text-[11px]" style={{ color: "#827B70", lineHeight: 1.3 }}>
                      {tt("desktop_scan_to_continue", locale)}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div
                    className="rounded-full flex items-center justify-center shrink-0"
                    style={{
                      width: 38,
                      height: 38,
                      background: "rgba(248,243,234,0.68)",
                      border: "1px solid rgba(35,31,26,0.10)",
                    }}
                  >
                    <Download className="w-[16px] h-[16px]" />
                  </div>
                  <div>
                    <div className="text-[13px] font-medium text-[var(--desktop-ink)]" style={{ lineHeight: 1.3 }}>
                      {tt("desktop_install_elyio", locale)}
                    </div>
                    <div className="text-[11px]" style={{ color: "#827B70", lineHeight: 1.3 }}>
                      {tt("desktop_available_platforms", locale)}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Round 6, Block 3 -- phone as a physical object in the scene,
                not a screenshot laid on top of the page. Stage width
                clamp raised ~9% (330-360 -> 360-392) and the taller
                HERO_HEIGHT above means PHONE_STAGE_MAX_HEIGHT no longer
                squeezes it back down under that width. A 50px translateY
                (on top of the existing rightward nudge) drops it further
                into the clock's spread instead of sitting near the
                header, and the ambient glow underneath is bigger and
                warmer (62%->74% of the stage, 0.34->0.48 alpha, 60->80px
                blur) so it reads as the light the phone is sitting in,
                not a faint hint of one. */}
            <div className="relative flex flex-col items-center">
              <div
                aria-hidden="true"
                className="absolute rounded-full pointer-events-none"
                style={{
                  width: "74%",
                  height: "74%",
                  bottom: "6%",
                  background: "radial-gradient(circle, rgba(232,197,142,0.48), transparent 68%)",
                  filter: "blur(80px)",
                }}
              />
              <div
                style={{
                  width: "clamp(360px, 22.3vw, 392px)",
                  transform: "translate(30px, 0px)",
                  filter: "drop-shadow(0 38px 90px rgba(42,32,22,0.18)) drop-shadow(0 12px 30px rgba(42,32,22,0.11))",
                }}
              >
                <PhoneFrame maxHeight={PHONE_STAGE_MAX_HEIGHT}>{children}</PhoneFrame>
              </div>
            </div>
          </div>
        </div>

        <div
          className="absolute bottom-0 pointer-events-none"
          style={{ left: 40, right: 40, height: 1, background: "rgba(41,35,28,0.10)" }}
        />
      </section>

      <JourneySection locale={locale} />
      <RecapStrip locale={locale} />
    </div>
  );
}
