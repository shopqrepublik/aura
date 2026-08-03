"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, X } from "lucide-react";
import { haptics } from "@/lib/haptics";
import { tt } from "@/lib/i18n";
import type { AppState } from "@/lib/app-state";

// "02 CAMERA" — bg/guide/shutter classNames mined from the HTML reference.
// Real capture logic ported from frontend/app.js (tryStartCamera +
// captureFrameBase64): getUserMedia -> <video> -> draw to a 512px-wide
// canvas -> JPEG base64, same as the old PWA sends to /v1/recognize.
//
// "Auto-capture on" in the reference copy is decorative — there is no
// client-side artwork detection here (that would need real computer vision
// running continuously, which is out of scope); capture is still a manual
// shutter tap, exactly like the old frontend. Flagged in the README as a
// label without behavior behind it, not silently implied as real.
export default function CameraScreen({
  state,
  onCapture,
  onGoProgress,
  onGoHome,
  preview = false,
}: {
  state: AppState;
  onCapture: (imageBase64: string) => void;
  onGoProgress: () => void;
  onGoHome: () => void;
  // Static-mockup mode for the landing page's Screens showcase: never
  // requests camera permission just because the card scrolled into view.
  preview?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hasCamera, setHasCamera] = useState(false);
  const [flashing, setFlashing] = useState(false);

  useEffect(() => {
    if (preview) return;
    let stream: MediaStream | null = null;
    let cancelled = false;

    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => {
        if (cancelled) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        stream = s;
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
        setHasCamera(true);
      })
      .catch(() => setHasCamera(false));

    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [preview]);

  useEffect(() => {
    haptics.detect();
  }, []);

  function captureFrameBase64(): string | null {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return null;
    canvas.width = 512;
    canvas.height = Math.round(512 * (video.videoHeight / video.videoWidth));
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.85).split(",")[1];
  }

  function handleShutter() {
    haptics.shutter();
    setFlashing(true);
    setTimeout(() => setFlashing(false), 400);
    const frame = captureFrameBase64();
    if (frame) onCapture(frame);
  }

  const failed = state.scanStatus === "not_identified";
  const scanning = state.scanStatus === "scanning";

  return (
    <div className="relative w-full h-full bg-[#0A0A0A] overflow-hidden">
      <div className="absolute inset-0">
        {hasCamera ? (
          <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full bg-[radial-gradient(100%_100%_at_50%_40%,#8FA8C8_0%,#6B7EA8_25%,#4A5A85_55%,#1A2333_100%)] opacity-90" />
        )}
        <div className="absolute inset-0 bg-[radial-gradient(70%_60%_at_50%_40%,#d6e8ff_0%,transparent_100%)] opacity-30 pointer-events-none" />
      </div>

      {flashing && <div className="absolute inset-0 bg-white animate-flash pointer-events-none z-30" />}

      <button
        type="button"
        onClick={onGoProgress}
        aria-label="Visit progress"
        className="absolute top-[54px] left-4 z-20 w-9 h-9 rounded-full bg-black/40 backdrop-blur flex items-center justify-center"
      >
        <ArrowUp className="w-4 h-4 text-white" />
      </button>
      <button
        type="button"
        onClick={onGoHome}
        aria-label="Close"
        className="absolute top-[54px] right-4 z-20 w-9 h-9 rounded-full bg-black/40 backdrop-blur flex items-center justify-center"
      >
        <X className="w-4 h-4 text-white" />
      </button>

      <div className="relative z-10 pt-[54px] text-center">
        <div className="text-[15px] font-[600] text-white tracking-[-0.01em] drop-shadow">
          {failed ? tt("we_could_not_identify", state.locale) : tt("frame_artwork_fully", state.locale)}
        </div>
        <div className="text-[12px] text-white/60 mt-1 font-medium">
          {scanning ? tt("scanning", state.locale) : tt("hold_steady", state.locale)}
        </div>
      </div>

      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[264px] h-[352px] z-10">
        <div className="absolute inset-0 border border-white/15 rounded-[8px]" />
        <div className="absolute -top-[1px] -left-[1px] w-8 h-8 border-t-[2.5px] border-l-[2.5px] border-white rounded-tl-[10px]" />
        <div className="absolute -top-[1px] -right-[1px] w-8 h-8 border-t-[2.5px] border-r-[2.5px] border-white rounded-tr-[10px]" />
        <div className="absolute -bottom-[1px] -left-[1px] w-8 h-8 border-b-[2.5px] border-l-[2.5px] border-white rounded-bl-[10px]" />
        <div className="absolute -bottom-[1px] -right-[1px] w-8 h-8 border-b-[2.5px] border-r-[2.5px] border-white rounded-br-[10px]" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className={`w-[52px] h-[52px] rounded-full border-2 border-white/30 flex items-center justify-center ${scanning ? "animate-pulse" : ""}`}>
            <div className="w-2 h-2 bg-white rounded-full" />
          </div>
        </div>
      </div>

      <canvas ref={canvasRef} className="hidden" />

      <div className="absolute bottom-0 left-0 right-0 z-20 pb-[34px] pt-8 bg-gradient-to-t from-black/60 to-transparent flex flex-col items-center gap-6">
        <div className="flex items-center gap-12">
          <div className="w-10 h-10 rounded-full bg-white/15 backdrop-blur-xl" />
          <button
            type="button"
            onClick={handleShutter}
            disabled={scanning}
            aria-label="Capture"
            className="w-[72px] h-[72px] rounded-full bg-white shadow-[0_0_0_4px_rgba(255,255,255,0.25),0_8px_24px_rgba(0,0,0,0.4)] flex items-center justify-center active:scale-95 transition-transform disabled:opacity-60"
          >
            <div className="w-[62px] h-[62px] rounded-full border border-black/10" />
          </button>
          <div className="w-10 h-10 rounded-full bg-white/15 backdrop-blur-xl flex items-center justify-center" />
        </div>
      </div>
    </div>
  );
}
