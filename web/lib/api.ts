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
  recognized_but_not_cataloged?: {
    artist: string | null;
    title: string | null;
    date?: string | null;
    object_type?: string | null;
    what_you_are_looking_at?: string | null;
    why_it_matters?: string | null;
    look_closer?: string | null;
    confidence?: number | null;
  } | null;
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
  localizations?: CatalogArtworkLocalizationResponse[];
}

export interface CatalogArtworkLocalizationResponse {
  locale: string;
  mode: string;
  title?: string | null;
  analogy?: string | null;
  why_it_matters?: string | null;
  where_to_look?: string | null;
  rarity_note?: string | null;
  audio_script?: string | null;
  audio_url?: string | null;
  editorial_status?: string | null;
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

export interface IndicativeValueRequest {
  artist: string | null;
  title: string | null;
  date?: string | null;
  object_type?: string | null;
  objectType?: string | null;
  medium?: string | null;
  dimensions?: string | null;
  museum?: string | null;
  movement?: string | null;
  collection_importance?: string | null;
  collectionImportance?: string | null;
  existing_market_context?: {
    amountMillions?: number;
    currency?: string;
    workTitle?: string;
    year?: string;
    sourceReference?: string;
    confidence?: string;
  } | null;
  existingMarketContext?: {
    amountMillions?: number;
    currency?: string;
    workTitle?: string;
    year?: string;
    sourceReference?: string;
    confidence?: string;
  } | null;
}

export interface IndicativeValueResponse {
  eligible: boolean;
  reason?: string | null;
  estimate?: {
    currency: "EUR";
    low_eur: number;
    high_eur: number;
    valuation_band_id: string;
    confidence: "HIGH" | "MEDIUM" | "LOW";
    short_reason: string;
    assumptions: string[];
    model?: string;
    version: string;
    generated_at: string;
    grounding_fingerprint: string;
    disclaimer?: string;
  } | null;
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

export async function getIndicativeValue(input: IndicativeValueRequest): Promise<IndicativeValueResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const res = await fetchWithTimeout(`${BACKEND_URL}/v1/indicative-value`, {
    method: "POST",
    headers,
    body: JSON.stringify({
    artist: input.artist,
    title: input.title,
    date: input.date ?? null,
    object_type: input.object_type ?? input.objectType ?? null,
    medium: input.medium ?? null,
    dimensions: input.dimensions ?? null,
    museum: input.museum ?? null,
    movement: input.movement ?? null,
    collection_importance: input.collection_importance ?? input.collectionImportance ?? null,
    existing_market_context: input.existing_market_context ?? input.existingMarketContext ?? null,
    }),
  }, 12000);
  if (!res.ok) throw new Error(`/v1/indicative-value failed: ${res.status}`);
  return res.json();
}

export async function getArtworkDetail(artworkId: string, locale: string, mode: string): Promise<CatalogArtworkResponse> {
  const raw = await getJSON<CatalogArtworkResponse>(
    `/v1/artworks/${encodeURIComponent(artworkId)}?locale=${encodeURIComponent(locale)}&mode=${encodeURIComponent(mode)}`
  );
  return { ...raw, locale, mode };
}

function mergeLocalized(base: string, values: Record<string, string | null | undefined>): Artwork["title"] {
  return {
    en: values.en || base,
    fr: values.fr || values.en || base,
    "zh-Hans": values["zh-Hans"] || values.en || base,
  };
}

function localizedRows(raw: CatalogArtworkResponse, mode: string): Record<string, CatalogArtworkLocalizationResponse> {
  const rows = raw.localizations || [];
  const byLocale: Record<string, CatalogArtworkLocalizationResponse> = {};
  for (const row of rows) {
    if (row.mode === mode) byLocale[row.locale] = row;
  }
  return byLocale;
}

const APPROVED_IMAGE_OVERRIDES: Record<string, string> = {
  // From exports/louvre/louvre_wikimedia_asset_manifest_final.jsonl:
  // rights_status=APPROVED, match_method=wikidata_p217_inventory_exact.
  cl010062370:
    "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_natural_color.jpg/960px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_natural_color.jpg",
};

function humanArtistName(value: string | null | undefined): string | null {
  if (!value) return null;
  const first = value.split(";")[0].trim();
  const parenthetical = first.match(/\(([^)]*(?:Leonardo da Vinci|Pablo Picasso|Auguste Rodin|Claude Monet|Paul Cezanne|Paul Cézanne)[^)]*)\)/i);
  if (parenthetical) {
    const aliases = parenthetical[1].split(",").map((x) => x.trim()).filter(Boolean);
    const best = aliases.find((x) => !/^dit\s+/i.test(x) && /Leonardo da Vinci|Pablo Picasso|Auguste Rodin|Claude Monet|Paul Cezanne|Paul Cézanne/i.test(x));
    if (best) return best.replace(/^dit\s+/i, "");
    const namedAlias = aliases.find((x) => /Leonardo da Vinci|Pablo Picasso|Auguste Rodin|Claude Monet|Paul Cezanne|Paul Cézanne/i.test(x));
    if (namedAlias) return namedAlias.replace(/^dit\s+/i, "");
  }
  return first.replace(/\s*\([^)]{20,}\)\s*/g, "").trim() || first;
}

function humanYear(value: string | null | undefined, locale = "en"): string {
  if (!value) return "";
  const yearRange = value.match(/(\d{3,4})\s*[-–]\s*(\d{2,4})/);
  if (yearRange) {
    const prefix = locale === "fr" ? "vers " : locale === "zh-Hans" ? "约 " : "c. ";
    return `${prefix}${yearRange[1]}–${yearRange[2]}`;
  }
  return value
    .replace(/^Date de création\/fabrication\s*:\s*/i, "")
    .replace(/^Date\s*:\s*/i, "")
    .trim();
}

function humanTitle(raw: CatalogArtworkResponse): string {
  const normal = localizedRows(raw, "normal").en?.title;
  if (normal) return normal;
  if (raw.id === "cl010062370") return "Mona Lisa";
  return raw.title || raw.id;
}

function modeText(
  raw: CatalogArtworkResponse,
  mode: "normal" | "simple" | "kids",
  field: "why_it_matters" | "where_to_look" | "rarity_note" | "analogy",
  fallback: string
): Artwork["title"] {
  const rows = localizedRows(raw, mode);
  const normalRows = mode === "normal" ? rows : localizedRows(raw, "normal");
  return mergeLocalized(fallback, {
    en: rows.en?.[field] || normalRows.en?.[field],
    fr: rows.fr?.[field] || normalRows.fr?.[field] || rows.en?.[field] || normalRows.en?.[field],
    "zh-Hans": rows["zh-Hans"]?.[field] || normalRows["zh-Hans"]?.[field] || rows.en?.[field] || normalRows.en?.[field],
  });
}

function titleText(raw: CatalogArtworkResponse, fallback: string): Artwork["title"] {
  const normalRows = localizedRows(raw, "normal");
  return mergeLocalized(fallback, {
    en: normalRows.en?.title,
    fr: normalRows.fr?.title,
    "zh-Hans": normalRows["zh-Hans"]?.title,
  });
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

function camelValueReveal(raw: Record<string, unknown> | null | undefined, locale = "en"): ValueReveal | null {
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
        methodology: localizeValueCopy(typeof estimated.methodology === "string" ? estimated.methodology : undefined, locale),
        disclaimer: localizeValueCopy(typeof estimated.disclaimer === "string" ? estimated.disclaimer : undefined, locale),
      },
    };
  }
  if (raw.mode === "AI_INDICATIVE_ESTIMATE") {
    const estimate = (raw.ai_indicative_estimate || raw.aiIndicativeEstimate || {}) as Record<string, unknown>;
    const version = typeof estimate.version === "string" ? estimate.version : "";
    if (version !== "ai-indicative-estimate-v4") return null;
    const lowEur = Number(estimate.low_eur ?? estimate.lowEur);
    const highEur = Number(estimate.high_eur ?? estimate.highEur);
    if (!Number.isFinite(lowEur) || !Number.isFinite(highEur)) return null;
    if (lowEur <= 0 || highEur <= lowEur || highEur > 1_000_000_000) return null;
    return {
      mode: "AI_INDICATIVE_ESTIMATE",
      aggregateValueEligible: false,
      indicativeAggregateEligible: true,
      aiIndicativeEstimate: {
        lowEur,
        highEur,
        currency: "EUR",
        valuationBandId: typeof estimate.valuation_band_id === "string" ? estimate.valuation_band_id : typeof estimate.valuationBandId === "string" ? estimate.valuationBandId : "",
        confidence: estimate.confidence === "HIGH" || estimate.confidence === "MEDIUM" || estimate.confidence === "LOW" ? estimate.confidence : "LOW",
        shortReason: localizeValueCopy(typeof estimate.short_reason === "string" ? estimate.short_reason : typeof estimate.shortReason === "string" ? estimate.shortReason : "", locale) || "",
        assumptions: Array.isArray(estimate.assumptions) ? estimate.assumptions.filter((x): x is string => typeof x === "string") : [],
        model: typeof estimate.model === "string" ? estimate.model : undefined,
        version,
        generatedAt: typeof estimate.generated_at === "string" ? estimate.generated_at : typeof estimate.generatedAt === "string" ? estimate.generatedAt : new Date().toISOString(),
        groundingFingerprint: typeof estimate.grounding_fingerprint === "string" ? estimate.grounding_fingerprint : typeof estimate.groundingFingerprint === "string" ? estimate.groundingFingerprint : "",
        disclaimer: localizeValueCopy(typeof estimate.disclaimer === "string" ? estimate.disclaimer : undefined, locale),
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
        explanation: localizeValueCopy(typeof context.explanation === "string" ? context.explanation : "", locale) || "",
        relationshipToArtwork: localizeValueCopy(typeof context.relationship_to_artwork === "string" ? context.relationship_to_artwork : "", locale) || "",
        contextType: typeof context.context_type === "string" ? context.context_type : "MARKET_CONTEXT",
        sourceReference: typeof context.source_reference === "string" ? context.source_reference : undefined,
        date: typeof context.date === "string" ? context.date : null,
        confidence: typeof context.confidence === "string" ? context.confidence : undefined,
        disclaimer: localizeValueCopy(typeof context.disclaimer === "string" ? context.disclaimer : undefined, locale),
      },
    };
  }
  if (raw.mode === "BEYOND_MARKET") {
    const beyond = (raw.beyond_market || {}) as Record<string, unknown>;
    const optionalContext = parseOptionalContext(beyond.optional_context, locale);
    return {
      mode: "BEYOND_MARKET",
      aggregateValueEligible: false,
      beyondMarket: {
        headline:
          localizeValueCopy(typeof beyond.headline === "string" ? beyond.headline : "No ordinary market price.", locale) ||
          "No ordinary market price.",
        explanation: localizeValueCopy(typeof beyond.explanation === "string" ? beyond.explanation : "", locale) || "",
        institutionalLegalContext: localizeValueCopy(
          typeof beyond.institutional_legal_context === "string" ? beyond.institutional_legal_context : undefined,
          locale
        ),
        optionalContext,
        disclaimer: localizeValueCopy(typeof beyond.disclaimer === "string" ? beyond.disclaimer : undefined, locale),
        confidence: typeof beyond.confidence === "string" ? beyond.confidence : undefined,
      },
    };
  }
  return null;
}

function parseOptionalContext(value: unknown, locale = "en"): string | undefined {
  if (typeof value !== "string" || !value.trim()) return undefined;
  const trimmed = value.trim();
  if (!trimmed.startsWith("{")) return localizeValueCopy(trimmed, locale);
  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>;
    const number = parsed.number;
    const currency = parsed.currency;
    const label = typeof parsed.label === "string" ? parsed.label : undefined;
    const explanation = typeof parsed.explanation === "string" ? parsed.explanation : undefined;
    let formatted: string | null = null;
    if (typeof number === "number") {
      if (currency === "USD_MILLION") formatted = `$${number}M`;
      else if (currency === "EUR_MILLION") formatted = `€${number}M`;
      else if (currency === "GBP_MILLION") formatted = `£${number}M`;
      else formatted = String(number);
    }
    if (locale === "fr" && label === "Leonardo auction record") {
      return [
        formatted ? `Record de vente de Leonardo : ${formatted}.` : "Record de vente de Leonardo.",
        "Le Salvator Mundi s'est vendu 450,3 millions de dollars chez Christie's en 2017. C'est un repère de grandeur, pas une estimation de La Joconde.",
      ].join(" ");
    }
    if (locale === "zh-Hans" && label === "Leonardo auction record") {
      return [
        "列奥纳多拍卖纪录：4.503 亿美元。",
        "《救世主》2017 年在佳士得成交。这只是规模参照，不是《蒙娜丽莎》的估值。",
      ].join("");
    }
    return [label && formatted ? `${label}: ${formatted}.` : label || formatted, localizeValueCopy(explanation, locale)].filter(Boolean).join(" ");
  } catch {
    return undefined;
  }
}

function localizeValueCopy(value: string | undefined, locale = "en"): string | undefined {
  if (!value || locale === "en") return value;
  if (/No ordinary market price/i.test(value)) {
    return locale === "fr" ? "Aucun prix de marché ordinaire." : "没有普通市场价格。";
  }
  if (/belongs to France's public museum collections/i.test(value)) {
    return locale === "fr"
      ? "Cette œuvre appartient aux collections publiques françaises et ne se vend pas comme une œuvre privée."
      : "这件作品属于法国公共博物馆收藏，并不像私人艺术品那样交易。";
  }
  if (/French public Musees de France collections are inalienable public property/i.test(value)) {
    return locale === "fr"
      ? "Les collections publiques des Musées de France sont des biens publics inaliénables."
      : "法国 Musees de France 公共收藏属于不可转让的公共财产。";
  }
  if (/Not an appraisal, insurance value, or sale estimate/i.test(value)) {
    return locale === "fr"
      ? "Ce n'est ni une expertise, ni une valeur d'assurance, ni une estimation de vente."
      : "这不是鉴定估价、保险价值或出售估价。";
  }
  if (/This is market context, not an appraisal of the museum work/i.test(value)) {
    return locale === "fr"
      ? "C'est un contexte de marché, pas une estimation de l'œuvre du musée."
      : "这是市场背景，不是对馆藏作品的估价。";
  }
  return value;
}

function louvrePlaceholderImage(): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e8d8bd"/><stop offset=".45" stop-color="#9bb1c9"/><stop offset="1" stop-color="#2b3f56"/></linearGradient></defs><rect width="800" height="600" fill="url(#g)"/><rect x="78" y="82" width="644" height="436" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="10"/><text x="400" y="312" text-anchor="middle" font-family="Georgia, serif" font-size="42" fill="rgba(255,255,255,.86)">ELYIO</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function artworkFromCatalogDetail(raw: CatalogArtworkResponse): Artwork {
  const title = humanTitle(raw);
  const room = raw.room || raw.hall || raw.current_location_raw || raw.department || null;
  const museumCatalogLabel =
    raw.museum_id === "louvre"
      ? "Louvre visitor catalog"
      : raw.museum_id === "versailles"
        ? "Versailles visitor catalog"
        : "ELYIO museum catalog";
  const creatorEvidence = stringFromUnknown(raw.creator_labels) || stringFromUnknown(raw.creator_raw);
  const mediumLine = [raw.object_type, raw.materials_and_techniques].filter(Boolean).join(" · ");
  const dimensionLine = raw.dimensions ? `Dimensions: ${raw.dimensions}` : "";
  const provenanceLine = raw.provenance || raw.object_history || raw.historical_context || "";
  const why = raw.description || provenanceLine || `${title} is recorded in the ${museumCatalogLabel}.`;
  const where = [raw.department, room].filter(Boolean).join(" · ") || `${museumCatalogLabel} record`;
  const rarity = [mediumLine, dimensionLine, raw.inventory_number ? `Inventory: ${raw.inventory_number}` : ""]
    .filter(Boolean)
    .join(" · ") || "Source metadata is available; editorial content is pending review.";
  const normalWhy = modeText(raw, "normal", "why_it_matters", why);
  const normalWhere = modeText(raw, "normal", "where_to_look", where);
  const normalRarity = modeText(raw, "normal", "rarity_note", rarity);
  const normalAudioRows = localizedRows(raw, "normal");
  const audioUrl = mergeLocalized("", {
    en: normalAudioRows.en?.audio_url,
    fr: normalAudioRows.fr?.audio_url,
    "zh-Hans": normalAudioRows["zh-Hans"]?.audio_url,
  });
  const audioScript = mergeLocalized("", {
    en: normalAudioRows.en?.audio_script,
    fr: normalAudioRows.fr?.audio_script,
    "zh-Hans": normalAudioRows["zh-Hans"]?.audio_script,
  });
  const hasAudioUrl = Boolean(audioUrl.en || audioUrl.fr || audioUrl["zh-Hans"]);
  const hasAudioScript = Boolean(audioScript.en || audioScript.fr || audioScript["zh-Hans"]);
  const displayArtist = humanArtistName(raw.artist) || humanArtistName(creatorEvidence);
  const displayYear = humanYear(raw.year, raw.locale || "en");
  const normalWhereText = normalWhere.en;
  const normalRarityText = normalRarity.en;
  const simpleWhy = modeText(raw, "simple", "analogy", why);
  const kidsWhy = modeText(raw, "kids", "analogy", why);
  const simpleHasOnlyOpening = simpleWhy.en !== normalWhy.en && modeText(raw, "simple", "where_to_look", normalWhereText).en === normalWhereText;
  const kidsHasOnlyOpening = kidsWhy.en !== normalWhy.en && modeText(raw, "kids", "where_to_look", normalWhereText).en === normalWhereText;
  const resolvedImageUrl = raw.image_url || APPROVED_IMAGE_OVERRIDES[raw.id] || louvrePlaceholderImage();
  const imageSourceType = raw.image_url || APPROVED_IMAGE_OVERRIDES[raw.id] ? "REFERENCE_REAL" : "PLACEHOLDER";

  return {
    id: raw.id,
    artist: displayArtist,
    rawArtist: raw.artist || creatorEvidence,
    year: displayYear,
    rawYear: raw.year || "",
    hall: room,
    inventoryNumber: raw.inventory_number || raw.id,
    image: "L",
    imageUrl: resolvedImageUrl,
    imageSourceType,
    imageSourceId: imageSourceType === "REFERENCE_REAL" ? `catalog:${raw.id}` : "placeholder:elyio",
    accent: "#8C6A4C",
    priority: raw.priority == null ? "" : String(raw.priority),
    needsEditorialReview: raw.needs_editorial_review ?? true,
    editorialStatus: raw.metadata_status || "metadata_only",
    title: titleText(raw, title),
    titleNeedsReview: { en: false, fr: false, "zh-Hans": false },
    estimate: {
      low: raw.estimate_low,
      high: raw.estimate_high,
    },
    valueReveal: camelValueReveal(raw.value_reveal || null, raw.locale || "en"),
    why: normalWhy,
    where: normalWhere,
    rarity: normalRarity,
    whySimple: simpleWhy,
    whereSimple: simpleHasOnlyOpening ? simpleWhy : modeText(raw, "simple", "where_to_look", normalWhereText),
    raritySimple: simpleHasOnlyOpening ? simpleWhy : modeText(raw, "simple", "rarity_note", normalRarityText),
    whyKids: kidsWhy,
    whereKids: kidsHasOnlyOpening ? kidsWhy : modeText(raw, "kids", "where_to_look", normalWhereText),
    rarityKids: kidsHasOnlyOpening ? kidsWhy : modeText(raw, "kids", "rarity_note", normalRarityText),
    ...(hasAudioScript ? { audioScript } : {}),
    ...(hasAudioUrl ? { audioUrl } : {}),
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
