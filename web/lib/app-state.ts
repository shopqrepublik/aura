"use client";

import { useCallback, useMemo, useState } from "react";
import * as api from "./api";
import { getArtwork, ARTWORKS } from "./artworks";
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
    try {
      const result = await api.recognize(imageBase64, state.locale);
      const artwork = result.artwork_id ? getArtwork(result.artwork_id) : undefined;

      if (!artwork || result.status === "no_match") {
        setState((s) => ({ ...s, scanStatus: "not_identified" }));
        return;
      }

      setState((s) => ({
        ...s,
        currentArtwork: artwork,
        lastConfidence: result.confidence,
        seen: s.seen.includes(artwork.id) ? s.seen : [...s.seen, artwork.id],
        scanStatus: null,
        screen: "card",
        cardOpenedAt: Date.now(),
      }));
    } catch {
      setState((s) => ({ ...s, scanStatus: "not_identified" }));
    }
  }, [state.locale]);

  const addToVisit = useCallback(() => {
    setState((s) => {
      if (!s.currentArtwork) return s;
      const id = s.currentArtwork.id;
      const nextAdded = new Set(s.added);
      const wasAdded = nextAdded.has(id);
      if (wasAdded) nextAdded.delete(id);
      else nextAdded.add(id);
      if (!wasAdded && s.visitId) {
        api.addVisitArtwork(s.visitId, id, s.lastConfidence).catch(() => {});
      }
      return { ...s, added: nextAdded };
    });
  }, []);

  const toggleFavorite = useCallback(() => {
    setState((s) => {
      if (!s.currentArtwork) return s;
      const id = s.currentArtwork.id;
      const next = new Set(s.favorites);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { ...s, favorites: next };
    });
  }, []);

  const completeVisit = useCallback(async () => {
    if (state.visitId) {
      api.completeVisit(state.visitId).catch(() => {});
    }
    goto("recap");
  }, [state.visitId, goto]);

  const newVisit = useCallback(() => {
    setState((s) => ({ ...initialState, locale: s.locale }));
  }, []);

  // TEMP DEBUG: seed a visit and jump to Recap. kind: "3" three works
  // (>€100M total, no seal), "billion" crosses the real €1B threshold.
  // Revert before considering this done.
  const debugShowRecap = useCallback((kind: string) => {
    setState((s) => {
      const sorted = ARTWORKS.slice().sort((a, b) => (b.estimate.high ?? 0) - (a.estimate.high ?? 0));
      let seen: string[];
      if (kind === "billion") {
        seen = [];
        let sum = 0;
        for (const a of sorted) {
          seen.push(a.id);
          sum += a.estimate.high ?? 0;
          if (sum >= 1000) break;
        }
      } else {
        seen = sorted.slice(2, 5).map((a) => a.id);
      }
      return {
        ...s,
        seen,
        favorites: new Set(seen.slice(0, 1)),
        added: new Set(),
        visitStarted: true,
        startTime: Date.now() - 22 * 60000,
        screen: "recap",
      };
    });
  }, []);

  const seenArtworks = useMemo(
    () => state.seen.map((id) => getArtwork(id)).filter((a): a is Artwork => !!a),
    [state.seen]
  );

  return {
    state,
    seenArtworks,
    actions: { goto, setLocale, setMode, startVisit, recognizeFrame, addToVisit, toggleFavorite, completeVisit, newVisit, debugShowRecap },
  };
}
