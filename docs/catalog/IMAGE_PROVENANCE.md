# Image and Media Provenance

Status: CURRENT after migration `0004_global_media_identity_foundation`.

## Generic model

`media_assets` links an asset to its cultural object and optionally the compatibility artwork, holding and source record. It records provider, provider asset ID, original/asset URL, media type, purpose, rights status, verification state, license, attribution, public-domain assertion, retrieval time, SHA-256, derivative parent/specification and independent presentation/recognition eligibility.

| Dimension | Values/current meaning |
|---|---|
| Purpose | `PRESENTATION`, `REFERENCE`, `RECOGNITION_ASSET`, `SOURCE_ORIGINAL`, `DERIVATIVE` |
| Rights | `VERIFIED_PUBLIC_DOMAIN`, `LICENSED`, `UNKNOWN`, `RESTRICTED` |
| Verification | `VERIFIED`, `DECLARED_BY_SOURCE`, `UNKNOWN`, `RESTRICTED` |
| Eligibility | `presentation_eligible` and `recognition_eligible` are independent nullable booleans; null means not determined |

`UNKNOWN` is never promoted to public domain. A source declaration is not ELYIO verification. An asset suitable for presentation is not automatically legal or technically suitable for recognition, and an approved recognition asset is not automatically a public presentation image.

## Legacy migration

- `Artwork.image_url` becomes a `PRESENTATION` asset with UNKNOWN rights/verification and undetermined presentation eligibility. Runtime continues reading the legacy column.
- `RecognitionAsset` becomes `RECOGNITION_ASSET`; existing declared license/attribution/rights are preserved. Recognition eligibility is true only when existing AI/TDM and embedding flags were both explicitly true.
- `LouvreImageReference` becomes a generic `REFERENCE` asset while the Louvre source table remains as a source-adapter compatibility table. It is not silently made fetchable or recognition-eligible.
- No legacy media is marked `VERIFIED` by the migration.

Pre-deployment transaction snapshot (2026-08-23, current 944 artworks): 3,290 prospective asset rows: 2,923 `DECLARED_BY_SOURCE` and 367 `UNKNOWN`; rights were 133 declared public-domain, 45 licensed, 3,112 unknown, 0 restricted. These are asset rows, not unique artworks, and remain a dated snapshot. Among 790 active visitor-catalog artworks: 0 have VERIFIED provenance, 495 have at least declared/partial provenance, 295 remain provenance-unknown, 0 have a restricted asset, and 295 lack a non-restricted REFERENCE/RECOGNITION_ASSET/SOURCE_ORIGINAL URL. Admin Catalog exposes these operational categories.

## Invariants and privacy

Presentation image != source/reference image != recognition asset != visitor capture. A placeholder must not suppress a real private visitor capture. Browser captures remain private visit/session material and never become catalog media, recognition assets or SEO images automatically. The proxy/cache creates a delivery derivative but must not be treated as a new rights grant.

## Provider unknowns

Upstream license changes, source availability, OpenAI input retention, Fly/Vercel logs and local cache deletion remain provider/operations truths. They require manual contractual/operational verification; this document makes no legal or GDPR conclusion.
