// Shared types for ELYIO's ported content dataset (see lib/data/*.json,
// ported from the original frontend/data.js — same fields, same content
// policy, just typed and consumed from a Next.js app instead of vanilla JS).

export type Locale = "en" | "fr" | "zh-Hans";
export type Mode = "normal" | "simple" | "kids";

export type LocalizedText = Record<Locale, string>;

export interface TitleNeedsReview {
  en: boolean;
  fr: boolean;
  "zh-Hans": boolean;
}

export interface Estimate {
  low: number | null;
  high: number | null;
  // Editorial provenance for AI-drafted estimate ranges — internal/review
  // metadata, not shown verbatim in the app UI (the §11 disclaimer covers
  // the user-facing side of "how was this number produced"). English only:
  // this is for a human editor's review pass, not translated content.
  logic?: string;
  comparableSales?: string[];
  editorialConfidence?: "low" | "medium" | "high";
  estimateConfidence?: "low" | "medium" | "high";
  reviewedBy?: string | null;
}

export interface Artwork {
  id: string;
  artist: string;
  year: string;
  hall: string | null;
  inventoryNumber: string;
  image: string;
  imageUrl: string;
  accent: string;
  priority: string;
  needsEditorialReview: boolean;
  editorialStatus: string;
  title: LocalizedText;
  titleNeedsReview: TitleNeedsReview;
  estimate: Estimate;
  why: LocalizedText;
  where: LocalizedText;
  rarity: LocalizedText;
  // Content policy (§ Kids mode) — only present on the handful of works that
  // needed a decision. Absence means Kids mode == Normal mode for that work.
  whyKids?: LocalizedText;
  whereKids?: LocalizedText;
  rarityKids?: LocalizedText;
  kidsModeExcluded?: boolean;
  contentFlag?: string;
  // Simple mode — shorter, plainer language, same meaning as Normal.
  // Absence means Simple mode falls back to Normal (same rule as Kids).
  whySimple?: LocalizedText;
  whereSimple?: LocalizedText;
  raritySimple?: LocalizedText;
}

export interface Mission {
  id: string;
  en: string;
  fr: string;
  "zh-Hans": string;
}

export type UIStringKey =
  | "start_visit"
  | "frame_artwork"
  | "add_to_visit"
  | "why_it_matters"
  | "where_to_look"
  | "indicative_estimate"
  | "share_visit"
  | "try_again"
  | "added_to_visit"
  | "kids_mode_excluded";

export type UIStrings = Record<UIStringKey, LocalizedText>;
