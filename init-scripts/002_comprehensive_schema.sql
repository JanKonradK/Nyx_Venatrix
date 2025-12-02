-- ============================================================================
-- Nyx Venatrix: Comprehensive Database Schema
-- Version: 2.0
-- Python: 3.12 | Embeddings: OpenAI text-embedding-3-small | Agents: Ray
-- ============================================================================
-- This schema supports:
--   • Multi-user job application system
--   • Session-based batch processing
--   • Multi-agent concurrency (Ray)
--   • Email integration (Saturnus)
--   • Interview tracking and prep
--   • LLM usage and cost tracking
--   • QA and policy enforcement
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- ============================================================================
-- 1. CORE IDENTITY & USER PROFILES
-- ============================================================================

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id TEXT UNIQUE,  -- GitHub/Google ID if applicable
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  timezone TEXT DEFAULT 'UTC',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  is_active BOOLEAN DEFAULT true,
  notes TEXT
);

CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  profile_name TEXT NOT NULL,  -- 'AI_ML_Tech', 'Finance', etc.
  headline TEXT,
  summary_text TEXT,
  skills_true JSONB DEFAULT '[]',  -- Skills user actually has
  skills_false JSONB DEFAULT '[]',  -- Skills to never claim
  languages JSONB DEFAULT '[]',  -- [{lang: 'English', level: 'C2'}]
  location_preference TEXT,
  role_preferences JSONB DEFAULT '{}',  -- {titles: [], domains: []}
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  is_active BOOLEAN DEFAULT true,
  UNIQUE(user_id, profile_name)
);

CREATE TABLE resumes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_profile_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  resume_key TEXT NOT NULL,  -- 'master_ai_ml', 'finance_cv'
  display_name TEXT NOT NULL,
  description TEXT,
  primary_language TEXT DEFAULT 'en',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  is_active BOOLEAN DEFAULT true,
  UNIQUE(user_profile_id, resume_key)
);

CREATE TABLE resume_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
  version_number INT NOT NULL,
  source_format TEXT NOT NULL,  -- 'latex', 'pdf', 'txt'
  file_path TEXT NOT NULL,
  content_text TEXT,  -- Full plaintext for embeddings
  content_hash TEXT NOT NULL,
  generated_by TEXT DEFAULT 'human',  -- 'human', 'llm', 'mixed'
  created_at TIMESTAMPTZ DEFAULT now(),
  is_default_for_resume BOOLEAN DEFAULT false,
  UNIQUE(resume_id, version_number),
  CHECK (source_format IN ('latex', 'pdf', 'txt', 'docx')),
  CHECK (generated_by IN ('human', 'llm', 'mixed'))
);

CREATE TABLE cover_letter_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_profile_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  template_name TEXT NOT NULL,
  base_text TEXT NOT NULL,
  intended_effort_level TEXT DEFAULT 'medium',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CHECK (intended_effort_level IN ('medium', 'high'))
);

-- ============================================================================
-- 2. JOB SOURCING & POSTINGS
-- ============================================================================

CREATE TABLE job_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,  -- 'LinkedIn', 'CompanySite', 'StepStone'
  source_type TEXT NOT NULL,  -- 'job_board', 'company_site', 'referral'
  base_url TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CHECK (source_type IN ('job_board', 'company_site', 'referral', 'other'))
);

CREATE TABLE companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  canonical_domain TEXT UNIQUE,
  hq_city TEXT,
  hq_country TEXT,
  industry TEXT,
  size_bucket TEXT,  -- '0-50', '50-200', '200-1000', '1000+'
  tier TEXT DEFAULT 'normal',  -- 'top', 'normal', 'avoid'
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CHECK (tier IN ('top', 'normal', 'avoid'))
);

CREATE TABLE company_properties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  key TEXT NOT NULL,  -- 'avg_reply_time_days', 'interview_rate'
  value JSONB,
  source TEXT DEFAULT 'computed',  -- 'computed', 'manual', 'external_api'
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(company_id, key),
  CHECK (source IN ('computed', 'manual', 'external_api'))
);

CREATE TABLE job_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_source_id UUID REFERENCES job_sources(id),
  company_id UUID REFERENCES companies(id),
  source_url TEXT NOT NULL,
  canonical_url TEXT,
  job_title TEXT,
  raw_location TEXT,
  location_city TEXT,
  location_country TEXT,
  employment_type TEXT,  -- 'full_time', 'part_time', 'contract', 'intern'
  seniority_level TEXT,  -- 'junior', 'mid', 'senior', 'lead', 'executive'
  department TEXT,
  posting_datetime TIMESTAMPTZ,
  scraped_html TEXT,
  description_raw TEXT,
  description_clean TEXT,
  embedding_vector_id TEXT,  -- Reference to Qdrant or embeddings table
  is_remote_allowed BOOLEAN DEFAULT false,
  compensation_currency TEXT,
  compensation_min NUMERIC,
  compensation_max NUMERIC,
  compensation_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CHECK (employment_type IN ('full_time', 'part_time', 'contract', 'intern', 'temporary', 'other')),
  CHECK (seniority_level IN ('intern', 'junior', 'mid', 'senior', 'lead', 'executive', 'other'))
);

CREATE TABLE job_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL,  -- 'skill', 'tech', 'domain', 'seniority'
  created_at TIMESTAMPTZ DEFAULT now(),
  CHECK (category IN ('skill', 'tech', 'domain', 'seniority', 'other'))
);

CREATE TABLE job_post_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_post_id UUID NOT NULL REFERENCES job_posts(id) ON DELETE CASCADE,
  job_tag_id UUID NOT NULL REFERENCES job_tags(id) ON DELETE CASCADE,
  UNIQUE(job_post_id, job_tag_id)
);

-- ============================================================================
-- 3. APPLICATION SESSIONS & HIGH-LEVEL CONTROL
-- ============================================================================

CREATE TABLE application_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_name TEXT,
  start_datetime TIMESTAMPTZ DEFAULT now(),
  end_datetime TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'planned',
  max_applications INT,
  max_duration_seconds INT,
  max_parallel_agents INT DEFAULT 5,
  config_snapshot JSONB DEFAULT '{}',  -- Stealth config, thresholds, etc.
  total_applications_attempted INT DEFAULT 0,
  total_applications_successful INT DEFAULT 0,
  total_tokens_input INT DEFAULT 0,
  total_tokens_output INT DEFAULT 0,
  total_cost_estimated NUMERIC DEFAULT 0,
  num_low_effort INT DEFAULT 0,
  num_medium_effort INT DEFAULT 0,
  num_high_effort INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CHECK (status IN ('planned', 'running', 'completed', 'paused', 'failed'))
);

CREATE TABLE session_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES application_sessions(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  message TEXT,
  payload JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- 4. APPLICATIONS (NYX CORE)
-- ============================================================================

CREATE TABLE applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id UUID REFERENCES application_sessions(id) ON DELETE SET NULL,
  job_post_id UUID NOT NULL REFERENCES job_posts(id) ON DELETE CASCADE,

  -- Effort & matching
  effort_level TEXT NOT NULL DEFAULT 'medium',
  effort_hint_source TEXT DEFAULT 'user',  -- 'user', 'auto'
  match_score NUMERIC CHECK (match_score >= 0 AND match_score <= 1),

  -- Resume & profile selection
  selected_resume_id UUID REFERENCES resumes(id),
  selected_resume_version_id UUID REFERENCES resume_versions(id),
  profile_id UUID REFERENCES user_profiles(id),

  -- Cover letter
  cover_letter_template_id UUID REFERENCES cover_letter_templates(id),
  cover_letter_text TEXT,
  cover_letter_generated_by TEXT,  -- 'llm', 'mixed', 'none'

  -- Application lifecycle
  application_status TEXT NOT NULL DEFAULT 'queued',
  application_started_at TIMESTAMPTZ,
  application_submitted_at TIMESTAMPTZ,
  success_flag BOOLEAN DEFAULT false,

  -- Confirmation
  final_confirmation_type TEXT,  -- 'confirmation_page', 'confirmation_email', 'unknown'
  final_confirmation_screenshot_path TEXT,

  -- Failure tracking
  failure_reason_code TEXT,
  failure_reason_detail TEXT,
  manual_followup_needed BOOLEAN DEFAULT false,

  -- Observability
  mlflow_run_id TEXT,
  langfuse_trace_id TEXT,

  -- Metrics
  domain_name TEXT,
  tokens_input_total INT DEFAULT 0,
  tokens_output_total INT DEFAULT 0,
  cost_estimated_total NUMERIC DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  CHECK (effort_level IN ('low', 'medium', 'high')),
  CHECK (effort_hint_source IN ('user', 'auto')),
  CHECK (cover_letter_generated_by IN ('llm', 'mixed', 'none', 'template')),
  CHECK (application_status IN ('queued', 'in_progress', 'submitted', 'failed', 'paused')),
  CHECK (final_confirmation_type IN ('confirmation_page', 'confirmation_email', 'unknown', 'none'))
);

CREATE TABLE application_status_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  old_status TEXT,
  new_status TEXT NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT now(),
  reason TEXT,
  actor TEXT DEFAULT 'system',  -- 'system', 'user', 'qa_agent'
  CHECK (actor IN ('system', 'user', 'qa_agent'))
);

CREATE TABLE application_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  step_index INT NOT NULL,  -- Order in flow
  page_url TEXT,

  -- Field identification
  field_type TEXT NOT NULL,
  field_label_raw TEXT,
  field_label_normalized TEXT,
  field_name_attr TEXT,
  field_id_attr TEXT,
  placeholder_text TEXT,

  -- Value & metadata
  is_required BOOLEAN DEFAULT false,
  value_filled TEXT,
  value_source TEXT,  -- 'profile', 'llm', 'default', 'manual_correction'
  effort_level_at_time TEXT,
  confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1),

  -- Validation & correction
  validation_error_message TEXT,
  corrected_value TEXT,
  corrected_by TEXT,  -- 'qa_agent', 'user'

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  CHECK (field_type IN ('text', 'textarea', 'select', 'checkbox', 'radio', 'upload', 'date', 'unknown')),
  CHECK (value_source IN ('profile', 'llm', 'default', 'manual_correction', 'template')),
  CHECK (corrected_by IN ('qa_agent', 'user', 'system'))
);

CREATE TABLE application_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  step_index INT NOT NULL,
  action_type TEXT NOT NULL,
  description TEXT,
  page_url TEXT,
  dom_selector TEXT,
  screenshot_path TEXT,
  timestamp_start TIMESTAMPTZ DEFAULT now(),
  timestamp_end TIMESTAMPTZ,
  success BOOLEAN DEFAULT true,
  error_message TEXT,
  CHECK (action_type IN ('navigate', 'click', 'fill_field', 'select_option', 'upload_file', 'submit_form', 'wait', 'other'))
);

-- ============================================================================
-- 5. EVENTS, ERRORS, CAPTCHAs, 2FA
-- ============================================================================

CREATE TABLE application_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
  session_id UUID REFERENCES application_sessions(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  event_detail TEXT,
  payload JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);
COMMENT ON TABLE application_events IS 'Central append-only event log for all application lifecycle events';

CREATE TABLE captcha_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  provider TEXT,  -- 'hcaptcha', 'recaptcha_v2', 'recaptcha_v3', 'unknown'
  attempt_number INT DEFAULT 1,
  status TEXT NOT NULL,  -- 'attempted', 'solved', 'failed', 'skipped'
  solver_type TEXT,  -- 'agent', 'human', 'external_service'
  created_at TIMESTAMPTZ DEFAULT now(),
  CHECK (provider IN ('hcaptcha', 'recaptcha_v2', 'recaptcha_v3', 'cloudflare', 'unknown')),
  CHECK (status IN ('attempted', 'solved', 'failed', 'skipped')),
  CHECK (solver_type IN ('agent', 'human', 'external_service', '2captcha'))
);

CREATE TABLE two_factor_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  method TEXT NOT NULL,  -- 'sms', 'email', 'app'
  requested_at TIMESTAMPTZ DEFAULT now(),
  code_supplied_at TIMESTAMPTZ,
  status TEXT NOT NULL,  -- 'pending', 'completed', 'failed', 'skipped'
  notes TEXT,
  CHECK (method IN ('sms', 'email', 'app', 'unknown')),
  CHECK (status IN ('pending', 'completed', 'failed', 'skipped'))
);

CREATE TABLE domain_rate_limits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_name TEXT NOT NULL UNIQUE,
  date DATE DEFAULT CURRENT_DATE,
  applications_attempted INT DEFAULT 0,
  applications_successful INT DEFAULT 0,
  applications_failed INT DEFAULT 0,
  last_block_timestamp TIMESTAMPTZ,
  is_temporarily_blocked BOOLEAN DEFAULT false,
  blocked_until TIMESTAMPTZ,
  notes TEXT,
  UNIQUE(domain_name, date)
);

-- ============================================================================
-- 6. LLM / MODEL USAGE & COST TRACKING
-- ============================================================================

CREATE TABLE model_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,  -- 'OpenAI', 'xAI', 'Anthropic'
  base_url TEXT,
  pricing_json JSONB DEFAULT '{}',  -- Snapshot of known prices
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE model_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
  session_id UUID REFERENCES application_sessions(id) ON DELETE CASCADE,
  provider_id UUID REFERENCES model_providers(id),
  model_name TEXT NOT NULL,
  call_type TEXT NOT NULL,  -- 'embedding', 'chat_completion', 'tool_call'
  tokens_input INT DEFAULT 0,
  tokens_output INT DEFAULT 0,
  cost_estimated NUMERIC DEFAULT 0,
  started_at TIMESTAMPTZ DEFAULT now(),
  ended_at TIMESTAMPTZ,
  purpose TEXT,  -- 'match_score', 'cover_letter', 'qa_check', 'profile_embedding'
  status TEXT DEFAULT 'success',
  error_message TEXT,
  CHECK (call_type IN ('embedding', 'chat_completion', 'tool_call', 'other')),
  CHECK (status IN ('success', 'failed', 'timeout'))
);

-- ============================================================================
-- 7. QA / POLICY ENFORCEMENT
-- ============================================================================

CREATE TABLE qa_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  qa_type TEXT NOT NULL,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  issues_found_count INT DEFAULT 0,
  notes TEXT,
  CHECK (qa_type IN ('hallucination_check', 'consistency_check', 'policy_compliance', 'other')),
  CHECK (status IN ('passed', 'issues_found', 'failed', 'skipped'))
);

CREATE TABLE qa_issues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  qa_check_id UUID NOT NULL REFERENCES qa_checks(id) ON DELETE CASCADE,
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  field_label TEXT,
  issue_type TEXT NOT NULL,
  description TEXT,
  suggested_fix TEXT,
  fix_applied BOOLEAN DEFAULT false,
  fixed_value TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- 8. SATURNUS: EMAIL & MATCHING
-- ============================================================================

CREATE TABLE email_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,  -- 'gmail', 'outlook', 'other'
  address TEXT NOT NULL UNIQUE,
  display_name TEXT,
  connection_config JSONB DEFAULT '{}',  -- IMAP/SMTP/OAuth tokens location
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  is_active BOOLEAN DEFAULT true,
  CHECK (provider IN ('gmail', 'outlook', 'imap', 'other'))
);

CREATE TABLE email_threads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_account_id UUID NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,
  thread_external_id TEXT NOT NULL,  -- Gmail thread ID, etc.
  subject_normalized TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(email_account_id, thread_external_id)
);

CREATE TABLE emails (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_account_id UUID NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,
  thread_id UUID REFERENCES email_threads(id) ON DELETE CASCADE,
  message_external_id TEXT NOT NULL,
  in_reply_to_message_id UUID REFERENCES emails(id),
  from_address TEXT NOT NULL,
  to_address TEXT NOT NULL,
  cc_addresses JSONB DEFAULT '[]',
  bcc_addresses JSONB DEFAULT '[]',
  subject TEXT,
  body_plain TEXT,
  body_html TEXT,
  received_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  direction TEXT NOT NULL,  -- 'inbound', 'outbound'
  raw_source_path TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  CHECK (direction IN ('inbound', 'outbound')),
  UNIQUE(email_account_id, message_external_id)
);

CREATE TABLE email_classifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  classification_label TEXT NOT NULL,
  eisenhower_quadrant TEXT,  -- 'Q1', 'Q2', 'Q3', 'Q4'
  importance_score NUMERIC CHECK (importance_score >= 0 AND importance_score <= 1),
  confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1),
  generated_by TEXT DEFAULT 'llm',  -- 'llm', 'rule'
  created_at TIMESTAMPTZ DEFAULT now(),
  CHECK (classification_label IN ('interview_invite', 'rejection', 'status_update', 'newsletter', 'confirmation', 'other')),
  CHECK (eisenhower_quadrant IN ('Q1', 'Q2', 'Q3', 'Q4')),
  CHECK (generated_by IN ('llm', 'rule', 'manual'))
);

CREATE TABLE email_application_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  link_type TEXT NOT NULL,
  confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1),
  created_at TIMESTAMPTZ DEFAULT now(),
  CHECK (link_type IN ('confirmation', 'interview_invite', 'rejection', 'status_update', 'other'))
);

CREATE TABLE email_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  action_type TEXT NOT NULL,
  action_payload JSONB DEFAULT '{}',  -- e.g., TickTick task ID
  created_at TIMESTAMPTZ DEFAULT now(),
  CHECK (action_type IN ('created_task', 'sent_reply', 'archived', 'labeled', 'forwarded', 'other'))
);

-- ============================================================================
-- 9. INTERVIEW PREP / OUTCOME TRACKING
-- ============================================================================

CREATE TABLE interviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  company_id UUID REFERENCES companies(id),
  interview_type TEXT NOT NULL,
  round_number INT DEFAULT 1,
  scheduled_datetime TIMESTAMPTZ,
  duration_minutes INT,
  location TEXT,  -- 'remote', 'onsite', 'hybrid'
  interviewer_names JSONB DEFAULT '[]',
  interviewer_roles JSONB DEFAULT '[]',
  calendar_event_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CHECK (interview_type IN ('phone_screen', 'technical', 'onsite', 'hr', 'behavioral', 'case_study', 'other')),
  CHECK (location IN ('remote', 'onsite', 'hybrid'))
);

CREATE TABLE interview_outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  interview_id UUID NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
  outcome TEXT NOT NULL,
  feedback_summary TEXT,
  offer_extended BOOLEAN DEFAULT false,
  offer_details JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  CHECK (outcome IN ('passed', 'failed', 'pending', 'withdrawn', 'no_show'))
);

CREATE TABLE interview_prep_packages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  interview_id UUID REFERENCES interviews(id) ON DELETE CASCADE,
  application_id UUID REFERENCES applications(id) ON DELETE CASCADE,  -- Can be standalone
  generated_at TIMESTAMPTZ DEFAULT now(),
  prep_document_path TEXT,
  topics_summary TEXT,
  company_research_notes TEXT,
  question_bank JSONB DEFAULT '[]',
  model_used TEXT,
  tokens_input INT DEFAULT 0,
  tokens_output INT DEFAULT 0,
  cost_estimated NUMERIC DEFAULT 0
);

-- ============================================================================
-- 10. SESSION DIGESTS & ANALYTICS SNAPSHOTS
-- ============================================================================

CREATE TABLE session_digests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES application_sessions(id) ON DELETE CASCADE,
  generated_at TIMESTAMPTZ DEFAULT now(),
  summary_text TEXT,
  applications_total INT DEFAULT 0,
  applications_successful INT DEFAULT 0,
  applications_failed INT DEFAULT 0,
  num_low_effort INT DEFAULT 0,
  num_medium_effort INT DEFAULT 0,
  num_high_effort INT DEFAULT 0,
  tokens_input_total INT DEFAULT 0,
  tokens_output_total INT DEFAULT 0,
  cost_estimated_total NUMERIC DEFAULT 0,
  avg_match_score NUMERIC,
  per_domain_stats JSONB DEFAULT '{}',
  per_company_tier_stats JSONB DEFAULT '{}',
  digest_email_sent BOOLEAN DEFAULT false,
  digest_email_id UUID REFERENCES emails(id)
);

CREATE TABLE company_metrics_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  applications_sent INT DEFAULT 0,
  applications_successful INT DEFAULT 0,
  interviews_received INT DEFAULT 0,
  offers_received INT DEFAULT 0,
  avg_response_time_days NUMERIC,
  last_response_datetime TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(company_id, date)
);

-- ============================================================================
-- 11. CONFIGURATION & VERSIONING
-- ============================================================================

CREATE TABLE system_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_name TEXT NOT NULL UNIQUE,
  config_json JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  created_by TEXT DEFAULT 'system',  -- 'user', 'system'
  is_active BOOLEAN DEFAULT true,
  CHECK (created_by IN ('user', 'system'))
);

CREATE TABLE domain_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_name TEXT NOT NULL UNIQUE,
  max_applications_per_day INT,
  min_seconds_between_applications INT,
  max_concurrent_applications INT DEFAULT 1,
  avoid_if_possible BOOLEAN DEFAULT false,
  last_reviewed_at TIMESTAMPTZ,
  notes TEXT
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Users & Profiles
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_resumes_profile_id ON resumes(user_profile_id);
CREATE INDEX idx_resume_versions_resume_id ON resume_versions(resume_id);

-- Jobs
CREATE INDEX idx_job_posts_company_id ON job_posts(company_id);
CREATE INDEX idx_job_posts_source_id ON job_posts(job_source_id);
CREATE INDEX idx_job_posts_created_at ON job_posts(created_at);
CREATE INDEX idx_job_post_tags_job_id ON job_post_tags(job_post_id);
CREATE INDEX idx_job_post_tags_tag_id ON job_post_tags(job_tag_id);

-- Sessions
CREATE INDEX idx_sessions_user_id ON application_sessions(user_id);
CREATE INDEX idx_sessions_status ON application_sessions(status);
CREATE INDEX idx_sessions_start_time ON application_sessions(start_datetime);
CREATE INDEX idx_session_events_session_id ON session_events(session_id);

-- Applications
CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_session_id ON applications(session_id);
CREATE INDEX idx_applications_job_post_id ON applications(job_post_id);
CREATE INDEX idx_applications_status ON applications(application_status);
CREATE INDEX idx_applications_effort ON applications(effort_level);
CREATE INDEX idx_applications_created_at ON applications(created_at);
CREATE INDEX idx_app_status_history_app_id ON application_status_history(application_id);
CREATE INDEX idx_app_questions_app_id ON application_questions(application_id);
CREATE INDEX idx_app_steps_app_id ON application_steps(application_id);

-- Events
CREATE INDEX idx_app_events_app_id ON application_events(application_id);
CREATE INDEX idx_app_events_session_id ON application_events(session_id);
CREATE INDEX idx_app_events_type ON application_events(event_type);
CREATE INDEX idx_captcha_events_app_id ON captcha_events(application_id);
CREATE INDEX idx_2fa_events_app_id ON two_factor_events(application_id);
CREATE INDEX idx_domain_limits_domain ON domain_rate_limits(domain_name);

-- Model Usage
CREATE INDEX idx_model_usage_app_id ON model_usage(application_id);
CREATE INDEX idx_model_usage_session_id ON model_usage(session_id);
CREATE INDEX idx_model_usage_provider ON model_usage(provider_id);

-- QA
CREATE INDEX idx_qa_checks_app_id ON qa_checks(application_id);
CREATE INDEX idx_qa_issues_check_id ON qa_issues(qa_check_id);
CREATE INDEX idx_qa_issues_app_id ON qa_issues(application_id);

-- Emails
CREATE INDEX idx_email_threads_account_id ON email_threads(email_account_id);
CREATE INDEX idx_emails_account_id ON emails(email_account_id);
CREATE INDEX idx_emails_thread_id ON emails(thread_id);
CREATE INDEX idx_emails_direction ON emails(direction);
CREATE INDEX idx_email_classifications_email_id ON email_classifications(email_id);
CREATE INDEX idx_email_app_links_email_id ON email_application_links(email_id);
CREATE INDEX idx_email_app_links_app_id ON email_application_links(application_id);

-- Interviews
CREATE INDEX idx_interviews_app_id ON interviews(application_id);
CREATE INDEX idx_interviews_company_id ON interviews(company_id);
CREATE INDEX idx_interview_outcomes_interview_id ON interview_outcomes(interview_id);

-- Analytics
CREATE INDEX idx_session_digests_session_id ON session_digests(session_id);
CREATE INDEX idx_company_metrics_company_id ON company_metrics_daily(company_id);
CREATE INDEX idx_company_metrics_date ON company_metrics_daily(date);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

CREATE OR REPLACE VIEW effort_mode_stats AS
SELECT
  effort_level,
  COUNT(*) as total_applications,
  COUNT(*) FILTER (WHERE application_status = 'submitted') as successful,
  COUNT(*) FILTER (WHERE application_status = 'failed') as failed,
  AVG(cost_estimated_total) as avg_cost,
  SUM(cost_estimated_total) as total_cost,
  AVG(tokens_input_total + tokens_output_total) as avg_tokens,
  ROUND(
    COUNT(*) FILTER (WHERE application_status = 'submitted')::NUMERIC /
    NULLIF(COUNT(*), 0) * 100,
    2
  ) as success_rate_pct
FROM applications
GROUP BY effort_level;

CREATE OR REPLACE VIEW captcha_stats AS
SELECT
  provider,
  COUNT(*) as total_attempts,
  COUNT(*) FILTER (WHERE status = 'solved') as solved_count,
  COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
  ROUND(
    COUNT(*) FILTER (WHERE status = 'solved')::NUMERIC /
    NULLIF(COUNT(*), 0) * 100,
    2
  ) as solve_rate_pct,
  solver_type
FROM captcha_events
GROUP BY provider, solver_type;

CREATE OR REPLACE VIEW company_performance AS
SELECT
  c.name,
  c.tier,
  COUNT(a.id) as total_applications,
  COUNT(*) FILTER (WHERE a.success_flag = true) as successful_applications,
  COUNT(i.id) as interviews_received,
  COUNT(io.id) FILTER (WHERE io.offer_extended = true) as offers_received,
  ROUND(
    COUNT(*) FILTER (WHERE a.success_flag = true)::NUMERIC /
    NULLIF(COUNT(a.id), 0) * 100,
    2
  ) as success_rate_pct
FROM companies c
LEFT JOIN applications a ON a.job_post_id IN (SELECT id FROM job_posts WHERE company_id = c.id)
LEFT JOIN interviews i ON i.application_id = a.id
LEFT JOIN interview_outcomes io ON io.interview_id = i.id
GROUP BY c.id, c.name, c.tier;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default model providers
INSERT INTO model_providers (name, base_url, pricing_json) VALUES
  ('OpenAI', 'https://api.openai.com/v1', '{"text-embedding-3-small": {"input": 0.00002}}'),
  ('xAI', 'https://api.x.ai/v1', '{"grok-beta": {"input": 0.000005, "output": 0.000015}}')
ON CONFLICT (name) DO NOTHING;

-- Insert default job sources
INSERT INTO job_sources (name, source_type, base_url) VALUES
  ('LinkedIn', 'job_board', 'https://www.linkedin.com/jobs/'),
  ('Indeed', 'job_board', 'https://www.indeed.com/'),
  ('StepStone', 'job_board', 'https://www.stepstone.de/'),
  ('CompanySite', 'company_site', NULL)
ON CONFLICT (name) DO NOTHING;

-- Insert default system config
INSERT INTO system_configs (config_name, config_json, is_active) VALUES
  ('default_stealth', '{
    "global": {
      "min_delay_between_apps_sec": 30,
      "max_delay_between_apps_sec": 180,
      "max_apps_per_session": 300
    },
    "randomization": {
      "keystroke_delay_ms": {"mean": 120, "stddev": 40},
      "inter_question_pause_sec": {"min": 0.5, "max": 3.0}
    }
  }', true)
ON CONFLICT (config_name) DO NOTHING;

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables with updated_at column
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resumes_updated_at BEFORE UPDATE ON resumes
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_posts_updated_at BEFORE UPDATE ON job_posts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON application_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  table_count INT;
BEGIN
  SELECT COUNT(*) INTO table_count
  FROM information_schema.tables
  WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

  RAISE NOTICE '✅ Schema created successfully';
  RAISE NOTICE '📊 Total tables: %', table_count;
  RAISE NOTICE '🔍 Expected: 40+ tables';

  IF table_count < 40 THEN
    RAISE WARNING 'Expected at least 40 tables, found %', table_count;
  END IF;
END $$;
