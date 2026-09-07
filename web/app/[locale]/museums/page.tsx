import type { Metadata } from "next";
import Link from "@/components/seo/SeoLink";
import { notFound } from "next/navigation";
import SeoNav from "@/components/seo/SeoNav";
import "@/components/seo/museum-guide.css";
import { LOCALES, SITE_URL, alternatesFor, museums as legacyMuseums, type SeoLocale } from "@/lib/seo-content";
import { museumV1CityGroups, type V1Locale } from "@/lib/museum-content-v1";

const toV1Locale = (l: SeoLocale): V1Locale => l;

const copy = {
  en: { title: "Museum Guides — ELYIO", description: "Editorial ELYIO guides to 17 museums worldwide plus a curated French museum network — highlights, self-guided visit framing, and camera-first artwork stories.", eyebrow: "ELYIO Museum Guides", h1: "A Museum Atlas", lede: "Seventeen museums, three continents, centuries of looking. Every guide is written for one institution at a time — what it holds, how to move through it, and how to point your camera at whatever catches your eye.", leadMuseum: null },
  fr: { title: "Guides de musées — ELYIO", description: "Guides éditoriaux ELYIO pour 17 musées dans le monde et un réseau de musées français sélectionnés — incontournables, visite libre et récits d'œuvres via la caméra.", eyebrow: "Guides de musées ELYIO", h1: "Un Atlas de Musées", lede: "Dix-sept musées, trois continents, des siècles de regard. Chaque guide est pensé pour une institution à la fois : ce qu'elle renferme, comment la traverser, et comment pointer votre appareil photo vers ce qui attire votre regard.", leadMuseum: null },
  "zh-hans": { title: "博物馆指南 — ELYIO", description: "ELYIO 为全球 17 家博物馆及精选法国博物馆网络撰写的编辑向导——重点作品、自由行参观方式，以及镜头优先的艺术故事。", eyebrow: "ELYIO 博物馆指南", h1: "一座博物馆版图", lede: "十七家博物馆，三大洲，几个世纪的观看方式。每份指南都专注于一家机构：它藏有什么、如何穿行其中，以及如何把镜头对准吸引你的那一件作品。", leadMuseum: null },
} as const;

const nav = { fr: "Musées", "zh-hans": "博物馆", en: "Museums" } as const;

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
  const v1 = toV1Locale(l);
  const c = copy[l];

  const v1Groups = museumV1CityGroups().map((g) => ({
    city: g.city,
    museums: g.museums.map((m) => ({
      slug: m.slug, href: `/${l}/museums/${m.slug}`, name: m.name[v1], country: m.country,
      blurb: m.locales[v1].heroSubhead, status: m.status,
    })),
  }));

  const v1Slugs = new Set(museumV1CityGroups().flatMap((g) => g.museums.map((m) => m.slug)));
  const legacyOnly = legacyMuseums.filter((m) => !v1Slugs.has(m.slug));
  const legacyByCity = new Map<string, typeof legacyOnly>();
  for (const m of legacyOnly) {
    if (!legacyByCity.has(m.city)) legacyByCity.set(m.city, []);
    legacyByCity.get(m.city)!.push(m);
  }
  const legacyGroups = Array.from(legacyByCity.entries()).map(([city, items]) => ({
    city,
    museums: items.map((m) => ({ slug: m.slug, href: `/${l}/museums/${m.slug}`, name: m.name, country: "France", blurb: m.intro[l], status: "LEGACY_CURATED" as const })),
  }));

  const allGroups = [...v1Groups, ...legacyGroups];

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    itemListElement: allGroups.flatMap((g) => g.museums).map((card, i) => ({ "@type": "ListItem", position: i + 1, url: `${SITE_URL}${card.href}`, name: card.name })),
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
        {allGroups.map((group) => (
          <section className="mg-city-group" key={group.city}>
            <div className="mg-city-heading">
              <h2>{group.city}</h2>
              <span>{group.museums.length} {group.museums.length === 1 ? (l === "fr" ? "musée" : l === "zh-hans" ? "家博物馆" : "museum") : (l === "fr" ? "musées" : l === "zh-hans" ? "家博物馆" : "museums")}</span>
            </div>
            <div className="mg-city-layout">
              {group.museums.map((m, mi) => (
                <Link key={m.slug} href={m.href} className={`mg-museum-module${mi === 0 ? " mg-lead" : ""}`}>
                  <div className="mg-module-inner">
                    <p className="mg-module-country">{m.country}{m.status === "PRODUCTION_CATALOG" ? " · LIVE" : ""}</p>
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
