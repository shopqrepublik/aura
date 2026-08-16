import {LOCALES,SITE_URL,artworks,museums} from "@/lib/seo-content";
const esc=(s:string)=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const langs=(suffix:string)=>LOCALES.map(l=>`<xhtml:link rel="alternate" hreflang="${l==="zh-hans"?"zh-Hans":l}" href="${SITE_URL}/${l}${suffix}"/>`).join("")+`<xhtml:link rel="alternate" hreflang="x-default" href="${SITE_URL}/en${suffix}"/>`;
const url=(loc:string,suffix:string,image?:{loc:string;title:string})=>`<url><loc>${esc(loc)}</loc>${langs(suffix)}${image?`<image:image><image:loc>${esc(image.loc)}</image:loc><image:title>${esc(image.title)}</image:title></image:image>`:""}</url>`;
type SitemapEntry={loc:string;suffix:string;image?:{loc:string;title:string}};
const pageEntries=():SitemapEntry[]=>LOCALES.flatMap(l=>[
  {loc:`${SITE_URL}/${l}`,suffix:""},
  {loc:`${SITE_URL}/${l}/museums`,suffix:"/museums"},
]);
const museumEntries=():SitemapEntry[]=>LOCALES.flatMap(l=>museums.filter(m=>m.readiness==="SEO_READY_CURATED").map(m=>({loc:`${SITE_URL}/${l}/museums/${m.slug}`,suffix:`/museums/${m.slug}`})));
const artworkEntries=():SitemapEntry[]=>LOCALES.flatMap(l=>artworks.filter(a=>a.readiness==="SEO_READY_CURATED").map(a=>({loc:`${SITE_URL}/${l}/artworks/${a.slug}`,suffix:`/artworks/${a.slug}`,image:{loc:a.imageUrl,title:`${a.title[l==="zh-hans"?"zh-Hans":l]} — ${a.artist}`}})));
export const indexableEntries=():SitemapEntry[]=>[...pageEntries(),...museumEntries(),...artworkEntries()];
export const sitemapXml=()=>`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">${indexableEntries().map(entry=>url(entry.loc,entry.suffix,entry.image)).join("")}</urlset>`;
export const sitemapUrlsText=()=>indexableEntries().map(entry=>entry.loc).join("\n")+"\n";
export const pagesSitemap=()=>`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">${LOCALES.flatMap(l=>[url(`${SITE_URL}/${l}`,""),url(`${SITE_URL}/${l}/museums`,"/museums")]).join("")}</urlset>`;
export const museumsSitemap=()=>`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">${LOCALES.flatMap(l=>museums.filter(m=>m.readiness==="SEO_READY_CURATED").map(m=>url(`${SITE_URL}/${l}/museums/${m.slug}`,`/museums/${m.slug}`))).join("")}</urlset>`;
export const artworksSitemap=()=>`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">${LOCALES.flatMap(l=>artworks.filter(a=>a.readiness==="SEO_READY_CURATED").map(a=>url(`${SITE_URL}/${l}/artworks/${a.slug}`,`/artworks/${a.slug}`,{loc:a.imageUrl,title:`${a.title[l==="zh-hans"?"zh-Hans":l]} — ${a.artist}`}))).join("")}</urlset>`;
