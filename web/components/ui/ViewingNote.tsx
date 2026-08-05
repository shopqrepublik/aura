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
      className="mt-5 flex gap-3"
      style={{
        backgroundColor: hexToRgba(accent, 0.1),
        borderLeft: `2px solid ${hexToRgba(accent, 0.7)}`,
        borderRadius: "4px 16px 16px 4px",
        padding: "17px 18px",
      }}
    >
      <Eye className="w-[18px] h-[18px] shrink-0 mt-0.5 text-[#181714]/60" strokeWidth={1.5} />
      <p className="text-[15px] leading-[21px] text-[#272622] font-normal">{text}</p>
    </div>
  );
}
