-- Unknown-museum recognition is valid; preserve NULL rather than a fake id.
ALTER TABLE recognition_attempts ALTER COLUMN institution_id DROP NOT NULL;
