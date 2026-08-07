"use client";

import { useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { tt } from "@/lib/i18n";
import { track } from "@/lib/analytics";
import type { Locale } from "@/lib/types";

// Mount this keyed by `${artwork.id}-${locale}` from the parent so React
// remounts (and therefore resets play/loading/error state, and stops any
// in-flight playback) on artwork or locale change, instead of needing an
// effect that resets state synchronously.
export default function ListenButton({
  audioUrl,
  locale,
  artworkId,
}: {
  audioUrl: string;
  locale: Locale;
  artworkId: string;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  // If playback fails (file missing, network error), disappear rather than
  // leave a dead button — same "hide, don't break the card" rule used for
  // null estimates elsewhere.
  if (hasError) return null;

  const handleClick = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
      return;
    }
    setIsLoading(true);
    audio.play().catch(() => {
      setIsLoading(false);
      setHasError(true);
    });
  };

  return (
    <>
      <audio
        ref={audioRef}
        src={audioUrl}
        preload="none"
        className="hidden"
        onPlay={() => {
          setIsPlaying(true);
          setIsLoading(false);
          track("audio_started", { artwork_id: artworkId, locale });
        }}
        onPause={() => setIsPlaying(false)}
        onEnded={() => {
          setIsPlaying(false);
          track("audio_completed", { artwork_id: artworkId, locale });
        }}
        onWaiting={() => setIsLoading(true)}
        onCanPlay={() => setIsLoading(false)}
        onError={() => {
          setIsPlaying(false);
          setIsLoading(false);
          setHasError(true);
        }}
      />
      <button
        type="button"
        onClick={handleClick}
        aria-pressed={isPlaying}
        className="flex-1 h-[44px] rounded-full bg-[#F5F5F7] text-[14px] font-semibold flex items-center justify-center gap-2"
      >
        {isLoading ? (
          "…"
        ) : isPlaying ? (
          <Pause className="w-4 h-4 fill-black" />
        ) : (
          <Play className="w-4 h-4 fill-black" />
        )}
        {isLoading ? tt("listen_label", locale) : isPlaying ? tt("listen_playing_label", locale) : tt("listen_label", locale)}
      </button>
    </>
  );
}
