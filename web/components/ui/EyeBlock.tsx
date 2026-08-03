import { Eye } from "lucide-react";

// "Eye Block mt5: rounded 16px bg #FFF8E1 border #F5E6B8 p3.5 flex gap3 -
// Icon w7 h7 rounded-full bg-black text-white center - Text 13.5px 19px
// -0.01em #5C4D1E 500" — "returns eye to painting" (the where-to-look copy).
export default function EyeBlock({ text }: { text: string }) {
  return (
    <div className="mt-5 rounded-[16px] bg-[#FFF8E1] border border-[#F5E6B8] p-3.5 flex gap-3">
      <div className="w-7 h-7 rounded-full bg-black text-white flex items-center justify-center shrink-0 mt-0.5">
        <Eye className="w-4 h-4" />
      </div>
      <p className="text-[13.5px] leading-[19px] tracking-[-0.01em] text-[#5C4D1E] font-[500]">{text}</p>
    </div>
  );
}
