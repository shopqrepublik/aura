CREATE TABLE IF NOT EXISTS ingestion_runs (
    id VARCHAR PRIMARY KEY,
    mode VARCHAR NOT NULL,
    adapter_key VARCHAR NOT NULL,
    provider_id VARCHAR NOT NULL REFERENCES source_providers(id),
    institution_id VARCHAR NOT NULL REFERENCES museums(id),
    status VARCHAR NOT NULL DEFAULT 'RUNNING',
    code_version VARCHAR,
    source_snapshot VARCHAR,
    operator_id VARCHAR,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    records_inspected INTEGER NOT NULL DEFAULT 0,
    created_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    conflict_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    summary JSONB,
    error TEXT,
    CONSTRAINT ck_ingestion_run_mode CHECK (mode IN ('APPLY')),
    CONSTRAINT ck_ingestion_run_status CHECK (status IN ('RUNNING','APPLIED','FAILED','PARTIAL'))
);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_provider_institution_started
    ON ingestion_runs(provider_id, institution_id, started_at);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status ON ingestion_runs(status);

ALTER TABLE source_providers ADD COLUMN IF NOT EXISTS adapter_key VARCHAR;
ALTER TABLE source_providers ADD COLUMN IF NOT EXISTS adapter_config JSONB;

ALTER TABLE source_records ADD COLUMN IF NOT EXISTS provider_modified_at TIMESTAMPTZ;
ALTER TABLE source_records ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE source_records ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE source_records ADD COLUMN IF NOT EXISTS content_checksum VARCHAR(64);
ALTER TABLE source_records ADD COLUMN IF NOT EXISTS ingestion_status VARCHAR NOT NULL DEFAULT 'INGESTED';
ALTER TABLE source_records ADD COLUMN IF NOT EXISTS review_status VARCHAR NOT NULL DEFAULT 'UNREVIEWED';
ALTER TABLE source_records ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE source_records ADD COLUMN IF NOT EXISTS last_ingestion_run_id VARCHAR REFERENCES ingestion_runs(id);
CREATE INDEX IF NOT EXISTS idx_source_records_sync_state
    ON source_records(provider_id, active, last_seen_at);
CREATE INDEX IF NOT EXISTS idx_source_records_last_run ON source_records(last_ingestion_run_id);

ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS source_rights_metadata JSONB;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS review_notes TEXT;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS ingestion_run_id VARCHAR REFERENCES ingestion_runs(id);
CREATE INDEX IF NOT EXISTS idx_media_assets_review_queue
    ON media_assets(verification_state, rights_status, presentation_eligible, recognition_eligible);
CREATE INDEX IF NOT EXISTS idx_media_assets_ingestion_run ON media_assets(ingestion_run_id);

CREATE TABLE IF NOT EXISTS ingestion_changes (
    id BIGSERIAL PRIMARY KEY,
    ingestion_run_id VARCHAR NOT NULL REFERENCES ingestion_runs(id),
    provider_id VARCHAR NOT NULL,
    provider_record_id VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    risk VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    cultural_object_id VARCHAR REFERENCES cultural_objects(id),
    institution_holding_id VARCHAR REFERENCES institution_holdings(id),
    source_record_id VARCHAR REFERENCES source_records(id),
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ingestion_change_risk CHECK (risk IN ('SAFE_AUTOMATIC','REVIEW_RECOMMENDED','HIGH_RISK'))
);
CREATE INDEX IF NOT EXISTS idx_ingestion_changes_run ON ingestion_changes(ingestion_run_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_changes_source ON ingestion_changes(provider_id, provider_record_id);

CREATE TABLE IF NOT EXISTS media_provenance_reviews (
    id BIGSERIAL PRIMARY KEY,
    media_asset_id VARCHAR NOT NULL REFERENCES media_assets(id),
    actor VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    before_state JSONB,
    after_state JSONB,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_media_provenance_reviews_asset_created
    ON media_provenance_reviews(media_asset_id, created_at);

-- Existing records retain truthful legacy state. No review, checksum,
-- synchronization or operator history is fabricated by this migration.
