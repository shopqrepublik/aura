import { tt } from "./i18n";
import type { Artwork, Estimate, Locale, ValueReveal } from "./types";

export interface AggregateEligibleValue {
  low: number;
  high: number;
  currency: string;
}

export interface VisitValueSummary {
  estimatedValueLow: number;
  estimatedValueHigh: number;
  estimatedValueCurrency: string;
  estimatedValueArtworkCount: number;
  marketContextCount: number;
  beyondMarketCount: number;
  unvaluedCount: number;
  totalArtworkCount: number;
  hasEstimatedValue: boolean;
}

export function valueRevealFromEstimate(estimate: Estimate | null | undefined): ValueReveal | null {
  if (estimate?.low == null || estimate.high == null) return null;
  return {
    mode: "ESTIMATED_VALUE",
    aggregateValueEligible: true,
    estimatedValue: {
      low: estimate.low,
      high: estimate.high,
      currency: "EUR",
      confidence: estimate.estimateConfidence ?? estimate.editorialConfidence,
      methodology: estimate.logic,
      disclaimer: undefined,
    },
  };
}

export function getArtworkValueReveal(artwork: Artwork): ValueReveal | null {
  return artwork.valueReveal ?? valueRevealFromEstimate(artwork.estimate);
}

export function getAggregateEligibleValue(artwork: Artwork): AggregateEligibleValue | null {
  const reveal = getArtworkValueReveal(artwork);
  if (reveal?.mode !== "ESTIMATED_VALUE" || reveal.aggregateValueEligible !== true) return null;
  return {
    low: reveal.estimatedValue.low,
    high: reveal.estimatedValue.high,
    currency: reveal.estimatedValue.currency,
  };
}

export function summarizeVisitValue(artworks: Artwork[]): VisitValueSummary {
  return artworks.reduce<VisitValueSummary>(
    (summary, artwork) => {
      const reveal = getArtworkValueReveal(artwork);
      const aggregate = getAggregateEligibleValue(artwork);
      summary.totalArtworkCount += 1;
      if (aggregate) {
        summary.estimatedValueLow += aggregate.low;
        summary.estimatedValueHigh += aggregate.high;
        summary.estimatedValueCurrency = aggregate.currency;
        summary.estimatedValueArtworkCount += 1;
        summary.hasEstimatedValue = true;
        return summary;
      }
      if (reveal?.mode === "MARKET_CONTEXT") {
        summary.marketContextCount += 1;
      } else if (reveal?.mode === "BEYOND_MARKET") {
        summary.beyondMarketCount += 1;
      } else {
        summary.unvaluedCount += 1;
      }
      return summary;
    },
    {
      estimatedValueLow: 0,
      estimatedValueHigh: 0,
      estimatedValueCurrency: "EUR",
      estimatedValueArtworkCount: 0,
      marketContextCount: 0,
      beyondMarketCount: 0,
      unvaluedCount: 0,
      totalArtworkCount: 0,
      hasEstimatedValue: false,
    }
  );
}

export function getMostValuableArtwork(artworks: Artwork[]): Artwork | null {
  let best: Artwork | null = null;
  let bestHigh = Number.NEGATIVE_INFINITY;
  for (const artwork of artworks) {
    const aggregate = getAggregateEligibleValue(artwork);
    if (!aggregate) continue;
    if (aggregate.high > bestHigh) {
      best = artwork;
      bestHigh = aggregate.high;
    }
  }
  return best;
}

export function formatEstimatedValueRange(value: AggregateEligibleValue): string {
  const prefix = value.currency === "EUR" ? "€" : `${value.currency} `;
  return `${prefix}${value.low}–${value.high}M`;
}

function formatContextNumber(value: number | string | { low: number; high: number }, currency?: string): string {
  if (typeof value === "string") return value;

  const symbol = currency === "USD" || currency === "USD_MILLION"
    ? "$"
    : currency === "GBP" || currency === "GBP_MILLION"
      ? "£"
      : currency === "EUR" || currency === "EUR_MILLION"
        ? "€"
        : "";
  const suffix = currency?.endsWith("_MILLION") ? "M" : "";
  const label = symbol ? "" : currency && !currency.includes("CATEGORY_SOURCE") ? `${currency} ` : "";

  if (typeof value === "object") {
    if (suffix) return `${symbol}${value.low}–${value.high}${suffix}`;
    return `${label}${value.low}–${value.high}`;
  }

  if (suffix) return `${symbol}${value}${suffix}`;
  if (symbol && Math.abs(value) >= 1_000_000) return `${symbol}${Number((value / 1_000_000).toFixed(1))}M`;
  return `${label}${value}`;
}

export function formatVisitValueHeadline(summary: VisitValueSummary, locale: Locale): string {
  if (summary.hasEstimatedValue) {
    return formatEstimatedValueRange({
      low: summary.estimatedValueLow,
      high: summary.estimatedValueHigh,
      currency: summary.estimatedValueCurrency,
    });
  }
  const contextCount = summary.marketContextCount + summary.beyondMarketCount;
  if (contextCount > 0) {
    return tt(contextCount === 1 ? "value_context_work_one" : "value_context_work_other", locale).replace("{n}", String(contextCount));
  }
  return tt("pending_review", locale);
}

export function formatVisitValueSubtitle(summary: VisitValueSummary, locale: Locale): string {
  if (summary.hasEstimatedValue) {
    const extras = summary.marketContextCount + summary.beyondMarketCount;
    if (extras > 0) {
      return tt("mixed_value_recap_subtitle", locale)
        .replace("{n}", String(summary.estimatedValueArtworkCount))
        .replace("{total}", String(summary.totalArtworkCount))
        .replace("{context}", String(extras));
    }
    return tt("in_estimated_market_value", locale);
  }
  if (summary.beyondMarketCount > 0 && summary.marketContextCount > 0) return tt("context_and_beyond_market_seen", locale);
  if (summary.beyondMarketCount > 0) return tt("beyond_market_icons_seen", locale);
  if (summary.marketContextCount > 0) return tt("market_context_seen", locale);
  return tt("recap_value_pending_caption", locale);
}

export function formatValueRevealHeadline(valueReveal: ValueReveal | null, locale: Locale): string {
  if (!valueReveal) return tt("pending_review", locale);
  if (valueReveal.mode === "ESTIMATED_VALUE") {
    return formatEstimatedValueRange(valueReveal.estimatedValue);
  }
  if (valueReveal.mode === "MARKET_CONTEXT") {
    const number = valueReveal.marketContext.headlineNumber;
    if (number == null) return valueReveal.marketContext.label;
    return formatContextNumber(number, valueReveal.marketContext.currency);
  }
  return valueReveal.beyondMarket.headline;
}
