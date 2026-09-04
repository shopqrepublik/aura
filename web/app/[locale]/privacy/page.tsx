import { notFound } from "next/navigation";
import PrivacyContent from "@/components/PrivacyContent";
import { LOCALES, type SeoLocale, alternatesFor, SITE_URL } from "@/lib/seo-content";
export function generateStaticParams() { return LOCALES.map((locale) => ({ locale })); }
export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) { const { locale } = await params; if (!LOCALES.includes(locale as SeoLocale)) return {}; const l = locale as SeoLocale; const title = l === "fr" ? "Confidentialité — ELYIO" : l === "zh-hans" ? "隐私 — ELYIO" : "Privacy — ELYIO"; return { title, alternates: alternatesFor(`/${l}/privacy`), openGraph: { title, url: `${SITE_URL}/${l}/privacy`, siteName: "ELYIO", type: "website" } }; }
export default async function LocalPrivacyPage({ params }: { params: Promise<{ locale: string }> }) { const { locale } = await params; if (!LOCALES.includes(locale as SeoLocale)) notFound(); return <PrivacyContent locale={locale as SeoLocale} />; }
