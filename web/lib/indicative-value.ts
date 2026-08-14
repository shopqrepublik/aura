import * as api from "./api";
import { getArtistMarketContext } from "./generated-enrichment";
import { getArtworkValueReveal } from "./valueReveal";
import type { Artwork, ValueReveal } from "./types";

export const VALUATION_ENGINE_VERSION = "ai-indicative-estimate-v4";

const VALUATION_BANDS: Record<string, { lowEur: number; highEur: number }> = {
  V01: { lowEur: 100_000, highEur: 250_000 },
  V02: { lowEur: 250_000, highEur: 500_000 },
  V03: { lowEur: 500_000, highEur: 1_000_000 },
  V04: { lowEur: 1_000_000, highEur: 2_000_000 },
  V05: { lowEur: 2_000_000, highEur: 5_000_000 },
  V06: { lowEur: 5_000_000, highEur: 10_000_000 },
  V07: { lowEur: 10_000_000, highEur: 20_000_000 },
  V08: { lowEur: 20_000_000, highEur: 40_000_000 },
  V09: { lowEur: 40_000_000, highEur: 70_000_000 },
  V10: { lowEur: 70_000_000, highEur: 120_000_000 },
  V11: { lowEur: 120_000_000, highEur: 200_000_000 },
  V12: { lowEur: 200_000_000, highEur: 350_000_000 },
  V13: { lowEur: 350_000_000, highEur: 600_000_000 },
  V14: { lowEur: 600_000_000, highEur: 1_000_000_000 },
};

export interface IndicativeValueInput {
  artist: string | null;
  title: string | null;
  date?: string | null;
  objectType?: string | null;
  medium?: string | null;
  dimensions?: string | null;
  museum?: string | null;
  movement?: string | null;
  collectionImportance?: string | null;
  existingMarketContext?: {
    amountMillions?: number;
    currency?: string;
    workTitle?: string;
    year?: string;
    sourceReference?: string;
    confidence?: string;
  } | null;
}

export function reviewedValueWins(artwork: Artwork): boolean {
  const reveal = getArtworkValueReveal(artwork);
  return reveal?.mode === "ESTIMATED_VALUE" && reveal.aggregateValueEligible === true;
}

export function preservesExistingValuePolicy(artwork: Artwork): boolean {
  const reveal = getArtworkValueReveal(artwork);
  return reveal?.mode === "BEYOND_MARKET";
}

export function isIndicativeEstimateEligible(input: IndicativeValueInput): boolean {
  const text = [
    input.artist,
    input.title,
    input.objectType,
    input.medium,
    input.movement,
    input.collectionImportance,
  ].filter(Boolean).join(" ").toLowerCase();
  if (!input.artist || !input.title) return false;
  if (/(painting|oil|canvas|panel|portrait|self-portrait|drawing|pastel|watercolor|sculpture|statue|marble|bronze|bust)/i.test(text)) return true;
  if (/(vase|bowl|textile|tapestry|ceramic|porcelain|furniture|decorative)/i.test(text)) return true;
  if (/(relic|human remains|mummy|fragment|coin|weapon|armour|armor|ritual|funerary)/i.test(text)) return false;
  return /(monet|renoir|degas|cezanne|cézanne|gauguin|manet|van gogh|picasso|rodin|titian|leonardo|antonello|raphael|rembrandt|courbet|morisot|sisley)/i.test(text);
}

export async function fetchIndicativeValueReveal(input: IndicativeValueInput): Promise<ValueReveal | null> {
  if (!isIndicativeEstimateEligible(input)) return null;
  try {
    const response = await api.getIndicativeValue(input);
    if (!response.eligible || !response.estimate) return null;
    return {
      mode: "AI_INDICATIVE_ESTIMATE",
      aggregateValueEligible: false,
      indicativeAggregateEligible: true,
      aiIndicativeEstimate: {
        lowEur: response.estimate.low_eur,
        highEur: response.estimate.high_eur,
        currency: "EUR",
        valuationBandId: response.estimate.valuation_band_id,
        confidence: response.estimate.confidence,
        shortReason: response.estimate.short_reason,
        assumptions: response.estimate.assumptions,
        model: response.estimate.model,
        version: response.estimate.version,
        generatedAt: response.estimate.generated_at,
        groundingFingerprint: response.estimate.grounding_fingerprint,
        disclaimer: response.estimate.disclaimer,
      },
    };
  } catch {
    return localIndicativeEstimateFallback(input);
  }
}

export function localIndicativeEstimateFallback(input: IndicativeValueInput): ValueReveal | null {
  if (!isIndicativeEstimateEligible(input)) return null;
  const context = input.existingMarketContext || artistContextFor(input.artist);
  if (!context?.amountMillions || !context.currency) return null;
  const eurMillions = toEurMillions(context.amountMillions, context.currency);
  if (!eurMillions) return null;
  const significance = significanceMultiplier(input);
  const confidence = context.confidence === "HIGH" ? "MEDIUM" : "LOW";
  const midpointEur = eurMillions * ((significance.low + significance.high) / 2) * 1_000_000;
  const band = capBandForConfidence(valuationBandForMidpoint(midpointEur), context, confidence);
  return {
    mode: "AI_INDICATIVE_ESTIMATE",
    aggregateValueEligible: false,
    indicativeAggregateEligible: true,
    aiIndicativeEstimate: {
      lowEur: band.lowEur,
      highEur: band.highEur,
      currency: "EUR",
      valuationBandId: band.id,
      confidence,
      shortReason: "ELYIO indicative estimate derived from trusted artist-market context and broad artwork comparability.",
      assumptions: [
        "Hypothetical scale estimate only.",
        "Museum work is not for sale.",
        context.workTitle ? `Grounded by artist-market context for ${context.workTitle}.` : "Grounded by artist-market context.",
      ],
      model: "elyio-local-guardrail-fallback",
      version: VALUATION_ENGINE_VERSION,
      generatedAt: new Date().toISOString(),
      groundingFingerprint: fallbackFingerprint(input),
      disclaimer: "ELYIO indicative estimate for scale only; not an appraisal, insurance value, or sale estimate.",
    },
  };
}

export async function attachIndicativeValueIfEligible(
  artwork: Artwork,
  museumName: string | null | undefined,
  collectionImportance?: string | null
): Promise<Artwork> {
  if (reviewedValueWins(artwork)) return artwork;
  if (preservesExistingValuePolicy(artwork)) return artwork;
  if (artwork.valueReveal?.mode === "AI_INDICATIVE_ESTIMATE") return artwork;
  const reveal = await fetchIndicativeValueReveal({
    artist: artwork.artist,
    title: artwork.title.en,
    date: artwork.rawYear || artwork.year,
    objectType: artwork.priority,
    museum: museumName || undefined,
    movement: artwork.editorialStatus,
    collectionImportance,
    existingMarketContext: marketContextFromReveal(artwork.valueReveal),
  });
  return reveal ? { ...artwork, valueReveal: reveal } : artwork;
}

function artistContextFor(artist: string | null): IndicativeValueInput["existingMarketContext"] {
  const context = getArtistMarketContext(artist);
  if (!context || context.confidence === "NONE") return null;
  return {
    amountMillions: context.amountMillions,
    currency: context.currency,
    workTitle: context.workTitle,
    year: context.year,
    sourceReference: context.sourceReference,
    confidence: context.confidence,
  };
}

function marketContextFromReveal(valueReveal: ValueReveal | null | undefined): IndicativeValueInput["existingMarketContext"] {
  if (valueReveal?.mode !== "MARKET_CONTEXT") return null;
  const number = valueReveal.marketContext.headlineNumber;
  if (typeof number !== "number") return null;
  return {
    amountMillions: number,
    currency: valueReveal.marketContext.currency,
    sourceReference: valueReveal.marketContext.sourceReference,
    confidence: valueReveal.marketContext.confidence,
  };
}

function toEurMillions(amountMillions: number, currency: string): number | null {
  if (!Number.isFinite(amountMillions) || amountMillions <= 0) return null;
  if (currency === "EUR" || currency === "EUR_MILLION") return amountMillions;
  if (currency === "USD" || currency === "USD_MILLION") return amountMillions * 0.92;
  if (currency === "GBP" || currency === "GBP_MILLION") return amountMillions * 1.17;
  return null;
}

function significanceMultiplier(input: IndicativeValueInput): { low: number; high: number } {
  const text = [input.title, input.date, input.objectType, input.movement, input.collectionImportance].filter(Boolean).join(" ").toLowerCase();
  if (/(mona lisa|joconde|masterpiece|highlight|iconic|self-portrait|autoportrait)/i.test(text)) return { low: 0.58, high: 0.86 };
  if (/(portrait|painting|oil|canvas|panel)/i.test(text)) return { low: 0.18, high: 0.38 };
  if (/(sculpture|statue|marble|bronze|bust)/i.test(text)) return { low: 0.12, high: 0.3 };
  if (/(drawing|pastel|watercolor)/i.test(text)) return { low: 0.05, high: 0.18 };
  return { low: 0.04, high: 0.14 };
}

function fallbackFingerprint(input: IndicativeValueInput): string {
  return [VALUATION_ENGINE_VERSION, input.artist, input.title, input.date, input.objectType, input.museum].filter(Boolean).join("|").toLowerCase();
}

function valuationBandForMidpoint(midpointEur: number): { id: string; lowEur: number; highEur: number } {
  if (!Number.isFinite(midpointEur) || midpointEur <= 0) return { id: "V01", ...VALUATION_BANDS.V01 };
  for (const [id, band] of Object.entries(VALUATION_BANDS)) {
    if (midpointEur >= band.lowEur && midpointEur <= band.highEur) return { id, ...band };
  }
  return { id: "V14", ...VALUATION_BANDS.V14 };
}

function capBandForConfidence(
  band: { id: string; lowEur: number; highEur: number },
  context: NonNullable<IndicativeValueInput["existingMarketContext"]>,
  confidence: "HIGH" | "MEDIUM" | "LOW"
): { id: string; lowEur: number; highEur: number } {
  const contextMillions = toEurMillions(context.amountMillions || 0, context.currency || "");
  const contextCap = contextMillions
    ? contextMillions * 1_000_000 * (confidence === "HIGH" ? 3.0 : confidence === "MEDIUM" ? 2.5 : 1.25)
    : null;
  const confidenceCap = confidence === "HIGH" ? 120_000_000 : confidence === "MEDIUM" ? 70_000_000 : 10_000_000;
  const cap = Math.min(contextCap || confidenceCap, 1_000_000_000);
  if (band.highEur <= cap) return band;
  let selected = { id: "V01", ...VALUATION_BANDS.V01 };
  for (const [id, candidate] of Object.entries(VALUATION_BANDS)) {
    if (candidate.highEur <= cap) selected = { id, ...candidate };
  }
  return selected;
}
