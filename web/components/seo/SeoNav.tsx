import Link from "@/components/seo/SeoLink";
import type { SeoLocale } from "@/lib/seo-content";
import { localeNames } from "@/lib/seo-content";

// `path` is the locale-invariant suffix of the current page (e.g. "/museums",
// "/museums/musee-du-louvre", "/artworks/some-slug", or "" for the locale
// homepage). Passing it lets the language switcher preserve the current
// museum/artwork instead of bouncing back to the homepage — required so a
// visitor switching FR -> ZH-Hans on a museum page lands on the same museum.
export default function SeoNav({ locale, path = "" }: { locale: SeoLocale; path?: string }) {
  return <header className="seo-nav">
    <Link className="seo-logo" href={`/${locale}`}>ELYIO</Link>
    <nav aria-label="Main navigation">
      <Link href={`/${locale}/museums`}>{locale === "fr" ? "Musées" : locale === "zh-hans" ? "博物馆" : "Museums"}</Link>
      <Link className="seo-start" data-ga-begin-visit="direct" href={`/visit?from=organic&locale=${locale}`}>{locale === "fr" ? "Commencer la visite" : locale === "zh-hans" ? "开始参观" : "Begin your visit"}</Link>
    </nav>
    <div className="seo-langs" aria-label="Language">{(["en","fr","zh-hans"] as const).map((l)=><Link key={l} href={`/${l}${path}`} hrefLang={l === "zh-hans" ? "zh-Hans" : l} aria-current={l===locale?"page":undefined}>{localeNames[l]}</Link>)}</div>
  </header>;
}
