-- ResuMind database schema.
-- Safe to run repeatedly against a fresh database or an existing installation.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    resume_text TEXT,
    resume_filename TEXT,
    desired_role TEXT,
    onboarding_done BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_skills (
    role TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'General',
    impact INTEGER NOT NULL DEFAULT 1 CHECK (impact > 0),
    stage INTEGER NOT NULL DEFAULT 1 CHECK (stage BETWEEN 1 AND 4),
    PRIMARY KEY (role, skill_name)
);

CREATE TABLE IF NOT EXISTS user_skills (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    acquired BOOLEAN NOT NULL DEFAULT FALSE,
    manual_override BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role, skill_name)
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT,
    skills_desc TEXT,
    experience_level TEXT,
    work_type TEXT,
    remote BOOLEAN,
    apply_url TEXT,
    max_salary NUMERIC,
    med_salary NUMERIC,
    min_salary NUMERIC,
    pay_period TEXT,
    currency TEXT,
    compensation_type TEXT,
    listed_time BIGINT,
    expiry BIGINT,
    closed_time BIGINT,
    industry TEXT,
    company_size INTEGER,
    employee_count INTEGER,
    benefits TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add fields to installations created from the original minimal schema.
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS onboarding_done BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE user_skills ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
-- Same preservation rule as migrations/20260907_roadmap_manual_override.sql.
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
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS max_salary NUMERIC;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS med_salary NUMERIC;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS min_salary NUMERIC;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS pay_period TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS currency TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS compensation_type TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS listed_time BIGINT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS expiry BIGINT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS closed_time BIGINT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS industry TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_size INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS employee_count INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS benefits TEXT;
ALTER TABLE role_skills ADD COLUMN IF NOT EXISTS stage INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS jobs_work_type_idx ON jobs(work_type);
CREATE INDEX IF NOT EXISTS jobs_experience_level_idx ON jobs(experience_level);
CREATE INDEX IF NOT EXISTS jobs_remote_idx ON jobs(remote);
CREATE INDEX IF NOT EXISTS jobs_salary_idx ON jobs(min_salary, max_salary);
CREATE INDEX IF NOT EXISTS jobs_embedding_idx
    ON jobs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
