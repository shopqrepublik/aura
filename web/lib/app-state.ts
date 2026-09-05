"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as api from "./api";
import { getArtwork } from "./artworks";
import { getAnonymousId, getSessionId, track, trackGoogleEvent } from "./analytics";
import { isRecognitionNetworkError } from "./recognitionErrors";
import { buildGeneratedEnrichment, generatedValueReveal, type GeneratedEnrichment } from "./generated-enrichment";
import { attachIndicativeValueIfEligible, fetchIndicativeValueReveal } from "./indicative-value";
import { buildVisitGame } from "./visit-game";
import type { Artwork, ArtworkImageSourceType, Locale, Mode, ValueReveal } from "./types";

export type Screen = "home" | "camera" | "card" | "progress" | "recap";

// AI recognized an artwork/object, but it did not resolve to a full curated
// ELYIO catalog record. The recognition is still useful: we keep the visitor's
// scan as the result image and attach a bounded generated enrichment payload.
export interface UncatalogedSighting {
  id: string;
  artist: string | null;
  title: string | null;
  date?: string | null;
  objectType?: string | null;
  confidence?: number | null;
  imageUrl?: string | null;
  enrichment: GeneratedEnrichment;
  valueReveal?: ValueReveal | null;
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
  museumName: string | null;
  museumCity: string | null;
  visitId: string | null;
  visitStarted: boolean;
  startTime: number | null;
  lastActivityAt: number | null;
  completedAt: number | null;
  seen: string[]; // artwork ids, in scan order
  favorites: Set<string>;
  favoriteOrder: string[];
  added: Set<string>;
  catalogArtworks: Record<string, Artwork>;
  currentArtwork: Artwork | null;
  uncatalogedSighting: UncatalogedSighting | null;
  uncatalogedAdded: Set<string>;
  lastConfidence: number;
  scanStatus: string | null; // transient message on the camera screen
  recognitionRequestId: string | null;
  pendingRecognitionImageBase64: string | null;
  cardOpenedAt: number | null; // real wall-clock timestamp, for Deep focus
  unlockedAchievements: Record<string, number>;
  achievementToast: string | null;
  missionToast: string | null;
}

const initialState: AppState = {
  screen: "home",
  locale: "en",
  mode: "normal",
  museumId: null,
  museumName: null,
  museumCity: null,
  visitId: null,
  visitStarted: false,
  startTime: null,
  lastActivityAt: null,
  completedAt: null,
  seen: [],
  favorites: new Set(),
  favoriteOrder: [],
  added: new Set(),
  catalogArtworks: {},
  currentArtwork: null,
  uncatalogedSighting: null,
  uncatalogedAdded: new Set(),
  lastConfidence: 0,
  scanStatus: null,
  recognitionRequestId: null,
  pendingRecognitionImageBase64: null,
  cardOpenedAt: null,
  unlockedAchievements: {},
  achievementToast: null,
  missionToast: null,
};

function eventId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function useElyioApp(options?: { directToScanner?: boolean; initialLocale?: Locale }) {
  const [state, setState] = useState<AppState>(() => ({
    ...initialState,
    ...(options?.initialLocale ? { locale: options.initialLocale } : {}),
  }));
  // Recognition callbacks can outlive the render that created them (notably
  // while the scanner remains mounted during background museum detection).
  // Keep the latest authoritative context available to every scan without
  // making geolocation a blocking prerequisite.
  const museumContextRef = useRef<{ id: string | null; name: string | null; city: string | null }>({ id: null, name: null, city: null });
  useEffect(() => {
    museumContextRef.current = { id: state.museumId, name: state.museumName, city: state.museumCity };
  }, [state.museumId, state.museumName, state.museumCity]);

  // Browser persistence is restored after hydration. Reading localStorage in
  // the state initializer made returning visits render different client HTML
  // from the server and caused a real React hydration recovery on /visit.
  useEffect(() => {
    const stored = loadVisitState();
    if (!stored) return;
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setState({
        ...stored,
        ...(options?.initialLocale ? { locale: options.initialLocale } : {}),
        ...(options?.directToScanner && stored.visitStarted ? { screen: "camera" as Screen } : {}),
      });
    });
    return () => { cancelled = true; };
    // Entry behavior is fixed for the lifetime of an app mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const goto = useCallback((screen: Screen) => {
    if (typeof window !== "undefined") {
      window.history.pushState({ ...(window.history.state || {}), elyioScreen: screen }, "", window.location.href);
    }
    setState((s) => persistVisitState({ ...s, screen, lastActivityAt: Date.now() }));
  }, []);
  const restoreScreen = useCallback((screen: Screen) => {
    setState((s) => persistVisitState({ ...s, screen, lastActivityAt: Date.now() }));
  }, []);
  const setLocale = useCallback((locale: Locale) => setState((s) => persistVisitState({ ...s, locale })), []);
  const setMode = useCallback((mode: Mode) => setState((s) => ({ ...s, mode })), []);

  // Phase 2 §1 -- museumId comes from HomeScreen's useMuseumDetection
  // (detected via GPS or manually confirmed), not a hardcoded constant.
  // Resolved once here and reused for every recognize() call during this
  // visit, rather than re-checking geolocation per scan.
  const startVisit = useCallback(async (museumId?: string | null, museumName?: string | null, museumCity?: string | null) => {
    setState((s) => {
      if (s.visitStarted) return s;
      track("visit_started", { museum_id: museumId || undefined });
      track("scan_opened", { museum_id: museumId || undefined, source: "visit_started" });
      trackGoogleEvent("camera_opened", { locale: s.locale, museum_slug: museumId || undefined, museum_city: museumCity || undefined, source_surface: "scanner" });
      const now = Date.now();
      return persistVisitState({
        ...s,
        visitStarted: true,
        startTime: now,
        lastActivityAt: now,
        museumId: museumId || null,
        museumName: museumName || null,
        museumCity: museumCity || null,
      });
    });
    setState((s) => {
      if (!s.visitId && museumId) {
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

  const setMuseumContext = useCallback((museumId: string, museumName?: string | null, museumCity?: string | null) => {
    museumContextRef.current = { id: museumId, name: museumName || null, city: museumCity || null };
    setState((s) => persistVisitState({ ...s, museumId, museumName: museumName || null, museumCity: museumCity || null, lastActivityAt: Date.now() }));
  }, []);

  const recognizeFrame = useCallback(async (imageBase64: string) => {
    const latestMuseum = museumContextRef.current;
    setState((s) => persistVisitState({ ...s, scanStatus: "scanning", recognitionRequestId: null, pendingRecognitionImageBase64: null, lastActivityAt: Date.now() }));
    const recognitionAttemptId = eventId();
    track("image_captured", { museum_id: latestMuseum.id, recognition_attempt_id: recognitionAttemptId });
    track("scan_attempt", { museum_id: latestMuseum.id, seen_count: state.seen.length, recognition_attempt_id: recognitionAttemptId });
    if (state.seen.length > 0) {
      track("second_scan_started", { museum_id: state.museumId, seen_count: state.seen.length, recognition_attempt_id: recognitionAttemptId });
    }
    track("recognition_started", { museum_id: state.museumId, recognition_attempt_id: recognitionAttemptId });
    trackGoogleEvent("scan_started", { locale: state.locale, museum_slug: state.museumId || undefined, museum_city: state.museumCity || undefined, source_surface: "scanner" });
    try {
      const result = await api.recognize(
        imageBase64,
        state.locale,
        latestMuseum.id,
        undefined,
        recognitionAttemptId,
        getAnonymousId(),
        getSessionId(),
      );
      setState((s) => ({ ...s, recognitionRequestId: result.recognition_request_id || null }));
      track("recognition_completed", {
        museum_id: state.museumId,
        recognition_attempt_id: recognitionAttemptId,
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
          track("scan_failed", { reason: "uncataloged", recognition_attempt_id: recognitionAttemptId });
          track("catalog_no_match", {
            museum_id: state.museumId,
            recognition_attempt_id: recognitionAttemptId,
            confidence: result.confidence,
            ai_candidate: uncataloged,
          });
          const sighting = await enrichUncatalogedSightingValue(
            buildUncatalogedSighting(uncataloged, result.vision, result.confidence, imageBase64),
            state.museumName
          );
          setState((s) => persistVisitState(applyVisitGameUnlocks({
            ...recordUncatalogedDiscovery(s, sighting, s.locale),
            uncatalogedSighting: sighting,
            currentArtwork: null,
            scanStatus: null,
            screen: "card",
            cardOpenedAt: Date.now(),
            lastActivityAt: Date.now(),
          }, s)));
          track("result_viewed", {
            result_type: "uncataloged",
            museum_id: state.museumId,
            recognition_attempt_id: recognitionAttemptId,
            confidence: result.confidence,
            ai_candidate: uncataloged,
          });
          trackGoogleEvent("artwork_recognized", { locale: state.locale, museum_slug: state.museumId || undefined, museum_city: state.museumCity || undefined, recognition_mode: "ai_fallback", catalog_status: "uncataloged", source_surface: "scanner" });
          return;
        }
        track("scan_failed", { reason: result.status, recognition_attempt_id: recognitionAttemptId });
        track("catalog_no_match", { museum_id: state.museumId, confidence: result.confidence, recognition_attempt_id: recognitionAttemptId });
        trackGoogleEvent("recognition_failed", { locale: state.locale, museum_slug: state.museumId || undefined, museum_city: state.museumCity || undefined, recognition_mode: "other", catalog_status: "no_match", source_surface: "scanner" });
        setState((s) => persistVisitState({ ...s, scanStatus: "not_identified", pendingRecognitionImageBase64: null, lastActivityAt: Date.now() }));
        return;
      }

      // "needs_confirmation" (backend/app/main.py CONFIDENCE_REVIEW band) is
      // shown as a regular card today -- there's no separate confirm/reject
      // UI yet (out of scope here). candidate_confirmed still fires for
      // this band specifically so the low-confidence-match rate is visible
      // in PostHog even before that UI exists; a real confirm step, when
      // built, should fire this on the user's actual confirm tap instead.
      if (result.status === "needs_confirmation") {
        track("candidate_confirmed", { artwork_id: artwork.id, confidence: result.confidence, recognition_attempt_id: recognitionAttemptId });
      }
      track("scan_success", { artwork_id: artwork.id, museum_id: state.museumId, confidence: result.confidence, status: result.status, recognition_attempt_id: recognitionAttemptId });
      track("catalog_match", {
        museum_id: state.museumId,
        artwork_id: artwork.id,
        recognition_attempt_id: recognitionAttemptId,
        confidence: result.confidence,
        recognition_mode: result.recognition_mode,
      });
      track("result_viewed", {
        result_type: "catalog",
        museum_id: state.museumId,
        artwork_id: artwork.id,
        recognition_attempt_id: recognitionAttemptId,
        confidence: result.confidence,
        status: result.status,
      });
      track("artwork_viewed", {
        result_type: "catalog",
        museum_id: state.museumId,
        artwork_id: artwork.id,
        recognition_attempt_id: recognitionAttemptId,
      });
      trackGoogleEvent("artwork_recognized", { locale: state.locale, museum_slug: state.museumId || undefined, museum_city: state.museumCity || undefined, artwork_id: artwork.id, recognition_mode: result.recognition_mode === "catalog" ? "catalog" : "other", catalog_status: "catalog", source_surface: "scanner" });

      artwork = withCapturedScanFallbackImage(
        await attachIndicativeValueIfEligible(artwork, state.museumName, artwork.why?.en || artwork.editorialStatus),
        imageBase64
      );

      setState((s) => {
        const next: AppState = {
          ...recordCatalogDiscovery(s, artwork, result.confidence),
          currentArtwork: artwork,
          uncatalogedSighting: null,
          lastConfidence: result.confidence,
          scanStatus: null,
          pendingRecognitionImageBase64: null,
          screen: "card",
          cardOpenedAt: Date.now(),
          lastActivityAt: Date.now(),
        };
        return persistVisitState(applyVisitGameUnlocks(next, s));
      });
    } catch (error) {
      track("recognition_failed", { museum_id: state.museumId, recognition_attempt_id: recognitionAttemptId, reason: error instanceof Error ? error.message : "error" });
      trackGoogleEvent("recognition_failed", { locale: state.locale, museum_slug: state.museumId || undefined, museum_city: state.museumCity || undefined, recognition_mode: "other", catalog_status: "error", source_surface: "scanner" });
      const networkError = isRecognitionNetworkError(error);
      const diagnosticId = error instanceof api.RecognitionHttpError ? error.recognitionRequestId : undefined;
      track("scan_failed", { reason: networkError ? "network_error" : "error", recognition_attempt_id: recognitionAttemptId });
      setState((s) => persistVisitState({
        ...s,
        recognitionRequestId: diagnosticId || s.recognitionRequestId,
        scanStatus: networkError ? "network_error" : "not_identified",
        pendingRecognitionImageBase64: networkError ? imageBase64 : null,
        lastActivityAt: Date.now(),
      }));
    }
  }, [state.catalogArtworks, state.locale, state.mode, state.museumCity, state.museumId, state.museumName, state.seen.length]);

  const addToVisit = useCallback(() => {
    setState((s) => {
      if (!s.currentArtwork) return s;
      const id = s.currentArtwork.id;
      if (s.added.has(id) && s.seen.includes(id)) return s;
      const nextAdded = new Set(s.added);
      nextAdded.add(id);
      track("artwork_added", { artwork_id: id, source: "manual_confirm" });
      if (s.visitId) api.addVisitArtwork(s.visitId, id, s.lastConfidence).catch(() => {});
      const nextSeen = appendUnique(s.seen, id);
      return persistVisitState(applyVisitGameUnlocks({ ...s, added: nextAdded, seen: nextSeen, lastActivityAt: Date.now() }, s));
    });
  }, []);

  const addUncatalogedToVisit = useCallback(() => {
    setState((s) => {
      if (!s.uncatalogedSighting) return s;
      const id = s.uncatalogedSighting.id;
      if (s.uncatalogedAdded.has(id) && s.seen.includes(id)) return s;
      const nextAdded = new Set(s.uncatalogedAdded);
      const nextCatalogArtworks = { ...s.catalogArtworks };
      nextAdded.add(id);
      nextCatalogArtworks[id] = uncatalogedArtworkForVisit(s.uncatalogedSighting, s.locale);
      const nextSeen = appendUnique(s.seen, id);
      track("artwork_added", {
        artwork_id: id,
        result_type: "uncataloged",
        source: "manual_confirm",
        artist: s.uncatalogedSighting.artist,
        title: s.uncatalogedSighting.title,
      });
      return persistVisitState(applyVisitGameUnlocks({ ...s, uncatalogedAdded: nextAdded, catalogArtworks: nextCatalogArtworks, seen: nextSeen, lastActivityAt: Date.now() }, s));
    });
  }, []);

  const toggleFavorite = useCallback(() => {
    setState((s) => {
      if (!s.currentArtwork) return s;
      const id = s.currentArtwork.id;
      const next = new Set(s.favorites);
      const favoriteOrder = s.favoriteOrder.filter((favoriteId) => favoriteId !== id);
      const nextAdded = new Set(s.added);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        favoriteOrder.push(id);
        nextAdded.add(id);
        if (!s.seen.includes(id)) track("artwork_added", { artwork_id: id, source: "favorite_backfill" });
        if (s.visitId) api.addVisitArtwork(s.visitId, id, s.lastConfidence).catch(() => {});
        track("artwork_favorited", { artwork_id: id });
        track("favorite_added", { artwork_id: id });
      }
      const nextSeen = appendUnique(s.seen, id);
      return persistVisitState(applyVisitGameUnlocks({ ...s, favorites: next, favoriteOrder, added: nextAdded, seen: nextSeen, lastActivityAt: Date.now() }, s));
    });
  }, []);

  const toggleUncatalogedFavorite = useCallback(() => {
    setState((s) => {
      if (!s.uncatalogedSighting) return s;
      const id = s.uncatalogedSighting.id;
      const next = new Set(s.favorites);
      const favoriteOrder = s.favoriteOrder.filter((favoriteId) => favoriteId !== id);
      const nextCatalogArtworks = { ...s.catalogArtworks };
      const nextAdded = new Set(s.uncatalogedAdded);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        favoriteOrder.push(id);
        nextAdded.add(id);
        if (!nextCatalogArtworks[id]) nextCatalogArtworks[id] = uncatalogedArtworkForVisit(s.uncatalogedSighting, s.locale);
        if (!s.seen.includes(id)) {
          track("artwork_added", { artwork_id: id, result_type: "uncataloged", source: "favorite_backfill" });
        }
        track("artwork_favorited", { artwork_id: id, result_type: "uncataloged" });
        track("favorite_added", { artwork_id: id, result_type: "uncataloged" });
      }
      const nextSeen = appendUnique(s.seen, id);
      return persistVisitState(applyVisitGameUnlocks({ ...s, favorites: next, favoriteOrder, uncatalogedAdded: nextAdded, catalogArtworks: nextCatalogArtworks, seen: nextSeen, lastActivityAt: Date.now() }, s));
    });
  }, []);

  const completeVisit = useCallback(async () => {
    // Reads seen.length via the setState updater (and returns `s` unchanged)
    // rather than closing over the outer `state` -- this callback's deps
    // are [state.visitId, goto], so a closed-over state.seen could be stale
    // by the time this actually runs.
    setState((s) => {
      track("visit_completed", { works_count: s.seen.length });
      track("finish_visit_clicked", { works_count: s.seen.length });
      track("recap_viewed", { works_count: s.seen.length });
      return persistVisitState({ ...s, completedAt: Date.now(), lastActivityAt: Date.now() });
    });
    if (state.visitId) {
      api.completeVisit(state.visitId).catch(() => {});
    }
    goto("recap");
  }, [state.visitId, goto]);

  const newVisit = useCallback(() => {
    clearVisitState();
    setState((s) => ({ ...initialState, locale: s.locale }));
  }, []);

  const dismissAchievementToast = useCallback(() => {
    setState((s) => persistVisitState({ ...s, achievementToast: null }));
  }, []);

  const dismissMissionToast = useCallback(() => {
    setState((s) => persistVisitState({ ...s, missionToast: null }));
  }, []);

  const seenArtworks = useMemo(
    () => state.seen.map((id) => getArtwork(id) || state.catalogArtworks[id]).filter((a): a is Artwork => !!a),
    [state.catalogArtworks, state.seen]
  );

  return {
    state,
    seenArtworks,
    actions: {
      goto,
      restoreScreen,
      setLocale,
      setMode,
      startVisit,
      setMuseumContext,
      recognizeFrame,
      addToVisit,
      addUncatalogedToVisit,
      toggleFavorite,
      toggleUncatalogedFavorite,
      completeVisit,
      newVisit,
      dismissAchievementToast,
      dismissMissionToast,
    },
  };
}

function appendUnique(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids : [...ids, id];
}

function recordCatalogDiscovery(state: AppState, artwork: Artwork, confidence: number): AppState {
  const alreadySeen = state.seen.includes(artwork.id);
  const nextAdded = new Set(state.added);
  nextAdded.add(artwork.id);
  if (!alreadySeen) {
    track("artwork_added", { artwork_id: artwork.id, source: "auto_sighting" });
    if (state.visitId) api.addVisitArtwork(state.visitId, artwork.id, confidence).catch(() => {});
  }
  return {
    ...state,
    added: nextAdded,
    catalogArtworks: getArtwork(artwork.id) ? state.catalogArtworks : { ...state.catalogArtworks, [artwork.id]: artwork },
    seen: appendUnique(state.seen, artwork.id),
    lastActivityAt: Date.now(),
  };
}

function recordUncatalogedDiscovery(state: AppState, sighting: UncatalogedSighting, locale: Locale): AppState {
  const alreadySeen = state.seen.includes(sighting.id);
  const nextAdded = new Set(state.uncatalogedAdded);
  const nextCatalogArtworks = { ...state.catalogArtworks };
  nextAdded.add(sighting.id);
  nextCatalogArtworks[sighting.id] = uncatalogedArtworkForVisit(sighting, locale);
  if (!alreadySeen) {
    track("artwork_added", {
      artwork_id: sighting.id,
      result_type: "uncataloged",
      source: "auto_sighting",
      artist: sighting.artist,
      title: sighting.title,
    });
  }
  return {
    ...state,
    uncatalogedAdded: nextAdded,
    catalogArtworks: nextCatalogArtworks,
    seen: appendUnique(state.seen, sighting.id),
    lastActivityAt: Date.now(),
  };
}

function withCapturedScanFallbackImage(artwork: Artwork, imageBase64: string | null | undefined): Artwork {
  if (hasReusableArtworkImage(artwork)) return artwork;
  const captured = capturedImageDataUrl(imageBase64);
  if (!captured) return artwork;
  return { ...artwork, imageUrl: captured, image: captured, imageSourceType: "VISITOR_CAPTURE", imageSourceId: imageSourceId(captured) };
}

function hasReusableArtworkImage(artwork: Artwork): boolean {
  const classified = artwork.imageSourceType || classifyArtworkImageSource(artwork.imageUrl);
  return classified === "REFERENCE_REAL" || classified === "VISITOR_CAPTURE";
}

function classifyArtworkImageSource(url: string | null | undefined): ArtworkImageSourceType {
  if (!url) return "PLACEHOLDER";
  if (/^https?:\/\//i.test(url)) return "REFERENCE_REAL";
  if (/^data:image\/(jpeg|jpg|png|webp)/i.test(url)) return "VISITOR_CAPTURE";
  if (/^data:image\/svg\+xml/i.test(url)) {
    const decoded = safeDecodeImageDataUrl(url);
    return /(ELYIO|AI recognized|Recognized artwork)/i.test(decoded) ? "PLACEHOLDER" : "REFERENCE_REAL";
  }
  return "PLACEHOLDER";
}

function safeDecodeImageDataUrl(url: string): string {
  try {
    return decodeURIComponent(url);
  } catch {
    return url;
  }
}

function imageSourceId(url: string): string {
  let hash = 2166136261;
  for (let i = 0; i < url.length; i++) {
    hash ^= url.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return `image:${(hash >>> 0).toString(16)}`;
}

function uncatalogedPlaceholderImage(): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e7e1d6"/><stop offset=".55" stop-color="#d6c8b8"/><stop offset="1" stop-color="#8c6a4c"/></linearGradient></defs><rect width="800" height="600" fill="url(#g)"/><text x="400" y="308" text-anchor="middle" font-family="Georgia, serif" font-size="38" fill="rgba(24,23,20,.62)">AI recognized</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

interface StoredVisitState {
  version: 1;
  state: Omit<AppState, "favorites" | "added" | "uncatalogedAdded"> & {
    favorites: string[];
    added: string[];
    uncatalogedAdded: string[];
  };
}

const VISIT_STORAGE_KEY = "elyio-current-visit-v2";

function loadVisitState(): AppState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(VISIT_STORAGE_KEY);
    if (!raw) return null;
    const stored = JSON.parse(raw) as StoredVisitState;
    if (stored.version !== 1 || !stored.state?.visitStarted) return null;
    return {
      ...stored.state,
      favorites: new Set(stored.state.favorites || []),
      added: new Set(stored.state.added || []),
      uncatalogedAdded: new Set(stored.state.uncatalogedAdded || []),
    };
  } catch {
    return null;
  }
}

function persistVisitState(state: AppState): AppState {
  if (typeof window === "undefined") return state;
  try {
    if (!state.visitStarted) {
      window.localStorage.removeItem(VISIT_STORAGE_KEY);
      return state;
    }
    const storedState = {
      ...state,
      favorites: Array.from(state.favorites),
      added: Array.from(state.added),
      uncatalogedAdded: Array.from(state.uncatalogedAdded),
    };
    // A long visit can otherwise serialize one JPEG data URL per captured
    // result into localStorage. Keep the current result and metadata, but
    // remove older visitor captures once the browser record approaches a
    // conservative 4 MB budget. Recognition itself still receives the full
    // in-memory frame and retry remains available for the latest failure.
    let encoded = JSON.stringify({ version: 1, state: storedState });
    if (encoded.length > 4_000_000) {
      for (const id of [...storedState.seen].reverse()) {
        if (id === state.currentArtwork?.id) continue;
        const artwork = storedState.catalogArtworks[id];
        if (artwork?.imageSourceType === "VISITOR_CAPTURE") {
          storedState.catalogArtworks = { ...storedState.catalogArtworks, [id]: { ...artwork, imageUrl: "" } };
          encoded = JSON.stringify({ version: 1, state: storedState });
          if (encoded.length <= 4_000_000) break;
        }
      }
    }
    if (encoded.length > 4_000_000) storedState.pendingRecognitionImageBase64 = null;
    const stored: StoredVisitState = {
      version: 1,
      state: storedState,
    };
    window.localStorage.setItem(VISIT_STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // Local persistence is best-effort. The visit remains usable in memory.
  }
  return state;
}

function clearVisitState() {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(VISIT_STORAGE_KEY);
  } catch {}
}

function resolveSeenArtworks(state: AppState): Artwork[] {
  return state.seen.map((id) => getArtwork(id) || state.catalogArtworks[id]).filter((a): a is Artwork => !!a);
}

function applyVisitGameUnlocks(next: AppState, previous?: AppState): AppState {
  const now = Date.now();
  const seenArtworks = resolveSeenArtworks(next);
  const before = previous
    ? buildVisitGame({
        locale: previous.locale,
        museumName: previous.museumName,
        museumCity: previous.museumCity,
        startTime: previous.startTime,
        now,
        seenArtworks: resolveSeenArtworks(previous),
        favoriteIds: previous.favorites,
        unlockedAchievements: previous.unlockedAchievements,
      })
    : null;
  const game = buildVisitGame({
    locale: next.locale,
    museumName: next.museumName,
    museumCity: next.museumCity,
    startTime: next.startTime,
    now,
    seenArtworks,
    favoriteIds: next.favorites,
    unlockedAchievements: next.unlockedAchievements,
  });

  const unlockedAchievements = { ...next.unlockedAchievements };
  let achievementToast = next.achievementToast;
  for (const achievement of game.achievements) {
    if (achievement.unlocked && !unlockedAchievements[achievement.id]) {
      unlockedAchievements[achievement.id] = now;
      achievementToast = achievement.id;
      track("achievement_unlocked", { achievement_id: achievement.id });
    }
  }

  let missionToast = next.missionToast;
  if (before) {
    const beforeCompleted = new Set(before.completedMissionIds);
    const newlyCompleted = game.completedMissionIds.find((id) => !beforeCompleted.has(id));
    if (newlyCompleted) {
      missionToast = newlyCompleted;
      track("mission_completed", { mission_id: newlyCompleted });
    }
  }

  return { ...next, unlockedAchievements, achievementToast, missionToast };
}

function localizedSame(value: string): Record<Locale, string> {
  return { en: value, fr: value, "zh-Hans": value };
}

function uncatalogedArtworkForVisit(sighting: UncatalogedSighting, locale: Locale): Artwork {
  const title = sighting.enrichment.displayTitle || sighting.title || "Recognized artwork";
  const artist = sighting.enrichment.displayArtist || sighting.artist || null;
  const normal = sighting.enrichment.content[locale]?.normal || sighting.enrichment.content.en.normal;
  const simple = sighting.enrichment.content[locale]?.simple || sighting.enrichment.content.en.simple;
  const kids = sighting.enrichment.content[locale]?.kids || sighting.enrichment.content.en.kids;
  const imageUrl = sighting.imageUrl || uncatalogedPlaceholderImage();
  const imageSourceType: ArtworkImageSourceType = sighting.imageUrl ? "VISITOR_CAPTURE" : "PLACEHOLDER";
  return {
    id: sighting.id,
    artist,
    year: sighting.enrichment.displayDate || sighting.date || "",
    hall: null,
    inventoryNumber: sighting.id,
    image: "AI",
    imageUrl,
    imageSourceType,
    imageSourceId: sighting.imageUrl ? imageSourceId(sighting.imageUrl) : "placeholder:uncataloged",
    accent: "#8C6A4C",
    priority: "uncataloged",
    needsEditorialReview: true,
    editorialStatus: "ai_recognized_uncurated",
    title: localizedSame(title),
    titleNeedsReview: { en: true, fr: true, "zh-Hans": true },
    estimate: { low: null, high: null },
    valueReveal: sighting.valueReveal || generatedValueReveal(sighting.enrichment, locale),
    why: localizedSame(normal.whyItMatters),
    where: localizedSame(normal.lookCloser),
    rarity: localizedSame(normal.deeperContext),
    whySimple: localizedSame(simple.whyItMatters),
    whereSimple: localizedSame(simple.lookCloser),
    raritySimple: localizedSame(simple.deeperContext),
    whyKids: localizedSame(kids.whyItMatters),
    whereKids: localizedSame(kids.lookCloser),
    rarityKids: localizedSame(kids.funFactOrMission || kids.deeperContext),
  };
}

async function enrichUncatalogedSightingValue(sighting: UncatalogedSighting, museumName: string | null): Promise<UncatalogedSighting> {
  const context = sighting.enrichment.artistMarketContext;
  const valueReveal = await fetchIndicativeValueReveal({
    artist: sighting.artist || sighting.enrichment.displayArtist,
    title: sighting.title || sighting.enrichment.displayTitle,
    date: sighting.date || sighting.enrichment.displayDate,
    objectType: sighting.objectType || sighting.enrichment.objectType,
    museum: museumName || undefined,
    movement: sighting.enrichment.movementOrPeriod,
    collectionImportance: sighting.enrichment.content.en.normal.whyItMatters,
    existingMarketContext: context && context.confidence !== "NONE"
      ? {
          amountMillions: context.amountMillions,
          currency: context.currency,
          workTitle: context.workTitle,
          year: context.year,
          sourceReference: context.sourceReference,
          confidence: context.confidence,
        }
      : null,
  });
  return valueReveal ? { ...sighting, valueReveal } : sighting;
}

function buildUncatalogedSighting(
  base: NonNullable<Awaited<ReturnType<typeof api.recognize>>["recognized_but_not_cataloged"]>,
  vision: Record<string, unknown> | null | undefined,
  confidence: number,
  imageBase64?: string | null
): UncatalogedSighting {
  const objectType = base.object_type || (typeof vision?.object_type === "string" ? vision.object_type : null);
  const period = base.date || (typeof vision?.period_guess === "string" ? vision.period_guess : null);
  const enrichment = buildGeneratedEnrichment({
    artist: base.artist,
    title: base.title,
    date: period,
    objectType,
    vision,
    confidence: base.confidence ?? confidence,
  });

  return {
    id: `uncataloged:${Date.now()}:${base.artist || ""}:${base.title || ""}`,
    artist: base.artist,
    title: base.title,
    date: period,
    objectType,
    confidence: base.confidence ?? confidence,
    imageUrl: capturedImageDataUrl(imageBase64),
    enrichment,
  };
}

function capturedImageDataUrl(imageBase64: string | null | undefined): string | null {
  if (!imageBase64) return null;
  if (imageBase64.startsWith("data:image/")) return imageBase64;
  return `data:image/jpeg;base64,${imageBase64}`;
}
