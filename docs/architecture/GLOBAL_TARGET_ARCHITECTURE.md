# Global Target Architecture

Status: **PROPOSED — NOT IMPLEMENTED**.

## Goal

Evolve the current modular monolith and Postgres schema without premature microservices. Keep Next.js, FastAPI and PostgreSQL; replace museum-specific code maps and ambiguous identity with data-driven entities/configuration.

## Target entities

- `Country`: ISO code, localized name, default currency/legal region.
- `City`: country FK, canonical timezone, localized name/slug.
- `Institution`: current Museum generalized with type, country/city, languages, coordinates and operational status.
- `Collection`: hierarchical institution-owned department/collection with stable source IDs.
- `CanonicalWork`: conceptual work where defensible.
- `ArtworkObject`: physical object/copy/edition, canonical identity and source provenance.
- `InstitutionHolding`: owning/displaying institution, collection, location, loan/exhibition and effective dates.
- `SourceRecord`: provider, record ID/URL, retrieved timestamp, raw payload/hash and license policy.
- `MediaAsset`: presentation/recognition roles, exact source/license/attribution/derivative lineage.
- `VisitorCatalog`: institution, version, recognition policy, activation state.
- `RecognitionProfile`: candidate strategy, thresholds, model, benchmark gate and asset requirements.

## Pragmatic evolution

1. Add country/institution configuration and migration ledger without renaming public APIs.
2. Move `DEFAULT_VISITOR_CATALOG_VERSION_BY_MUSEUM`, prompt context, ordering and thresholds into versioned DB/config rows.
3. Introduce source/media tables alongside current image columns; backfill provenance before removing legacy fields.
4. Add collection/holding/location only when onboarding the second country demonstrates real mappings.
5. Keep synchronous FastAPI for user recognition; add queue/batch only for ingestion, enrichment and analytics aggregation.

## Recognition configuration

Each visitor catalog should declare candidate universe, maximum candidate count, Stage 2 strategy, thresholds, asset eligibility, prompt context, supported object types and benchmark version. No code branch should be named after an institution.

## Multilingual data

Use BCP-47 locale rows for Institution, Collection, Work and editorial content. Preserve source-language text and declare fallback policy. UI locale registry must be data/config-driven, not a TypeScript union requiring code edits for every language.

## Analytics dimensions

Events should reference institution/catalog/object and a server-issued anonymous identity token or signed event envelope. Definitions must be versioned. Raw events feed daily aggregates; internal/QA dimension is server-trusted.

## Future B2B administration

Extend the current Control Center with institution-scoped roles, catalog activation workflows, provenance/readiness gates and benchmark approvals. Do not expose direct table editing. Founder global access and institution operator access must have separate authorization scopes/audit logs.

## Non-goals

No museum-per-service architecture, no separate database per institution, no mandatory event streaming platform at current volume, and no graph database unless measured queries justify one.
