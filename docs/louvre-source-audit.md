# Louvre Collections (collections.louvre.fr) — Phase 0 Source Audit

Date: 2026-08-11. Investigated live via `curl` (User-Agent: `AURA-MVP-backend/1.0
(contact: repo owner; research/museum-app project)`) and Chrome browser/network
inspection. No bulk fetching performed — one sample record fetched twice, one
sitemap sub-file inspected, search UI exercised a handful of times.

## 1. How search pagination works

`https://collections.louvre.fr/en/recherche?q=<term>` is a server-rendered
results page (no separate XHR/JSON search API observed in the network log —
the initial document response already contains the rendered results and a
"page X/Y" title). A `page`-style querystring parameter did **not** reliably
reproduce page 2 when set by hand (`?q=...&p=2` silently reset to page 1 in
one test); the in-page "next page" button also did not visibly advance state
in a quick test. This looks like client-side-JS-assisted pagination
(`searchMain.js`/`searchSimple.js` were loaded) rather than a clean GET-param
contract. **Not fully reverse-engineered** — see §9, it turned out to be
unnecessary.

## 2. Official "Export .csv" functionality

Not tested directly — **`robots.txt` explicitly disallows `/search/export`
for all user agents** (see §13). Per the task's own explicit instruction
("do not bypass access controls"), this endpoint was not probed or called.

## 3. Whether CSV export has a result limit

Unknown — not tested, per §2.

## 4. Whether a single export can contain the complete result set

Unknown — not tested, per §2.

## 5. What HTTP endpoint the export button calls

Unknown — not tested, per §2 (would require triggering the disallowed
`/search/export` path to observe).

## 6. What query parameters the export endpoint accepts

Unknown — not tested, per §2.

## 7. Whether different collections/departments can be exported separately

Unknown — not tested, per §2. However: department-level filtering **is**
visible in the *record* data itself (`collection` field, e.g. "Département
des Arts de Byzance et des chrétientés en Orient" — see §11), so
department-level segmentation is achievable downstream even without the
export feature.

## 8. Whether there is an official bulk dataset/download endpoint

No dedicated open-data/API page found (`/en/page/opendata`, `/en/page/api`,
`/opendata` all 404). No developer documentation discovered. The closest
thing to an "official enumeration mechanism" is the sitemap (§9).

## 9. Whether sitemap(s) expose collection ARK URLs — YES, this is the answer

`https://collections.louvre.fr/sitemap.xml` is a sitemap **index** listing 26
sub-sitemaps (`sitemap0.xml` .. `sitemap25.xml`). Not disallowed by
`robots.txt`. Inspected `sitemap0.xml`: 40,010 `<loc>` entries, of which
120,000 raw substring-matches on `ark:` — each unique record appears ~6 times
(fr canonical + en canonical + hreflang alternates for both), so **~20,000
unique ARK records per sub-sitemap**. Extrapolated across all 26 sub-sitemaps:
**roughly 500,000+ unique records total**, consistent with the ballpark this
task itself anticipated.

**This is the enumeration mechanism to use** — not the disallowed CSV export,
and not a fragile reverse-engineered search-pagination contract.

## 10. Another documented machine-readable enumeration mechanism

None found beyond the sitemap.

## 11. Exact JSON structure of an artwork `.json` endpoint — CONFIRMED

Pattern confirmed: appending `.json` to any ARK permalink returns
`Content-Type: application/json`, HTTP 200.

```
https://collections.louvre.fr/ark:/53355/cl010000780
  -> https://collections.louvre.fr/ark:/53355/cl010000780.json
```

Two real records inspected in full (see `docs/louvre-schema.md` companion
notes / raw samples in scratch space):

**Example A — not on display** (`cl010000780`, a Byzantine/Roman-era terracotta
figurine, inv. E 15429):
- `currentLocation: "non exposé"` (French: "not on display"), `room: ""`
- `creator: []` (anonymous work)
- Full provenance chain: `previousOwner`, `acquisitionDetails`,
  `objectHistory`, `placeOfDiscovery`, `bibliography`

**Example B — on display** (`cl010066107`, Leonardo da Vinci, "The Virgin and
Child with Saint Anne", inv. INV 776 — matches our earlier Wikidata-sourced
Top 100 candidate list):
- `currentLocation: "Denon, [Peint] Salle 710 - Grande Galerie, Salle 710 -
  (2e travée)"`, `room: "Salle 710, Aile Aile Denon, Niveau 1"`
- `creator: [{label: "Léonard de Vinci...", wikidata: ...}]` — creator
  objects can carry a `wikidata` QID directly, a useful cross-reference
- 20 separate `image[]` entries (multiple photography sessions/angles/details
  over the years), **each with its own `copyright` string** that varies by
  year and photographer (e.g. "© 2012 GrandPalaisRmn (musée du Louvre) /
  René-Gabriel Ojéda" vs "© 2007 Musée du Louvre, Dist. GrandPalaisRmn /
  Angèle Dequier")

**Key fields observed** (non-exhaustive, see raw JSON for full shape):
`arkId`, `url`, `modified`, `title`, `titleComplement`, `denominationTitle[]`,
`displayDateCreated`, `currentLocation`, `room`,
`isMuseesNationauxRecuperation`, `dateCreated[]` (structured `startYear`/
`endYear`/`text`/`doubt`), `creator[]` (`label`, `attributionLevel`,
`linkType`, `dates[]`, `wikidata`), `objectNumber[]` (inventory number(s),
typed), `collection` (department name), `description`, `inscriptions`,
`dimension[]` (typed: Hauteur/Largeur/Profondeur, with unit + display
string), `materialsAndTechniques`, `placeOfCreation`, `placeOfDiscovery`,
`provenance`, `historicalContext[]`, `objectHistory`, `previousOwner[]`,
`acquisitionDetails[]`, `ownedBy`, `heldBy`, `longTermLoanTo`, `index`
(faceted search terms), `bibliography[]`, `exhibition[]`, `relatedWork[]`,
`image[]` (`urlImage`, `urlThumbnail`, `copyright`, `type`, `position`).

**This directly answers the on-display-status requirement**: `currentLocation`
is the Louvre's own authoritative field for this. A literal value of "non
exposé" is an explicit, high-confidence "not on display" signal; a populated
room/wing/gallery string is an explicit, high-confidence "on display" signal.
No inference needed — the museum tells us directly.

## 12. Terms of Use / reuse restrictions — READ IN FULL, see below (critical)

`https://collections.louvre.fr/en/page/cgu`, last updated 2026-03-19. Full
text captured. Key points:

**Text content (Article 4.1.2)**: entry text (titles, descriptions, dates,
etc.) is published under France's **Etalab Open Licence** — comparable to
CC-BY. Explicitly permits commercial and non-commercial reuse, reproduction,
adaptation, and combination with other data, on condition of attribution
(source + last-update date). **This clears Layer-1 factual text for our
use.**

**Images — copyright-protected works (Article 4.1.1.1)**: some Louvre-held
works are themselves still under copyright (named examples: Anselm Kiefer,
Elias Crespin, Cy Twombly, François Morellet, Georges Braque, Jean-Michel
Othoniel, Joseph Kosuth, I. M. Pei, "and all photographic works labelled
ADAGP" — non-exhaustive). Reproducing a photograph of these requires prior
authorization from the copyright holder, obtained by the user. **Explicit
AI-specific clause**: "The ADAGP expressly prohibits the reproduction of
works belonging to its repertory and related data... in order to perform
text mining or data mining, especially when these mining operations are
intended to feed or train artificial intelligence tools designed or adapted
to generate creations." This is a direct, named prohibition relevant to us as
an AI product — any ADAGP-repertory artist must be excluded outright, not
just flagged low-confidence. In practice this affects a small, identifiable
slice of the collection (mostly 20th-century+ named artists), not the
Old-Masters/antiquities core of a "Top 100 by significance" set — but must be
checked per artist, not assumed.

**Images — non-copyright-protected (public-domain) works (Article
4.1.1.2)**: free re-use is granted **only** for an exhaustively-listed set of
purposes: museographic/pedagogic/scientific activities (exhibition labels,
guided tours, workshops, teaching, symposia), publication of catalogues/
scientific papers/theses (EU publishers, ≤1500 copies), and "digital
scientific and educational publications" — each requiring photo credit +
permalink back to the record. **Anything outside that list — explicitly
including commercial use — requires a paid license from Rmn-GP** (the
Réunion des musées nationaux–Grand Palais photo agency), via
`photo.rmn.fr` or `agence_photo@rmngp.fr`.

**This is the single biggest open question for this project**: does ELYIO —
a consumer app doing AI-based visual-recognition matching against these
images, with a commercial trajectory — fit inside "digital scientific and
educational publications," or does it require a paid Rmn-GP license? The
Terms of Use do not define that phrase precisely enough to self-certify with
confidence, and self-certifying incorrectly on a national museum's copyright
terms is not a call I'm willing to make unilaterally. **Flagging this for
your explicit decision before any image is downloaded, cached, or served for
recognition matching** — this is a real legal/business decision, not an
engineering one.

Also relevant: **Article 5 explicitly forbids deep-linking / embedding** —
"pages from the collections website must not be embedded within the pages of
another site" and content must open "in a new window." Directly hotlinking
Louvre-hosted image URLs from inside the ELYIO app would likely violate this;
if we go forward with images at all, they'd need to be legitimately
downloaded (within whatever license basis applies) and re-served from our own
infrastructure, not hotlinked.

## 13. Rate-limit / crawling guidance — robots.txt (critical)

Full `robots.txt`:

```
Sitemap: https://collections.louvre.fr/sitemap.xml

User-agent: *
Disallow: /search/export

# Bloque les IA
User-agent: GPTBot
Disallow: /*.jpg$
Disallow: /*.jpeg$
Disallow: /*.png$
Disallow: /*.webp$

User-agent: ChatGPT-User
Disallow: /*.jpg$ [...same pattern...]
User-agent: anthropic-ai
Disallow: /*.jpg$ [...same pattern...]
User-agent: ClaudeBot
Disallow: /*.jpg$ [...same pattern...]
User-agent: CCBot / Amazonbot / Bytespider / Applebot / Sogou web spider /
Google-Extended / FacebookBot / omgili
Disallow: /*.jpg$ [...same pattern, each...]
```

Two findings, both important:

1. **`/search/export` is disallowed for every user agent, unconditionally.**
   No automated CSV export is permitted by the site's own published policy.
   This rules out the CSV-export approach hypothesized in the original task
   spec entirely — not just "risky," actually disallowed.

2. **The site explicitly, by name, blocks `anthropic-ai` and `ClaudeBot`
   (among other named AI crawlers) from fetching image files**, under a
   comment that translates to "Blocks the AIs." My actual requests in this
   audit used a custom User-Agent (`AURA-MVP-backend/1.0`), not the literal
   string `ClaudeBot` or `anthropic-ai` — so no `robots.txt` rule was
   technically triggered by anything fetched so far (record `.json` and
   sitemap XML are not image files, and aren't disallowed for `*` either).
   But the *intent* is unambiguous: the Louvre does not want Anthropic-built
   AI systems bulk-harvesting its images. I am Claude, built by Anthropic,
   acting as an agent. Deliberately using a different User-Agent string to
   route around a rule that specifically and by name targets systems like me
   would be circumventing an access control, which the task's own
   instructions explicitly forbid ("do not bypass access controls," "if
   Louvre signals that automated harvesting is not permitted, STOP and
   report it"). **I'm treating this as exactly that signal and stopping
   before fetching any image bytes, pending your explicit decision.**

No `Crawl-delay` directive is present in `robots.txt`, and no separate
rate-limit documentation was found anywhere on the site.

## 14. Image rights/copyright behavior

Covered in full under §12. Summary: rights are **not inferable from artwork
age** — confirmed directly in the data (Example B above has 20 separate image
entries spanning 2004–2012, each independently copyrighted to
GrandPalaisRmn/named photographers, for a 500-year-old public-domain
painting). Every `image[]` entry carries its own `copyright` string that must
be read and respected per-image, never assumed.

---

## Summary of what changes the plan

1. **Enumeration**: use the sitemap (§9), not search pagination (§1,
   unresolved and unnecessary) or CSV export (§2–7, explicitly disallowed).
2. **Per-record data**: the `<ark>.json` endpoint (§11) is rich, well
   -structured, and already gives us most of the proposed schema fields
   directly — including a genuine on-display signal (`currentLocation`) that
   needs no inference.
3. **Text content**: clear to use under the Etalab Open Licence (§12) —
   Layer-1 facts are not blocked.
4. **Images are the open question**, on two independent fronts:
   - **Legal**: our use case (commercial AI recognition app) does not
     obviously fit the Terms of Use's free-reuse bucket (§12) — may require
     a paid Rmn-GP license, and ADAGP-repertory artists must be excluded
     outright regardless.
   - **robots.txt intent**: an explicit, named block on Anthropic/Claude bots
     fetching image files (§13) — a signal I'm not willing to route around
     with a different User-Agent string without your explicit sign-off.

Per the task's own "STOP and report" instruction: **I'm pausing here.** No
image has been downloaded (only two `.json` metadata records and one sitemap
sub-file were fetched, both permitted). No importer, schema, or 100-record
test has been built yet — that's Phase 1/2, and building it before this is
resolved would bake in an assumption about image handling that isn't mine to
make.
