"use client";

import { useEffect, useRef, useState } from "react";
import { Download } from "lucide-react";
import { LOCALES, tt } from "@/lib/i18n";
import { track } from "@/lib/analytics";
import { usePwaInstall } from "@/lib/pwaInstall";
import type { Locale } from "@/lib/types";

// Desktop rebuild spec §15, hero-refinement round 3 (§7) -- explicit 3-col
// grid (wordmark / nav / controls) so the nav is genuinely centered against
// the header's own content width, not just visually near-center via flex
// justify-between (which centers relative to the OUTER edges, not the
// wordmark-to-controls span -- looked slightly off once the controls
// grew wider with the Install button).
//
// Final wiring pass -- "How it works"/"Experience" scroll to the real
// Journey section (id="journey", JourneySection.tsx); "Install ELYIO"
// triggers the real beforeinstallprompt (spec §21) when the browser
// supports it, falling back to a short honest instructions popover
// otherwise (Safari/Firefox never fire that event at all); "Your visits"
// stays a disabled label with a "coming soon" tooltip -- there's no real
// visit-history view on desktop yet.
export default function DesktopHeader({
  locale,
  onSetLocale,
}: {
  locale: Locale;
  onSetLocale: (locale: Locale) => void;
}) {
  const [showInstallHint, setShowInstallHint] = useState(false);
  const installWrapRef = useRef<HTMLDivElement>(null);
  const { canPromptInstall, installed, promptInstall } = usePwaInstall();

  useEffect(() => {
    if (!showInstallHint) return;
    const onClickOutside = (e: MouseEvent) => {
      if (installWrapRef.current && !installWrapRef.current.contains(e.target as Node)) {
        setShowInstallHint(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [showInstallHint]);

  const scrollToJourney = () => {
    document.getElementById("journey")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleInstallClick = async () => {
    if (canPromptInstall) {
      setShowInstallHint(false);
      await promptInstall();
      return;
    }
    setShowInstallHint((v) => !v);
  };

  return (
    // z-20, not z-10 -- DesktopShell's phone-stage row is ALSO z-10 and
    // comes later in DOM order, so at equal z-index it was painting on
    // top of this header's own popover (the install-hint fallback was
    // rendering partially behind the phone). Header needs to win that
    // stacking fight since its own dropdown content lives here now.
    <header
      className="relative z-20 mx-auto grid items-center"
      style={{
        width: "min(1480px, calc(100vw - 80px))",
        height: 72,
        gridTemplateColumns: "1fr auto 1fr",
      }}
    >
      <div
        style={{ fontFamily: "var(--font-editorial)" }}
        className="text-[22px] font-medium tracking-[0.18em] text-[var(--desktop-ink)]"
      >
        ELYIO
      </div>

      <nav className="flex items-center gap-9 text-[13px] text-[#2E2B27]">
        <button type="button" onClick={scrollToJourney} className="hover:opacity-70 transition-opacity">
          {tt("desktop_nav_how_it_works", locale)}
        </button>
        <button type="button" onClick={scrollToJourney} className="hover:opacity-70 transition-opacity">
          {tt("desktop_nav_experience", locale)}
        </button>
        {/* Disabled, not removed -- an honest "not built yet" beats a
            link that goes nowhere. title= gives every browser a native
            tooltip for free; aria-disabled keeps it out of the tab order
            semantics without literally hiding it from screen readers. */}
        <span
          aria-disabled="true"
          title={tt("desktop_coming_soon", locale)}
          className="cursor-default select-none"
          style={{ opacity: 0.55 }}
        >
          {tt("desktop_nav_your_visits", locale)}
        </span>
      </nav>

      <div className="flex items-center justify-end gap-3">
        <select
          aria-label="Language"
          value={locale}
          onChange={(e) => {
            const next = e.target.value as Locale;
            track("language_selected", { locale: next });
            onSetLocale(next);
          }}
          className="h-[38px] min-w-[68px] px-3 rounded-[12px] text-[13px] font-medium text-[var(--desktop-ink)]"
          style={{ background: "rgba(250,247,240,0.55)", border: "1px solid rgba(30,27,22,0.16)" }}
        >
          {LOCALES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.code === "zh-Hans" ? "中文" : l.code.toUpperCase()}
            </option>
          ))}
        </select>
        {!installed && <div ref={installWrapRef} className="relative">
          <button
            type="button"
            onClick={handleInstallClick}
            className="h-[38px] px-4 rounded-[12px] bg-[var(--desktop-ink)] text-[#FAF6ED] text-[13px] font-medium flex items-center gap-1.5"
          >
            {tt("desktop_install_elyio", locale)}
            <Download className="w-[13px] h-[13px]" />
          </button>
          {/* Fallback for browsers that never fire beforeinstallprompt
              (Safari, Firefox) -- honest instructions, not a fake
              install action. */}
          {showInstallHint && (
            <div
              role="tooltip"
              className="absolute top-full right-0 mt-2 rounded-[12px] p-4"
              style={{
                width: 260,
                background: "#FFFDF8",
                border: "1px solid rgba(30,27,22,0.12)",
                boxShadow: "0 18px 40px rgba(28,23,17,0.14)",
              }}
            >
              <div className="text-[12px] font-semibold text-[var(--desktop-ink)]">
                {tt("desktop_install_hint_title", locale)}
              </div>
              <p className="mt-1.5 text-[11.5px] leading-[1.5]" style={{ color: "#5E584F" }}>
                {tt("desktop_install_hint_body", locale)}
              </p>
            </div>
          )}
        </div>}
      </div>
    </header>
  );
}
