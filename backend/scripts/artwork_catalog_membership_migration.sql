-- ELYIO versioned visitor catalog membership.
--
-- Scope:
--   * Add artwork_catalog_memberships as an explicit subset/version layer.
--   * Preserve all existing artworks as museum knowledge rows.
--   * No DELETE, DROP, TRUNCATE, table recreation, or destructive rewrites.
--
-- Louvre invariant after production reconciliation:
--   artworks where museum_id='louvre' may exceed 500.
--   active memberships for catalog_version='2026-08-11-v1' must equal 500.

BEGIN;

CREATE TABLE IF NOT EXISTS artwork_catalog_memberships (
    id SERIAL PRIMARY KEY,
    artwork_id TEXT NOT NULL REFERENCES artworks(id),
    museum_id TEXT NOT NULL REFERENCES museums(id),
    catalog_version TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    tier TEXT,
    visitor_priority DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_artwork_catalog_membership_version UNIQUE (artwork_id, catalog_version)
);

CREATE INDEX IF NOT EXISTS idx_artwork_catalog_memberships_museum_version_active
    ON artwork_catalog_memberships (museum_id, catalog_version, active);

CREATE INDEX IF NOT EXISTS idx_artwork_catalog_memberships_artwork_id
    ON artwork_catalog_memberships (artwork_id);

COMMIT;
