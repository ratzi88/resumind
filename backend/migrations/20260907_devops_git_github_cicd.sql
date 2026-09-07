-- Add explicit GitHub and CI/CD cards to the DevOps roadmap.
-- Git and GitHub share one original foundation weight; application logic keeps
-- their learned state synchronized.
BEGIN;

UPDATE role_skills
SET impact = 5
WHERE role = 'devops' AND skill_name = 'Git';

INSERT INTO role_skills (role, skill_name, category, impact, stage)
VALUES
    ('devops', 'GitHub', 'Stage 1', 5, 1),
    ('devops', 'CI/CD', 'Stage 4', 4, 4)
ON CONFLICT (role, skill_name) DO UPDATE
SET category = EXCLUDED.category,
    impact = EXCLUDED.impact,
    stage = EXCLUDED.stage;

COMMIT;
