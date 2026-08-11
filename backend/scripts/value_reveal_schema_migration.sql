-- ELYIO value reveal architecture migration.
-- Review first. Do not apply to production until backup/rollback point is confirmed.
--
-- Scope:
--   * Add canonical artwork_value_reveals table for three visitor-facing modes:
--     ESTIMATED_VALUE, MARKET_CONTEXT, BEYOND_MARKET.
--   * Preserve existing artwork_estimates and all existing Orsay/Orangerie data.
--   * No content import, no RecognitionAsset creation, no embeddings.
--
-- Safety:
--   * No DROP.
--   * No TRUNCATE.
--   * No table recreation.
--   * Existing estimate rows remain the backward-compatible fallback.

BEGIN;

CREATE TABLE IF NOT EXISTS artwork_value_reveals (
    id SERIAL PRIMARY KEY,
    artwork_id TEXT NOT NULL REFERENCES artworks(id),
    catalog_version TEXT,
    mode TEXT NOT NULL CHECK (mode IN ('ESTIMATED_VALUE', 'MARKET_CONTEXT', 'BEYOND_MARKET')),
    aggregate_value_eligible BOOLEAN NOT NULL DEFAULT FALSE,

    estimated_value_low DOUBLE PRECISION,
    estimated_value_high DOUBLE PRECISION,
    estimated_value_currency TEXT,

    market_context_headline_number JSONB,
    market_context_currency TEXT,
    market_context_label TEXT,
    market_context_explanation TEXT,
    relationship_to_artwork TEXT,
    context_type TEXT,
    source_reference TEXT,
    context_date TEXT,

    beyond_market_headline TEXT,
    beyond_market_explanation TEXT,
    institutional_legal_context TEXT,
    optional_context TEXT,

    confidence TEXT,
    methodology TEXT,
    sources JSONB,
    disclaimer TEXT,
    review_status TEXT NOT NULL DEFAULT 'DRAFT',
    generated_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT ck_value_reveal_estimated_aggregate
        CHECK (mode <> 'ESTIMATED_VALUE' OR aggregate_value_eligible = TRUE),
    CONSTRAINT ck_value_reveal_context_nonaggregate
        CHECK (mode = 'ESTIMATED_VALUE' OR aggregate_value_eligible = FALSE)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_artwork_value_reveal_version
    ON artwork_value_reveals (artwork_id, catalog_version);
CREATE INDEX IF NOT EXISTS idx_artwork_value_reveals_artwork_id
    ON artwork_value_reveals (artwork_id);
CREATE INDEX IF NOT EXISTS idx_artwork_value_reveals_mode
    ON artwork_value_reveals (mode);
CREATE INDEX IF NOT EXISTS idx_artwork_value_reveals_review_status
    ON artwork_value_reveals (review_status);

COMMIT;
