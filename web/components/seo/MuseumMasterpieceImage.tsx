"use client";
import { useState } from "react";
import Image from "next/image";

export default function MuseumMasterpieceImage({
  src,
  alt,
  title,
  artist,
}: {
  src: string | null;
  alt: string;
  title: string;
  artist: string;
}) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div className="mg-masterpiece-textled">
        <span className="mg-masterpiece-textled-title">{title}</span>
        <span className="mg-masterpiece-textled-artist">{artist}</span>
      </div>
    );
  }
  return (
    <div className="mg-masterpiece-image">
      <Image
        src={src}
        alt={alt}
        fill
        sizes="(max-width: 760px) calc(100vw - 40px), 420px"
        style={{ objectFit: "cover" }}
        onError={() => setFailed(true)}
      />
    </div>
  );
}
