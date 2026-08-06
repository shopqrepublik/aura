// Client for the EXISTING backend (backend/app/main.py) — contract unchanged,
// see README "API" section. Default port matches the documented run command
// (`uvicorn app.main:app --port 8090`); override with NEXT_PUBLIC_BACKEND_URL
// if your backend runs elsewhere.
// Exported so lib/visitPalette.ts can build the /v1/image-proxy URL for the
// Recap PNG export without duplicating this fallback logic.
import { supabase } from "./supabase";

export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8090";
const MUSEUM_ID = "orsay";

// /v1/visits* now requires a real signed-in user (backend/app/auth.py
// verifies this as a Supabase JWT) -- getSession() reads from supabase-js's
// own in-memory/localStorage cache and only hits the network to refresh a
// near-expired token, so this isn't a network round trip on every call.
async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface RecognizeResponse {
  status: "matched" | "needs_confirmation" | "no_match";
  artwork_id: string | null;
  confidence: number;
  alternatives: string[];
  recognized_but_not_cataloged?: { artist: string | null; title: string | null } | null;
}

export interface Visit {
  id: string;
  museum_id: string;
  locale: string;
  started_at: string;
  completed_at: string | null;
  artworks: { artwork_id: string; confidence: number; added: boolean }[];
}

export interface VisitProgress {
  works_count: number;
  artists_count: number;
  value_low_eur_m: number;
  value_high_eur_m: number;
  route_completion_pct: number;
}

async function postJSON<T>(path: string, body: unknown, auth = false): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) Object.assign(headers, await authHeaders());
  const res = await fetch(`${BACKEND_URL}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export async function recognize(imageBase64: string, locale: string, hallHint?: string): Promise<RecognizeResponse> {
  return postJSON<RecognizeResponse>("/v1/recognize", {
    image_base64: imageBase64,
    museum_id: MUSEUM_ID,
    hall_hint: hallHint ?? null,
    locale,
  });
}

export async function createVisit(locale: string): Promise<Visit> {
  return postJSON<Visit>("/v1/visits", { museum_id: MUSEUM_ID, locale }, true);
}

export async function addVisitArtwork(visitId: string, artworkId: string, confidence: number): Promise<{ ok: boolean; count: number }> {
  return postJSON(`/v1/visits/${visitId}/artworks`, { artwork_id: artworkId, confidence, added: true }, true);
}

export async function getVisitProgress(visitId: string): Promise<VisitProgress> {
  const res = await fetch(`${BACKEND_URL}/v1/visits/${visitId}/progress`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(`progress fetch failed: ${res.status}`);
  return res.json();
}

export async function completeVisit(visitId: string): Promise<{ ok: boolean; completed_at: string }> {
  return postJSON(`/v1/visits/${visitId}/complete`, {}, true);
}
