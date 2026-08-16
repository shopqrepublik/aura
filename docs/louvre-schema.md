# Louvre Data Model — Phase 1 Design

Builds on `docs/louvre-source-audit.md` (Phase 0). Two architectural
decisions from that audit drive this design:

1. **Text/metadata is clear to ingest from Louvre Collections** (Etalab Open
   Licence). **Image bytes are a hard stop** — ADAGP's explicit AI/TDM
   prohibition and `robots.txt`'s named block on Anthropic/Claude bots on
   image files mean no image is fetched, cached, proxied, or embedded in
   this phase, for any artwork, regardless of that artwork's own copyright
   status.
2. Per explicit product decision: **artwork metadata and recognition imagery
   are architecturally independent.** An artwork sourced from Louvre
   Collections must never imply its recognition image also comes from
   Louvre — those are two separate entities below, linked only by
   `artwork_id`, and the Louvre import creates rows in the first and never
   the second.

## Entity overview

```
museum_object (extends existing Artwork table)
    Louvre-authoritative facts: title, artist, date, department, room,
    provenance, inventory number, dimensions, bibliography...
    + source provenance (ark_id, source_url, raw_json, last_source_sync)
    + display-status classification (currentLocation-derived)
        |
        +--- louvre_image_references (NEW table)
        |       Louvre's own published image URLs + copyright strings.
        |       METADATA ONLY. `fetched` is always False for Louvre-sourced
        |       rows in this phase -- no bytes ever touch our infrastructure.
        |
        +--- recognition_assets (NEW table)
                Independent image source for actual visual recognition.
                ZERO rows created by the Louvre importer. Exists so a later,
                separately-vetted pipeline (Wikimedia Commons, Wikidata media,
                our own photography, a future Rmn-GP license) can attach a
                recognition-usable image to this same museum_object without
                ever touching or depending on Louvre's own image hosting.
```

## `museum_object` — extending the existing `Artwork` table

`backend/app/models.py` already has an `Artwork` table (museum_id, artist,
title_original, year, inventory_number, hall, technique, dimensions,
image_url, priority, tags, source_urls) used as the Layer-1 target for
Orsay/Orangerie, currently unpopulated in production (those two museums are
still served from the in-memory `DEMO_ARTWORKS` list in `main.py`). Rather
than inventing a parallel `museum_objects` table, this extends that same
table — it was already museum-agnostic — with the columns Louvre's richer
records need. Orsay/Orangerie rows (whenever they're eventually migrated
into this table) simply leave the new columns null.

New columns added:

| Column | Type | Notes |
|---|---|---|
| `source` | String | `"louvre_collections"` for this import. Distinguishes from e.g. `"wikidata_cirrus"` used for Orsay/Orangerie's original build. |
| `source_record_id` | String | The ARK id, e.g. `"cl010066107"`. |
| `source_url` | String | Full permalink, e.g. `https://collections.louvre.fr/ark:/53355/cl010066107`. |
| `department` | String | Louvre's `collection` field (curatorial department name). |
| `current_location_raw` | Text | Verbatim `currentLocation` string from the source record — never overwritten or normalized away, so the original evidence is always inspectable. |
| `is_on_display` | Boolean, nullable | Derived. `NULL` when confidence is `UNKNOWN`. |
| `display_status_confidence` | String | `HIGH` \| `MEDIUM` \| `LOW` \| `UNKNOWN` — see classification rules below. |
| `display_status_reason` | Text | Human-readable justification, e.g. `"currentLocation matches known reserve/storage pattern: 'Nouvelle réserve des pièces encadrées'"`. |
| `creator_wikidata_qid` | String, nullable | When Louvre's own `creator[].wikidata` field supplies one — useful later for locating independently-licensed images without ever fetching from Louvre. |
| `last_source_sync` | DateTime | When this row was last refreshed from the source. |
| `raw_json` | JSON | The complete, unmodified source payload. Never partially overwritten by normalization. |

Existing columns reused as-is (no redundant new columns): `artist` ←
`creator[0].label`, `title_original` ← `title`, `year` ← `displayDateCreated`,
`inventory_number` ← `objectNumber[0].value`, `hall` ← `room`, `technique` ←
`materialsAndTechniques`, `dimensions` ← formatted `dimension[]`, `image_url`
← the first `image[0].urlImage` **as a URL string only** (see below — this
does not imply the bytes are fetched).

## `louvre_image_references` (NEW) — metadata-only, no bytes

```python
class LouvreImageReference(Base):
    __tablename__ = "louvre_image_references"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    url_image = Column(String, nullable=False)
    url_thumbnail = Column(String)
    image_copyright = Column(String)       # verbatim Louvre copyright/credit string
    image_credit = Column(String, nullable=True)
    image_rights_status = Column(String)   # see classification below
    image_source = Column(String, default="louvre_collections")
    image_type = Column(String)            # Louvre's own "type" field (angle/detail description)
    position = Column(Integer)
    fetched = Column(Boolean, default=False)  # ALWAYS False for this import — documents intent, not just absence of data
```

`image_rights_status` is computed per image, not assumed from the artwork's
age:
- `"adagp_restricted"` — creator matches (or the record otherwise signals)
  the ADAGP repertory / a named still-in-copyright artist from the Terms of
  Use (§12 of the audit doc). These must never get a `recognition_asset` from
  any source without separate legal clearance, not just from Louvre.
- `"museum_photo_copyright"` — the default case: artwork itself is public
  domain, but the *photograph* carries an explicit Louvre/GrandPalaisRmn
  copyright string, so the photo itself is not free to use outside the
  Terms of Use's enumerated purposes.
- `"unknown"` — no copyright string present, or creator unresolved.

## `recognition_assets` (NEW) — independent image layer

```python
class RecognitionAsset(Base):
    __tablename__ = "recognition_assets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    artwork_id = Column(String, ForeignKey("artworks.id"), nullable=False)
    source = Column(String, nullable=False)      # e.g. "wikimedia_commons", "wikidata", "own_photograph", "rmn_gp_licensed" (future)
    source_url = Column(String, nullable=False)
    license = Column(String)                      # e.g. "CC0", "CC-BY-SA-4.0", "PD-old-100", "proprietary_licensed"
    attribution = Column(Text)
    rights_status = Column(String)                 # "public_domain" | "cc_licensed" | "proprietary_licensed" | "unknown"
    ai_tdm_eligible = Column(Boolean, default=False)     # explicit opt-in, NEVER inferred from artwork age or rights_status alone
    embedding_eligible = Column(Boolean, default=False)  # explicit opt-in, independent of ai_tdm_eligible
    local_storage_status = Column(String, default="not_fetched")  # "not_fetched" | "cached" | "cache_expired"
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
```

**The Louvre importer never writes to this table.** It exists in this
phase purely as the architectural seam a future, separately-vetted image
pipeline attaches to. `ai_tdm_eligible` and `embedding_eligible` are
deliberately two different booleans, not derived from `rights_status` —
"public domain artwork" tells you nothing about whether a *specific
photograph's* license clears AI/TDM use; that has to be asserted explicitly,
per asset, when it's actually added.

## Display-status classification (`is_on_display` / `display_status_confidence` / `display_status_reason`)

Rules applied in order, first match wins, computed purely from
`currentLocation` + `room` (never guessed from having-an-image or
belonging-to-Louvre):

| Rule | `is_on_display` | `confidence` | Example |
|---|---|---|---|
| `currentLocation` contains "non exposé" | `False` | `HIGH` | The Byzantine figurine example, §11 of the audit |
| `currentLocation` contains "réserve" (reserve/storage) | `False` | `HIGH` | Storage designation, not a gallery |
| `currentLocation` contains "atelier" (workshop, e.g. chalcography workshop) | `False` | `MEDIUM` | A working department, not public display — less certain this generalizes across all departments |
| `currentLocation` matches a real wing/room pattern (contains "Salle" or "Aile" or a known wing name) **and** `room` is also populated | `True` | `HIGH` | "Denon, Salle 710 - Grande Galerie" + room "Salle 710, Aile Denon, Niveau 1" |
| `currentLocation` is empty/blank | `None` | `UNKNOWN` | No data at all |
| Anything else (non-empty but unrecognized pattern) | `None` | `LOW` | Flagged for manual review, not guessed either way |

## Recognition-readiness classification (revised per explicit instruction)

Deliberately **not** based on "has a Louvre `image_url`" — that would
conflate "Louvre published a URL" with "we can use it," which is exactly the
conflation this phase is designed to avoid. Computed per record from
metadata completeness, display status, and whether a `recognition_asset` row
actually exists (it never does yet, by construction, for Louvre-sourced
objects):

1. `INSUFFICIENT_DATA` — missing title AND creator AND date; barely any
   identifying facts at all.
2. `RIGHTS_RESTRICTED` — creator/work matches an ADAGP-repertory or otherwise
   still-in-copyright signal. Excluded from any future recognition pipeline
   outright, not just deprioritized.
3. `NEEDS_RECOGNITION_ASSET` — has workable identifying metadata (title +
   creator or title + date), but no `recognition_asset` row exists.
4. `DISPLAY_CONFIRMED` — `NEEDS_RECOGNITION_ASSET` **and**
   `display_status_confidence == HIGH` **and** `is_on_display == True`. This
   is the practically useful bucket for prioritizing which objects to seek a
   legally-clean image for first — good metadata, confirmed on a wall
   somewhere, just missing a usable photo.
5. `METADATA_READY` — has workable identifying metadata but display status
   is `UNKNOWN`/`LOW` confidence (we don't know if a visitor could even
   encounter it).
6. `RECOGNITION_READY` — **only reachable once an actual `recognition_asset`
   row exists** for the artwork. The Louvre importer can never produce this
   value for any record, by construction — there is no code path in this
   phase that creates a `recognition_asset`. Included in the enum because
   it's the real target state once the image-rights question is resolved,
   not because this phase can produce it.

**Expected outcome for this phase**: most good Louvre records will land on
`DISPLAY_CONFIRMED` (metadata-good, confirmed on display, recognition asset
still needed) or `NEEDS_RECOGNITION_ASSET` (metadata-good, display status
unclear). This is the correct, honest result — not a bug to fix later in
this same import.

## Raw JSON preservation

Two layers, matching the "never throw away source data" requirement:

1. **Flat files** (used during this test-import phase, no DB writes yet):
   `backend/data/louvre/raw/{arkId}.json` — the exact, unmodified response
   body from `{ark}.json`. Never edited after being written once.
2. **`raw_json` column** on `museum_object` (`artworks` table) — same
   content, for when this eventually lands in Postgres. Populated at import
   time, not derived or reconstructed later.

## Importer design (resumable, bounded, courteous)

`backend/scripts/louvre_import.py` (single file for this test phase, given
scope — the original suggested `discover.ts`/`fetch-record.ts`/etc. split
maps onto functions within one script rather than separate files, since
Python + this repo's existing script conventions don't use a TS build step):

- **Discover**: parse `sitemap.xml` → sub-sitemaps → extract unique ARK ids
  from `<loc>` entries (dedup the fr/en/hreflang duplicates already observed
  in Phase 0).
- **Fetch**: `concurrency=1`, one `.json` request at a time, `User-Agent:
  AURA-MVP-backend/1.0 (contact: repo owner; research/museum-app project)`
  (same identity used throughout Phase 0 — never rotated to route around
  any rule), 1.5s courtesy delay between requests, retry with exponential
  backoff on transient errors (timeout, 5xx, connection errors), immediate
  hard stop (not a retry) on 403 — that would be an explicit access-control
  signal, not a transient failure.
- **Checkpoint**: a JSON file recording every ARK id already processed
  (success or permanent failure) — safe to kill and resume without
  re-fetching or double-counting.
- **Raw storage**: write `raw/{arkId}.json` immediately on successful fetch,
  before normalization — if normalization logic has a bug later, the raw
  archive is never at risk.
- **Normalize**: title/creator/date/department/room/dimensions extraction +
  display-status classification + recognition-readiness classification →
  written to `normalized/{arkId}.json`.
- **Error log**: `errors/errors.jsonl`, one line per permanent failure with
  ARK id, HTTP status, and error text — never silently dropped.
- **No image fetching anywhere in this script.** `image[]` entries are read
  from the JSON response already in hand (it came bundled with the record
  metadata) and written into `louvre_image_references`-shaped records —
  zero additional HTTP requests to any Louvre media URL.
