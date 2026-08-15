import { notFound } from "next/navigation";
import { LOCALES, type SeoLocale } from "@/lib/seo-content";

export function generateStaticParams() { return LOCALES.map((locale) => ({ locale })); }

export default async function LocaleLayout({ children, params }:{children:React.ReactNode;params:Promise<{locale:string}>}) {
  const { locale } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) notFound();
  return <div lang={locale === "zh-hans" ? "zh-Hans" : locale} className="seo-site">{children}</div>;
}
