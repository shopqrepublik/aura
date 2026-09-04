import { notFound } from "next/navigation";
import PrivacyContent from "@/components/PrivacyContent";
import { LOCALES, type SeoLocale } from "@/lib/seo-content";
export function generateStaticParams() { return LOCALES.map((locale) => ({ locale })); }
export default async function LocalPrivacyPage({ params }: { params: Promise<{ locale: string }> }) { const { locale } = await params; if (!LOCALES.includes(locale as SeoLocale)) notFound(); return <PrivacyContent locale={locale as SeoLocale} />; }
