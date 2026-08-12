// Client for the EXISTING backend (backend/app/main.py) — contract unchanged,
// see README "API" section. Default port matches the documented run command
// (`uvicorn app.main:app --port 8090`); override with NEXT_PUBLIC_BACKEND_URL
// if your backend runs elsewhere.
// Exported so lib/visitPalette.ts can build the /v1/image-proxy URL for the
// Recap PNG export without duplicating this fallback logic.
import { supabase } from "./supabase";
import type { Artwork, ValueReveal } from "./types";

export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8090";

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
  recognition_mode?: string | null;
  vision?: Record<string, unknown> | null;
  top_candidates?: unknown[];
  stage2_verifier?: Record<string, unknown> | null;
  recognized_but_not_cataloged?: { artist: string | null; title: string | null } | null;
}

export interface CatalogArtworkResponse {
  id: string;
  museum_id: string;
  artist: string | null;
  title: string;
  year: string | null;
  hall: string | null;
  inventory_number: string | null;
  image_url: string | null;
  priority: string | number | null;
  estimate_low: number | null;
  estimate_high: number | null;
  value_reveal?: Record<string, unknown> | null;
  needs_editorial_review?: boolean | null;
  metadata_status?: string | null;
  department?: string | null;
  object_type?: string | null;
  materials_and_techniques?: string | null;
  dimensions?: string | null;
  description?: string | null;
  provenance?: string | null;
  object_history?: string | null;
  historical_context?: string | null;
  current_location_raw?: string | null;
  room?: string | null;
  creator_raw?: unknown;
  creator_labels?: unknown;
  locale?: string;
  mode?: string;
}

// Phase 2 §1 (geofence generalization) -- one row per real museum in
// backend/app/models.py's Museum table. Fetched once (see lib/geolocation.ts)
// instead of a single hardcoded coordinate pair, so adding a second real
// museum is a database row, not a code change here.
export interface Museum {
  id: string;
  name: string;
  lat: number | null;
  lng: number | null;
  geofence_radius_m: number;
  external_source?: string | null;
  external_id?: string | null;
  slug?: string | null;
  common_name?: string | null;
  city?: string | null;
  department?: string | null;
  region?: string | null;
  address?: string | null;
  postal_code?: string | null;
  website_url?: string | null;
  collection_categories?: string[];
  notable_terms?: string[];
  source?: string | null;
  source_updated_at?: string | null;
  experience_level?: "CURATED" | "AI_GUIDE" | string;
  curated_artwork_count?: number;
}

export async function getMuseums(params?: { q?: string; city?: string; region?: string; limit?: number }): Promise<Museum[]> {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.city) search.set("city", params.city);
  if (params?.region) search.set("region", params.region);
  if (params?.limit) search.set("limit", String(params.limit));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  const res = await fetch(`${BACKEND_URL}/v1/museums${suffix}`);
  if (!res.ok) throw new Error(`museums fetch failed: ${res.status}`);
  return res.json();
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
  estimated_value_artwork_count?: number;
  market_context_count?: number;
  beyond_market_count?: number;
  unvalued_count?: number;
  route_completion_pct: number;
}

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 30000): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

async function postJSON<T>(path: string, body: unknown, auth = false): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) Object.assign(headers, await authHeaders());
  const res = await fetchWithTimeout(`${BACKEND_URL}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

async function getJSON<T>(path: string, auth = false): Promise<T> {
  const headers = auth ? await authHeaders() : undefined;
  const res = await fetchWithTimeout(`${BACKEND_URL}${path}`, { headers });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export async function recognize(
  imageBase64: string,
  locale: string,
  museumId: string,
  hallHint?: string
): Promise<RecognizeResponse> {
  return postJSON<RecognizeResponse>("/v1/recognize", {
    image_base64: imageBase64,
    museum_id: museumId,
    hall_hint: hallHint ?? null,
    locale,
  });
}

export async function getArtworkDetail(artworkId: string, locale: string, mode: string): Promise<CatalogArtworkResponse> {
  return getJSON<CatalogArtworkResponse>(
    `/v1/artworks/${encodeURIComponent(artworkId)}?locale=${encodeURIComponent(locale)}&mode=${encodeURIComponent(mode)}`
  );
}

function localized(text: string): Artwork["title"] {
  return { en: text, fr: text, "zh-Hans": text };
}

function stringFromUnknown(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (Array.isArray(value)) {
    const joined = value.map((v) => (typeof v === "string" ? v : "")).filter(Boolean).join(", ");
    return joined || null;
  }
  if (value && typeof value === "object") return JSON.stringify(value);
  return null;
}

function camelValueReveal(raw: Record<string, unknown> | null | undefined): ValueReveal | null {
  if (!raw || typeof raw.mode !== "string") return null;
  if (raw.mode === "ESTIMATED_VALUE") {
    const estimated = (raw.estimated_value || {}) as Record<string, unknown>;
    if (typeof estimated.low !== "number" || typeof estimated.high !== "number") return null;
    return {
      mode: "ESTIMATED_VALUE",
      aggregateValueEligible: true,
      estimatedValue: {
        low: estimated.low,
        high: estimated.high,
        currency: typeof estimated.currency === "string" ? estimated.currency : "EUR",
        confidence: typeof estimated.confidence === "string" ? estimated.confidence : undefined,
        asOfDate: typeof estimated.as_of_date === "string" ? estimated.as_of_date : undefined,
        methodology: typeof estimated.methodology === "string" ? estimated.methodology : undefined,
        disclaimer: typeof estimated.disclaimer === "string" ? estimated.disclaimer : undefined,
      },
    };
  }
  if (raw.mode === "MARKET_CONTEXT") {
    const context = (raw.market_context || {}) as Record<string, unknown>;
    return {
      mode: "MARKET_CONTEXT",
      aggregateValueEligible: false,
      marketContext: {
        headlineNumber: context.headline_number as number | string | { low: number; high: number } | undefined,
        currency: typeof context.currency === "string" ? context.currency : undefined,
        label: typeof context.label === "string" ? context.label : "Market context",
        explanation: typeof context.explanation === "string" ? context.explanation : "",
        relationshipToArtwork: typeof context.relationship_to_artwork === "string" ? context.relationship_to_artwork : "",
        contextType: typeof context.context_type === "string" ? context.context_type : "MARKET_CONTEXT",
        sourceReference: typeof context.source_reference === "string" ? context.source_reference : undefined,
        date: typeof context.date === "string" ? context.date : null,
        confidence: typeof context.confidence === "string" ? context.confidence : undefined,
        disclaimer: typeof context.disclaimer === "string" ? context.disclaimer : undefined,
      },
    };
  }
  if (raw.mode === "BEYOND_MARKET") {
    const beyond = (raw.beyond_market || {}) as Record<string, unknown>;
    return {
      mode: "BEYOND_MARKET",
      aggregateValueEligible: false,
      beyondMarket: {
        headline: typeof beyond.headline === "string" ? beyond.headline : "No ordinary market price.",
        explanation: typeof beyond.explanation === "string" ? beyond.explanation : "",
        institutionalLegalContext: typeof beyond.institutional_legal_context === "string" ? beyond.institutional_legal_context : undefined,
        optionalContext: typeof beyond.optional_context === "string" ? beyond.optional_context : undefined,
        disclaimer: typeof beyond.disclaimer === "string" ? beyond.disclaimer : undefined,
        confidence: typeof beyond.confidence === "string" ? beyond.confidence : undefined,
      },
    };
  }
  return null;
}

function louvrePlaceholderImage(): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e8d8bd"/><stop offset=".45" stop-color="#9bb1c9"/><stop offset="1" stop-color="#2b3f56"/></linearGradient></defs><rect width="800" height="600" fill="url(#g)"/><rect x="78" y="82" width="644" height="436" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="10"/><text x="400" y="312" text-anchor="middle" font-family="Georgia, serif" font-size="42" fill="rgba(255,255,255,.86)">ELYIO</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function artworkFromCatalogDetail(raw: CatalogArtworkResponse): Artwork {
  const title = raw.title || raw.id;
  const room = raw.room || raw.hall || raw.current_location_raw || raw.department || null;
  const creatorEvidence = stringFromUnknown(raw.creator_labels) || stringFromUnknown(raw.creator_raw);
  const mediumLine = [raw.object_type, raw.materials_and_techniques].filter(Boolean).join(" · ");
  const dimensionLine = raw.dimensions ? `Dimensions: ${raw.dimensions}` : "";
  const provenanceLine = raw.provenance || raw.object_history || raw.historical_context || "";
  const why = raw.description || provenanceLine || `${title} is recorded in the Louvre visitor catalog.`;
  const where = [raw.department, room].filter(Boolean).join(" · ") || "Louvre catalog record";
  const rarity = [mediumLine, dimensionLine, raw.inventory_number ? `Inventory: ${raw.inventory_number}` : ""]
    .filter(Boolean)
    .join(" · ") || "Source metadata is available; editorial content is pending review.";

  return {
    id: raw.id,
    artist: raw.artist || creatorEvidence,
    year: raw.year || "",
    hall: room,
    inventoryNumber: raw.inventory_number || raw.id,
    image: "L",
    imageUrl: louvrePlaceholderImage(),
    accent: "#8C6A4C",
    priority: raw.priority == null ? "" : String(raw.priority),
    needsEditorialReview: raw.needs_editorial_review ?? true,
    editorialStatus: raw.metadata_status || "metadata_only",
    title: localized(title),
    titleNeedsReview: { en: false, fr: false, "zh-Hans": false },
    estimate: {
      low: raw.estimate_low,
      high: raw.estimate_high,
    },
    valueReveal: camelValueReveal(raw.value_reveal || null),
    why: localized(why),
    where: localized(where),
    rarity: localized(rarity),
    whySimple: localized(why),
    whereSimple: localized(where),
    raritySimple: localized(rarity),
    whyKids: localized(why),
    whereKids: localized(where),
    rarityKids: localized(rarity),
  };
}

export async function createVisit(locale: string, museumId: string): Promise<Visit> {
  return postJSON<Visit>("/v1/visits", { museum_id: museumId, locale }, true);
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
