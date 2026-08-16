import {sitemapUrlsText} from "@/lib/sitemap-xml";

export const dynamic="force-static";

export function GET(){
  return new Response(sitemapUrlsText(),{headers:{"Content-Type":"text/plain; charset=utf-8","Cache-Control":"public, max-age=3600, s-maxage=86400"}});
}
