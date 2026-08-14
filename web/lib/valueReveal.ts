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
  indicativeValueLow: number;
  indicativeValueHigh: number;
  indicativeValueCurrency: string;
  aiIndicativeArtworkCount: number;
  indicativeValueArtworkCount: number;
  marketContextCount: number;
  beyondMarketCount: number;
  unvaluedCount: number;
  totalArtworkCount: number;
  hasEstimatedValue: boolean;
  hasIndicativeValue: boolean;
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

export function getIndicativeEligibleValue(artwork: Artwork): AggregateEligibleValue | null {
  const reveal = getArtworkValueReveal(artwork);
  if (!reveal) return null;
  if (reveal.mode === "ESTIMATED_VALUE" && reveal.aggregateValueEligible === true) {
    return {
      low: reveal.estimatedValue.low,
      high: reveal.estimatedValue.high,
      currency: reveal.estimatedValue.currency,
    };
  }
  if (reveal.mode === "AI_INDICATIVE_ESTIMATE" && reveal.indicativeAggregateEligible === true) {
    return {
      low: reveal.aiIndicativeEstimate.low,
      high: reveal.aiIndicativeEstimate.high,
      currency: reveal.aiIndicativeEstimate.currency,
    };
  }
  return null;
}

export function summarizeVisitValue(artworks: Artwork[]): VisitValueSummary {
  return artworks.reduce<VisitValueSummary>(
    (summary, artwork) => {
      const reveal = getArtworkValueReveal(artwork);
      const aggregate = getAggregateEligibleValue(artwork);
      const indicative = getIndicativeEligibleValue(artwork);
      summary.totalArtworkCount += 1;
      if (aggregate) {
        summary.estimatedValueLow += aggregate.low;
        summary.estimatedValueHigh += aggregate.high;
        summary.estimatedValueCurrency = aggregate.currency;
        summary.estimatedValueArtworkCount += 1;
        summary.hasEstimatedValue = true;
      }
      if (indicative) {
        summary.indicativeValueLow += indicative.low;
        summary.indicativeValueHigh += indicative.high;
        summary.indicativeValueCurrency = indicative.currency;
        summary.indicativeValueArtworkCount += 1;
        summary.hasIndicativeValue = true;
        if (reveal?.mode === "AI_INDICATIVE_ESTIMATE") summary.aiIndicativeArtworkCount += 1;
      }
      if (reveal?.mode === "MARKET_CONTEXT") {
        summary.marketContextCount += 1;
      } else if (reveal?.mode === "BEYOND_MARKET") {
        summary.beyondMarketCount += 1;
      } else if (!indicative) {
        summary.unvaluedCount += 1;
      }
      return summary;
    },
    {
      estimatedValueLow: 0,
      estimatedValueHigh: 0,
      estimatedValueCurrency: "EUR",
      estimatedValueArtworkCount: 0,
      indicativeValueLow: 0,
      indicativeValueHigh: 0,
      indicativeValueCurrency: "EUR",
      aiIndicativeArtworkCount: 0,
      indicativeValueArtworkCount: 0,
      marketContextCount: 0,
      beyondMarketCount: 0,
      unvaluedCount: 0,
      totalArtworkCount: 0,
      hasEstimatedValue: false,
      hasIndicativeValue: false,
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
  const low = formatMoneyMillions(value.low);
  const high = formatMoneyMillions(value.high);
  return `${prefix}${low}–${high}`;
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
  if (valueReveal.mode === "AI_INDICATIVE_ESTIMATE") {
    return formatEstimatedValueRange(valueReveal.aiIndicativeEstimate);
  }
  if (valueReveal.mode === "MARKET_CONTEXT") {
    const number = valueReveal.marketContext.headlineNumber;
    if (number == null) return valueReveal.marketContext.label;
    return formatContextNumber(number, valueReveal.marketContext.currency);
  }
  return valueReveal.beyondMarket.headline;
}

function formatMoneyMillions(value: number): string {
  if (!Number.isFinite(value)) return "0M";
  if (Math.abs(value) >= 1000) return `${Number((value / 1000).toFixed(value % 1000 === 0 ? 0 : 1))}B`;
  if (Math.abs(value) >= 100) return `${Math.round(value)}M`;
  if (Math.abs(value) >= 10) return `${Number(value.toFixed(value % 1 === 0 ? 0 : 1))}M`;
  return `${Number(value.toFixed(1))}M`;
}
