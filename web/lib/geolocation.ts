"use client";

import { useEffect, useRef, useState } from "react";
import { getMuseums, type Museum } from "./api";

function haversineDistanceMeters(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number }
): number {
  const R = 6_371_000; // Earth radius, meters
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

// "checking" and "manual-prompt" render identically in the chip (both are
// the honest "we don't know yet / didn't confirm via GPS" state) --
// kept as separate values so the UI can show a non-interactive "Locating…"
// pill for the brief moment before the first position callback resolves,
// rather than a tappable "Select your museum" button that might change
// under the user's finger mid-tap.
export type MuseumStatus = "checking" | "detected" | "manual-prompt" | "manual-confirmed";

// Phase 2 §1 -- generalized from a single hardcoded Musée d'Orsay coordinate
// pair to "nearest museum, in ITS OWN geofence_radius_m, out of whatever the
// backend's /v1/museums returns". Adding a second real museum is then a
// database row (backend/scripts/init_db.py's seed block), not a code change
// here -- this hook and the endpoint it calls are what make that true.
export function useMuseumDetection({ enabled = true }: { enabled?: boolean } = {}) {
  // Always starts "checking" on BOTH server and client -- a lazy
  // initializer branching on `typeof navigator !== "undefined"` looked safe
  // (a read-only check) but isn't: it runs during render on the server
  // (navigator is undefined there -> "manual-prompt") AND during the
  // client's first hydration render (navigator always exists in a browser
  // -> "checking"), producing two different initial trees and a real
  // hydration mismatch (confirmed live: server rendered the tappable
  // "manual-prompt" button branch, client's first paint rendered the
  // non-interactive "checking" pill branch instead). Capability detection
  // now only happens inside the effect, which never runs during SSR --
  // same pattern this app already uses for RecapScreen/ProgressScreen's
  // `now` starting null.
  const [status, setStatus] = useState<MuseumStatus>("checking");
  const [museums, setMuseums] = useState<Museum[]>([]);
  const [museum, setMuseum] = useState<Museum | null>(null);
  const manualChosen = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    const watchdog = window.setTimeout(() => {
      if (!cancelled) setStatus("manual-prompt");
    }, 5_000);
    getMuseums()
      .then((list) => {
        if (cancelled) return;
        setMuseums(list);

        if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
          setStatus("manual-prompt");
          return;
        }
        // Explicit, visible permission request on Home-screen mount (§6 step 2)
        // -- not a silent navigator.permissions.query() precheck. Never blocks
        // the app: any failure (denied, timeout, position unavailable) or a
        // position that isn't within ANY known museum's own radius both just
        // fall back to manual confirmation (§4.1 -- GPS/geofence OR manual,
        // both valid paths).
        navigator.geolocation.getCurrentPosition(
          (position) => {
            if (cancelled || manualChosen.current) return;
            const here = { lat: position.coords.latitude, lng: position.coords.longitude };
            // Nearest-within-its-own-radius, not just nearest overall -- a
            // visitor 2km from museum A and 3km from museum B is inside
            // neither's geofence and should still get "manual-prompt", not
            // a false "detected" for whichever happens to be closer.
            let nearest: { m: Museum; distance: number } | null = null;
            for (const m of list) {
              if (m.lat == null || m.lng == null) continue;
              const distance = haversineDistanceMeters(here, { lat: m.lat, lng: m.lng });
              if (distance <= m.geofence_radius_m && (!nearest || distance < nearest.distance)) {
                nearest = { m, distance };
              }
            }
            if (nearest) {
              setMuseum(nearest.m);
              setStatus("detected");
            } else {
              setStatus("manual-prompt");
            }
          },
          () => { if (!manualChosen.current) setStatus("manual-prompt"); },
          { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 }
        );
      })
      .catch(() => {
        if (!cancelled) setStatus("manual-prompt");
      });

    return () => {
      cancelled = true;
      window.clearTimeout(watchdog);
    };
  }, [enabled]);

  // Defaults to the first museum in the list when the sheet doesn't specify
  // one (today there's only ever one real row, so this matches the old
  // hardcoded-Orsay behavior exactly) -- a real "which one did you mean"
  // picker only matters once a second museum actually exists, which is
  // explicitly a separate decision (not this task's scope).
  const confirmManually = (museumId?: string) => {
    manualChosen.current = true;
    const picked = (museumId ? museums.find((m) => m.id === museumId) : undefined) ?? museums[0] ?? null;
    setMuseum(picked);
    setStatus("manual-confirmed");
  };

  return { status, museums, museum, confirmManually };
}
