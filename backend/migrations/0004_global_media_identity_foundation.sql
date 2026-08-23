ALTER TABLE countries ADD COLUMN IF NOT EXISTS default_currency VARCHAR(3);
ALTER TABLE countries ADD COLUMN IF NOT EXISTS content_policy JSONB;
ALTER TABLE museums ADD COLUMN IF NOT EXISTS display_currency VARCHAR(3);
ALTER TABLE museums ADD COLUMN IF NOT EXISTS content_policy JSONB;
ALTER TABLE institution_profiles ADD COLUMN IF NOT EXISTS directory_priority INTEGER NOT NULL DEFAULT 100;
ALTER TABLE artwork_value_reveals ADD COLUMN IF NOT EXISTS content_policy_code VARCHAR;
ALTER TABLE artwork_value_reveals ADD COLUMN IF NOT EXISTS institutional_legal_context_localizations JSONB;

UPDATE countries SET default_currency = 'EUR' WHERE code = 'FR' AND default_currency IS NULL;
UPDATE museums SET display_currency = 'EUR'
WHERE country_code = 'FR' AND display_currency IS NULL;
UPDATE institution_profiles SET directory_priority = CASE institution_id
    WHEN 'louvre' THEN 1 WHEN 'orsay' THEN 2 WHEN 'orangerie' THEN 3 ELSE directory_priority END;

-- Convert known reviewed legacy copy to an explicit policy/localization
-- boundary. No jurisdiction or legal conclusion is inferred for other text.
UPDATE artwork_value_reveals SET
    content_policy_code = 'FR_MUSEES_DE_FRANCE_INALIENABLE',
    institutional_legal_context_localizations = jsonb_build_object(
      'en', institutional_legal_context,
      'fr', 'Les collections publiques des Musées de France sont des biens publics inaliénables.',
      'zh-Hans', '法国 Musees de France 公共收藏属于不可转让的公共财产.'
    )
WHERE institutional_legal_context = 'French public Musees de France collections are inalienable public property.'
  AND content_policy_code IS NULL;

UPDATE artwork_value_reveals SET
    content_policy_code = 'GENERIC_PUBLIC_COLLECTION_CONTEXT',
    institutional_legal_context_localizations = jsonb_build_object(
      'en', institutional_legal_context,
      'fr', 'Contexte de collection publique ; ni expertise, ni valeur d''assurance, ni estimation de vente.',
      'zh-Hans', '公共收藏背景；并非鉴定估价、保险价值或出售估价。'
    )
WHERE institutional_legal_context IN (
    'Public cultural heritage context; not an appraisal, insurance value, or sale estimate.',
    'Public collection context; not an appraisal, insurance value, or sale estimate.'
) AND content_policy_code IS NULL;

CREATE TABLE IF NOT EXISTS cultural_objects (
    id VARCHAR PRIMARY KEY,
    object_kind VARCHAR NOT NULL DEFAULT 'PHYSICAL_OBJECT',
    canonical_title VARCHAR,
    canonical_creator VARCHAR,
    identity_status VARCHAR NOT NULL DEFAULT 'LEGACY_SINGLETON',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS source_providers (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    provider_type VARCHAR NOT NULL DEFAULT 'OTHER',
    base_url VARCHAR,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS institution_holdings (
    id VARCHAR PRIMARY KEY,
    cultural_object_id VARCHAR NOT NULL REFERENCES cultural_objects(id),
    institution_id VARCHAR NOT NULL REFERENCES museums(id),
    institution_record_id VARCHAR,
    collection_id VARCHAR REFERENCES collections(id),
    relationship_type VARCHAR NOT NULL DEFAULT 'HOLDING',
    status VARCHAR NOT NULL DEFAULT 'CURRENT',
    location_text TEXT,
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_holding_institution_record UNIQUE (institution_id, institution_record_id)
);
CREATE INDEX IF NOT EXISTS idx_institution_holdings_object ON institution_holdings(cultural_object_id);
CREATE INDEX IF NOT EXISTS idx_institution_holdings_institution_status ON institution_holdings(institution_id, status);

CREATE TABLE IF NOT EXISTS source_records (
    id VARCHAR PRIMARY KEY,
    provider_id VARCHAR NOT NULL REFERENCES source_providers(id),
    provider_record_id VARCHAR NOT NULL,
    cultural_object_id VARCHAR NOT NULL REFERENCES cultural_objects(id),
    institution_holding_id VARCHAR REFERENCES institution_holdings(id),
    institution_id VARCHAR REFERENCES museums(id),
    source_url VARCHAR,
    source_language VARCHAR,
    retrieved_at TIMESTAMPTZ,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_source_records_provider_record UNIQUE (provider_id, provider_record_id)
);
CREATE INDEX IF NOT EXISTS idx_source_records_object ON source_records(cultural_object_id);
CREATE INDEX IF NOT EXISTS idx_source_records_holding ON source_records(institution_holding_id);

CREATE TABLE IF NOT EXISTS cultural_object_identifiers (
    id BIGSERIAL PRIMARY KEY,
    cultural_object_id VARCHAR NOT NULL REFERENCES cultural_objects(id),
    namespace VARCHAR NOT NULL,
    identifier VARCHAR NOT NULL,
    verification_state VARCHAR NOT NULL DEFAULT 'DECLARED_BY_SOURCE',
    source_record_id VARCHAR REFERENCES source_records(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_object_identifier_namespace_value UNIQUE (namespace, identifier)
);
CREATE INDEX IF NOT EXISTS idx_object_identifiers_object ON cultural_object_identifiers(cultural_object_id);

CREATE TABLE IF NOT EXISTS cultural_object_duplicate_reviews (
    id BIGSERIAL PRIMARY KEY,
    object_a_id VARCHAR NOT NULL REFERENCES cultural_objects(id),
    object_b_id VARCHAR NOT NULL REFERENCES cultural_objects(id),
    decision VARCHAR NOT NULL DEFAULT 'POSSIBLE_DUPLICATE',
    evidence JSONB,
    reviewed_by VARCHAR,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_object_duplicate_pair UNIQUE (object_a_id, object_b_id),
    CONSTRAINT ck_object_duplicate_distinct CHECK (object_a_id <> object_b_id),
    CONSTRAINT ck_object_duplicate_decision CHECK (decision IN ('CONFIRMED_SAME', 'POSSIBLE_DUPLICATE', 'DISTINCT'))
);

ALTER TABLE artworks ADD COLUMN IF NOT EXISTS cultural_object_id VARCHAR REFERENCES cultural_objects(id);
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS institution_holding_id VARCHAR REFERENCES institution_holdings(id);
ALTER TABLE artworks ADD COLUMN IF NOT EXISTS source_language VARCHAR;

-- One conservative singleton object + holding per existing Artwork row.
-- This preserves every public artwork ID and makes no cross-record merge claim.
INSERT INTO cultural_objects (id, canonical_title, canonical_creator, identity_status)
SELECT 'object:' || id, title_original, artist, 'LEGACY_SINGLETON' FROM artworks
ON CONFLICT (id) DO NOTHING;

INSERT INTO institution_holdings (
    id, cultural_object_id, institution_id, institution_record_id,
    collection_id, relationship_type, status, location_text
)
SELECT
    'holding:' || id, 'object:' || id, museum_id,
    COALESCE(NULLIF(source_record_id, ''), NULLIF(inventory_number, ''), id),
    collection_id, 'HOLDING', 'CURRENT', COALESCE(current_location_raw, room, hall)
FROM artworks
ON CONFLICT (id) DO NOTHING;

UPDATE artworks SET
    cultural_object_id = 'object:' || id,
    institution_holding_id = 'holding:' || id
WHERE cultural_object_id IS NULL OR institution_holding_id IS NULL;

-- Compatibility bridge for existing import scripts during phased adapter
-- migration. New rows still receive stable object/holding identity even when
-- an old importer does not yet provide the normalized foreign keys.
CREATE OR REPLACE FUNCTION ensure_artwork_global_identity() RETURNS trigger AS $$
BEGIN
  IF NEW.cultural_object_id IS NULL THEN
    NEW.cultural_object_id := 'object:' || NEW.id;
    INSERT INTO cultural_objects (id, canonical_title, canonical_creator, identity_status)
    VALUES (NEW.cultural_object_id, NEW.title_original, NEW.artist, 'LEGACY_SINGLETON')
    ON CONFLICT (id) DO NOTHING;
  END IF;
  IF NEW.institution_holding_id IS NULL THEN
    NEW.institution_holding_id := 'holding:' || NEW.id;
    INSERT INTO institution_holdings (
      id, cultural_object_id, institution_id, institution_record_id,
      collection_id, relationship_type, status, location_text
    ) VALUES (
      NEW.institution_holding_id, NEW.cultural_object_id, NEW.museum_id,
      COALESCE(NULLIF(NEW.source_record_id, ''), NULLIF(NEW.inventory_number, ''), NEW.id),
      NEW.collection_id, 'HOLDING', 'CURRENT', COALESCE(NEW.current_location_raw, NEW.room, NEW.hall)
    ) ON CONFLICT (id) DO NOTHING;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_artworks_global_identity ON artworks;
CREATE TRIGGER trg_artworks_global_identity
BEFORE INSERT ON artworks
FOR EACH ROW EXECUTE FUNCTION ensure_artwork_global_identity();

ALTER TABLE artworks ALTER COLUMN cultural_object_id SET NOT NULL;
ALTER TABLE artworks ALTER COLUMN institution_holding_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_artworks_cultural_object ON artworks(cultural_object_id);
CREATE INDEX IF NOT EXISTS idx_artworks_holding ON artworks(institution_holding_id);

INSERT INTO source_providers (id, name, provider_type)
SELECT DISTINCT source, source, 'CATALOG_PROVIDER'
FROM artworks WHERE source IS NOT NULL AND source <> ''
ON CONFLICT (id) DO NOTHING;
INSERT INTO source_providers (id, name, provider_type) VALUES
    ('legacy_presentation', 'Legacy presentation URL', 'LEGACY'),
    ('louvre_collections', 'Louvre Collections', 'MUSEUM'),
    ('unknown', 'Unknown legacy provider', 'LEGACY')
ON CONFLICT (id) DO NOTHING;
INSERT INTO source_providers (id, name, provider_type)
SELECT DISTINCT source, source, 'MEDIA_PROVIDER'
FROM recognition_assets WHERE source IS NOT NULL AND source <> ''
ON CONFLICT (id) DO NOTHING;

INSERT INTO source_records (
    id, provider_id, provider_record_id, cultural_object_id,
    institution_holding_id, institution_id, source_url, source_language,
    retrieved_at, raw_payload
)
SELECT
    'source-record:' || md5(source || E'\x1f' || source_record_id),
    source, source_record_id, cultural_object_id, institution_holding_id,
    museum_id, source_url, source_language, last_source_sync, raw_json
FROM artworks
WHERE source IS NOT NULL AND source <> '' AND source_record_id IS NOT NULL AND source_record_id <> ''
ON CONFLICT (provider_id, provider_record_id) DO NOTHING;

INSERT INTO cultural_object_identifiers (cultural_object_id, namespace, identifier, verification_state, source_record_id)
SELECT
    a.cultural_object_id, 'provider:' || a.source, a.source_record_id,
    'DECLARED_BY_SOURCE', sr.id
FROM artworks a
LEFT JOIN source_records sr ON sr.provider_id = a.source AND sr.provider_record_id = a.source_record_id
WHERE a.source IS NOT NULL AND a.source <> '' AND a.source_record_id IS NOT NULL AND a.source_record_id <> ''
ON CONFLICT (namespace, identifier) DO NOTHING;

CREATE TABLE IF NOT EXISTS media_assets (
    id VARCHAR PRIMARY KEY,
    cultural_object_id VARCHAR NOT NULL REFERENCES cultural_objects(id),
    artwork_id VARCHAR REFERENCES artworks(id),
    institution_holding_id VARCHAR REFERENCES institution_holdings(id),
    source_record_id VARCHAR REFERENCES source_records(id),
    provider_id VARCHAR NOT NULL REFERENCES source_providers(id),
    purpose VARCHAR NOT NULL,
    media_type VARCHAR NOT NULL DEFAULT 'IMAGE',
    original_url VARCHAR,
    asset_url VARCHAR,
    provider_asset_id VARCHAR,
    rights_status VARCHAR NOT NULL DEFAULT 'UNKNOWN',
    verification_state VARCHAR NOT NULL DEFAULT 'UNKNOWN',
    license_code VARCHAR,
    license_text TEXT,
    attribution TEXT,
    public_domain BOOLEAN,
    presentation_eligible BOOLEAN,
    recognition_eligible BOOLEAN,
    retrieved_at TIMESTAMPTZ,
    checksum_sha256 VARCHAR(64),
    derivative_of_id VARCHAR REFERENCES media_assets(id),
    derivative_spec JSONB,
    legacy_source_table VARCHAR,
    legacy_source_id VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_media_provider_url_purpose UNIQUE (provider_id, original_url, purpose),
    CONSTRAINT ck_media_purpose CHECK (purpose IN ('PRESENTATION','REFERENCE','RECOGNITION_ASSET','SOURCE_ORIGINAL','DERIVATIVE')),
    CONSTRAINT ck_media_rights CHECK (rights_status IN ('VERIFIED_PUBLIC_DOMAIN','LICENSED','UNKNOWN','RESTRICTED')),
    CONSTRAINT ck_media_verification CHECK (verification_state IN ('VERIFIED','DECLARED_BY_SOURCE','UNKNOWN','RESTRICTED'))
);
CREATE INDEX IF NOT EXISTS idx_media_assets_object_purpose ON media_assets(cultural_object_id, purpose);
CREATE INDEX IF NOT EXISTS idx_media_assets_artwork ON media_assets(artwork_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_rights ON media_assets(rights_status, verification_state);
CREATE INDEX IF NOT EXISTS idx_media_assets_derivative ON media_assets(derivative_of_id);

-- Existing presentation is preserved operationally, but its rights are not invented.
INSERT INTO media_assets (
    id, cultural_object_id, artwork_id, institution_holding_id, provider_id,
    purpose, original_url, asset_url, rights_status, verification_state,
    presentation_eligible, recognition_eligible, legacy_source_table, legacy_source_id
)
SELECT
    'presentation:' || id, cultural_object_id, id, institution_holding_id,
    'legacy_presentation', 'PRESENTATION', image_url, image_url,
    'UNKNOWN', 'UNKNOWN', NULL, FALSE, 'artworks', id
FROM artworks WHERE image_url IS NOT NULL AND image_url <> ''
ON CONFLICT DO NOTHING;

INSERT INTO media_assets (
    id, cultural_object_id, artwork_id, institution_holding_id, provider_id,
    purpose, original_url, asset_url, rights_status, verification_state,
    license_code, attribution, public_domain, presentation_eligible,
    recognition_eligible, legacy_source_table, legacy_source_id, created_at, updated_at
)
SELECT
    'recognition:' || ra.id, a.cultural_object_id, a.id, a.institution_holding_id,
    COALESCE(NULLIF(ra.source, ''), 'unknown'), 'RECOGNITION_ASSET', ra.source_url, ra.source_url,
    CASE
      WHEN lower(COALESCE(ra.rights_status, '')) = 'public_domain' THEN 'VERIFIED_PUBLIC_DOMAIN'
      WHEN lower(COALESCE(ra.rights_status, '')) IN ('cc_licensed','proprietary_licensed') THEN 'LICENSED'
      WHEN lower(COALESCE(ra.rights_status, '')) IN ('rights_restricted','restricted') THEN 'RESTRICTED'
      ELSE 'UNKNOWN'
    END,
    CASE WHEN ra.license IS NOT NULL OR ra.rights_status IS NOT NULL OR ra.attribution IS NOT NULL
      THEN 'DECLARED_BY_SOURCE' ELSE 'UNKNOWN' END,
    ra.license, ra.attribution,
    CASE WHEN lower(COALESCE(ra.rights_status, '')) = 'public_domain' THEN TRUE ELSE NULL END,
    NULL, (COALESCE(ra.ai_tdm_eligible, FALSE) AND COALESCE(ra.embedding_eligible, FALSE)),
    'recognition_assets', ra.id::VARCHAR, ra.created_at, ra.updated_at
FROM recognition_assets ra JOIN artworks a ON a.id = ra.artwork_id
ON CONFLICT DO NOTHING;

INSERT INTO media_assets (
    id, cultural_object_id, artwork_id, institution_holding_id, provider_id,
    purpose, original_url, asset_url, rights_status, verification_state,
    attribution, presentation_eligible, recognition_eligible,
    legacy_source_table, legacy_source_id
)
SELECT
    'louvre-reference:' || lir.id, a.cultural_object_id, a.id, a.institution_holding_id,
    'louvre_collections', 'REFERENCE', lir.url_image, lir.url_thumbnail,
    'UNKNOWN', CASE WHEN lir.image_copyright IS NOT NULL OR lir.image_credit IS NOT NULL
      THEN 'DECLARED_BY_SOURCE' ELSE 'UNKNOWN' END,
    COALESCE(lir.image_credit, lir.image_copyright), NULL, FALSE,
    'louvre_image_references', lir.id::VARCHAR
FROM louvre_image_references lir JOIN artworks a ON a.id = lir.artwork_id
ON CONFLICT DO NOTHING;

ALTER TABLE recognition_attempts ADD COLUMN IF NOT EXISTS engine_outcome VARCHAR;
ALTER TABLE recognition_attempts ADD COLUMN IF NOT EXISTS visitor_resolution VARCHAR;
CREATE INDEX IF NOT EXISTS idx_recognition_attempts_engine_resolution
    ON recognition_attempts(engine_outcome, visitor_resolution, completed_at);
