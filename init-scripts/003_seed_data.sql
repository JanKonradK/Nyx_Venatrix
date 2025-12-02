-- Seed data for testing Nyx Venatrix
-- Creates a test user, profile, resume, and sample companies

-- Create test user
INSERT INTO users (id, name, email, timezone, is_active)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'Jan Kruszynski', 'jan@example.com', 'Europe/Berlin', true)
ON CONFLICT (email) DO NOTHING;

-- Create test profile
INSERT INTO user_profiles (id, user_id, profile_name, headline, skills_true, skills_false, location_preference)
VALUES (
  '00000000-0000-0000-0000-000000000002',
  '00000000-0000-0000-0000-000000000001',
  'AI_ML_Engineer',
  'Senior AI & MLOps Engineer',
  '["Python", "Ray", "MLflow", "Docker", "PostgreSQL", "LLMs", "Agentic AI"]'::jsonb,
  '["Java", "C++", "PHP"]'::jsonb,
  'Berlin, Germany / Remote'
)
ON CONFLICT (user_id, profile_name) DO NOTHING;

-- Create test resume
INSERT INTO resumes (id, user_profile_id, resume_key, display_name, description, is_active)
VALUES (
  '00000000-0000-0000-0000-000000000003',
  '00000000-0000-0000-0000-000000000002',
  'master_ai_ml',
  'Master AI/ML Resume',
  'Primary resume for AI/ML positions',
  true
)
ON CONFLICT (user_profile_id, resume_key) DO NOTHING;

-- Create resume version
INSERT INTO resume_versions (id, resume_id, version_number, source_format, file_path, content_hash, is_default_for_resume)
VALUES (
  '00000000-0000-0000-0000-000000000004',
  '00000000-0000-0000-0000-000000000003',
  1,
  'pdf',
  '/data/resumes/jan_ai_ml_v1.pdf',
  'mock_hash_123',
  true
)
ON CONFLICT (resume_id, version_number) DO NOTHING;

-- Create sample companies
INSERT INTO companies (id, name, canonical_domain, tier) VALUES
  ('00000000-0000-0000-0000-000000000010', 'Google', 'google.com', 'top'),
  ('00000000-0000-0000-0000-000000000011', 'OpenAI', 'openai.com', 'top'),
  ('00000000-0000-0000-0000-000000000012', 'GenAI Corp', 'genai-corp.com', 'normal'),
  ('00000000-0000-0000-0000-000000000013', 'Scam Inc', 'scam.io', 'avoid')
ON CONFLICT (canonical_domain) DO NOTHING;

-- Create sample job posts
INSERT INTO job_posts (id, company_id, source_url, job_title, raw_location, description_clean) VALUES
  (
    '00000000-0000-0000-0000-000000000020',
    '00000000-0000-0000-0000-000000000010',
    'https://careers.google.com/jobs/results/123',
    'Senior ML Engineer',
    'Mountain View, CA',
    'We are looking for an experienced ML engineer to join our team...'
  ),
  (
    '00000000-0000-0000-0000-000000000021',
    '00000000-0000-0000-0000-000000000012',
    'https://genai-corp.com/careers/automation-engineer',
    'Senior Automation Engineer',
    'Berlin, Germany',
    'Join our team building the next generation of AI automation tools...'
  )
ON CONFLICT DO NOTHING;

-- Create domain policies
INSERT INTO domain_policies (domain_name, max_applications_per_day, min_seconds_between_applications) VALUES
  ('linkedin.com', 5, 300),
  ('greenhouse.io', 20, 60),
  ('myworkdayjobs.com', 10, 120)
ON CONFLICT (domain_name) DO NOTHING;

COMMENT ON TABLE users IS 'Seeded with test user Jan Kruszynski';
