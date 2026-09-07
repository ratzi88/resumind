-- Keep explicit user decisions separate from automated onboarding detection.
-- Existing updates made after onboarding are preserved as manual decisions.
BEGIN;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'user_skills'
          AND column_name = 'manual_override'
    ) THEN
        ALTER TABLE user_skills ADD COLUMN manual_override BOOLEAN NOT NULL DEFAULT FALSE;
        UPDATE user_skills us SET manual_override = TRUE
        FROM user_profiles p
        WHERE p.user_id = us.user_id AND us.updated_at > p.updated_at;
    END IF;
END $$;
COMMIT;
