// Client for the EXISTING backend (backend/app/main.py) — contract unchanged,
// see README "API" section. Default port matches the documented run command
// (`uvicorn app.main:app --port 8090`); override with NEXT_PUBLIC_BACKEND_URL
// if your backend runs elsewhere.
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8090";
const MUSEUM_ID = "orsay";

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

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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
  return postJSON<Visit>("/v1/visits", { museum_id: MUSEUM_ID, locale });
}

export async function addVisitArtwork(visitId: string, artworkId: string, confidence: number): Promise<{ ok: boolean; count: number }> {
  return postJSON(`/v1/visits/${visitId}/artworks`, { artwork_id: artworkId, confidence, added: true });
}

export async function getVisitProgress(visitId: string): Promise<VisitProgress> {
  const res = await fetch(`${BACKEND_URL}/v1/visits/${visitId}/progress`);
  if (!res.ok) throw new Error(`progress fetch failed: ${res.status}`);
  return res.json();
}

export async function completeVisit(visitId: string): Promise<{ ok: boolean; completed_at: string }> {
  return postJSON(`/v1/visits/${visitId}/complete`, {});
}
