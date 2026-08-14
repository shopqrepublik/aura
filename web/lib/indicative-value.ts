import * as api from "./api";
import { getArtistMarketContext } from "./generated-enrichment";
import { getArtworkValueReveal } from "./valueReveal";
import type { Artwork, ValueReveal } from "./types";

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
        low: response.estimate.low_estimate,
        high: response.estimate.high_estimate,
        currency: "EUR",
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
  const low = roundEstimate(eurMillions * significance.low);
  const high = Math.max(low + estimateStep(low), roundEstimate(eurMillions * significance.high));
  return {
    mode: "AI_INDICATIVE_ESTIMATE",
    aggregateValueEligible: false,
    indicativeAggregateEligible: true,
    aiIndicativeEstimate: {
      low,
      high,
      currency: "EUR",
      confidence: context.confidence === "HIGH" ? "MEDIUM" : "LOW",
      shortReason: "ELYIO indicative estimate derived from trusted artist-market context and broad artwork comparability.",
      assumptions: [
        "Hypothetical scale estimate only.",
        "Museum work is not for sale.",
        context.workTitle ? `Grounded by artist-market context for ${context.workTitle}.` : "Grounded by artist-market context.",
      ],
      model: "elyio-local-guardrail-fallback",
      version: "ai-indicative-estimate-v1",
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

function roundEstimate(value: number): number {
  if (value >= 100) return Math.round(value / 10) * 10;
  if (value >= 20) return Math.round(value / 5) * 5;
  if (value >= 5) return Math.round(value);
  return Number(value.toFixed(1));
}

function estimateStep(value: number): number {
  if (value >= 100) return 20;
  if (value >= 20) return 5;
  if (value >= 5) return 2;
  return 0.5;
}

function fallbackFingerprint(input: IndicativeValueInput): string {
  return [input.artist, input.title, input.date, input.objectType, input.museum].filter(Boolean).join("|").toLowerCase();
}
