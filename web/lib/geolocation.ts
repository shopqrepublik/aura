"use client";

import { useEffect, useState } from "react";

// Mirrors backend/app/models.py Museum's real current values (lat/lng
// aren't set as Python column defaults there, only geofence_radius_m is
// -- 48.8600, 2.3266 is the actual Musée d'Orsay row). Duplicated here
// rather than fetched, since there's no shared config layer between web/
// and backend/ yet and this is a frontend-only feature (§6 step 2) that
// doesn't touch recognition.
export const MUSEUM_COORDS = { lat: 48.86, lng: 2.3266 };
export const GEOFENCE_RADIUS_M = 150;

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

export function useMuseumDetection() {
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

  useEffect(() => {
    if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
      setStatus("manual-prompt");
      return;
    }
    // Explicit, visible permission request on Home-screen mount (§6 step 2)
    // -- not a silent navigator.permissions.query() precheck. Never blocks
    // the app: any failure (denied, timeout, position unavailable) or an
    // in-range-but-too-far result both just fall back to manual
    // confirmation (§4.1 -- GPS/geofence OR manual, both valid paths).
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const distance = haversineDistanceMeters(
          { lat: position.coords.latitude, lng: position.coords.longitude },
          MUSEUM_COORDS
        );
        setStatus(distance <= GEOFENCE_RADIUS_M ? "detected" : "manual-prompt");
      },
      () => setStatus("manual-prompt"),
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 }
    );
  }, []);

  const confirmManually = () => setStatus("manual-confirmed");

  return { status, confirmManually };
}
