-- Block 4.5: separate media identity from object/holding relationships.
-- Additive compatibility migration; no asset, provenance or legacy pointer is removed.
ALTER TABLE media_assets ALTER COLUMN cultural_object_id DROP NOT NULL;

CREATE TABLE IF NOT EXISTS media_asset_associations (
    id VARCHAR PRIMARY KEY,
    media_asset_id VARCHAR NOT NULL REFERENCES media_assets(id),
    target_scope VARCHAR NOT NULL,
    cultural_object_id VARCHAR REFERENCES cultural_objects(id),
    institution_holding_id VARCHAR REFERENCES institution_holdings(id),
    source_record_id VARCHAR REFERENCES source_records(id),
    provider_id VARCHAR NOT NULL REFERENCES source_providers(id),
    source_relationship_key VARCHAR NOT NULL,
    relationship_role VARCHAR NOT NULL,
    position INTEGER,
    "primary" BOOLEAN,
    presentation_eligible BOOLEAN,
    recognition_eligible BOOLEAN,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ingestion_run_id VARCHAR REFERENCES ingestion_runs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_media_assoc_scope CHECK (
      (target_scope='OBJECT' AND cultural_object_id IS NOT NULL AND institution_holding_id IS NULL)
      OR
      (target_scope='HOLDING' AND cultural_object_id IS NOT NULL AND institution_holding_id IS NOT NULL)
    ),
    CONSTRAINT ck_media_assoc_role CHECK (relationship_role IN ('PRESENTATION','REFERENCE','RECOGNITION_ASSET','SOURCE_ORIGINAL','DERIVATIVE','CONTEXTUAL'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_media_assoc_source_edge
ON media_asset_associations (
  media_asset_id, provider_id, source_relationship_key, target_scope,
  COALESCE(cultural_object_id, ''), COALESCE(institution_holding_id, ''), relationship_role
);
CREATE INDEX IF NOT EXISTS idx_media_assoc_asset_active ON media_asset_associations(media_asset_id, active);
CREATE INDEX IF NOT EXISTS idx_media_assoc_object_role ON media_asset_associations(cultural_object_id, relationship_role, active);
CREATE INDEX IF NOT EXISTS idx_media_assoc_holding_role ON media_asset_associations(institution_holding_id, relationship_role, active);
CREATE INDEX IF NOT EXISTS idx_media_assoc_source ON media_asset_associations(source_record_id, active);

-- Exact compatibility edge for every existing MediaAsset. Existing eligibility
-- and provenance values are copied, not reinterpreted or promoted.
INSERT INTO media_asset_associations (
  id, media_asset_id, target_scope, cultural_object_id, institution_holding_id,
  source_record_id, provider_id, source_relationship_key, relationship_role,
  presentation_eligible, recognition_eligible, active, first_seen_at,
  last_seen_at, ingestion_run_id, created_at, updated_at
)
SELECT
  'media-assoc:legacy:' || md5(id), id,
  CASE WHEN institution_holding_id IS NOT NULL THEN 'HOLDING' ELSE 'OBJECT' END,
  cultural_object_id, institution_holding_id, source_record_id, provider_id,
  'legacy:' || id, purpose, presentation_eligible, recognition_eligible, TRUE,
  COALESCE(created_at, NOW()), COALESCE(updated_at, created_at, NOW()),
  ingestion_run_id, COALESCE(created_at, NOW()), COALESCE(updated_at, created_at, NOW())
FROM media_assets
WHERE cultural_object_id IS NOT NULL
ON CONFLICT (id) DO NOTHING;

-- Strong provider media identity is preferred when present. URL remains the
-- fallback for providers whose media IDs are absent or documented unstable.
CREATE UNIQUE INDEX IF NOT EXISTS uq_media_assets_provider_asset_id
ON media_assets(provider_id, provider_asset_id)
WHERE provider_asset_id IS NOT NULL;
