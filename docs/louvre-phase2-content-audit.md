# Louvre Phase 2A Content System Audit

Catalog version: `2026-08-11-v1`

This audit was completed before creating the Louvre 20-work content pilot. It is an export/review-package audit only. No production writes, RecognitionAsset rows, embeddings, audio files, Louvre image bytes, or catalog membership changes are part of Phase 2A.

## Current ELYIO Content Architecture

### Database models

The backend already has a layered artwork model in `backend/app/models.py`.

- `Artwork` is the Layer 1 catalog object. It stores museum identity, source provenance, display/status fields, location, image reference URL, and the legacy fields needed by the existing UI/recognition card shape.
- `Artwork.artist` is nullable, which supports Louvre objects with no conventional creator label.
- `SourceRecordIndex` is the source-enumeration layer and is not a production artwork table.
- `LouvreImageReference` is a Louvre-specific metadata-only image reference table. It is separate from recognition assets and does not imply image-byte fetching.
- `RecognitionAsset` is the rights-vetted asset layer for recognition. It is intentionally independent from Louvre image references.
- `ArtworkLocalization` is the existing Layer 2 editorial content table. It stores one row per artwork, locale, and mode with `title`, `analogy`, `why_it_matters`, `where_to_look`, `rarity_note`, `audio_script`, `audio_url`, `editorial_status`, and review metadata.
- `ArtworkEstimate` is the existing value layer. It stores low/high estimate values in EUR millions, methodology text, comparable sales text, confidence, and review metadata.
- `ArtworkEmbedding` is the visual retrieval layer. It must remain untouched for Phase 2A.

### Backend API/runtime

`backend/app/catalog.py` maps database `Artwork` rows into the legacy DEMO_ARTWORKS-shaped catalog object used by recognition and detail APIs. The mapper currently joins the latest `ArtworkEstimate`, but the current detail path does not yet hydrate `ArtworkLocalization` into the API card payload. The application therefore has a production DB catalog, but the frontend content experience still expects the static card schema used by `web/lib/data/artworks.json`.

The recognition path now queries the DB-backed catalog by `museum_id`, preserving museum scoping. Phase 2A does not change recognition behavior.

### Frontend content shape

The web app uses `web/lib/data/artworks.json` and TypeScript types in `web/lib/types.ts`.

The rendered card supports:

- localized title;
- nullable `artist`;
- `year`, `hall`, `inventoryNumber`;
- image/reference URL;
- `estimate.low`, `estimate.high`, `logic`, `comparableSales`, and estimate confidence;
- localized `why`, `where`, `rarity`;
- localized Simple-mode overrides: `whySimple`, `whereSimple`, `raritySimple`;
- localized Kids-mode overrides: `whyKids`, `whereKids`, `rarityKids`;
- localized `audioScript` and optional `audioUrl`;
- `editorialStatus`, `needsEditorialReview`, and review metadata.

`CardScreen` renders the identity, provenance/value reveal, visual looking note, rarity note, and audio button. `ProgressScreen`, `RecapScreen`, and recap-image generation already handle null estimates by showing pending-review copy rather than inventing value totals. `ArtworkIdentity` and recap components are null-artist safe and use localized display fallbacks.

### Value reveal

`ProvenanceReveal` shows a monetary range only when both low and high estimates exist. Otherwise it shows a pending-review state. `MarketMethodologySheet` describes the estimate methodology generically and intentionally does not expose raw internal `estimate.logic`.

This means Phase 2A can produce evidence-rich value analysis, but production display of non-market cultural value context would require a later additive UI/API change if we want more than the current “pending review” state.

### Audio

Audio scripts are already represented in the frontend card schema and `ArtworkLocalization`. Existing audio cache generation is implemented by `backend/scripts/generate_audio_cache.py`, which calls TTS and writes MP3 files under `web/public/audio`.

Phase 2A creates scripts only. It does not run TTS or create audio assets.

### Localization

The existing app supports `en`, `fr`, and `zh-Hans`. Static card data stores localized text directly per field. `ArtworkLocalization` stores locale/mode rows in the backend. Phase 2A mirrors this model in the review JSONL by storing generated fields per language and audience mode.

## What Louvre Can Reuse

Louvre can reuse:

- `Artwork` as the Layer 1 factual catalog object;
- `ArtworkLocalization` for Normal/Simple/Kids editorial text and audio scripts;
- `ArtworkEstimate` for market estimates where defensible;
- existing null-artist UI/API behavior;
- existing museum-scoped catalog repository;
- existing value reveal behavior for numeric estimates;
- `LouvreImageReference` for source image metadata only;
- `RecognitionAsset` later, only after separate rights-vetted asset approval;
- existing `en`, `fr`, `zh-Hans` localization model.

## Missing For Phase 2A-Quality Content

The existing architecture is compatible, but it is narrower than the requested Phase 2A review package.

Missing or insufficiently structured fields for production-scale Louvre enrichment:

- field-level provenance (`field_name`, `source_ids`, `generation_version`, field confidence, field review status);
- structured evidence bundles for each artwork;
- structured value methodology with `valuation_type`, `currency`, `valuation_date`, nullable non-market cultural context, structured comparables, and deterministic calculation inputs;
- structured QA flags;
- explicit separation between source facts and ELYIO editorial interpretation;
- richer “what to notice” as a list of visual observations rather than a single paragraph;
- explicit content-readiness and recognition-readiness statuses per generated content package;
- translation QA status per field/language.

## Schema Changes Required Now

None for Phase 2A.

This phase writes a review package under `exports/louvre/content/` and does not write to production.

## Likely Additive Schema Work Before Production Content Import

If the pilot is approved for production import, use additive structures rather than a parallel artwork model:

- Add a source/evidence bundle table, for example `artwork_content_sources`.
- Add a field-level generated-content table, or extend `ArtworkLocalization` with companion provenance rows keyed by `artwork_id`, `locale`, `mode`, and `field_name`.
- Add a structured value-evidence table, or extend `ArtworkEstimate` with additive nullable fields: `valuation_type`, `currency`, `valuation_date`, `value_low`, `value_high`, `value_context`, `structured_comparables`, `calculation_inputs`, and `visitor_disclaimer`.
- Add a content QA table keyed to generated package/version.

These are additive and should not replace `Artwork`, `ArtworkLocalization`, `ArtworkEstimate`, `LouvreImageReference`, `RecognitionAsset`, or `ArtworkEmbedding`.

## Compatibility Conclusion

The existing system is compatible with Louvre Phase 2A as a review package. It can later ingest approved content into the existing architecture, but production import should first add structured provenance/value/QA support if ELYIO wants to preserve the full evidence model requested here.
