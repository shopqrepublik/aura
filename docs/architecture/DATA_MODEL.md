# Data Model: Current and Target

Status: CURRENT schema plus separately marked PROPOSED target.

## Current model

```mermaid
erDiagram
  MUSEUM ||--o{ ARTWORK : owns_current_row
  ARTWORK ||--o{ ARTWORK_CATALOG_MEMBERSHIP : activated_in
  ARTWORK ||--o{ ARTWORK_LOCALIZATION : has
  ARTWORK ||--o{ ARTWORK_ESTIMATE : has
  ARTWORK ||--o{ ARTWORK_VALUE_REVEAL : has
  ARTWORK ||--o{ RECOGNITION_ASSET : recognized_with
  ARTWORK ||--o{ LOUVRE_IMAGE_REFERENCE : source_reference
  USER ||--o{ VISIT : owns
  VISIT ||--o{ VISIT_ARTWORK : records
  PRODUCT_EVENT }o--o| MUSEUM : dimensions
  PRODUCT_EVENT }o--o| ARTWORK : dimensions
  ADMIN_SESSION }o--|| ADMIN_LOGIN_ATTEMPT : operationally_related
```

### Current support by concept

| Concept | Current representation | Limitation |
|---|---|---|
| Country | None on `museums`; `product_events.country` only | Institution geography cannot be canonically country-scoped. |
| City | `museums.city` string; events optional `city` | No City entity/code/timezone/locales. |
| Museum/institution | `museums` row | Museum-specific naming; no institution type, country, parent, default language/timezone. |
| Collection/department | artwork strings plus museum JSON categories | No normalized entity, stable collection ID or hierarchy. |
| Artwork | `artworks.id` plus source identity | One row belongs to one museum; cannot model the same work across owning/display institutions cleanly. |
| Artist | `artist` string, optional creator QID/raw JSON | No canonical Artist entity/alias graph. |
| Catalog membership | versioned `artwork_catalog_memberships` | Version defaults are hardcoded in Python; no catalog/config entity. |
| Artwork location | `hall`, `room`, `current_location_raw`, display status | Point-in-time strings; no effective dates/history. |
| Temporary exhibition/loan | Not modeled | Requires overwriting location/museum or custom metadata. |
| Editions/copies | No explicit work/object/edition distinction | Source IDs can distinguish objects, but semantic relationships are absent. |

### Identity

`Artwork.id` is ELYIO's operational primary key. `(source, source_record_id)` is unique when populated. `inventory_number` is not globally unique. `museum_id` is a required FK, so current identity conflates catalog object with one institution association. Catalog membership has its own row but repeats museum ID without a cross-field DB constraint tying membership museum to artwork museum.

## Current production counts

Read-only snapshot 2026-08-23: 1,222 museums; 944 artwork rows; 790 active membership rows; 180 recognition assets; 2,745 Louvre image-reference rows. Counts are not architectural constants.

## Proposed global model

```mermaid
erDiagram
  COUNTRY ||--o{ CITY : contains
  CITY ||--o{ INSTITUTION : hosts
  INSTITUTION ||--o{ COLLECTION : organizes
  CANONICAL_WORK ||--o{ ARTWORK_OBJECT : realized_as
  ARTWORK_OBJECT ||--o{ INSTITUTION_HOLDING : held_or_displayed
  COLLECTION ||--o{ INSTITUTION_HOLDING : groups
  ARTWORK_OBJECT ||--o{ SOURCE_RECORD : evidenced_by
  ARTWORK_OBJECT ||--o{ MEDIA_ASSET : depicted_by
  MEDIA_ASSET ||--o{ RECOGNITION_ASSET : approved_as
  INSTITUTION ||--o{ VISITOR_CATALOG : publishes
  VISITOR_CATALOG ||--o{ CATALOG_MEMBERSHIP : contains
```

This target is PROPOSED. It separates canonical work concepts, physical objects/editions, institution holdings, time-bounded location/loan state, source records and licensed media. See `GLOBAL_TARGET_ARCHITECTURE.md`.
