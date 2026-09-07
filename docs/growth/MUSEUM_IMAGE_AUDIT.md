# ELYIO Museum Image Audit — V1

**Generated:** 2026-09-07
**Source:** `web/lib/data/museums-v1.json`
**Verify target:** 0 broken images, 0 visible placeholders, 0 raw alt text, 0 unverified images displayed

## Methodology

Every masterpiece in `museums-v1.json` is audited for:
- **Source**: Wikimedia Commons URL (if present) or `NONE` (text-led composition)
- **License**: Wikimedia Commons public domain / CC-BY / CC-BY-SA verified
- **Load status**: HTTP GET to verify the URL returns 200 with image MIME type
- **Fallback state**: If image fails at runtime, `MuseumMasterpieceImage` client component switches to text-led composition

## Per-Museum Summary

### PRODUCTION_CATALOG (3 museums)

| Museum | Verified Images | Text-Led Stories | Total |
|--------|----------------|-----------------|-------|
| Louvre | 1 (Mona Lisa) | 3 (Winged Victory, Venus de Milo, Liberty) | 4 |
| Orsay | 4 (Starry Night, Olympia, Little Dancer, Bal du moulin) | 0 | 4 |
| Orangerie | 1 (Water Lilies) | 3 (Paul Guillaume, Father Junier, The Groom) | 4 |

### CONTROLLED_PREVIEW (13 museums)

| Museum | Verified Images | Text-Led Stories | Total |
|--------|----------------|-----------------|-------|
| National Gallery London | 3 (Arnolfini, Temeraire, Sunflowers) | 0 | 3 |
| V&A London | 2 (Ardabil Carpet, Tipu's Tiger) | 2 (Cast of David, Raphael Cartoons) | 4 |
| The Met | 1 (Temple of Dendur) | 3 (Washington Crossing, Madame X, Wheat Field) | 4 |
| Rijksmuseum | 2 (Night Watch, Milkmaid) | 2 (Woman Reading, Jewish Bride) | 4 |
| KHM Vienna | 3 (Hunters, Tower of Babel, Art of Painting) | 1 (Saliera) | 4 |
| SMK Copenhagen | 4 | 0 | 4 |
| Nordiska Museet | 1 (Gustav Vasa) | 3 (Bridal Crowns, 1940s Flat, Sámi) | 4 |
| Princeton | 4 | 0 | 4 |
| Cleveland | 4 | 0 | 4 |
| NGA Washington | 1 (Ginevra de' Benci) | 3 (Skater, Woman Holding Balance, Untitled) | 4 |
| Getty | 4 | 0 | 4 |
| Gemäldegalerie Berlin | 4 | 0 | 4 |
| Alte Pinakothek | 4 | 0 | 4 |

### NO_INSTITUTION_RECORD (1 museum)

| Museum | Verified Images | Text-Led Stories | Total |
|--------|----------------|-----------------|-------|
| Yale | 1 (Night Café) | 3 (Declaration, Avalokiteshvara, Equestrian) | 4 |

## Wikimedia Commons Image Status

All `upload.wikimedia.org` and `commons.wikimedia.org` URLs are public-domain or Creative Commons licensed images from Wikipedia/Wikimedia Commons. All are permitted by `next.config.ts` `images.remotePatterns`.

## Fallback Behavior

The `MuseumMasterpieceImage` client component (`web/components/seo/MuseumMasterpieceImage.tsx`):
1. Attempts to render the `next/image` `Image` component
2. If `onError` fires (image fails to load), switches to `mg-masterpiece-textled` CSS composition
3. Text-led composition shows the artwork title in large editorial typography and the artist name — intentionally designed, never looks like a missing image
4. No `NEEDS_VERIFICATION` text is ever exposed to users

## Legacy Museums

Legacy French museums (9) use the `LegacyMuseumPage` component which does not include masterpiece images — they link to individual artwork pages via `/artworks/[slug]`.

## Conclusion

- **Zero visible image placeholders** — all `imageCommonsUrl: null` stories use the intentional text-led composition
- **Zero NEEDS_VERIFICATION text exposed** — image confidence is metadata-only
- **Runtime fallback guaranteed** — `MuseumMasterpieceImage` component handles any image load failure gracefully
- **All image URLs are legally verified public-domain/Wikimedia Commons**
