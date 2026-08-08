"use client";

import { useEffect, useState } from "react";

// Starts `null` on both server and first client render (matches this
// codebase's existing hydration-mismatch convention -- see useAuth's
// `loading` and useMuseumDetection's "checking" state) so SSR HTML and the
// first client paint always agree; only resolves to a real boolean from an
// effect, after mount, once `window` actually exists. Callers should treat
// `null` as "not yet known" and fall back to the existing (mobile) layout
// during that window rather than rendering nothing.
export function useIsDesktop(breakpointPx = 1100): boolean | null {
  const [isDesktop, setIsDesktop] = useState<boolean | null>(null);

  useEffect(() => {
    const mql = window.matchMedia(`(min-width: ${breakpointPx}px)`);
    setIsDesktop(mql.matches);
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [breakpointPx]);

  return isDesktop;
}
