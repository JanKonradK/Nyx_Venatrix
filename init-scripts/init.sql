-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  original_url   TEXT NOT NULL,
  canonical_url  TEXT NOT NULL,
  source         TEXT NOT NULL,    -- 'webapp', 'telegram', 'discovery'
  source_platform TEXT NOT NULL,   -- 'linkedin', 'indeed', 'company_site', etc.
  created_at     TIMESTAMPTZ DEFAULT now(),

  -- Metadata
  company_name   TEXT,
  title          TEXT,
  location       TEXT,
  description    TEXT,

  -- Resolution
  apply_url      TEXT,
  apply_platform TEXT,
  application_mode TEXT, -- 'external', 'platform_easy_apply'
  handling_mode  TEXT,   -- 'auto_apply', 'manual_only', 'ignore'
  requires_manual BOOLEAN DEFAULT false,
  manual_reason  TEXT,

  status         TEXT NOT NULL DEFAULT 'queued',
                 -- 'queued', 'skipped', 'in_progress', 'applied', 'failed', 'manual_only'

  -- Analytics
  cost_usd       NUMERIC DEFAULT 0,
  tokens_input   INT DEFAULT 0,
  tokens_output  INT DEFAULT 0
);

-- Embeddings Table (for RAG)
CREATE TABLE IF NOT EXISTS embeddings (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content     TEXT NOT NULL,
  embedding   vector(1536) NOT NULL, -- OpenAI text-embedding-3-small
  source      TEXT,                  -- Filename or origin
  metadata    JSONB,                 -- Extra info
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- CVs Table
CREATE TABLE IF NOT EXISTS cvs (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  label      TEXT NOT NULL,  -- 'DS-general', 'Frontend-Dev', etc.
  file_path  TEXT NOT NULL,  -- Path to PDF/Docx
  summary    TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Applications Table
CREATE TABLE IF NOT EXISTS applications (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id        UUID REFERENCES jobs(id),
  cv_id         UUID REFERENCES cvs(id),
  applied_at    TIMESTAMPTZ,
  outcome       TEXT,          -- 'submitted', 'error'
  raw_form_data JSONB,
  notes         TEXT
);

-- Application Answers (Log of Q&A)
CREATE TABLE IF NOT EXISTS application_answers (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id  UUID REFERENCES applications(id),
  question_label  TEXT,
  question_text   TEXT,
  answer_text     TEXT,
  model_name      TEXT,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Screenshots
CREATE TABLE IF NOT EXISTS screenshots (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id  UUID REFERENCES applications(id),
  step_name       TEXT,
  image_path      TEXT,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Salary Cache (for kdb+ or external API results)
CREATE TABLE IF NOT EXISTS salary_cache (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role       TEXT,
  location   TEXT,
  seniority  TEXT,
  yoe        INT,
  industry   TEXT,
  low        NUMERIC,
  mid        NUMERIC,
  high       NUMERIC,
  currency   TEXT,
  n_points   INT,
  cached_at  TIMESTAMPTZ DEFAULT now()
);
