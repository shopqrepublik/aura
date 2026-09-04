-- AI-only recognition is a successful product outcome even when no catalog
-- artwork row can be safely attached. Preserve the existing terminal-outcome
-- vocabulary and extend it additively.
ALTER TABLE recognition_attempts
    DROP CONSTRAINT IF EXISTS ck_recognition_attempt_terminal_outcome;

ALTER TABLE recognition_attempts
    ADD CONSTRAINT ck_recognition_attempt_terminal_outcome CHECK (
        terminal_outcome IS NULL OR terminal_outcome IN (
            'success', 'ai_result', 'no_match', 'uncataloged_result',
            'invalid_image', 'timeout', 'failed', 'institution_not_ready'
        )
    );
