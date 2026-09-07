"use client";
import { useState } from "react";
import Image from "next/image";

// Renders a local artwork asset with its natural aspect ratio (clamped to
// avoid extreme panoramas/portraits breaking the editorial grid). If the
// file unexpectedly fails at runtime, the media block is removed entirely
// and the story text reflows to a single column (see .mg-masterpiece-media
// and :has() rules in museum-guide.css) — never a fake artwork tile.
export default function MuseumMasterpieceImage({
  src,
  alt,
  width,
  height,
  attribution,
}: {
  src: string | null;
  alt: string;
  width: number | null;
  height: number | null;
  attribution: string | null;
}) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return <div className="mg-masterpiece-media" data-empty="true" aria-hidden="true" />;
  }
  const w = width && width > 0 ? width : 4;
  const h = height && height > 0 ? height : 5;
  // Clamp aspect ratio between 3:4 portrait and 16:10 landscape so very
  // wide panoramas and very tall scrolls don't distort the page rhythm.
  const ratio = Math.min(Math.max(w / h, 0.625), 1.6);
  return (
    <figure className="mg-masterpiece-media" style={{ aspectRatio: String(ratio) }}>
      <Image
        src={src}
        alt={alt}
        width={w}
        height={h}
        sizes="(max-width: 760px) calc(100vw - 40px), 480px"
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
        loading="lazy"
        onError={() => setFailed(true)}
      />
      {attribution ? <figcaption className="mg-credit">{attribution}</figcaption> : null}
    </figure>
  );
}
