// iPhone 15 Pro frame — exact classNames mined from
// D:\AURA\design\ELYIO-iPhone-WoW-Design-System.html (see
// COMPONENT SPECS FOR FIGMA > iPhone Frame in ELYIO-FINAL-PROMPT.md).
// Landing-page showcase only — the real app (app/app) renders full-viewport,
// since on an actual phone the phone itself is the frame.
export default function PhoneFrame({
  children,
  label,
  note,
}: {
  children: React.ReactNode;
  label?: string;
  note?: string;
}) {
  return (
    <div className="group flex flex-col items-center w-full max-w-[390px]">
      <div
        className="relative w-full max-w-[390px] aspect-[390/852] h-auto min-h-[640px] md:h-[852px] md:aspect-auto rounded-[54px] bg-black p-[10px] shadow-[0_50px_100px_-20px_rgba(0,0,0,0.25),0_20px_40px_-20px_rgba(0,0,0,0.3)] transition-all duration-[600ms] ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:-translate-y-2 group-hover:shadow-[0_60px_120px_-20px_rgba(0,0,0,0.35),0_30px_60px_-20px_rgba(0,0,0,0.25)]"
      >
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[96px] h-[28px] bg-black rounded-b-[16px] z-30" />
        <div className="absolute top-[11px] left-1/2 -translate-x-1/2 w-[56px] h-[6px] bg-[#1a1a1a] rounded-full z-30 opacity-60" />
        <div className="w-full h-full rounded-[44px] overflow-hidden bg-white relative flex flex-col">
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
