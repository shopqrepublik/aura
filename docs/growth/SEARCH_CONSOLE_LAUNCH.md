# ELYIO Search Console Launch — Museum Acquisition Network V1

**Production:** https://www.elyio.co
**Sitemap to submit:** https://www.elyio.co/sitemap.xml
**Verified live:** 2026-09-07 — 435 URLs, 78 museum detail + 3 museum index URLs, 0 duplicates, all canonical host, 81/81 HTTP 200, 0 noindex, 0 robots-blocked, self-referencing canonicals, full en/fr/zh-Hans hreflang clusters (head `<link>` + sitemap `xhtml:link`).

## Property

- URL-prefix or Domain property for `www.elyio.co` (do NOT create duplicates — use the existing property if one exists).
- Submit `https://www.elyio.co/sitemap.xml` under Sitemaps. Expect ~435 discovered URLs.

## Priority URL Inspection (~14 pages — do NOT bulk-request all 81)

EN:
- https://www.elyio.co/en/museums
- https://www.elyio.co/en/museums/musee-du-louvre
- https://www.elyio.co/en/museums/musee-d-orsay
- https://www.elyio.co/en/museums/musee-de-l-orangerie
- https://www.elyio.co/en/museums/national-gallery-london
- https://www.elyio.co/en/museums/the-met
- https://www.elyio.co/en/museums/rijksmuseum
- https://www.elyio.co/en/museums/va-london
- https://www.elyio.co/en/museums/getty

FR:
- https://www.elyio.co/fr/museums
- https://www.elyio.co/fr/museums/musee-du-louvre
- https://www.elyio.co/fr/museums/musee-d-orsay

ZH-HANS:
- https://www.elyio.co/zh-hans/museums
- https://www.elyio.co/zh-hans/museums/musee-du-louvre

Note: the V&A slug is `va-london` (not `victoria-and-albert-museum`). Always use production slugs from the live sitemap.

## First-30-day monitoring

1. **Coverage:** museum pages move from "Discovered – currently not indexed" to "Indexed". 3–5 image stories per page are server-rendered — no JS rendering bottlenecks expected.
2. **Enhancements:** FAQ (`FAQPage` JSON-LD) rich-result eligibility per museum page; `Museum` + `BreadcrumbList` entity association.
3. **Performance:** track queries from `docs/growth/MUSEUM_KEYWORD_MAP.md` clusters (e.g. "louvre self guided tour", "que voir au louvre", Orsay/Van Gogh, Rijksmuseum/Night Watch). Collect impression data BEFORE building any V2 child clusters (`/what-to-see`, artwork pages, etc.).
4. **Images:** `/_next/image` optimizer URLs are not in the sitemap (by design — local `/images/museums/*` originals are same-origin and crawlable via `<img>`); monitor image impressions separately.
5. **Core Web Vitals:** 27MB of local artwork assets are lazy-loaded below the fold with explicit dimensions (no CLS); watch LCP on Louvre/Orsay hero-adjacent stories.
6. **Hreflang:** no "no return tags" errors expected — every museum URL carries en/fr/zh-Hans/x-default both in `<head>` and sitemap; FR/ZH canonicalize to themselves, never to EN.

## What NOT to do yet

- No V2 SEO child pages until query data arrives.
- No manual indexing requests beyond the priority set above.
- No robots.txt loosening (`/visit`, `/admin`, `/api` stay disallowed).
