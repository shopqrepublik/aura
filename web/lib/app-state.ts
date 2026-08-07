"use client";

import { useCallback, useMemo, useState } from "react";
import * as api from "./api";
import { getArtwork, MISSIONS } from "./artworks";
import { isMissionComplete } from "./missions";
import { track } from "./analytics";
import type { Artwork, Locale, Mode } from "./types";

export type Screen = "home" | "camera" | "card" | "progress" | "recap";

export interface AppState {
  screen: Screen;
  locale: Locale;
  mode: Mode;
  visitId: string | null;
  visitStarted: boolean;
  startTime: number | null;
  seen: string[]; // artwork ids, in scan order
  favorites: Set<string>;
  added: Set<string>;
  currentArtwork: Artwork | null;
  lastConfidence: number;
  scanStatus: string | null; // transient message on the camera screen
  cardOpenedAt: number | null; // real wall-clock timestamp, for Deep focus
}

const initialState: AppState = {
  screen: "home",
  locale: "en",
  mode: "normal",
  visitId: null,
  visitStarted: false,
  startTime: null,
  seen: [],
  favorites: new Set(),
  added: new Set(),
  currentArtwork: null,
  lastConfidence: 0,
  scanStatus: null,
  cardOpenedAt: null,
};

export function useElyioApp() {
  const [state, setState] = useState<AppState>(initialState);

  const goto = useCallback((screen: Screen) => setState((s) => ({ ...s, screen })), []);
  const setLocale = useCallback((locale: Locale) => setState((s) => ({ ...s, locale })), []);
  const setMode = useCallback((mode: Mode) => setState((s) => ({ ...s, mode })), []);

  const startVisit = useCallback(async () => {
    setState((s) => {
      if (s.visitStarted) return s;
      track("visit_started");
      return { ...s, visitStarted: true, startTime: Date.now() };
    });
    setState((s) => {
      if (!s.visitId) {
        api.createVisit(s.locale).then((visit) => {
          setState((s2) => ({ ...s2, visitId: visit.id }));
        }).catch(() => {
          // Visit tracking is best-effort — recognition still works without a
          // visit id, we just can't persist progress server-side.
        });
      }
      return s;
    });
    goto("camera");
  }, [goto]);

  const recognizeFrame = useCallback(async (imageBase64: string) => {
    setState((s) => ({ ...s, scanStatus: "scanning" }));
    track("scan_attempt");
    try {
      const result = await api.recognize(imageBase64, state.locale);
      const artwork = result.artwork_id ? getArtwork(result.artwork_id) : undefined;

      if (!artwork || result.status === "no_match") {
        track("scan_failed", { reason: result.status });
        setState((s) => ({ ...s, scanStatus: "not_identified" }));
        return;
      }

      // "needs_confirmation" (backend/app/main.py CONFIDENCE_REVIEW band) is
      // shown as a regular card today -- there's no separate confirm/reject
      // UI yet (out of scope here). candidate_confirmed still fires for
      // this band specifically so the low-confidence-match rate is visible
      // in PostHog even before that UI exists; a real confirm step, when
      // built, should fire this on the user's actual confirm tap instead.
      if (result.status === "needs_confirmation") {
        track("candidate_confirmed", { artwork_id: artwork.id, confidence: result.confidence });
      }
      track("scan_success", { artwork_id: artwork.id, confidence: result.confidence, status: result.status });

      setState((s) => {
        const alreadySeen = s.seen.includes(artwork.id);
        if (!alreadySeen) {
          // mission_completed (§13): seen is only ever appended to here, so
          // this is the one place a mission can flip from incomplete to
          // complete -- compare before/after this specific addition rather
          // than re-deriving from the post-update state, so a mission whose
          // target was already scanned earlier in the visit doesn't re-fire.
          for (const m of MISSIONS) {
            if (!isMissionComplete(m.id, s.seen) && isMissionComplete(m.id, [...s.seen, artwork.id])) {
              track("mission_completed", { mission_id: m.id });
            }
          }
        }
        return {
          ...s,
          currentArtwork: artwork,
          lastConfidence: result.confidence,
          seen: alreadySeen ? s.seen : [...s.seen, artwork.id],
          scanStatus: null,
          screen: "card",
          cardOpenedAt: Date.now(),
        };
      });
    } catch {
      track("scan_failed", { reason: "error" });
      setState((s) => ({ ...s, scanStatus: "not_identified" }));
    }
  }, [state.locale]);

  const addToVisit = useCallback(() => {
    setState((s) => {
      if (!s.currentArtwork) return s;
      const id = s.currentArtwork.id;
      const nextAdded = new Set(s.added);
      const wasAdded = nextAdded.has(id);
      if (wasAdded) {
        nextAdded.delete(id);
      } else {
        nextAdded.add(id);
        track("artwork_added", { artwork_id: id });
        if (s.visitId) api.addVisitArtwork(s.visitId, id, s.lastConfidence).catch(() => {});
      }
      return { ...s, added: nextAdded };
    });
  }, []);

  const toggleFavorite = useCallback(() => {
    setState((s) => {
      if (!s.currentArtwork) return s;
      const id = s.currentArtwork.id;
      const next = new Set(s.favorites);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        track("artwork_favorited", { artwork_id: id });
      }
      return { ...s, favorites: next };
    });
  }, []);

  const completeVisit = useCallback(async () => {
    // Reads seen.length via the setState updater (and returns `s` unchanged)
    // rather than closing over the outer `state` -- this callback's deps
    // are [state.visitId, goto], so a closed-over state.seen could be stale
    // by the time this actually runs.
    setState((s) => {
      track("visit_completed", { works_count: s.seen.length });
      return s;
    });
    if (state.visitId) {
      api.completeVisit(state.visitId).catch(() => {});
    }
    goto("recap");
  }, [state.visitId, goto]);

  const newVisit = useCallback(() => {
    setState((s) => ({ ...initialState, locale: s.locale }));
  }, []);

  const seenArtworks = useMemo(
    () => state.seen.map((id) => getArtwork(id)).filter((a): a is Artwork => !!a),
    [state.seen]
  );

  return {
    state,
    seenArtworks,
    actions: { goto, setLocale, setMode, startVisit, recognizeFrame, addToVisit, toggleFavorite, completeVisit, newVisit },
  };
}
