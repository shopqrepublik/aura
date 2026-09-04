"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { track, trackGoogleEvent } from "./analytics";

export interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

function isIosLike(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  const platform = navigator.platform || "";
  const maxTouchPoints = navigator.maxTouchPoints || 0;
  return /iPad|iPhone|iPod/.test(ua) || (platform === "MacIntel" && maxTouchPoints > 1);
}

function isSafari(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  return /^((?!chrome|android|crios|fxios|edgios).)*safari/i.test(ua);
}

export function isStandaloneDisplayMode(): boolean {
  if (typeof window === "undefined") return false;
  const standaloneMedia = window.matchMedia?.("(display-mode: standalone)").matches ?? false;
  const fullscreenMedia = window.matchMedia?.("(display-mode: fullscreen)").matches ?? false;
  const iosStandalone = Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
  return standaloneMedia || fullscreenMedia || iosStandalone;
}

export function usePwaInstall() {
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(() => isStandaloneDisplayMode());
  const [isIosSafari] = useState(() => isIosLike() && isSafari());
  const shownRef = useRef(false);

  useEffect(() => {
    if (isStandaloneDisplayMode()) track("pwa_standalone_open");
    const media = window.matchMedia?.("(display-mode: standalone)");
    const onDisplayModeChange = () => setInstalled(isStandaloneDisplayMode());
    media?.addEventListener?.("change", onDisplayModeChange);

    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      if (isStandaloneDisplayMode()) return;
      setInstallPrompt(event as BeforeInstallPromptEvent);
      if (!shownRef.current) {
        shownRef.current = true;
        track("pwa_install_prompt_shown");
      }
    };

    const onAppInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
      track("pwa_installed");
      trackGoogleEvent("pwa_installed");
    };

    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onAppInstalled);

    return () => {
      media?.removeEventListener?.("change", onDisplayModeChange);
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onAppInstalled);
    };
  }, []);

  const promptInstall = useCallback(async () => {
    if (!installPrompt || installed) return;
    track("pwa_install_started");
    trackGoogleEvent("pwa_install_prompt");
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    track(choice.outcome === "accepted" ? "pwa_install_prompt_accepted" : "pwa_install_prompt_dismissed", {
      platform: choice.platform,
    });
    setInstallPrompt(null);
  }, [installPrompt, installed]);

  return {
    canPromptInstall: Boolean(installPrompt) && !installed,
    installed,
    isIosSafari,
    promptInstall,
  };
}
