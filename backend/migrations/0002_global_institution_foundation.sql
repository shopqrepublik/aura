CREATE TABLE IF NOT EXISTS countries (
    code VARCHAR(2) PRIMARY KEY,
    name VARCHAR NOT NULL,
    default_locale VARCHAR,
    default_timezone VARCHAR,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO countries (code, name, default_locale, default_timezone)
VALUES ('FR', 'France', 'fr', 'Europe/Paris')
ON CONFLICT (code) DO NOTHING;

ALTER TABLE museums ADD COLUMN IF NOT EXISTS country_code VARCHAR(2) REFERENCES countries(code);
ALTER TABLE museums ADD COLUMN IF NOT EXISTS timezone VARCHAR;
ALTER TABLE museums ADD COLUMN IF NOT EXISTS default_locale VARCHAR;
ALTER TABLE museums ADD COLUMN IF NOT EXISTS supported_locales JSONB;
ALTER TABLE museums ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

-- This is a migration of the current French Museofile dataset, not a global
-- application default. Future institutions must supply their own geography.
UPDATE museums SET
    country_code = COALESCE(country_code, 'FR'),
    timezone = COALESCE(timezone, 'Europe/Paris'),
    default_locale = COALESCE(default_locale, 'fr'),
    supported_locales = COALESCE(supported_locales, '["en", "fr", "zh-Hans"]'::jsonb);

CREATE TABLE IF NOT EXISTS collections (
    id VARCHAR PRIMARY KEY,
    institution_id VARCHAR NOT NULL REFERENCES museums(id),
    parent_id VARCHAR REFERENCES collections(id),
    slug VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    source VARCHAR,
    source_record_id VARCHAR,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_collections_institution_slug UNIQUE (institution_id, slug)
);

ALTER TABLE artworks ADD COLUMN IF NOT EXISTS collection_id VARCHAR REFERENCES collections(id);
CREATE INDEX IF NOT EXISTS idx_artworks_collection_id ON artworks(collection_id);

CREATE TABLE IF NOT EXISTS institution_profiles (
    institution_id VARCHAR PRIMARY KEY REFERENCES museums(id),
    visitor_catalog_version VARCHAR,
    candidate_universe VARCHAR NOT NULL DEFAULT 'NONE',
    recognition_policy VARCHAR NOT NULL DEFAULT 'NOT_READY',
    supported_modes JSONB NOT NULL DEFAULT '["normal", "simple", "kids"]'::jsonb,
    max_candidates INTEGER NOT NULL DEFAULT 5,
    confidence_auto DOUBLE PRECISION NOT NULL DEFAULT 0.92,
    confidence_review DOUBLE PRECISION NOT NULL DEFAULT 0.82,
    fuzzy_candidate_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.55,
    prompt_context TEXT,
    allow_recognition_asset_substitution BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_institution_profiles_candidate_universe
        CHECK (candidate_universe IN ('ACTIVE_CATALOG', 'INSTITUTION_ARTWORKS', 'NONE')),
    CONSTRAINT ck_institution_profiles_recognition_policy
        CHECK (recognition_policy IN ('TOP_N_METADATA', 'ASSET_VERIFY', 'UNCATALOGED_ONLY', 'NOT_READY'))
);

-- Every imported directory institution gets an explicit AI-guide profile.
-- NONE means open recognition may describe an uncataloged work, but no
-- catalog candidate can leak from another institution.
INSERT INTO institution_profiles (
    institution_id, candidate_universe, recognition_policy, supported_modes
)
SELECT id, 'NONE', 'UNCATALOGED_ONLY', '["normal", "simple", "kids"]'::jsonb
FROM museums
ON CONFLICT (institution_id) DO NOTHING;

-- An active visitor catalog is resolved from data, not a Python museum map.
WITH active_versions AS (
    SELECT museum_id, MAX(catalog_version) AS catalog_version
    FROM artwork_catalog_memberships
    WHERE active IS TRUE
    GROUP BY museum_id
)
UPDATE institution_profiles p SET
    visitor_catalog_version = v.catalog_version,
    candidate_universe = 'ACTIVE_CATALOG',
    recognition_policy = 'TOP_N_METADATA',
    updated_at = NOW()
FROM active_versions v
WHERE p.institution_id = v.museum_id;

-- These current catalogs predate membership versioning. This explicit data
-- preserves their deployed asset-verification behavior without core branches.
UPDATE institution_profiles SET
    candidate_universe = 'INSTITUTION_ARTWORKS',
    recognition_policy = 'ASSET_VERIFY',
    updated_at = NOW()
WHERE institution_id IN ('orsay', 'orangerie');

UPDATE institution_profiles SET prompt_context =
    'Musée du Louvre. The final identity must later be resolved against ELYIO''s own Louvre visitor catalog; do not invent or output an ARK id.'
WHERE institution_id = 'louvre';
UPDATE institution_profiles SET prompt_context =
    'Musée d''Orsay. The final identity must later be resolved against ELYIO''s own Orsay catalog.'
WHERE institution_id = 'orsay';
UPDATE institution_profiles SET prompt_context =
    'Musée de l''Orangerie. The final identity must later be resolved against ELYIO''s own Orangerie catalog.'
WHERE institution_id = 'orangerie';

-- Current Louvre RecognitionAssets stay quarantined until their identity
-- audit is resolved. The exception is configuration data, not core logic.
UPDATE institution_profiles SET allow_recognition_asset_substitution = FALSE
WHERE institution_id = 'louvre';

CREATE INDEX IF NOT EXISTS idx_museums_country_active ON museums(country_code, active);
CREATE INDEX IF NOT EXISTS idx_institution_profiles_policy_active ON institution_profiles(recognition_policy, active);
