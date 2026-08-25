import type { Metadata } from "next";
import { notFound } from "next/navigation";
import LandingPage from "@/components/landing/LandingPage";
import { LOCALES, SITE_URL, alternatesFor, type SeoLocale } from "@/lib/seo-content";

const metadataCopy = {
  en: { title: "ELYIO — AI Museum Guide for France | Identify Art, Discover Its Story", description: "Explore French museums with ELYIO. Identify an artwork, understand its story, notice the details and see carefully labelled value context." },
  fr: { title: "ELYIO — Guide IA des musées de France | Identifier et comprendre l’art", description: "Explorez les musées français avec ELYIO. Identifiez une œuvre, comprenez son histoire, observez ses détails et découvrez un contexte de valeur clairement expliqué." },
  "zh-hans": { title: "ELYIO — 法国博物馆 AI 导览 | 识别艺术，读懂故事", description: "使用 ELYIO 探索法国博物馆：识别艺术品、理解故事，并查看明确说明的价值背景。" },
} as const;

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) return {};
  const copy = metadataCopy[locale as SeoLocale];
  return { title: copy.title, description: copy.description, alternates: alternatesFor(`/${locale}`), openGraph: { title: copy.title, description: copy.description, url: `${SITE_URL}/${locale}`, siteName: "ELYIO", type: "website", images: [{ url: "/icons/icon-512.png", width: 512, height: 512, alt: "ELYIO museum guide" }] }, twitter: { card: "summary_large_image", title: copy.title, description: copy.description, images: ["/icons/icon-512.png"] } };
}

export default async function LocaleHome({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) notFound();
  const selectedLocale = locale as SeoLocale;
  const jsonLd = { "@context": "https://schema.org", "@graph": [{ "@type": "Organization", "@id": `${SITE_URL}/#organization`, name: "ELYIO", url: SITE_URL, logo: `${SITE_URL}/icons/icon-512.png` }, { "@type": "WebApplication", name: "ELYIO", url: `${SITE_URL}/${selectedLocale}`, applicationCategory: "TravelApplication", operatingSystem: "Web", description: metadataCopy[selectedLocale].description, publisher: { "@id": `${SITE_URL}/#organization` } }] };
  return <><LandingPage locale={selectedLocale} /><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} /></>;
}
