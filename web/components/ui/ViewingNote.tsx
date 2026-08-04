import { Eye } from "lucide-react";
import { hexToRgba } from "@/lib/cardReveal";

// Replaces EyeBlock (design-direction-v3.md §7): "не жёлтая предупреждающая
// карточка — Viewing Note" -- background is the artwork's own accent color
// at 8-12% opacity instead of a fixed warning-yellow, a thin 2px accent
// line on the left instead of a full colored border, no yellow anywhere.
// Constitution-v1.md's step 5 ("now I look at the painting again") is
// exactly this block's job: it's the thing shown right after the price
// reveal that sends the eye back to the artwork.
export default function ViewingNote({ text, accent }: { text: string; accent: string }) {
  return (
    <div
      className="mt-5 rounded-[14px] pl-4 pr-3.5 py-3.5 flex gap-3"
      style={{
        backgroundColor: hexToRgba(accent, 0.1),
        borderLeft: `2px solid ${hexToRgba(accent, 0.7)}`,
      }}
    >
      <div className="w-6 h-6 rounded-full bg-[#111111]/[0.06] flex items-center justify-center shrink-0 mt-0.5">
        <Eye className="w-3.5 h-3.5 text-[#111111]" />
      </div>
      <p className="text-[13.5px] leading-[19px] tracking-[-0.01em] text-[#3C3C43] font-[500]">{text}</p>
    </div>
  );
}
