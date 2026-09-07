import type { Metadata } from "next";
import Link from "@/components/seo/SeoLink";
import { notFound } from "next/navigation";
import SeoNav from "@/components/seo/SeoNav";
import "@/components/seo/museum-guide.css";
import { LOCALES, SITE_URL, alternatesFor, museums as legacyMuseums, type SeoLocale } from "@/lib/seo-content";
import { museumV1CityGroups, type V1Locale } from "@/lib/museum-content-v1";

const toV1Locale = (l: SeoLocale): V1Locale => l;

const copy = {
  en: { title: "Museum Guides — ELYIO", description: "Editorial ELYIO guides to 17 museums worldwide plus a curated French museum network — highlights, self-guided visit framing, and camera-first artwork stories.", eyebrow: "ELYIO Museum Guides", h1: "Explore museums with ELYIO", lede: "Every guide is written for one museum at a time — what to see, how to explore it at your own pace, and how to point your camera at whatever catches your eye." },
  fr: { title: "Guides de musées — ELYIO", description: "Guides éditoriaux ELYIO pour 17 musées dans le monde et un réseau de musées français sélectionnés — incontournables, visite libre et récits d'œuvres via la caméra.", eyebrow: "Guides de musées ELYIO", h1: "Explorez les musées avec ELYIO", lede: "Chaque guide est pensé pour un musée à la fois : que voir, comment le visiter à votre rythme, et comment pointer votre appareil photo vers ce qui attire votre regard." },
  "zh-hans": { title: "博物馆指南 — ELYIO", description: "ELYIO 为全球 17 家博物馆及精选法国博物馆网络撰写的编辑向导——重点作品、自由行参观方式，以及镜头优先的艺术故事。", eyebrow: "ELYIO 博物馆指南", h1: "与 ELYIO 一起探索博物馆", lede: "每份指南都专注于一家博物馆：值得看什么、如何按自己的节奏参观，以及如何把镜头对准吸引你的那一件作品。" },
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

  // V1 museums already grouped by city, in geographic-cluster order.
  const v1Groups = museumV1CityGroups().map((g) => ({
    city: g.city,
    cards: g.museums.map((m) => ({
      slug: m.slug, href: `/${l}/museums/${m.slug}`, name: m.name[v1], country: m.country,
      blurb: m.locales[v1].heroSubhead,
    })),
  }));

  // Legacy French museums not in the V1 set stay listed (never dropped), under
  // their own "Paris — more museums" / city groups, using their existing prose.
  const v1Slugs = new Set(museumV1CityGroups().flatMap((g) => g.museums.map((m) => m.slug)));
  const legacyOnly = legacyMuseums.filter((m) => !v1Slugs.has(m.slug));
  const legacyByCity = new Map<string, typeof legacyOnly>();
  for (const m of legacyOnly) {
    if (!legacyByCity.has(m.city)) legacyByCity.set(m.city, []);
    legacyByCity.get(m.city)!.push(m);
  }
  const legacyGroups = Array.from(legacyByCity.entries()).map(([city, items]) => ({
    city,
    cards: items.map((m) => ({ slug: m.slug, href: `/${l}/museums/${m.slug}`, name: m.name, country: "France", blurb: m.intro[l] })),
  }));

  const allGroups = [...v1Groups, ...legacyGroups];

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    itemListElement: allGroups.flatMap((g) => g.cards).map((card, i) => ({ "@type": "ListItem", position: i + 1, url: `${SITE_URL}${card.href}`, name: card.name })),
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
              <span>{group.cards.length} {group.cards.length === 1 ? (l === "fr" ? "musée" : l === "zh-hans" ? "家博物馆" : "museum") : (l === "fr" ? "musées" : l === "zh-hans" ? "家博物馆" : "museums")}</span>
            </div>
            <div className="mg-museum-cards">
              {group.cards.map((card) => (
                <Link className="mg-museum-card" key={card.slug} href={card.href}>
                  <p className="mg-museum-card-eyebrow">{card.country}</p>
                  <h3>{card.name}</h3>
                  <p>{card.blurb}</p>
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
