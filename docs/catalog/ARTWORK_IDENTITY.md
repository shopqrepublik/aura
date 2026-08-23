# Artwork Identity

Status: CURRENT limitations and target rules.

## Current identity

- `Artwork.id`: ELYIO operational primary key.
- `(source, source_record_id)`: unique provider identity when present.
- `inventory_number`: institution-local label, nullable/non-unique globally.
- `creator_wikidata_qid`: creator link only, not artwork identity.
- `ArtworkCatalogMembership`: visitor activation, not identity.

## Duplicate/copy risks

Title+artist matching is candidate discovery, never canonical identity. Multiple editions/casts/copies, ownership transfers, loans and exhibition locations cannot currently be related explicitly. The same conceptual work at two institutions would require separate artwork rows with no first-class relationship.

## Required global identity rules

1. Preserve every source namespace/record ID.
2. Separate conceptual work from physical object where evidence supports it.
3. Model institution holding/display as a relationship with dates.
4. Never merge solely on title, artist, inventory number or image similarity.
5. Record aliases/previous IDs and merge decisions with provenance.
6. Recognition returns a physical catalog object/membership, not an abstract title.
