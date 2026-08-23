# Catalog Architecture

Status: CURRENT after Globalization Blocks 1–3.

`museums` is the compatible canonical Institution directory. `institution_profiles` owns visitor catalog version, candidate universe, recognition policy/thresholds, prompt context, supported modes and operational ordering. `artworks` remains the visitor/editorial compatibility record; `cultural_objects`, `institution_holdings`, `source_records` and `media_assets` now separate identity and evidence. `artwork_catalog_memberships` activates a versioned visitor subset. Localizations, estimates and value reveals are editorial layers and source refreshes must not overwrite them.

## Runtime selection

`backend/app/catalog.py` resolves an active Institution Profile. Candidate universes are `ACTIVE_CATALOG`, `INSTITUTION_ARTWORKS`, or `NONE`; policies are `TOP_N_METADATA`, `ASSET_VERIFY`, `UNCATALOGED_ONLY`, or `NOT_READY`. Missing, inactive, invalid, or empty configured catalogs fail closed with `institution_not_ready`; there is no all-museum fallback. Directory priority is profile configuration rather than an institution-name branch.

## Source adapter contract

`backend/app/source_adapter.py` defines provider-neutral `AdapterObjectRecord` and `AdapterMediaRecord`. A Louvre or future National Gallery adapter may contain provider-specific parsing, but it must emit provider/source IDs, institution ID, source language/URL, normalized metadata, optional collection ID, retrieval time, raw payload and media rights/provenance. Core catalog/recognition code must not branch on provider, country, currency or language.

## Import and activation

1. Resolve Country, Institution and Institution Profile.
2. Upsert SourceProvider and exact SourceRecord by provider namespace/record ID.
3. Create or explicitly link CulturalObject; never title/artist auto-merge.
4. Create InstitutionHolding; current artwork need not be forced into a collection.
5. Create media rows with purpose, provenance and independent eligibility.
6. Preserve original/source-language metadata; add localized visitor content separately.
7. Create the compatibility Artwork with stable ID, then versioned membership.
8. Benchmark and activate. Deactivation changes membership/profile state; it does not delete identity/evidence.

## Loans/location foundation

Holding status, relationship type, optional collection/location and `valid_from`/`valid_to` permit a future loan or temporary display relationship without changing the object. Exhibition scheduling and automatic location history are not implemented.

## Current compatibility debt

Recognition and editorial APIs still address `Artwork.id`; old image/source columns and provider-specific research tables remain. They are compatibility/read-model inputs, not the target identity model. Frontend SEO content remains a checked-in France content package and is not a generic global catalog route yet.

During phased migration, a generic DB trigger creates deterministic singleton object/holding rows for legacy Artwork inserts. New adapters should still write SourceRecord and MediaAsset explicitly; the trigger is a safety bridge, not a substitute for provenance-aware ingestion.
