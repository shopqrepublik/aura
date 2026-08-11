import fs from "node:fs";
import path from "node:path";
import Golden20ValuePreview from "@/components/review/Golden20ValuePreview";
import type { ValueReveal } from "@/lib/types";

const PREVIEW_IDS = new Set([
  "cl010062370",
  "cl010277627",
  "cl010252531",
  "cl010059199",
  "cl010065566",
]);

type HeadlineNumber = number | string | { low: number; high: number };

interface RawValueReveal {
  mode?: string;
  aggregate_value_eligible?: boolean;
  value_low?: number;
  value_high?: number;
  currency?: string | null;
  confidence?: string;
  as_of_date?: string;
  methodology?: string;
  disclaimer?: string;
  headline_number?: HeadlineNumber;
  context_label_en?: string;
  explanation_en?: string;
  context_explanation?: string;
  relationship_to_artwork?: string;
  context_type?: string;
  sources?: string[];
  date?: string | null;
  headline?: string;
  institutional_legal_context?: string;
  optional_numeric_context?: {
    explanation?: string;
  };
}

interface GoldenRecord {
  artwork_id: string;
  identity: {
    short_title: string;
    artist_display?: string | null;
    artist?: string | null;
    date: string;
    room: string;
    inventory_number: string;
  };
  value_reveal: RawValueReveal;
  content: {
    en: {
      hook: string;
    };
  };
}

function mapGoldenValueReveal(raw: RawValueReveal): ValueReveal | null {
  if (raw.mode === "ESTIMATED_VALUE" && raw.value_low != null && raw.value_high != null) {
    return {
      mode: "ESTIMATED_VALUE",
      aggregateValueEligible: true,
      estimatedValue: {
        low: raw.value_low,
        high: raw.value_high,
        currency: raw.currency || "EUR",
        confidence: raw.confidence,
        asOfDate: raw.as_of_date,
        methodology: raw.methodology,
        disclaimer: raw.disclaimer,
      },
    };
  }

  if (raw.mode === "MARKET_CONTEXT") {
    return {
      mode: "MARKET_CONTEXT",
      aggregateValueEligible: false,
      marketContext: {
        headlineNumber: raw.headline_number,
        currency: raw.currency ?? undefined,
        label: raw.context_label_en || "market context",
        explanation: raw.explanation_en || raw.context_explanation || "",
        relationshipToArtwork: raw.relationship_to_artwork || "",
        contextType: raw.context_type || "MARKET_CONTEXT",
        sourceReference: Array.isArray(raw.sources) ? raw.sources[0] : undefined,
        date: raw.date ?? null,
        confidence: raw.confidence,
        disclaimer: raw.disclaimer,
      },
    };
  }

  if (raw.mode === "BEYOND_MARKET") {
    return {
      mode: "BEYOND_MARKET",
      aggregateValueEligible: false,
      beyondMarket: {
        headline: raw.headline || "No ordinary market price.",
        explanation: raw.explanation_en || "",
        institutionalLegalContext: raw.institutional_legal_context,
        optionalContext: raw.optional_numeric_context?.explanation,
        disclaimer: raw.disclaimer,
        confidence: raw.confidence,
      },
    };
  }

  return null;
}

function loadPreviewRecords() {
  const file = path.join(process.cwd(), "..", "exports", "louvre", "content", "louvre_golden20_final.jsonl");
  if (!fs.existsSync(file)) return [];
  return fs
    .readFileSync(file, "utf8")
    .trim()
    .split(/\r?\n/)
    .map((line) => JSON.parse(line) as GoldenRecord)
    .filter((record) => PREVIEW_IDS.has(record.artwork_id))
    .map((record) => ({
      id: record.artwork_id,
      title: record.identity.short_title,
      artist: record.identity.artist_display ?? record.identity.artist ?? null,
      date: record.identity.date,
      room: record.identity.room,
      inventoryNumber: record.identity.inventory_number,
      valueReveal: mapGoldenValueReveal(record.value_reveal),
      hook: record.content.en.hook,
    }));
}

export default function LouvreGolden20PreviewPage() {
  return <Golden20ValuePreview artworks={loadPreviewRecords()} />;
}
