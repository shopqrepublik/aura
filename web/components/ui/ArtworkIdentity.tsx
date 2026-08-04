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
  title,
  year,
  hookText,
}: {
  artist: string;
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
      <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#8A8A90]">
        {artist.toUpperCase()}
      </div>
      <h1 className="mt-1 text-[22px] font-bold leading-[24px] tracking-[-0.03em] text-[#111111]">{title}</h1>
      <p className="mt-1 text-[14px] text-[#626267] font-[450] tabular-nums">{year}</p>
      <p
        className="mt-4 text-[16px] leading-[24px] tracking-[-0.011em] text-[#1D1D1F] font-[450] transition-opacity duration-300 ease-out"
        style={{ opacity: hookVisible ? 1 : 0 }}
      >
        {hookText}
      </p>
    </div>
  );
}
