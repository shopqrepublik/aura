"use client";

import { useCallback, useMemo, useState } from "react";
import * as api from "./api";
import { getArtwork, MISSIONS } from "./artworks";
import { isMissionComplete } from "./missions";
import { track } from "./analytics";
import { isRecognitionNetworkError } from "./recognitionErrors";
import type { Artwork, Locale, Mode } from "./types";

export type Screen = "home" | "camera" | "card" | "progress" | "recap";

// Phase 2 §2 -- Stage 1 open recognition named a real artist/title, but
// fuzzy_match_catalog couldn't place it in the reviewed catalog. Distinct
// from "nothing recognized at all" (AppState.scanStatus === "not_identified",
// stays on Camera) -- this is a real, honest partial result, so it gets its
// own minimal card instead of a bare failure message. Never has estimate/
// why/where/rarity/audio/Kids text, because none of that has been reviewed
// for a work that isn't in the catalog at all.
export interface UncatalogedSighting {
  id: string;
  artist: string | null;
  title: string | null;
  date?: string | null;
  objectType?: string | null;
  whatYouAreLookingAt?: string | null;
  whyItMatters?: string | null;
  lookCloser?: string | null;
  confidence?: number | null;
}

export interface AppState {
  screen: Screen;
  locale: Locale;
  mode: Mode;
  // Phase 2 §1 -- resolved once, when a visit starts (HomeScreen passes the
  // detected/manually-confirmed museum id from useMuseumDetection), then
  // reused for every recognize() call during that visit rather than
  // re-deriving it per scan.
  museumId: string | null;
  visitId: string | null;
  visitStarted: boolean;
  startTime: number | null;
  seen: string[]; // artwork ids, in scan order
  favorites: Set<string>;
  added: Set<string>;
  catalogArtworks: Record<string, Artwork>;
  currentArtwork: Artwork | null;
  uncatalogedSighting: UncatalogedSighting | null;
  uncatalogedAdded: Set<string>;
  lastConfidence: number;
  scanStatus: string | null; // transient message on the camera screen
  pendingRecognitionImageBase64: string | null;
  cardOpenedAt: number | null; // real wall-clock timestamp, for Deep focus
}

const initialState: AppState = {
  screen: "home",
  locale: "en",
  mode: "normal",
  museumId: null,
  visitId: null,
  visitStarted: false,
  startTime: null,
  seen: [],
  favorites: new Set(),
  added: new Set(),
  catalogArtworks: {},
  currentArtwork: null,
  uncatalogedSighting: null,
  uncatalogedAdded: new Set(),
  lastConfidence: 0,
  scanStatus: null,
  pendingRecognitionImageBase64: null,
  cardOpenedAt: null,
};

export function useElyioApp() {
  const [state, setState] = useState<AppState>(initialState);

  const goto = useCallback((screen: Screen) => setState((s) => ({ ...s, screen })), []);
  const setLocale = useCallback((locale: Locale) => setState((s) => ({ ...s, locale })), []);
  const setMode = useCallback((mode: Mode) => setState((s) => ({ ...s, mode })), []);

  // Phase 2 §1 -- museumId comes from HomeScreen's useMuseumDetection
  // (detected via GPS or manually confirmed), not a hardcoded constant.
  // Resolved once here and reused for every recognize() call during this
  // visit, rather than re-checking geolocation per scan.
  const startVisit = useCallback(async (museumId: string) => {
    setState((s) => {
      if (s.visitStarted) return s;
      track("visit_started", { museum_id: museumId });
      return { ...s, visitStarted: true, startTime: Date.now(), museumId };
    });
    setState((s) => {
      if (!s.visitId) {
        api.createVisit(s.locale, museumId).then((visit) => {
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
    setState((s) => ({ ...s, scanStatus: "scanning", pendingRecognitionImageBase64: null }));
    track("scan_attempt", { museum_id: state.museumId, seen_count: state.seen.length });
    if (state.seen.length > 0) {
      track("second_scan_started", { museum_id: state.museumId, seen_count: state.seen.length });
    }
    track("recognition_started", { museum_id: state.museumId });
    try {
      const result = await api.recognize(imageBase64, state.locale, state.museumId ?? "");
      track("recognition_completed", {
        museum_id: state.museumId,
        status: result.status,
        confidence: result.confidence,
        recognition_mode: result.recognition_mode,
        resolved_artwork_id: result.artwork_id,
      });
      let artwork = result.artwork_id
        ? getArtwork(result.artwork_id) || state.catalogArtworks[result.artwork_id]
        : undefined;

      if (!artwork && result.artwork_id && result.status !== "no_match") {
        try {
          const raw = await api.getArtworkDetail(result.artwork_id, state.locale, state.mode);
          artwork = api.artworkFromCatalogDetail(raw);
        } catch {
          artwork = undefined;
        }
      }

      if (!artwork || result.status === "no_match") {
        // Phase 2 §2 -- Tier 2: Stage 1 recognized a real artist/title, just
        // not one fuzzy_match_catalog could place in the reviewed catalog.
        // Gets its own minimal card instead of the bare "not_identified"
        // failure message -- see UncatalogedSighting's doc comment above.
        const uncataloged = result.recognized_but_not_cataloged;
        if (uncataloged && (uncataloged.artist || uncataloged.title)) {
          track("scan_failed", { reason: "uncataloged" });
          track("catalog_no_match", {
            museum_id: state.museumId,
            confidence: result.confidence,
            ai_candidate: uncataloged,
          });
          setState((s) => ({
            ...s,
            uncatalogedSighting: buildUncatalogedSighting(uncataloged, result.vision, result.confidence),
            currentArtwork: null,
            scanStatus: null,
            screen: "card",
            cardOpenedAt: Date.now(),
          }));
          track("result_viewed", {
            result_type: "uncataloged",
            museum_id: state.museumId,
            confidence: result.confidence,
            ai_candidate: uncataloged,
          });
          return;
        }
        track("scan_failed", { reason: result.status });
        track("catalog_no_match", { museum_id: state.museumId, confidence: result.confidence });
        setState((s) => ({ ...s, scanStatus: "not_identified", pendingRecognitionImageBase64: null }));
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
      track("catalog_match", {
        museum_id: state.museumId,
        artwork_id: artwork.id,
        confidence: result.confidence,
        recognition_mode: result.recognition_mode,
      });
      track("result_viewed", {
        result_type: "catalog",
        museum_id: state.museumId,
        artwork_id: artwork.id,
        confidence: result.confidence,
        status: result.status,
      });

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
          catalogArtworks: getArtwork(artwork.id) ? s.catalogArtworks : { ...s.catalogArtworks, [artwork.id]: artwork },
          currentArtwork: artwork,
          uncatalogedSighting: null,
          lastConfidence: result.confidence,
          seen: alreadySeen ? s.seen : [...s.seen, artwork.id],
          scanStatus: null,
          pendingRecognitionImageBase64: null,
          screen: "card",
          cardOpenedAt: Date.now(),
        };
      });
    } catch (error) {
      track("recognition_failed", { museum_id: state.museumId, reason: error instanceof Error ? error.message : "error" });
      const networkError = isRecognitionNetworkError(error);
      track("scan_failed", { reason: networkError ? "network_error" : "error" });
      setState((s) => ({
        ...s,
        scanStatus: networkError ? "network_error" : "not_identified",
        pendingRecognitionImageBase64: networkError ? imageBase64 : null,
      }));
    }
  }, [state.catalogArtworks, state.locale, state.mode, state.museumId, state.seen.length]);

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

  const addUncatalogedToVisit = useCallback(() => {
    setState((s) => {
      if (!s.uncatalogedSighting) return s;
      const id = s.uncatalogedSighting.id;
      const nextAdded = new Set(s.uncatalogedAdded);
      const nextCatalogArtworks = { ...s.catalogArtworks };
      const nextSeen = s.seen.filter((seenId) => seenId !== id);
      if (nextAdded.has(id)) {
        nextAdded.delete(id);
        delete nextCatalogArtworks[id];
      } else {
        nextAdded.add(id);
        nextCatalogArtworks[id] = uncatalogedArtworkForVisit(s.uncatalogedSighting, s.locale);
        nextSeen.push(id);
        track("artwork_added", {
          artwork_id: id,
          result_type: "uncataloged",
          artist: s.uncatalogedSighting.artist,
          title: s.uncatalogedSighting.title,
        });
      }
      return { ...s, uncatalogedAdded: nextAdded, catalogArtworks: nextCatalogArtworks, seen: nextSeen };
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
      track("recap_viewed", { works_count: s.seen.length });
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
    () => state.seen.map((id) => getArtwork(id) || state.catalogArtworks[id]).filter((a): a is Artwork => !!a),
    [state.catalogArtworks, state.seen]
  );

  return {
    state,
    seenArtworks,
    actions: { goto, setLocale, setMode, startVisit, recognizeFrame, addToVisit, addUncatalogedToVisit, toggleFavorite, completeVisit, newVisit },
  };
}

function uncatalogedPlaceholderImage(): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e7e1d6"/><stop offset=".55" stop-color="#d6c8b8"/><stop offset="1" stop-color="#8c6a4c"/></linearGradient></defs><rect width="800" height="600" fill="url(#g)"/><text x="400" y="308" text-anchor="middle" font-family="Georgia, serif" font-size="38" fill="rgba(24,23,20,.62)">AI recognized</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function localizedSame(value: string): Record<Locale, string> {
  return { en: value, fr: value, "zh-Hans": value };
}

function uncatalogedArtworkForVisit(sighting: UncatalogedSighting, locale: Locale): Artwork {
  const title = sighting.title || "Recognized artwork";
  const artist = sighting.artist || null;
  return {
    id: sighting.id,
    artist,
    year: sighting.date || "",
    hall: null,
    inventoryNumber: sighting.id,
    image: "AI",
    imageUrl: uncatalogedPlaceholderImage(),
    accent: "#8C6A4C",
    priority: "uncataloged",
    needsEditorialReview: true,
    editorialStatus: "ai_recognized_uncurated",
    title: localizedSame(title),
    titleNeedsReview: { en: true, fr: true, "zh-Hans": true },
    estimate: { low: null, high: null },
    valueReveal: null,
    why: localizedSame(sighting.whyItMatters || "AI recognized this work, but ELYIO has not reviewed it as a curated catalog record yet."),
    where: localizedSame(sighting.lookCloser || "Look back at the object and compare the visible details with the recognition result."),
    rarity: localizedSame(locale === "fr" ? "Contexte de marché non vérifié." : locale === "zh-Hans" ? "市场背景尚未审核。" : "Market context not reviewed."),
  };
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((x): x is string => typeof x === "string" && x.trim().length > 0) : [];
}

function buildUncatalogedSighting(
  base: NonNullable<Awaited<ReturnType<typeof api.recognize>>["recognized_but_not_cataloged"]>,
  vision: Record<string, unknown> | null | undefined,
  confidence: number
): UncatalogedSighting {
  const clues = [
    ...(vision ? stringArray(vision.dominant_visual_features) : []),
    ...(vision ? stringArray(vision.distinctive_features) : []),
  ];
  const objectType = base.object_type || (typeof vision?.object_type === "string" ? vision.object_type : null);
  const subject = typeof vision?.depicted_subject === "string" ? vision.depicted_subject : null;
  const material = typeof vision?.material_guess === "string" ? vision.material_guess : null;
  const period = base.date || (typeof vision?.period_guess === "string" ? vision.period_guess : null);
  const firstClue = clues[0] || subject || objectType || base.title;
  const secondClue = clues.find((x) => x !== firstClue) || material || subject;

  return {
    id: `uncataloged:${Date.now()}:${base.artist || ""}:${base.title || ""}`,
    artist: base.artist,
    title: base.title,
    date: period,
    objectType,
    confidence: base.confidence ?? confidence,
    whatYouAreLookingAt:
      base.what_you_are_looking_at ||
      [objectType ? `A ${objectType}` : "An artwork", subject ? `showing ${subject}` : null, material ? `in ${material}` : null]
        .filter(Boolean)
        .join(" "),
    whyItMatters:
      base.why_it_matters ||
      (base.artist || base.title
        ? "The recognition is strong enough to give you a useful starting point, but ELYIO has not yet reviewed this work as a curated catalog record."
        : "ELYIO can describe what is visible, but this result needs review before we attach a full story."),
    lookCloser:
      base.look_closer ||
      (firstClue && secondClue
        ? `Look for ${firstClue}, then compare it with ${secondClue}.`
        : firstClue
          ? `Start by looking for ${firstClue}.`
          : "Step back and include the whole object in your next photo."),
  };
}
