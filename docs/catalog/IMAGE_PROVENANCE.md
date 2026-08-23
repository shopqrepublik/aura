# Image Provenance

Status: CURRENT audit.

## Current storage

| Role/table | Captured fields | Gaps |
|---|---|---|
| `Artwork.image_url` | presentation URL; `source_urls`, source record context | No per-image license, attribution or retrieved timestamp. |
| `RecognitionAsset` | source, URL, license, attribution, rights status, AI/TDM and embedding eligibility, local storage status, timestamps | No content hash, derivative lineage, provider retrieval timestamp or explicit presentation role. |
| `LouvreImageReference` | source URL/thumbnail, copyright/credit, rights evidence, type/position, fetched flag | Louvre-only; metadata-only; no generic provider-reference table. |
| Browser visitor capture | base64 in visit localStorage; sent for recognition | No explicit TTL/clear UI; private, not provenance for public catalog. |
| Backend proxy cache | hashed local JPEG derivative | Cache metadata is filesystem/key based, not a durable provenance row. |

## Role invariant

Presentation image != recognition asset != provider source/reference image != visitor capture. An asset can fill more than one role only when each use and rights basis is explicit.

## Required traceability

For each public/recognition image preserve provider, provider asset/record ID, source URL, license/version, attribution, retrieved_at, content hash, original metadata, derivative parameters/hash/storage, rights review, AI/TDM eligibility and links to the exact artwork identity.

## Provider-side unknowns

OpenAI input retention, Wikimedia availability/change history, upstream museum rights changes, Vercel/Fly request logging and cache deletion behavior were not verified. These are provider truths requiring contractual/manual checks; no GDPR conclusion is asserted.

## Current policy

Louvre references remain metadata-only and `fetched=false` by importer policy. Eligible non-Louvre `RecognitionAsset` can be used. A visitor capture may replace a placeholder for private UI but must never become public media or a catalog recognition asset automatically.
