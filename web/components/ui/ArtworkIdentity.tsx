"use client";

import { useEffect, useState } from "react";
import { usePrefersReducedMotion } from "@/lib/cardReveal";

// Design-direction-v3 §2/§14 "Observe" stage — art first, money later.
// Order: artist -> title -> year -> one short hook. The hero image itself
// stays exactly where it already was in CardScreen.tsx (untouched -- this
// component is deliberately just the text block underneath it, so the
// working image/back-button/SCAN-badge markup isn't touched by this
// redesign at all).
//
// The "hook" here is the artwork's existing `why` text (or, when Kids mode
// excludes the work, the exclusion message) -- v3's own mockup shows a
// SHORTER, differently-worded hook than its later labelled "WHY IT
// MATTERS" section, but the catalog has only one `why` field per work, and
// inventing a second, shorter paraphrase would be fabricating editorial
// content this project has consistently refused to do elsewhere (see
// lib/types.ts's comments on Estimate, RecapScreen's refusal to show fake
// GPS/attention stats, etc.). Showing the one real `why` text here, before
// the price reveal, is the closest honest match to v3's actual intent
// (constitution-v1.md's 5-step arc explicitly wants "meaning" understood
// BEFORE "how much" is revealed) -- and per constitution-v1's step 5 ("now
// I look at the painting again"), ViewingNote (ex-EyeBlock, the `where`
// text) does that job AFTER the reveal instead, so nothing is shown twice.
export default function ArtworkIdentity({
  artist,
  artistFallback,
  title,
  year,
  hookText,
}: {
  artist: string | null;
  artistFallback: string;
  title: string;
  year: string;
  hookText: string;
}) {
  const reducedMotion = usePrefersReducedMotion();
  const [hookVisible, setHookVisible] = useState(reducedMotion);

  useEffect(() => {
    // reducedMotion=true is already handled by hookVisible's initial value
    // (useState(reducedMotion) above) -- nothing to do here in that case.
    if (reducedMotion) return;
    // Frame 2 "Meaning" (design-direction-v3.md §5): hook fades in 180ms
    // after the card mounts, settled by ~380ms.
    const id = setTimeout(() => setHookVisible(true), 180);
    return () => clearTimeout(id);
  }, [reducedMotion]);

  return (
    <div>
      <div className="text-[11px] font-semibold tracking-[0.16em] uppercase text-[#696763]">
        {(artist || artistFallback).toUpperCase()}
      </div>
      {/* Editorial serif title -- catalogue-entry weight, not an app
          screen title. Falls through to Georgia/serif for zh-Hans (Cormorant
          Garamond has no CJK glyphs), which is the expected/accepted
          degradation, not a bug. */}
      <h1
        className="mt-1 font-medium leading-[0.98] tracking-[-0.025em] text-[#181714]"
        style={{ fontFamily: "var(--font-editorial)", fontSize: "clamp(28px, 7.3vw, 34px)" }}
      >
        {title}
      </h1>
      <p className="mt-1.5 text-[13px] leading-[18px] text-[#68665f]">{year}</p>
      <p
        className="mt-4 text-[17px] leading-[25px] tracking-[-0.01em] text-[#272622] font-normal transition-opacity duration-300 ease-out"
        style={{ opacity: hookVisible ? 1 : 0 }}
      >
        {hookText}
      </p>
    </div>
  );
}
