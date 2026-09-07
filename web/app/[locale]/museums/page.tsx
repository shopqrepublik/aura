import type { Metadata } from "next";
import Link from "@/components/seo/SeoLink";
import { notFound } from "next/navigation";
import SeoNav from "@/components/seo/SeoNav";
import "@/components/seo/museum-guide.css";
import { LOCALES, SITE_URL, alternatesFor, museums as legacyMuseums, type SeoLocale } from "@/lib/seo-content";
import { museumsV1, museumV1CityGroups, type V1Locale } from "@/lib/museum-content-v1";

const toV1Locale = (l: SeoLocale): V1Locale => l;

const copy = {
  en: { title: "Museum Guides — ELYIO", description: "Editorial ELYIO guides to 17 museums worldwide plus a curated French museum network — highlights, self-guided visit framing, and camera-first artwork stories.", eyebrow: "ELYIO Museum Guides", h1: "A Museum Atlas", lede: "Seventeen museums, three continents, centuries of looking. Every guide is written for one institution at a time — what it holds, how to move through it, and how to point your camera at whatever catches your eye." },
  fr: { title: "Guides de musées — ELYIO", description: "Guides éditoriaux ELYIO pour 17 musées dans le monde et un réseau de musées français sélectionnés — incontournables, visite libre et récits d'œuvres via la caméra.", eyebrow: "Guides de musées ELYIO", h1: "Un Atlas de Musées", lede: "Dix-sept musées, trois continents, des siècles de regard. Chaque guide est pensé pour une institution à la fois : ce qu'elle renferme, comment la traverser, et comment pointer votre appareil photo vers ce qui attire votre regard." },
  "zh-hans": { title: "博物馆指南 — ELYIO", description: "ELYIO 为全球 17 家博物馆及精选法国博物馆网络撰写的编辑向导——重点作品、自由行参观方式，以及镜头优先的艺术故事。", eyebrow: "ELYIO 博物馆指南", h1: "一座博物馆版图", lede: "十七家博物馆，三大洲，几个世纪的观看方式。每份指南都专注于一家机构：它藏有什么、如何穿行其中，以及如何把镜头对准吸引你的那一件作品。" },
} as const;

const nav = { fr: "Musées", "zh-hans": "博物馆", en: "Museums" } as const;

// Labels for the "more museums" sub-section
const moreLabel = {
  en: "More {city} Museums",
  fr: "Autres musées {city}",
  "zh-hans": "{city} 更多博物馆",
};

// Cities that get the "More" sub-treatment (cities with both V1 lead museums and legacy museums)
const moreCities = new Set(["Paris"]);

// Cities to show separately (not merged with Paris)
const separateCities = new Set(["Versailles"]);

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) return {};
  const l = locale as SeoLocale;
  const c = copy[l];
  return { title: c.title, description: c.description, alternates: alternatesFor(`/${l}/museums`) };
}

export default async function MuseumsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) notFound();
  const l = locale as SeoLocale;
  const v = toV1Locale(l);
  const c = copy[l];

  // Build a unified slug → museum map from V1 data
  const v1Map = new Map(museumsV1.map(m => [m.slug, m]));

  // Build legacy-only museums (not in V1)
  const v1Slugs = new Set(museumsV1.map(m => m.slug));
  const legacyOnly = legacyMuseums.filter((m) => !v1Slugs.has(m.slug));

  // Merge all museums by canonical city. Each museum slug appears exactly once.
  // Strategy:
  //  1. Start with V1 museums grouped by city (preserves V1 ordering)
  //  2. Add legacy museums to their city group
  //  3. Exclude cities in `separateCities` from the main merge
  const cityMuseums = new Map<string, Array<{
    slug: string; href: string; name: string; country: string;
    blurb: string; status: string; isLead: boolean;
  }>>();

  // Add V1 museums grouped by city
  const v1Groups = museumV1CityGroups();
  for (const g of v1Groups) {
    if (separateCities.has(g.city)) continue;
    const existing = cityMuseums.get(g.city) || [];
    cityMuseums.set(g.city, [
      ...existing,
      ...g.museums.map((m, i) => ({
        slug: m.slug, href: `/${l}/museums/${m.slug}`, name: m.name[v], country: m.country,
        blurb: m.locales[v].heroSubhead, status: m.status,
        isLead: i === 0,
      })),
    ]);
  }

  // Add legacy museums to their city groups
  for (const m of legacyOnly) {
    if (separateCities.has(m.city)) continue;
    const existing = cityMuseums.get(m.city) || [];
    // Check if this museum is already in the city (shouldn't happen, but safety)
    if (existing.find(x => x.slug === m.slug)) continue;
    existing.push({
      slug: m.slug, href: `/${l}/museums/${m.slug}`, name: m.name, country: "France",
      blurb: m.intro[l], status: "LEGACY_CURATED",
      isLead: false,
    });
    cityMuseums.set(m.city, existing);
  }

  // Add separate cities as their own groups
  for (const city of separateCities) {
    const v1ForCity = v1Groups.find(g => g.city === city);
    const legacyForCity = legacyMuseums.filter(m => m.city === city && !v1Slugs.has(m.slug));
    const museums: Array<{slug: string; href: string; name: string; country: string; blurb: string; status: string; isLead: boolean}> = [];
    if (v1ForCity) {
      museums.push(...v1ForCity.museums.map((m, i) => ({
        slug: m.slug, href: `/${l}/museums/${m.slug}`, name: m.name[v], country: m.country,
        blurb: m.locales[v].heroSubhead, status: m.status, isLead: i === 0,
      })));
    }
    for (const m of legacyForCity) {
      museums.push({
        slug: m.slug, href: `/${l}/museums/${m.slug}`, name: m.name, country: "France",
        blurb: m.intro[l], status: "LEGACY_CURATED", isLead: false,
      });
    }
    if (museums.length > 0) {
      cityMuseums.set(city, museums);
    }
  }

  // Convert to ordered array. For cities in `moreCities`, split into lead + more sections.
  const renderGroups: Array<{
    city: string; museums: Array<{slug: string; href: string; name: string; country: string; blurb: string; status: string}>;
    isMoreSubSection: boolean; parentCity?: string;
  }> = [];

  for (const [city, museums] of cityMuseums) {
    if (moreCities.has(city) && museums.length > 3) {
      // Lead section: first 3 museums (Louvre, Orsay, Orangerie)
      const leadMuseums = museums.slice(0, 3);
      renderGroups.push({ city, museums: leadMuseums, isMoreSubSection: false });
      // More section: remaining museums
      const moreMuseums = museums.slice(3);
      const label = moreLabel[l].replace("{city}", city);
      renderGroups.push({ city: label, museums: moreMuseums, isMoreSubSection: true, parentCity: city });
    } else {
      renderGroups.push({ city, museums, isMoreSubSection: false });
    }
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    itemListElement: renderGroups.flatMap((g) => g.museums).map((card, i) => ({ "@type": "ListItem", position: i + 1, url: `${SITE_URL}${card.href}`, name: card.name })),
  };

  return (
    <>
      <SeoNav locale={l} path="/museums" />
      <main className="mg-main">
        <nav className="mg-breadcrumbs"><Link href={`/${l}`}>ELYIO</Link> / {nav[l]}</nav>
        <section className="mg-index-hero">
          <p className="mg-kicker"><span className="mg-dot" />{c.eyebrow}</p>
          <h1>{c.h1}</h1>
          <p>{c.lede}</p>
        </section>
        {renderGroups.map((group) => (
          <section className="mg-city-group" key={group.city}>
            <div className="mg-city-heading">
              <h2>{group.city}</h2>
              <span>{group.museums.length} {group.museums.length === 1 ? (l === "fr" ? "musée" : l === "zh-hans" ? "家博物馆" : "museum") : (l === "fr" ? "musées" : l === "zh-hans" ? "家博物馆" : "museums")}</span>
            </div>
            <div className={`mg-city-layout${group.isMoreSubSection ? " mg-more-section" : ""}`}>
              {group.museums.map((m, mi) => (
                <Link key={m.slug} href={m.href} className={`mg-museum-module${!group.isMoreSubSection && mi === 0 ? " mg-lead" : ""}`}>
                  <div className="mg-module-inner">
                    <p className="mg-module-country">{m.country}{!group.isMoreSubSection && m.status === "PRODUCTION_CATALOG" ? " · LIVE" : ""}</p>
                    <h3>{m.name}</h3>
                    <p className="mg-module-blurb">{m.blurb}</p>
                    <span className="mg-module-cta">{l === "fr" ? "Explorer →" : l === "zh-hans" ? "探索 →" : "Explore →"}</span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </main>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </>
  );
}
