-- ELYIO DB-backed catalog migration.
-- Review first. Do not apply to production until explicitly approved.
--
-- Scope:
--   * Make artworks.artist nullable.
--   * Add source/status/provenance fields to the existing artworks table.
--   * Add generic source_record_index as an enumeration layer, not a catalog.
--   * Add metadata-only LouvreImageReference and independent RecognitionAsset
--     tables needed by the source/status architecture.
--
-- Safety:
--   * No DROP.
--   * No TRUNCATE.
--   * No table recreation.
--   * No destructive type conversion.
--   * Existing Orsay/Orangerie rows remain valid.

BEGIN;

ALTER TABLE artworks
    ALTER COLUMN artist DROP NOT NULL;

ALTER TABLE artworks ADD COLUMN IF NOT EXISTS title_complement TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS source_record_id TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS last_source_sync TIMESTAMPTZ;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS raw_json JSONB;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS department TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS collection TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS object_type TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS materials_and_techniques TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS provenance TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS object_history TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS historical_context TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS current_location_raw TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS room TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS creator_wikidata_qid TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS creator_raw JSONB;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS creator_labels JSONB;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS display_status TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS display_status_confidence TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS display_status_reason TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS metadata_status TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS recognition_status TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS rights_status TEXT;
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS rights_review_required BOOLEAN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_artworks_source_record
    ON artworks (source, source_record_id)
    WHERE source IS NOT NULL AND source_record_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_artworks_museum_priority ON artworks (museum_id, priority, id);
CREATE INDEX IF NOT EXISTS idx_artworks_department ON artworks (department);
CREATE INDEX IF NOT EXISTS idx_artworks_display_status ON artworks (display_status);
CREATE INDEX IF NOT EXISTS idx_artworks_artist ON artworks (artist);
CREATE INDEX IF NOT EXISTS idx_artworks_creator_wikidata_qid ON artworks (creator_wikidata_qid);
CREATE INDEX IF NOT EXISTS idx_artworks_hall ON artworks (hall);
CREATE INDEX IF NOT EXISTS idx_artworks_room ON artworks (room);
CREATE INDEX IF NOT EXISTS idx_artworks_object_type ON artworks (object_type);

CREATE TABLE IF NOT EXISTS source_record_index (
    source TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    sitemap_id TEXT,
    position_in_sitemap INTEGER,
    prefix TEXT,
    discovered_at TIMESTAMPTZ,
    metadata_ingested_at TIMESTAMPTZ,
    ingestion_status TEXT,
    PRIMARY KEY (source, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_source_record_index_source
    ON source_record_index (source);
CREATE INDEX IF NOT EXISTS idx_source_record_index_ingestion_status
    ON source_record_index (ingestion_status);

CREATE TABLE IF NOT EXISTS louvre_image_references (
    id SERIAL PRIMARY KEY,
    artwork_id TEXT NOT NULL REFERENCES artworks(id),
    url_image TEXT NOT NULL,
    url_thumbnail TEXT,
    image_copyright TEXT,
    image_credit TEXT,
    rights_status TEXT,
    rights_review_required BOOLEAN DEFAULT TRUE,
    rights_reason TEXT,
    image_source TEXT DEFAULT 'louvre_collections',
    image_type TEXT,
    position INTEGER,
    fetched BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_louvre_image_references_artwork_id
    ON louvre_image_references (artwork_id);
CREATE INDEX IF NOT EXISTS idx_louvre_image_references_fetched
    ON louvre_image_references (fetched);

CREATE TABLE IF NOT EXISTS recognition_assets (
    id SERIAL PRIMARY KEY,
    artwork_id TEXT NOT NULL REFERENCES artworks(id),
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    license TEXT,
    attribution TEXT,
    rights_status TEXT,
    ai_tdm_eligible BOOLEAN DEFAULT FALSE,
    embedding_eligible BOOLEAN DEFAULT FALSE,
    local_storage_status TEXT DEFAULT 'not_fetched',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recognition_assets_artwork_id
    ON recognition_assets (artwork_id);
CREATE INDEX IF NOT EXISTS idx_recognition_assets_embedding_eligible
    ON recognition_assets (embedding_eligible);

COMMIT;
