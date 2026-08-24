-- 0007_visual_candidate_retrieval
-- Non-destructive, versioned visual descriptors for cheap bounded retrieval.
ALTER TABLE recognition_assets
    ADD COLUMN IF NOT EXISTS visual_descriptor JSONB;

CREATE INDEX IF NOT EXISTS idx_recognition_assets_visual_descriptor_version
    ON recognition_assets ((visual_descriptor->>'version'))
    WHERE visual_descriptor IS NOT NULL;
