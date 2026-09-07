import type { Metadata } from "next";
import Link from "@/components/seo/SeoLink";
import { notFound } from "next/navigation";
import SeoNav from "@/components/seo/SeoNav";
import "@/components/seo/museum-guide.css";
import { LOCALES, SITE_URL, alternatesFor, artworks, museums as legacyMuseums, museumBySlug as legacyMuseumBySlug, type SeoLocale } from "@/lib/seo-content";
import { museumsV1, museumV1BySlug, museumVisitHref, type V1Locale } from "@/lib/museum-content-v1";
import MuseumMasterpieceImage from "@/components/seo/MuseumMasterpieceImage";

type ChromeCopy = { museums: string; howToApproach: string; whatToSee: string; masterpieces: string; explore: string; selfGuided: string; comparison: string; practical: string; faq: string; supportedStories: string; disclosure: string; traditional: string; withElyio: string };
const chrome: Record<SeoLocale, ChromeCopy> = {
  en: { museums: "Museums", howToApproach: "How to approach the visit", whatToSee: "What to see", masterpieces: "Masterpiece stories", explore: "How to explore with ELYIO", selfGuided: "Self-guided visits", comparison: "Traditional audio guide vs. ELYIO", practical: "Good to know", faq: "Frequently asked questions", supportedStories: "Supported artwork stories", disclosure: "ELYIO is an independent visitor tool and is not affiliated with, endorsed by, or sponsored by the museum.", traditional: "Traditional audio guide", withElyio: "With ELYIO" },
  fr: { museums: "Musées", howToApproach: "Comment organiser la visite", whatToSee: "À voir", masterpieces: "Œuvres racontées", explore: "Explorer avec ELYIO", selfGuided: "Visite libre", comparison: "Audioguide traditionnel vs. ELYIO", practical: "Bon à savoir", faq: "Questions fréquentes", supportedStories: "Œuvres accompagnées", disclosure: "ELYIO est un outil indépendant pour les visiteurs et n'est ni affilié, ni approuvé, ni parrainé par le musée.", traditional: "Audioguide traditionnel", withElyio: "Avec ELYIO" },
  "zh-hans": { museums: "博物馆", howToApproach: "如何规划参观", whatToSee: "重点作品", masterpieces: "作品故事", explore: "如何用ELYIO探索", selfGuided: "自由行参观", comparison: "传统语音导览 vs. ELYIO", practical: "实用提示", faq: "常见问题", supportedStories: "ELYIO 支持的作品", disclosure: "ELYIO 是独立的访客工具，与博物馆没有官方合作、认可或赞助关系。", traditional: "传统语音导览", withElyio: "使用 ELYIO" },
} as const;

function getArchetype(slug: string): string {
  const iconic = ["musee-du-louvre", "rijksmuseum", "national-gallery-london"];
  const intimate = ["musee-de-l-orangerie"];
  const encyclopedic = ["the-met", "khm-vienna"];
  const design = ["va-london", "nordiska-museet"];
  const regional = ["princeton", "yale-new-haven", "cleveland"];
  if (iconic.includes(slug)) return "iconic";
  if (intimate.includes(slug)) return "intimate";
  if (encyclopedic.includes(slug)) return "encyclopedic";
  if (design.includes(slug)) return "design";
  if (regional.includes(slug)) return "regional";
  return "standard";
}

function getRelatedMuseums(slug: string, locale: SeoLocale): Array<{slug: string; name: string}> {
  const relatedSlugs: Record<string, string[]> = {
    "musee-du-louvre": ["musee-d-orsay", "musee-de-l-orangerie", "musee-rodin"],
    "musee-d-orsay": ["musee-du-louvre", "musee-de-l-orangerie", "musee-guimet"],
    "musee-de-l-orangerie": ["musee-du-louvre", "musee-d-orsay", "musee-rodin"],
    "national-gallery-london": ["va-london", "chateau-de-versailles", "musee-de-cluny"],
    "va-london": ["national-gallery-london", "rijksmuseum", "the-met"],
    "the-met": ["national-gallery-london", "rijksmuseum", "gemaldegalerie-berlin"],
    rijksmuseum: ["the-met", "national-gallery-london", "musee-du-louvre"],
    "khm-vienna": ["the-met", "alte-pinakothek", "gemaldegalerie-berlin"],
    "smk-copenhagen": ["nordiska-museet", "musee-de-l-orangerie"],
    "nordiska-museet": ["smk-copenhagen", "va-london"],
    princeton: ["yale-new-haven", "cleveland", "nga-washington"],
    cleveland: ["princeton", "yale-new-haven", "getty"],
    "nga-washington": ["cleveland", "princeton", "getty"],
    getty: ["cleveland", "nga-washington", "the-met"],
    "gemaldegalerie-berlin": ["the-met", "khm-vienna", "alte-pinakothek"],
    "alte-pinakothek": ["khm-vienna", "gemaldegalerie-berlin", "musee-de-l-orangerie"],
    "yale-new-haven": ["princeton", "cleveland", "nga-washington"],
    "musee-carnavalet": ["musee-de-cluny", "musee-de-l-armee", "musee-du-quai-branly-jacques-chirac"],
    "musee-de-cluny": ["musee-carnavalet", "musee-de-l-armee", "musee-du-louvre"],
    "musee-de-l-armee": ["musee-de-cluny", "musee-du-quai-branly-jacques-chirac", "musee-rodin"],
    "musee-du-quai-branly-jacques-chirac": ["musee-guimet", "musee-de-l-armee", "musee-carnavalet"],
    "musee-guimet": ["musee-du-quai-branly-jacques-chirac", "musee-de-cluny"],
  };
  const slugMap = new Map(museumsV1.map(m => [m.slug, m]));
  const matchedSlugs = relatedSlugs[slug] || ["musee-du-louvre"];
  return matchedSlugs.map(s => {
    const m = slugMap.get(s);
    return { slug: s, name: m ? m.name[locale] : s };
  });
}

export function generateStaticParams() {
  const v1Slugs = museumsV1.map((m) => m.slug);
  const legacySlugs = legacyMuseums.map((m) => m.slug);
  return LOCALES.flatMap((locale) => [...v1Slugs, ...legacySlugs].map((slug) => ({ locale, slug })));
}
export const dynamicParams = true;

export async function generateMetadata({ params }: { params: Promise<{ locale: string; slug: string }> }): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) return {};
  const l = locale as SeoLocale;
  const v1 = museumV1BySlug(slug);
  if (v1) {
    const content = v1.locales[l as V1Locale];
    return {
      title: content.metaTitle,
      description: content.metaDescription,
      alternates: alternatesFor(`/${l}/museums/${slug}`),
      openGraph: { title: content.metaTitle, description: content.metaDescription, url: `${SITE_URL}/${l}/museums/${slug}`, type: "website", siteName: "ELYIO", images: [{ url: "/icons/icon-512.png", width: 512, height: 512, alt: `ELYIO guide to ${v1.name[l as V1Locale]}` }] },
      twitter: { card: "summary_large_image", title: content.metaTitle, description: content.metaDescription, images: ["/icons/icon-512.png"] },
    };
  }
  const legacy = legacyMuseumBySlug(slug);
  if (!legacy) return {};
  const title = l === "fr" ? `${legacy.name} — Guide, œuvres majeures et clés de visite | ELYIO` : l === "zh-hans" ? `${legacy.name} 指南 — 重点作品与观看线索 | ELYIO` : `${legacy.name} Guide — Highlights, Art Stories & Value Context | ELYIO`;
  return { title, description: legacy.intro[l], alternates: alternatesFor(`/${l}/museums/${slug}`), openGraph: { title, description: legacy.intro[l], url: `${SITE_URL}/${l}/museums/${slug}`, type: "website", siteName: "ELYIO", images: [{ url: "/icons/icon-512.png", width: 512, height: 512, alt: `ELYIO guide to ${legacy.name}` }] }, twitter: { card: "summary_large_image", title, description: legacy.intro[l], images: ["/icons/icon-512.png"] } };
}

export default async function MuseumPage({ params }: { params: Promise<{ locale: string; slug: string }> }) {
  const { locale, slug } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) notFound();
  const l = locale as SeoLocale;
  const v1 = museumV1BySlug(slug);
  const legacy = legacyMuseumBySlug(slug);
  if (!v1 && !legacy) notFound();
  const t = chrome[l];

  if (v1) return <V1MuseumPage v1={v1} locale={l} t={t} />;
  return <LegacyMuseumPage legacy={legacy!} locale={l} t={t} />;
}

function V1MuseumPage({ v1, locale: l, t }: { v1: NonNullable<ReturnType<typeof museumV1BySlug>>; locale: SeoLocale; t: ChromeCopy }) {
  const v = l as V1Locale;
  const content = v1.locales[v];
  const visitHref = museumVisitHref(v1, v);
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "Museum", name: v1.name[v], url: `${SITE_URL}/${l}/museums/${v1.slug}`, address: { "@type": "PostalAddress", addressLocality: v1.city, addressCountry: v1.country }, sameAs: v1.website, description: content.metaDescription },
      { "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "ELYIO", item: `${SITE_URL}/${l}` }, { "@type": "ListItem", position: 2, name: t.museums, item: `${SITE_URL}/${l}/museums` }, { "@type": "ListItem", position: 3, name: v1.name[v], item: `${SITE_URL}/${l}/museums/${v1.slug}` }] },
      { "@type": "FAQPage", mainEntity: content.faq.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })) },
    ],
  };
  const archetype = getArchetype(v1.slug);
  return (
    <>
      <SeoNav locale={l} path={`/museums/${v1.slug}`} />
      <main className={`mg-main mg-archetype-${archetype}`}>
        <nav className="mg-breadcrumbs"><Link href={`/${l}`}>ELYIO</Link> / <Link href={`/${l}/museums`}>{t.museums}</Link> / {v1.name[v]}</nav>
        <section className="mg-hero" data-variant={v1.artDirection.layoutVariant}>
          <div className="mg-hero-inner">
            <p className="mg-kicker"><span className="mg-dot" />{v1.city} · {v1.country}</p>
            <h1>{content.heroHeadline}</h1>
            <p className="mg-hero-subhead">{content.heroSubhead}</p>
            <div className="mg-hero-actions">
              <Link className="mg-cta-primary" href={visitHref} data-ga-begin-visit="museum-hero">{content.heroCta}</Link>
            </div>
          </div>
        </section>

        <section className="mg-problem">
          {content.problem.map((p, i) => <p key={i}>{p}</p>)}
        </section>

        <section>
          <h2 className="mg-section-heading">{t.whatToSee}</h2>
          <p className="mg-lede">{content.whatToSeeIntro}</p>
          <div className="mg-what-grid">
            {content.whatToSeeItems.map((item, i) => (
              <div className="mg-what-item" key={i}><h3>{item.name}</h3><p>{item.blurb}</p></div>
            ))}
          </div>
        </section>

<section className="mg-masterpieces">
           <h2 className="mg-section-heading">{t.masterpieces}</h2>
           {content.masterpieces.slice(0, 5).map((mp, i) => (
             <article className="mg-masterpiece" key={i}>
               <MuseumMasterpieceImage src={mp.imageCommonsUrl} alt={mp.imageAlt} title={mp.title} artist={mp.artist} />
               <div>
                 <p className="mg-masterpiece-eyebrow">{mp.artist} · {mp.year}</p>
                 <h3>{mp.title}</h3>
                 <p className="mg-masterpiece-hook">{mp.hook}</p>
                 <p className="mg-masterpiece-context">{mp.context}</p>
               </div>
             </article>
           ))}
         </section>

        <section className="mg-explore">
          <div><h3>{t.explore}</h3><p>{content.howToExplore}</p></div>
          <div><h3>{t.selfGuided}</h3><p>{content.selfGuided}</p></div>
        </section>

        <section>
          <h2 className="mg-section-heading">{t.comparison}</h2>
          <div className="mg-comparison">
            <div className="mg-comparison-col"><h4>{t.traditional}</h4><ul>{content.comparisonTraditional.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
            <div className="mg-comparison-col mg-elyio"><h4>{t.withElyio}</h4><ul>{content.comparisonElyio.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
          </div>
        </section>

        <section className="mg-practical">
          <p>{content.practicalNotes}</p>
        </section>

        <section className="mg-faq">
          <h2 className="mg-section-heading">{t.faq}</h2>
{content.faq.map((f, i) => (
             <details key={i}><summary>{f.q}</summary><p>{f.a}</p></details>
           ))}
         </section>

        <section className="mg-related">
          <h2 className="mg-section-heading">Continue exploring {v1.city}</h2>
          <div className="mg-related-grid">
            {getRelatedMuseums(v1.slug, l).map(({ slug, name }) => (
              <Link key={slug} className="mg-related-link" href={`/${l}/museums/${slug}`}>{name}</Link>
            ))}
          </div>
        </section>

        <section className="mg-final-cta">
          <h2>{content.finalCtaHeadline}</h2>
          <Link className="mg-cta-primary" href={visitHref} data-ga-begin-visit="museum-final">{content.finalCtaLabel}</Link>
        </section>

        <p className="mg-disclosure">{t.disclosure}</p>
      </main>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </>
  );
}

function LegacyMuseumPage({ legacy: m, locale: l, t }: { legacy: NonNullable<ReturnType<typeof legacyMuseumBySlug>>; locale: SeoLocale; t: ChromeCopy }) {
  const works = artworks.filter((a) => a.museumId === m.id).slice(0, 8);
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "Museum", name: m.name, url: `${SITE_URL}/${l}/museums/${m.slug}`, address: { "@type": "PostalAddress", addressLocality: m.city, addressCountry: "FR" }, sameAs: m.website, description: m.intro[l] },
      { "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "ELYIO", item: `${SITE_URL}/${l}` }, { "@type": "ListItem", position: 2, name: t.museums, item: `${SITE_URL}/${l}/museums` }, { "@type": "ListItem", position: 3, name: m.name, item: `${SITE_URL}/${l}/museums/${m.slug}` }] },
    ],
  };
  const visitHref = `/visit?from=organic&locale=${l}&landing=${encodeURIComponent(`museum:${m.slug}`)}`;
  const ctaLabel = l === "fr" ? `Explorer ${m.name} avec ELYIO` : l === "zh-hans" ? `用 ELYIO 探索${m.name}` : `Explore ${m.name} with ELYIO`;
  return (
    <>
      <SeoNav locale={l} path={`/museums/${m.slug}`} />
      <main className="mg-main">
        <nav className="mg-breadcrumbs"><Link href={`/${l}`}>ELYIO</Link> / <Link href={`/${l}/museums`}>{t.museums}</Link> / {m.name}</nav>
        <section className="mg-hero" data-variant="A">
          <div className="mg-hero-inner">
            <p className="mg-kicker"><span className="mg-dot" />{m.city} · ELYIO CURATED</p>
            <h1>{m.name}</h1>
            <p className="mg-hero-subhead">{m.intro[l]}</p>
            <div className="mg-hero-actions"><Link className="mg-cta-primary" href={visitHref} data-ga-begin-visit="museum-hero">{ctaLabel}</Link></div>
          </div>
        </section>
        <section className="mg-problem"><p>{m.focus[l]}</p></section>
        <section>
          <h2 className="mg-section-heading">{t.whatToSee}</h2>
          <p className="mg-lede">{m.highlights[l]}</p>
        </section>
        {works.length > 0 && (
          <section style={{ marginBottom: 60 }}>
            <h2 className="mg-section-heading">{t.supportedStories}</h2>
            <div className="mg-museum-cards">
              {works.map((a) => (
                <Link className="mg-museum-card" key={a.id} href={`/${l}/artworks/${a.slug}`}>
                  <h3>{a.title[l === "zh-hans" ? "zh-Hans" : l]}</h3>
                </Link>
              ))}
            </div>
          </section>
        )}
        <section className="mg-final-cta">
          <h2>{ctaLabel}</h2>
          <Link className="mg-cta-primary" href={visitHref} data-ga-begin-visit="museum-final">{ctaLabel}</Link>
        </section>
        <p className="mg-disclosure">{t.disclosure}</p>
      </main>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </>
  );
}
