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
  artist: string | null;
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
  // Per-artwork override for the neutral Kids-exclusion message. Absence
  // means the generic "kids_mode_excluded" UI string is used (e.g.
  // L'Origine du monde — excluded because the content itself literally
  // can't be shown). Set this when the exclusion reason is different and
  // the generic message would be misleading or too blunt for the actual
  // reason (e.g. a difficult personal/biographical subject rather than
  // explicit content) — see Camille Monet on her deathbed for the first
  // and, as of writing, only case. Each new case like this is a deliberate
  // per-artwork decision, not something to infer by analogy to this one.
  kidsExclusionMessage?: LocalizedText;
  contentFlag?: string;
  // Simple mode — shorter, plainer language, same meaning as Normal.
  // Absence means Simple mode falls back to Normal (same rule as Kids).
  whySimple?: LocalizedText;
  whereSimple?: LocalizedText;
  raritySimple?: LocalizedText;
  // Audio narration (§10.4/§11) — Normal mode only, Top 20 for launch.
  // audioScript is a separate spoken script per locale, not a literal
  // reading of why/where/rarity (natural spoken duration, not word-for-
  // word parity). audioUrl points at a pre-generated, cached file (static
  // asset under web/public/audio/) — never a generate-on-play endpoint.
  // Absence of either field means no Listen button for that work.
  audioScript?: LocalizedText;
  audioUrl?: LocalizedText;
  // Mission completion flags (see lib/missions.ts) -- structured, not
  // inferred from free-text why/where/rarity, so a mission check is never
  // guessing from prose. Absence means false/not-applicable, same
  // optional-field convention as the rest of this interface.
  isSelfPortrait?: boolean;
  // Free-text on purpose (not a closed enum) since only one real value
  // ("pointillism", on Seurat's The Circus) exists in the catalog today --
  // see lib/missions.ts for why the "dots or dabs" mission currently has
  // exactly one valid target work.
  techniqueTag?: string;
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
