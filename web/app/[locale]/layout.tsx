import { notFound } from "next/navigation";
import { LOCALES, type SeoLocale } from "@/lib/seo-content";

export function generateStaticParams() { return LOCALES.map((locale) => ({ locale })); }

export default async function LocaleLayout({ children, params }:{children:React.ReactNode;params:Promise<{locale:string}>}) {
  const { locale } = await params;
  if (!LOCALES.includes(locale as SeoLocale)) notFound();
  const language = locale === "zh-hans" ? "zh-Hans" : locale;
  return <><meta httpEquiv="content-language" content={language}/><script dangerouslySetInnerHTML={{__html:`document.documentElement.lang=${JSON.stringify(language)}`}}/><div lang={language} className="seo-site">{children}</div></>;
}
