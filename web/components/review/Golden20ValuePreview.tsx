"use client";

import ProvenanceReveal from "@/components/ui/ProvenanceReveal";
import type { Locale, ValueReveal } from "@/lib/types";

interface PreviewArtwork {
  id: string;
  title: string;
  artist: string | null;
  date: string;
  room: string;
  inventoryNumber: string;
  valueReveal: ValueReveal | null;
  hook: string;
}

export default function Golden20ValuePreview({ artworks, locale = "en" }: { artworks: PreviewArtwork[]; locale?: Locale }) {
  return (
    <main className="min-h-screen bg-[#F7F3EC] px-6 py-8 text-[#181714]">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#67635C]">Local review only</div>
          <h1 className="mt-2 text-[40px] font-medium leading-none" style={{ fontFamily: "var(--font-editorial)" }}>
            Louvre Golden 20 value reveal preview
          </h1>
          <p className="mt-2 max-w-2xl text-[14px] leading-6 text-[#67635C]">
            Frozen Golden 20 content is read from local export files. No production content, recognition asset, embedding, or image-byte writes occur here.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {artworks.map((artwork) => (
            <article key={artwork.id} className="rounded-[8px] border border-[rgba(24,23,20,0.10)] bg-[#FBF8F2] p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#8B867E]">{artwork.id}</div>
              <h2 className="mt-1 text-[24px] font-medium leading-tight" style={{ fontFamily: "var(--font-editorial)" }}>
                {artwork.title}
              </h2>
              <div className="mt-1 text-[13px] text-[#67635C]">{artwork.artist || "Creator not listed"}</div>
              <div className="mt-1 text-[12px] text-[#8B867E]">{artwork.date}</div>
              <div className="mt-1 text-[12px] text-[#8B867E]">{artwork.room}</div>

              <ProvenanceReveal
                valueReveal={artwork.valueReveal}
                accent="#8E5B48"
                inventoryNumber={artwork.inventoryNumber}
                locale={locale}
                mode="normal"
              />

              <p className="mt-4 text-[14px] leading-6 text-[#302E29]">{artwork.hook}</p>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
