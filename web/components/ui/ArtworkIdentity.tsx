"use client";

// Result Experience V2: this component is now identity only. The first
// product moment is no longer a database-style header followed by a long
// methodology block; CardScreen owns the visitor hierarchy explicitly:
// identity -> value/scale -> why it matters -> look closer.
export default function ArtworkIdentity({
  artist,
  artistFallback,
  title,
  year,
}: {
  artist: string | null;
  artistFallback: string;
  title: string;
  year: string;
}) {
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
    </div>
  );
}
