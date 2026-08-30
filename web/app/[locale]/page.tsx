import type { Metadata } from "next";
import { notFound } from "next/navigation";
import LandingPage from "@/components/landing/LandingPage";
import { LOCALES, SITE_URL, alternatesFor, type SeoLocale } from "@/lib/seo-content";

const metadataCopy = {
  en: { title: "ELYIO — AI Museum Guide for Art & Museums", description: "Point your camera at an artwork and ELYIO helps you recognize it, understand the story behind it, and explore museums from Paris to New York and beyond." },
  fr: { title: "ELYIO — Votre compagnon IA pour les musées du monde", description: "Pointez votre appareil photo vers une œuvre : ELYIO vous aide à la reconnaître, à comprendre son histoire et à explorer les musées de Paris à New York et au-delà." },
  "zh-hans": { title: "ELYIO — 全球博物馆 AI 艺术伴侣", description: "用相机对准艺术品，ELYIO 帮助您识别作品、了解背后的故事，并探索从巴黎到纽约及更远的博物馆。" },
} as const;

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) return {};
  const copy = metadataCopy[locale as SeoLocale];
  const canonicalPath = locale === "en" ? "/" : `/${locale}`;
  return { title: copy.title, description: copy.description, alternates: alternatesFor(canonicalPath), openGraph: { title: "ELYIO — Your AI Museum Companion", description: "See an artwork. Point your camera. Discover what you’re looking at and why it matters.", url: `${SITE_URL}${canonicalPath}`, siteName: "ELYIO", type: "website", images: [{ url: "/icons/icon-512.png", width: 512, height: 512, alt: "ELYIO AI museum companion" }] }, twitter: { card: "summary_large_image", title: "ELYIO — Your AI Museum Companion", description: "See an artwork. Point your camera. Discover what you’re looking at and why it matters.", images: ["/icons/icon-512.png"] } };
}

export default async function LocaleHome({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) notFound();
  const selectedLocale = locale as SeoLocale;
  const jsonLd = { "@context": "https://schema.org", "@graph": [{ "@type": "Organization", "@id": `${SITE_URL}/#organization`, name: "ELYIO", url: SITE_URL, logo: `${SITE_URL}/icons/icon-512.png` }, { "@type": "WebApplication", name: "ELYIO", url: `${SITE_URL}/${selectedLocale}`, applicationCategory: "TravelApplication", operatingSystem: "Web", description: metadataCopy[selectedLocale].description, publisher: { "@id": `${SITE_URL}/#organization` } }] };
  return <><LandingPage locale={selectedLocale} /><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} /></>;
}
