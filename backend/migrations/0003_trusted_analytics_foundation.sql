ALTER TABLE product_events ADD COLUMN IF NOT EXISTS schema_version INTEGER;
ALTER TABLE product_events ADD COLUMN IF NOT EXISTS client_occurred_at TIMESTAMPTZ;
ALTER TABLE product_events ADD COLUMN IF NOT EXISTS server_received_at TIMESTAMPTZ;
ALTER TABLE product_events ADD COLUMN IF NOT EXISTS internal_test BOOLEAN;
ALTER TABLE product_events ADD COLUMN IF NOT EXISTS trust_level VARCHAR;
ALTER TABLE product_events ADD COLUMN IF NOT EXISTS business_eligible BOOLEAN;

-- Existing rows stay explicitly legacy. Missing trust cannot be fabricated.
UPDATE product_events SET trust_level = 'LEGACY_UNVERIFIED'
WHERE trust_level IS NULL;

CREATE TABLE IF NOT EXISTS analytics_identity_links (
    anonymous_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_identity_links_user
    ON analytics_identity_links(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_identity_links_last_seen
    ON analytics_identity_links(last_seen_at);

CREATE TABLE IF NOT EXISTS analytics_sessions (
    session_id VARCHAR PRIMARY KEY,
    anonymous_id VARCHAR,
    user_id VARCHAR,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_sessions_anonymous ON analytics_sessions(anonymous_id);
CREATE INDEX IF NOT EXISTS idx_analytics_sessions_user ON analytics_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_sessions_last_seen ON analytics_sessions(last_seen_at);

CREATE TABLE IF NOT EXISTS recognition_attempts (
    recognition_attempt_id VARCHAR PRIMARY KEY,
    schema_version INTEGER NOT NULL DEFAULT 2,
    anonymous_id VARCHAR,
    user_id VARCHAR,
    session_id VARCHAR,
    institution_id VARCHAR NOT NULL REFERENCES museums(id),
    artwork_id VARCHAR REFERENCES artworks(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    terminal_outcome VARCHAR,
    response_status VARCHAR,
    confidence DOUBLE PRECISION,
    recognition_mode VARCHAR,
    latency_ms INTEGER,
    internal_test BOOLEAN NOT NULL DEFAULT FALSE,
    response_payload JSONB,
    CONSTRAINT ck_recognition_attempt_terminal_outcome CHECK (
        terminal_outcome IS NULL OR terminal_outcome IN (
            'success', 'no_match', 'uncataloged_result', 'invalid_image',
            'timeout', 'failed', 'institution_not_ready'
        )
    )
);
CREATE INDEX IF NOT EXISTS idx_recognition_attempts_completed_at
    ON recognition_attempts(completed_at);
CREATE INDEX IF NOT EXISTS idx_recognition_attempts_identity
    ON recognition_attempts(anonymous_id, user_id);
CREATE INDEX IF NOT EXISTS idx_recognition_attempts_session
    ON recognition_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_recognition_attempts_institution
    ON recognition_attempts(institution_id);
CREATE INDEX IF NOT EXISTS idx_recognition_attempts_artwork
    ON recognition_attempts(artwork_id);
CREATE INDEX IF NOT EXISTS idx_recognition_attempts_outcome
    ON recognition_attempts(terminal_outcome, completed_at);
CREATE INDEX IF NOT EXISTS idx_product_events_trusted_time
    ON product_events(business_eligible, internal_test, occurred_at);
