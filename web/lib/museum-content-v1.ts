import raw from "@/lib/data/museums-v1.json";

export type MuseumStatus = "PRODUCTION_CATALOG" | "CONTROLLED_PREVIEW" | "NO_INSTITUTION_RECORD";
export type V1Locale = "en" | "fr" | "zh-hans";

export type MuseumWhatToSeeItem = { name: string; blurb: string };
export type MuseumMasterpiece = {
  title: string;
  artist: string;
  year: string;
  hook: string;
  context: string;
  imageCommonsUrl: string | null;
  imageAlt: string;
  imageConfidence: "VERIFIED" | "LIKELY" | "NEEDS_VERIFICATION";
};
export type MuseumFaqItem = { q: string; a: string };

export type MuseumLocaleContent = {
  metaTitle: string;
  metaDescription: string;
  heroHeadline: string;
  heroSubhead: string;
  heroCta: string;
  problem: string[];
  whatToSeeIntro: string;
  whatToSeeItems: MuseumWhatToSeeItem[];
  masterpieces: MuseumMasterpiece[];
  howToExplore: string;
  selfGuided: string;
  comparisonTraditional: string[];
  comparisonElyio: string[];
  practicalNotes: string;
  faq: MuseumFaqItem[];
  finalCtaHeadline: string;
  finalCtaLabel: string;
};

export type MuseumKeywordMap = {
  canonicalName: string;
  nameVariants: string[];
  primaryKeyword: string;
  primaryIntent: string;
  secondaryCluster: string[];
  longTail: string[];
  artistOpportunities: string[];
  artworkOpportunities: string[];
  faqOpportunities: string[];
  searchIntent: string;
  productFit: string;
  competition: string;
  contentAngle: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
};

export type MuseumV1 = {
  slug: string;
  dbId: string | null;
  status: MuseumStatus;
  city: string;
  country: string;
  website: string;
  artDirection: { personality: string; accent: string; layoutVariant: string };
  name: Record<V1Locale, string>;
  locales: Record<V1Locale, MuseumLocaleContent>;
  keywordMap: Record<V1Locale, MuseumKeywordMap>;
};

export const museumsV1 = raw as unknown as MuseumV1[];

export const museumV1BySlug = (slug: string): MuseumV1 | undefined => museumsV1.find((m) => m.slug === slug);

export const museumV1CityGroups = (): { city: string; museums: MuseumV1[] }[] => {
  const order: string[] = [];
  const groups = new Map<string, MuseumV1[]>();
  for (const m of museumsV1) {
    if (!groups.has(m.city)) { groups.set(m.city, []); order.push(m.city); }
    groups.get(m.city)!.push(m);
  }
  return order.map((city) => ({ city, museums: groups.get(city)! }));
};

// CTA rule (see docs/growth/MUSEUM_KEYWORD_MAP.md and .tmp/museum_registry_v1.md):
// The scanner's real, tested museum-context mechanism is on-device geolocation
// detection (lib/geolocation.ts) — there is no existing, proven URL-param path
// that sets scanner museum context, so we deliberately do NOT invent one here
// (that would touch recognition/scanner initialization logic, which is out of
// scope and explicitly disallowed). For every museum regardless of status, the
// CTA goes to the existing generic /visit scanner and only carries acquisition
// context (`landing`, `locale`) through the already-existing, already-tested
// organic-landing bridge in components/ElyioApp.tsx — the same mechanism the
// /artworks/[slug] pages use (`landing=artwork:{slug}`). This can never 404
// and never overrides recognition behavior; confident general AI recognition
// remains the valid success path for CONTROLLED_PREVIEW/NO_INSTITUTION_RECORD
// museums, exactly as instructed.
export const museumVisitHref = (m: MuseumV1, locale: V1Locale): string => {
  const params = new URLSearchParams({ from: "organic", locale, landing: `museum:${m.slug}` });
  return `/visit?${params.toString()}`;
};
