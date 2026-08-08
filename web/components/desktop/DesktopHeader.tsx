"use client";

import { Download } from "lucide-react";
import { LOCALES, tt } from "@/lib/i18n";
import { track } from "@/lib/analytics";
import type { Locale } from "@/lib/types";

// Desktop rebuild spec §15, hero-refinement round 3 (§7) -- explicit 3-col
// grid (wordmark / nav / controls) so the nav is genuinely centered against
// the header's own content width, not just visually near-center via flex
// justify-between (which centers relative to the OUTER edges, not the
// wordmark-to-controls span -- looked slightly off once the controls
// grew wider with the Install button).
//
// Nav labels ("How it works" / "Experience" / "Your visits") and "Install
// ELYIO" are still inert (no href/onClick): no Journey/Recap anchor
// targets to scroll to yet from the nav specifically, and no real
// beforeinstallprompt wiring (spec §21, later work). Honest placeholders,
// not broken links.
export default function DesktopHeader({
  locale,
  onSetLocale,
}: {
  locale: Locale;
  onSetLocale: (locale: Locale) => void;
}) {
  return (
    <header
      className="relative z-10 mx-auto grid items-center"
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
        <span>{tt("desktop_nav_how_it_works", locale)}</span>
        <span>{tt("desktop_nav_experience", locale)}</span>
        <span>{tt("desktop_nav_your_visits", locale)}</span>
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
        <button
          type="button"
          className="h-[38px] px-4 rounded-[12px] bg-[var(--desktop-ink)] text-[#FAF6ED] text-[13px] font-medium flex items-center gap-1.5"
        >
          {tt("desktop_install_elyio", locale)}
          <Download className="w-[13px] h-[13px]" />
        </button>
      </div>
    </header>
  );
}
