# Catalog Architecture

Status: CURRENT.

`museums` is the institution directory. `artworks` is factual knowledge. `artwork_catalog_memberships` activates a versioned visitor subset. Localizations, estimates and value reveals are editorial layers and must not be overwritten by source refreshes.

## Selection behavior

For ten configured museums, `backend/app/catalog.py` selects active rows from a named catalog version. Orsay and Orangerie are not in that map and currently fall back to all artwork rows for their museum. A new museum without code configuration also falls back to all its artwork rows—unsafe for a knowledge catalog containing draft/off-display items.

## Current global constraints

- Version map and environment variable per museum are hardcoded.
- Artwork belongs to exactly one `museum_id`.
- Collections/departments are strings/JSON, not entities.
- Temporary exhibitions/loans have no effective-dated membership/location.
- Frontend curated visitor content and SEO content are separate checked-in data sets.
- Admin catalog health includes a Louvre-specific block and mixes legacy/current readiness labels.

## Import contract

An importer must preserve `(source, source_record_id)`, source URL, raw payload and sync time; normalize without destroying raw evidence; avoid overwriting editorial rows; populate memberships separately; and produce a dry-run/reconciliation manifest. Imports must never infer image rights from artwork copyright status.

## Deactivation

Set catalog membership inactive or move the catalog version pointer. Do not delete artwork/source/provenance rows merely to remove visitor availability. SEO removal and caches are separate steps.
