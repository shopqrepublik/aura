"use client";

import { haptics } from "@/lib/haptics";
import { tt } from "@/lib/i18n";
import type { Locale, Mode } from "@/lib/types";

// Exact classNames from ELYIO-iPhone-WoW-Design-System.html:
// "flex p-1 rounded-full bg-[#F5F5F7] mb-5" wrapping 3x
// "flex-1 h-7 rounded-full ... transition-all" buttons, active "bg-black
// text-white shadow", inactive "text-[#8E8E93]".
//
// Mode (Normal/Simple/Kids) and locale are two independent axes — this
// component only ever touches `mode`; the label text is looked up via the
// current `locale` but switching languages never resets or is reset by mode.
export default function SegmentControl({
  mode,
  locale,
  onChange,
}: {
  mode: Mode;
  locale: Locale;
  onChange: (mode: Mode) => void;
}) {
  const options: { value: Mode; key: string }[] = [
    { value: "normal", key: "mode_normal" },
    { value: "simple", key: "mode_simple" },
    { value: "kids", key: "mode_kids" },
  ];

  return (
    <div className="flex p-1 rounded-full bg-[#F5F5F7] mb-5">
      {options.map((opt) => {
        const active = mode === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            onClick={() => {
              if (opt.value !== mode) haptics.segmentSwitch();
              onChange(opt.value);
            }}
            className={`flex-1 h-7 rounded-full text-[12px] font-semibold transition-all ${
              active ? "bg-black text-white shadow" : "text-[#8E8E93]"
            }`}
          >
            {tt(opt.key, locale)}
          </button>
        );
      })}
    </div>
  );
}
