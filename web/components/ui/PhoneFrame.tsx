// iPhone 15 Pro frame — exact classNames mined from
// D:\AURA\design\ELYIO-iPhone-WoW-Design-System.html (see
// COMPONENT SPECS FOR FIGMA > iPhone Frame in ELYIO-FINAL-PROMPT.md).
// Landing-page showcase only — the real app (app/app) renders full-viewport,
// since on an actual phone the phone itself is the frame.
export default function PhoneFrame({
  children,
  label,
  note,
  maxHeight,
}: {
  children: React.ReactNode;
  label?: string;
  note?: string;
  // Overrides the default md:max-h-[calc(100vh-135px)] below -- that
  // default assumes the frame lives in a roughly full-viewport-tall
  // context. The desktop hero (deliberately compressed to
  // clamp(640px,72vh,760px), not ~100vh) is shorter than that, so a caller
  // there needs to pass the ACTUAL available height or the 100vh-based
  // default won't bind tightly enough to prevent clipping. Plain inline
  // style, so it wins over the Tailwind class below without touching it.
  maxHeight?: string;
}) {
  return (
    <div className="group flex flex-col items-center w-full max-w-[390px]">
      <div
        // md:h-[852px] (fixed, unconditional) used to be here -- on a
        // desktop hero shorter than 852+135px tall (e.g. 1440x900) that
        // guaranteed bottom clipping no matter how much room the layout
        // otherwise had. aspect-[390/852] + md:max-h caps BOTH dimensions
        // from a single constraint (whichever binds first, per CSS's own
        // aspect-ratio sizing algorithm) so the frame shrinks to fit a
        // short viewport instead of overflowing it.
        // Round-4 art-direction pass: bezel thinned from p-[10px]/rounded-54
        // to p-[7px]/rounded-48 (still a real device frame, not the
        // "grubby oversized emulator" the thicker bezel read as), shadow
        // softened to the new warmer-toned spec.
        className="relative w-full max-w-[390px] aspect-[390/852] h-auto min-h-[640px] md:min-h-0 md:max-h-[calc(100vh-135px)] rounded-[48px] bg-[#090909] p-[7px] shadow-[0_36px_85px_rgba(46,36,25,0.17),0_12px_28px_rgba(46,36,25,0.12)] transition-all duration-[600ms] ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:-translate-y-2"
        style={maxHeight ? { maxHeight } : undefined}
      >
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[92px] h-[26px] bg-black rounded-b-[15px] z-30" />
        <div className="absolute top-[10px] left-1/2 -translate-x-1/2 w-[54px] h-[6px] bg-[#1a1a1a] rounded-full z-30 opacity-60" />
        <div className="w-full h-full rounded-[41px] overflow-hidden bg-white relative flex flex-col">
          {children}
        </div>
        <div className="absolute bottom-[8px] left-1/2 -translate-x-1/2 w-[128px] h-[5px] bg-white rounded-full z-30 mix-blend-difference opacity-80" />
      </div>
      {(label || note) && (
        <div className="mt-8 max-w-[320px] text-center">
          {label && <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#8E8E93]">{label}</div>}
          {note && <div className="mt-2 text-[13px] leading-[18px] text-[#6E6E73] font-[450]">{note}</div>}
        </div>
      )}
    </div>
  );
}
