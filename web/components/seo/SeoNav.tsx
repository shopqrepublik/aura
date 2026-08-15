import Link from "@/components/seo/SeoLink";
import type { SeoLocale } from "@/lib/seo-content";
import { localeNames } from "@/lib/seo-content";

export default function SeoNav({ locale }: { locale: SeoLocale }) {
  return <header className="seo-nav">
    <Link className="seo-logo" href={`/${locale}`}>ELYIO</Link>
    <nav aria-label="Main navigation">
      <Link href={`/${locale}/museums`}>{locale === "fr" ? "Musées" : locale === "zh-hans" ? "博物馆" : "Museums"}</Link>
      <Link className="seo-start" href={`/visit?from=organic&locale=${locale}`}>{locale === "fr" ? "Commencer la visite" : locale === "zh-hans" ? "开始参观" : "Begin your visit"}</Link>
    </nav>
    <div className="seo-langs" aria-label="Language">{(["en","fr","zh-hans"] as const).map((l)=><Link key={l} href={`/${l}`} hrefLang={l === "zh-hans" ? "zh-Hans" : l} aria-current={l===locale?"page":undefined}>{localeNames[l]}</Link>)}</div>
  </header>;
}
