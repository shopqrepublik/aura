import type {Metadata} from "next";
import Image from "next/image";
import Link from "@/components/seo/SeoLink";
import {notFound} from "next/navigation";
import SeoNav from "@/components/seo/SeoNav";
import {LOCALES,SITE_URL,alternatesFor,artworkBySlug,artworks,localizedArtwork,museumForArtwork,type SeoLocale} from "@/lib/seo-content";

const proxy=(url:string)=>`https://api.elyio.co/v1/image-proxy?url=${encodeURIComponent(url)}`;
export function generateStaticParams(){return LOCALES.flatMap(locale=>artworks.filter(a=>a.readiness==="SEO_READY_CURATED").map(a=>({locale,slug:a.slug})))}
export const dynamicParams=true;

export async function generateMetadata({params}:{params:Promise<{locale:string;slug:string}>}):Promise<Metadata>{
  const{locale,slug}=await params,a=artworkBySlug(slug);if(!a||!LOCALES.includes(locale as SeoLocale))return{};
  const l=locale as SeoLocale,x=localizedArtwork(a,l),m=museumForArtwork(a);
  const title=l==="fr"?`${x.title} — Histoire et détails à observer | ELYIO`:l==="zh-hans"?`${x.title} — 故事、意义与观看细节 | ELYIO`:`${x.title} — Story, Meaning & What to Look For | ELYIO`;
  const description=`${a.artist}, ${x.title}${a.year?` (${a.year})`:""}, ${m.name}. ${x.why}`.slice(0,260),image=proxy(a.imageUrl);
  return{title,description,alternates:alternatesFor(`/${l}/artworks/${slug}`),openGraph:{title,description,url:`${SITE_URL}/${l}/artworks/${slug}`,type:"article",siteName:"ELYIO",images:[{url:image,alt:`${x.title} by ${a.artist}`}]},twitter:{card:"summary_large_image",title,description,images:[image]}};
}

export default async function ArtworkPage({params}:{params:Promise<{locale:string;slug:string}>}){
  const{locale,slug}=await params,a=artworkBySlug(slug);if(!a||a.readiness!=="SEO_READY_CURATED"||!LOCALES.includes(locale as SeoLocale))notFound();
  const l=locale as SeoLocale,x=localizedArtwork(a,l),m=museumForArtwork(a),related=artworks.filter(r=>r.museumId===a.museumId&&r.id!==a.id).slice(0,5),url=`${SITE_URL}/${l}/artworks/${a.slug}`,image=proxy(a.imageUrl);
  const jsonLd={"@context":"https://schema.org","@graph":[{"@type":"VisualArtwork",name:x.title,creator:{"@type":"Person",name:a.artist},dateCreated:a.year,image:{"@type":"ImageObject",contentUrl:image,caption:`${x.title} by ${a.artist}`},isPartOf:{"@type":"Museum",name:m.name,url:`${SITE_URL}/${l}/museums/${m.slug}`},description:x.why,url},{"@type":"BreadcrumbList",itemListElement:[{"@type":"ListItem",position:1,name:"ELYIO",item:`${SITE_URL}/${l}`},{"@type":"ListItem",position:2,name:m.name,item:`${SITE_URL}/${l}/museums/${m.slug}`},{"@type":"ListItem",position:3,name:x.title,item:url}]}]};
  return <><SeoNav locale={l}/><main className="seo-content"><nav className="seo-breadcrumbs"><Link href={`/${l}`}>ELYIO</Link> / <Link href={`/${l}/museums/${m.slug}`}>{m.name}</Link> / {x.title}</nav><div className="seo-artwork-hero"><div className="seo-artwork-image"><Image src={image} alt={`${x.title} — ${a.artist}`} fill priority fetchPriority="high" sizes="(max-width: 760px) calc(100vw - 48px), 520px" quality={78}/></div><div><p className="seo-kicker">{m.name} · {a.year}</p><h1>{x.title}</h1><p className="seo-lede">{a.artist}</p><p>{x.why}</p></div></div><h2>{l==="fr"?"Pourquoi cette œuvre compte":l==="zh-hans"?"为何重要":"Why it matters"}</h2><p>{x.why}</p><h2>{l==="fr"?"Regardez de plus près":l==="zh-hans"?"仔细观察":"Look closer"}</h2><p>{x.where}</p><p>{x.rarity}</p>{a.estimate&&<><h2>{l==="fr"?"Contexte de valeur":l==="zh-hans"?"价值背景":"Value context"}</h2><p>{l==="fr"?`ELYIO situe cette œuvre dans une fourchette éditoriale indicative de ${a.estimate.low} à ${a.estimate.high} millions d’euros.`:l==="zh-hans"?`ELYIO 为这件作品提供的编辑性参考区间为 ${a.estimate.low} 至 ${a.estimate.high} 百万欧元。`:`ELYIO places this work in an indicative editorial context of €${a.estimate.low}–${a.estimate.high} million.`}</p><p className="seo-disclaimer">{l==="fr"?"L’œuvre de musée n’est pas à vendre. Il s’agit d’un contexte indicatif ELYIO, et non d’une expertise, d’une valeur d’assurance ou d’une offre.":l==="zh-hans"?"博物馆作品并非待售。这是 ELYIO 的参考性背景，并非鉴定估价、保险价值或出售报价。":"The museum work is not for sale. This is ELYIO indicative context—not an appraisal, insurance value or offer."}</p></>}<h2>{l==="fr"?"Poursuivre la visite":l==="zh-hans"?"继续探索":"Continue exploring"}</h2><p><Link href={`/${l}/museums/${m.slug}`}>{m.name}</Link></p><div className="seo-related">{related.map(r=><Link key={r.id} href={`/${l}/artworks/${r.slug}`}>{localizedArtwork(r,l).title}</Link>)}</div><p><Link className="seo-primary" href={`/visit?from=organic&locale=${l}&landing=artwork:${a.slug}`}>{l==="fr"?"Utiliser ELYIO au musée":l==="zh-hans"?"在博物馆使用 ELYIO":"Use ELYIO in the museum"}</Link></p></main><script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify(jsonLd)}}/></>;
}
