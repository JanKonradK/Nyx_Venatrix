# Nyx Venatrix & Saturnus - Complete Database Schema

## Overview

This document defines the complete PostgreSQL database schema for the Nyx Venatrix job application agent and the future Saturnus email management system. The schema is designed to be:

- **Multi-user ready** from day one
- **Append-only** for audit trails (corrections, not deletions)
- **Shared** between Nyx and Saturnus via a single PostgreSQL instance
- **Extensible** for future projects (interview prep, analytics)

## Database Architecture

```
PostgreSQL Instance (shared_postgres)
├── nyx_venatrix database
│   ├── Core Identity (users, profiles, resumes)
│   ├── Job Sourcing (companies, job_posts)
│   ├── Applications (applications, questions, steps)
│   ├── Sessions (application_sessions, events)
│   ├── QA & Policy (qa_checks, qa_issues)
│   ├── LLM Tracking (model_usage)
│   └── Configuration (system_configs, domain_policies)
│
└── saturnus database
    ├── Email Management (email_accounts, emails, threads)
    ├── Classification (email_classifications)
    ├── Application Links (email_application_links)
    └── Actions (email_actions)
```

---

## Part 1: Core Identity / User Profile

### users
Even if it's "just you", design as multi-user from day one.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT,  -- Optional: GitHub/Google ID
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_external_id ON users(external_id) WHERE external_id IS NOT NULL;
```

### user_profiles
High-level professional profiles: AI/ML, Finance, Consulting, etc.

```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    profile_name TEXT NOT NULL,  -- e.g. "AI_ML_Tech", "Finance"
    headline TEXT,  -- Short tagline
    summary_text TEXT,  -- Full "about me" text
    skills_true JSONB DEFAULT '[]',  -- Skills you actually have
    skills_false JSONB DEFAULT '[]',  -- Skills to NOT claim
    languages JSONB DEFAULT '[]',  -- [{lang, level}]
    location_preference TEXT,
    role_preferences JSONB,  -- Titles, domains
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(user_id, profile_name)
);

CREATE INDEX idx_user_profiles_user ON user_profiles(user_id);
```

### resumes
Conceptual resumes, regardless of file versions.

```sql
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_profile_id UUID NOT NULL REFERENCES user_profiles(id),
    resume_key TEXT NOT NULL,  -- e.g. "master_ai_ml", "finance_cv"
    display_name TEXT NOT NULL,
    description TEXT,
    primary_language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(user_profile_id, resume_key)
);

CREATE INDEX idx_resumes_profile ON resumes(user_profile_id);
```

### resume_versions
Actual LaTeX/PDF/TXT variants.

```sql
CREATE TABLE resume_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id),
    version_number INTEGER NOT NULL,
    source_format TEXT NOT NULL CHECK (source_format IN ('latex', 'pdf', 'txt', 'docx')),
    file_path TEXT NOT NULL,  -- Local path or object storage URL
    content_text TEXT,  -- Full plain-text body for embeddings
    content_hash TEXT,  -- SHA256 for deduplication
    generated_by TEXT DEFAULT 'human' CHECK (generated_by IN ('human', 'llm', 'mixed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_default_for_resume BOOLEAN DEFAULT FALSE,

    UNIQUE(resume_id, version_number)
);

CREATE INDEX idx_resume_versions_resume ON resume_versions(resume_id);
CREATE INDEX idx_resume_versions_default ON resume_versions(resume_id) WHERE is_default_for_resume = TRUE;
```

### cover_letter_templates

```sql
CREATE TABLE cover_letter_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_profile_id UUID NOT NULL REFERENCES user_profiles(id),
    template_name TEXT NOT NULL,
    base_text TEXT NOT NULL,
    intended_effort_level TEXT CHECK (intended_effort_level IN ('medium', 'high')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_profile_id, template_name)
);
```

---

## Part 2: Job Sourcing & Postings

### job_sources
Where the job came from: LinkedIn, company site, StepStone, etc.

```sql
CREATE TABLE job_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,  -- "LinkedIn", "CompanySite", "StepStone"
    source_type TEXT NOT NULL CHECK (source_type IN ('job_board', 'company_site', 'referral', 'aggregator')),
    base_url TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed common sources
INSERT INTO job_sources (name, source_type, base_url) VALUES
    ('LinkedIn', 'job_board', 'https://www.linkedin.com'),
    ('Indeed', 'job_board', 'https://www.indeed.com'),
    ('Greenhouse', 'company_site', NULL),
    ('Workday', 'company_site', NULL),
    ('Lever', 'company_site', NULL),
    ('Direct', 'company_site', NULL);
```

### companies

```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    canonical_domain TEXT,  -- e.g. "google.com"
    hq_city TEXT,
    hq_country TEXT,
    industry TEXT,
    size_bucket TEXT CHECK (size_bucket IN ('1-50', '51-200', '201-1000', '1001-5000', '5001-10000', '10000+')),
    tier TEXT DEFAULT 'normal' CHECK (tier IN ('top', 'normal', 'avoid')),
    careers_page_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(name, canonical_domain)
);

CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_domain ON companies(canonical_domain);
CREATE INDEX idx_companies_tier ON companies(tier);
```

### company_properties
Extensible attributes for later analytics.

```sql
CREATE TABLE company_properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    key TEXT NOT NULL,  -- e.g. "avg_reply_time_days", "interview_rate"
    value JSONB NOT NULL,
    source TEXT DEFAULT 'manual' CHECK (source IN ('computed', 'manual', 'external_api')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(company_id, key)
);

CREATE INDEX idx_company_properties_company ON company_properties(company_id);
```

### job_posts
One row per actual job posting URL Nyx sees.

```sql
CREATE TABLE job_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_source_id UUID REFERENCES job_sources(id),
    company_id UUID REFERENCES companies(id),
    source_url TEXT NOT NULL,  -- Exact URL provided
    canonical_url TEXT,  -- Normalized URL if redirected
    job_title TEXT NOT NULL,
    raw_location TEXT,  -- As shown on page
    location_city TEXT,
    location_country TEXT,
    employment_type TEXT CHECK (employment_type IN ('full_time', 'part_time', 'contract', 'intern', 'freelance')),
    seniority_level TEXT CHECK (seniority_level IN ('intern', 'junior', 'mid', 'senior', 'lead', 'principal', 'director', 'vp', 'c_level')),
    department TEXT,  -- e.g. "Data Science", "Engineering"
    posting_datetime TIMESTAMPTZ,  -- If parseable from page
    scraped_html TEXT,  -- Optional, full HTML
    description_raw TEXT,
    description_clean TEXT,
    embedding_vector_id TEXT,  -- Reference to Qdrant vector
    is_remote_allowed BOOLEAN,
    compensation_currency TEXT,
    compensation_min NUMERIC,
    compensation_max NUMERIC,
    compensation_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source_url)
);

CREATE INDEX idx_job_posts_company ON job_posts(company_id);
CREATE INDEX idx_job_posts_source ON job_posts(job_source_id);
CREATE INDEX idx_job_posts_title ON job_posts(job_title);
CREATE INDEX idx_job_posts_location ON job_posts(location_country, location_city);
CREATE INDEX idx_job_posts_created ON job_posts(created_at DESC);
```

### job_tags
Normalized tags like "NLP", "GenAI", "Python".

```sql
CREATE TABLE job_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    category TEXT CHECK (category IN ('skill', 'tech', 'domain', 'seniority', 'benefit')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_job_tags_category ON job_tags(category);
```

### job_post_tags
Many-to-many relation between job_posts and tags.

```sql
CREATE TABLE job_post_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_post_id UUID NOT NULL REFERENCES job_posts(id),
    job_tag_id UUID NOT NULL REFERENCES job_tags(id),

    UNIQUE(job_post_id, job_tag_id)
);

CREATE INDEX idx_job_post_tags_post ON job_post_tags(job_post_id);
CREATE INDEX idx_job_post_tags_tag ON job_post_tags(job_tag_id);
```

---

## Part 3: Application Sessions & High-Level Control

### application_sessions
Your "runs"/batches.

```sql
CREATE TABLE application_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_name TEXT,
    start_datetime TIMESTAMPTZ DEFAULT NOW(),
    end_datetime TIMESTAMPTZ,
    status TEXT DEFAULT 'planned' CHECK (status IN ('planned', 'running', 'completed', 'paused', 'failed', 'cancelled')),
    max_applications INTEGER DEFAULT 200,
    max_duration_seconds INTEGER DEFAULT 7200,  -- 2 hours
    max_parallel_agents INTEGER DEFAULT 5,
    config_snapshot JSONB,  -- Stealth, thresholds, etc.
    total_applications_attempted INTEGER DEFAULT 0,
    total_applications_successful INTEGER DEFAULT 0,
    total_tokens_input BIGINT DEFAULT 0,
    total_tokens_output BIGINT DEFAULT 0,
    total_cost_estimated NUMERIC(10, 4) DEFAULT 0,
    num_low_effort INTEGER DEFAULT 0,
    num_medium_effort INTEGER DEFAULT 0,
    num_high_effort INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON application_sessions(user_id);
CREATE INDEX idx_sessions_status ON application_sessions(status);
CREATE INDEX idx_sessions_start ON application_sessions(start_datetime DESC);
```

### session_events
High-level events for sessions.

```sql
CREATE TABLE session_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES application_sessions(id),
    event_type TEXT NOT NULL,  -- "session_started", "session_completed", "session_paused", etc.
    message TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_session_events_session ON session_events(session_id);
CREATE INDEX idx_session_events_type ON session_events(event_type);
CREATE INDEX idx_session_events_created ON session_events(created_at DESC);
```

---

## Part 4: Applications (Nyx Core)

### applications

```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID REFERENCES application_sessions(id),
    job_post_id UUID NOT NULL REFERENCES job_posts(id),
    effort_level TEXT NOT NULL CHECK (effort_level IN ('low', 'medium', 'high')),
    effort_hint_source TEXT DEFAULT 'auto' CHECK (effort_hint_source IN ('user', 'auto')),
    match_score NUMERIC(4, 3),  -- 0.000 to 1.000
    selected_resume_id UUID REFERENCES resumes(id),
    selected_resume_version_id UUID REFERENCES resume_versions(id),
    profile_id UUID REFERENCES user_profiles(id),
    cover_letter_template_id UUID REFERENCES cover_letter_templates(id),
    cover_letter_text TEXT,
    cover_letter_generated_by TEXT CHECK (cover_letter_generated_by IN ('llm', 'mixed', 'none', 'template')),
    application_status TEXT DEFAULT 'queued' CHECK (application_status IN (
        'queued', 'in_progress', 'submitted', 'failed', 'paused', 'skipped', 'cancelled'
    )),
    application_started_at TIMESTAMPTZ,
    application_submitted_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    success_flag BOOLEAN,
    final_confirmation_type TEXT CHECK (final_confirmation_type IN ('confirmation_page', 'confirmation_email', 'unknown')),
    final_confirmation_screenshot_path TEXT,
    failure_reason_code TEXT,  -- "captcha_failed", "blocked_domain", "form_error", "timeout"
    failure_reason_detail TEXT,
    manual_followup_needed BOOLEAN DEFAULT FALSE,
    mlflow_run_id TEXT,
    langfuse_trace_id TEXT,
    domain_name TEXT,  -- e.g. "careers.company.com"
    tokens_input_total BIGINT DEFAULT 0,
    tokens_output_total BIGINT DEFAULT 0,
    cost_estimated_total NUMERIC(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_applications_user ON applications(user_id);
CREATE INDEX idx_applications_session ON applications(session_id);
CREATE INDEX idx_applications_job ON applications(job_post_id);
CREATE INDEX idx_applications_status ON applications(application_status);
CREATE INDEX idx_applications_effort ON applications(effort_level);
CREATE INDEX idx_applications_created ON applications(created_at DESC);
CREATE INDEX idx_applications_domain ON applications(domain_name);
```

### application_status_history
Audit trail of status changes.

```sql
CREATE TABLE application_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    reason TEXT,
    actor TEXT DEFAULT 'system' CHECK (actor IN ('system', 'user', 'qa_agent'))
);

CREATE INDEX idx_app_status_history_app ON application_status_history(application_id);
CREATE INDEX idx_app_status_history_changed ON application_status_history(changed_at DESC);
```

### application_questions
Every field the agent interacts with.

```sql
CREATE TABLE application_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    step_index INTEGER NOT NULL,  -- Order in the flow
    page_url TEXT,
    field_type TEXT CHECK (field_type IN ('text', 'textarea', 'select', 'checkbox', 'radio', 'upload', 'date', 'number', 'email', 'phone', 'url')),
    field_label_raw TEXT,
    field_label_normalized TEXT,  -- e.g. "years_of_experience"
    field_name_attr TEXT,  -- DOM name attribute
    field_id_attr TEXT,  -- DOM id attribute
    placeholder_text TEXT,
    is_required BOOLEAN DEFAULT FALSE,
    value_filled TEXT,
    value_source TEXT CHECK (value_source IN ('profile', 'llm', 'default', 'manual_correction', 'template')),
    effort_level_at_time TEXT,
    confidence_score NUMERIC(4, 3),  -- 0.000 to 1.000
    validation_error_message TEXT,
    corrected_value TEXT,
    corrected_by TEXT CHECK (corrected_by IN ('qa_agent', 'user')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_app_questions_app ON application_questions(application_id);
CREATE INDEX idx_app_questions_step ON application_questions(application_id, step_index);
CREATE INDEX idx_app_questions_label ON application_questions(field_label_normalized);
```

### application_steps
Optionally track fine-grained agent actions.

```sql
CREATE TABLE application_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    step_index INTEGER NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN (
        'navigate', 'click', 'fill_field', 'select_option', 'upload_file',
        'submit_form', 'wait', 'scroll', 'hover', 'captcha_solve', 'login'
    )),
    description TEXT,
    page_url TEXT,
    dom_selector TEXT,
    screenshot_path TEXT,
    timestamp_start TIMESTAMPTZ,
    timestamp_end TIMESTAMPTZ,
    success BOOLEAN,
    error_message TEXT
);

CREATE INDEX idx_app_steps_app ON application_steps(application_id);
CREATE INDEX idx_app_steps_order ON application_steps(application_id, step_index);
```

---

## Part 5: Events, Errors, CAPTCHAs, 2FA

### application_events
Central event log, append-only.

```sql
CREATE TABLE application_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),
    session_id UUID REFERENCES application_sessions(id),
    event_type TEXT NOT NULL,
    -- Examples: "captcha_detected", "captcha_solved", "captcha_failed",
    -- "two_factor_requested", "two_factor_supplied", "account_created",
    -- "login_failed", "domain_blocked", "qa_started", "qa_completed",
    -- "policy_violation_detected", "rate_limit_hit"
    event_detail TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_app_events_app ON application_events(application_id);
CREATE INDEX idx_app_events_session ON application_events(session_id);
CREATE INDEX idx_app_events_type ON application_events(event_type);
CREATE INDEX idx_app_events_created ON application_events(created_at DESC);
```

### captcha_events
Dedicated table for CAPTCHAs.

```sql
CREATE TABLE captcha_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    provider TEXT CHECK (provider IN ('hcaptcha', 'recaptcha_v2', 'recaptcha_v3', 'turnstile', 'funcaptcha', 'unknown')),
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('attempted', 'solved', 'failed', 'skipped', 'manual_required')),
    solver_type TEXT CHECK (solver_type IN ('agent', 'human', 'external_service')),
    solver_service TEXT,  -- e.g. "2captcha", "anticaptcha"
    solve_time_ms INTEGER,
    cost_cents NUMERIC(6, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_captcha_events_app ON captcha_events(application_id);
CREATE INDEX idx_captcha_events_status ON captcha_events(status);
```

### two_factor_events

```sql
CREATE TABLE two_factor_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    method TEXT CHECK (method IN ('sms', 'email', 'app', 'call')),
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    code_supplied_at TIMESTAMPTZ,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'skipped', 'timeout')),
    notes TEXT
);

CREATE INDEX idx_2fa_events_app ON two_factor_events(application_id);
CREATE INDEX idx_2fa_events_status ON two_factor_events(status);
```

### domain_rate_limits
Track "health"/limits per domain.

```sql
CREATE TABLE domain_rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_name TEXT NOT NULL,
    date DATE NOT NULL,
    applications_attempted INTEGER DEFAULT 0,
    applications_successful INTEGER DEFAULT 0,
    applications_failed INTEGER DEFAULT 0,
    last_block_timestamp TIMESTAMPTZ,
    is_temporarily_blocked BOOLEAN DEFAULT FALSE,
    blocked_until TIMESTAMPTZ,
    notes TEXT,

    UNIQUE(domain_name, date)
);

CREATE INDEX idx_domain_limits_domain ON domain_rate_limits(domain_name);
CREATE INDEX idx_domain_limits_date ON domain_rate_limits(date DESC);
CREATE INDEX idx_domain_limits_blocked ON domain_rate_limits(is_temporarily_blocked) WHERE is_temporarily_blocked = TRUE;
```

---

## Part 6: LLM / Model Usage & Cost Tracking

### model_providers

```sql
CREATE TABLE model_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,  -- "OpenAI", "xAI", "Anthropic"
    base_url TEXT,
    pricing_json JSONB,  -- Snapshot of known prices
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed providers
INSERT INTO model_providers (name, base_url, pricing_json) VALUES
    ('xAI', 'https://api.x.ai/v1', '{"grok-4-1-fast-reasoning": {"input": 0.20, "output": 0.50}}'),
    ('OpenAI', 'https://api.openai.com/v1', '{"text-embedding-3-small": {"input": 0.02, "output": 0}}');
```

### model_usage
Per logical LLM call or block.

```sql
CREATE TABLE model_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),
    session_id UUID REFERENCES application_sessions(id),
    provider_id UUID REFERENCES model_providers(id),
    model_name TEXT NOT NULL,  -- "grok-4-1-fast-reasoning", "text-embedding-3-small"
    call_type TEXT CHECK (call_type IN ('embedding', 'chat_completion', 'tool_call', 'function_call')),
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_estimated NUMERIC(10, 6),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    purpose TEXT,  -- "match_score", "cover_letter", "qa_check", "profile_embedding", "form_fill"
    status TEXT DEFAULT 'success' CHECK (status IN ('success', 'failed', 'timeout', 'rate_limited')),
    error_message TEXT,
    request_id TEXT,  -- Provider's request ID for debugging
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_model_usage_app ON model_usage(application_id);
CREATE INDEX idx_model_usage_session ON model_usage(session_id);
CREATE INDEX idx_model_usage_model ON model_usage(model_name);
CREATE INDEX idx_model_usage_purpose ON model_usage(purpose);
CREATE INDEX idx_model_usage_created ON model_usage(created_at DESC);
```

---

## Part 7: QA / Policy Enforcement

### qa_checks

```sql
CREATE TABLE qa_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    qa_type TEXT NOT NULL CHECK (qa_type IN ('hallucination_check', 'consistency_check', 'policy_compliance', 'completeness_check')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'passed', 'issues_found', 'failed')),
    issues_found_count INTEGER DEFAULT 0,
    notes TEXT
);

CREATE INDEX idx_qa_checks_app ON qa_checks(application_id);
CREATE INDEX idx_qa_checks_status ON qa_checks(status);
```

### qa_issues

```sql
CREATE TABLE qa_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    qa_check_id UUID NOT NULL REFERENCES qa_checks(id),
    application_id UUID NOT NULL REFERENCES applications(id),
    field_label TEXT,  -- If tied to specific question
    issue_type TEXT NOT NULL,  -- "false_skill", "years_experience_incorrect", "salary_conflict"
    description TEXT NOT NULL,
    suggested_fix TEXT,
    fix_applied BOOLEAN DEFAULT FALSE,
    fixed_value TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_qa_issues_check ON qa_issues(qa_check_id);
CREATE INDEX idx_qa_issues_app ON qa_issues(application_id);
CREATE INDEX idx_qa_issues_type ON qa_issues(issue_type);
```

---

## Part 8: Saturnus - Email & Matching

### email_accounts

```sql
CREATE TABLE email_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    provider TEXT CHECK (provider IN ('gmail', 'outlook', 'imap', 'other')),
    address TEXT NOT NULL,
    display_name TEXT,
    connection_config JSONB,  -- IMAP/SMTP/oauth tokens location (encrypted reference)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(user_id, address)
);

CREATE INDEX idx_email_accounts_user ON email_accounts(user_id);
```

### email_threads

```sql
CREATE TABLE email_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_account_id UUID NOT NULL REFERENCES email_accounts(id),
    thread_external_id TEXT,  -- Gmail thread ID, etc.
    subject_normalized TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(email_account_id, thread_external_id)
);

CREATE INDEX idx_email_threads_account ON email_threads(email_account_id);
CREATE INDEX idx_email_threads_external ON email_threads(thread_external_id);
```

### emails

```sql
CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_account_id UUID NOT NULL REFERENCES email_accounts(id),
    thread_id UUID REFERENCES email_threads(id),
    message_external_id TEXT,
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
    direction TEXT CHECK (direction IN ('inbound', 'outbound')),
    raw_source_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(email_account_id, message_external_id)
);

CREATE INDEX idx_emails_account ON emails(email_account_id);
CREATE INDEX idx_emails_thread ON emails(thread_id);
CREATE INDEX idx_emails_from ON emails(from_address);
CREATE INDEX idx_emails_received ON emails(received_at DESC);
CREATE INDEX idx_emails_direction ON emails(direction);
```

### email_classifications

```sql
CREATE TABLE email_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id),
    classification_label TEXT CHECK (classification_label IN (
        'interview_invite', 'rejection', 'status_update', 'offer',
        'assessment', 'newsletter', 'spam', 'other'
    )),
    eisenhower_quadrant TEXT CHECK (eisenhower_quadrant IN ('Q1', 'Q2', 'Q3', 'Q4')),
    importance_score NUMERIC(4, 3),  -- 0.000 to 1.000
    confidence_score NUMERIC(4, 3),
    generated_by TEXT CHECK (generated_by IN ('llm', 'rule', 'user')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_class_email ON email_classifications(email_id);
CREATE INDEX idx_email_class_label ON email_classifications(classification_label);
CREATE INDEX idx_email_class_quadrant ON email_classifications(eisenhower_quadrant);
```

### email_application_links
Bridge between Nyx apps and Saturnus emails.

```sql
CREATE TABLE email_application_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id),
    application_id UUID NOT NULL REFERENCES applications(id),
    link_type TEXT CHECK (link_type IN ('confirmation', 'interview_invite', 'rejection', 'offer', 'assessment', 'other')),
    confidence_score NUMERIC(4, 3),
    matched_by TEXT CHECK (matched_by IN ('company_name', 'job_title', 'date_proximity', 'email_content', 'manual')),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(email_id, application_id)
);

CREATE INDEX idx_email_app_links_email ON email_application_links(email_id);
CREATE INDEX idx_email_app_links_app ON email_application_links(application_id);
CREATE INDEX idx_email_app_links_type ON email_application_links(link_type);
```

### email_actions
What Saturnus did.

```sql
CREATE TABLE email_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID NOT NULL REFERENCES emails(id),
    action_type TEXT NOT NULL CHECK (action_type IN (
        'created_task', 'sent_reply', 'archived', 'labeled',
        'forwarded', 'scheduled_followup', 'marked_important'
    )),
    action_payload JSONB,  -- e.g. TickTick task ID, label name
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_actions_email ON email_actions(email_id);
CREATE INDEX idx_email_actions_type ON email_actions(action_type);
```

---

## Part 9: Interview Prep / Outcome Tracking

### interviews

```sql
CREATE TABLE interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    company_id UUID REFERENCES companies(id),
    interview_type TEXT CHECK (interview_type IN (
        'phone_screen', 'technical', 'behavioral', 'system_design',
        'onsite', 'hr', 'hiring_manager', 'panel', 'other'
    )),
    round_number INTEGER DEFAULT 1,
    scheduled_datetime TIMESTAMPTZ,
    duration_minutes INTEGER,
    location TEXT CHECK (location IN ('remote', 'onsite', 'hybrid')),
    meeting_link TEXT,
    interviewer_names JSONB DEFAULT '[]',
    interviewer_roles JSONB DEFAULT '[]',
    calendar_event_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_interviews_app ON interviews(application_id);
CREATE INDEX idx_interviews_company ON interviews(company_id);
CREATE INDEX idx_interviews_scheduled ON interviews(scheduled_datetime);
```

### interview_outcomes

```sql
CREATE TABLE interview_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id UUID NOT NULL REFERENCES interviews(id),
    outcome TEXT CHECK (outcome IN ('passed', 'failed', 'pending', 'withdrawn', 'rescheduled', 'no_show')),
    feedback_summary TEXT,
    offer_extended BOOLEAN DEFAULT FALSE,
    offer_details JSONB,  -- salary, benefits, start_date, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_interview_outcomes_interview ON interview_outcomes(interview_id);
CREATE INDEX idx_interview_outcomes_outcome ON interview_outcomes(outcome);
```

### interview_prep_packages
Your future interview-prep generator's output.

```sql
CREATE TABLE interview_prep_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id UUID REFERENCES interviews(id),
    application_id UUID REFERENCES applications(id),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    prep_document_path TEXT,
    topics_summary TEXT,
    company_research_notes TEXT,
    question_bank JSONB,  -- [{question, suggested_answer, category}]
    model_used TEXT,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_estimated NUMERIC(10, 6)
);

CREATE INDEX idx_prep_packages_interview ON interview_prep_packages(interview_id);
CREATE INDEX idx_prep_packages_app ON interview_prep_packages(application_id);
```

---

## Part 10: Session Digests & Analytics Snapshots

### session_digests

```sql
CREATE TABLE session_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES application_sessions(id),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    summary_text TEXT,  -- Human-readable summary
    applications_total INTEGER,
    applications_successful INTEGER,
    applications_failed INTEGER,
    num_low_effort INTEGER,
    num_medium_effort INTEGER,
    num_high_effort INTEGER,
    tokens_input_total BIGINT,
    tokens_output_total BIGINT,
    cost_estimated_total NUMERIC(10, 4),
    avg_match_score NUMERIC(4, 3),
    avg_duration_seconds INTEGER,
    per_domain_stats JSONB,
    per_company_tier_stats JSONB,
    errors_summary JSONB,
    digest_email_sent BOOLEAN DEFAULT FALSE,
    digest_email_id UUID REFERENCES emails(id)
);

CREATE INDEX idx_session_digests_session ON session_digests(session_id);
CREATE INDEX idx_session_digests_generated ON session_digests(generated_at DESC);
```

### company_metrics_daily
Aggregated stats per company per day.

```sql
CREATE TABLE company_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    date DATE NOT NULL,
    applications_sent INTEGER DEFAULT 0,
    applications_successful INTEGER DEFAULT 0,
    interviews_received INTEGER DEFAULT 0,
    offers_received INTEGER DEFAULT 0,
    avg_response_time_days NUMERIC(5, 2),
    last_response_datetime TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(company_id, date)
);

CREATE INDEX idx_company_metrics_company ON company_metrics_daily(company_id);
CREATE INDEX idx_company_metrics_date ON company_metrics_daily(date DESC);
```

---

## Part 11: Configuration & Versioning

### system_configs
Store snapshots of configuration.

```sql
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_name TEXT NOT NULL,
    config_json JSONB NOT NULL,  -- Thresholds, stealth config, domain rules
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'system' CHECK (created_by IN ('user', 'system')),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_system_configs_name ON system_configs(config_name);
CREATE INDEX idx_system_configs_active ON system_configs(is_active) WHERE is_active = TRUE;
```

### domain_policies
Detailed per-domain rules.

```sql
CREATE TABLE domain_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_name TEXT NOT NULL UNIQUE,
    max_applications_per_day INTEGER DEFAULT 10,
    min_seconds_between_applications INTEGER DEFAULT 60,
    max_concurrent_applications INTEGER DEFAULT 1,
    avoid_if_possible BOOLEAN DEFAULT FALSE,
    requires_account_creation BOOLEAN DEFAULT FALSE,
    typical_captcha_type TEXT,
    last_reviewed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_domain_policies_domain ON domain_policies(domain_name);
CREATE INDEX idx_domain_policies_avoid ON domain_policies(avoid_if_possible) WHERE avoid_if_possible = TRUE;
```

---

## Part 12: Data Corrections (Append-Only Pattern)

### data_corrections
Instead of updating/deleting, we add corrections.

```sql
CREATE TABLE data_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    field_name TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB NOT NULL,
    correction_reason TEXT,
    corrected_by TEXT DEFAULT 'user' CHECK (corrected_by IN ('user', 'system', 'qa_agent')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_corrections_table ON data_corrections(table_name);
CREATE INDEX idx_corrections_record ON data_corrections(record_id);
CREATE INDEX idx_corrections_created ON data_corrections(created_at DESC);
```

---

## Migration Script

```sql
-- Run this to create all tables in order
-- File: infrastructure/postgres/init-scripts/001_complete_schema.sql

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Create tables in dependency order
-- 1. Core Identity
-- 2. Job Sourcing
-- 3. Sessions
-- 4. Applications
-- 5. Events
-- 6. LLM Tracking
-- 7. QA
-- 8. Email (Saturnus)
-- 9. Interviews
-- 10. Analytics
-- 11. Configuration
-- 12. Corrections

-- Add triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
-- (Add CREATE TRIGGER statements for each table)
```

---

## Summary Statistics

| Category | Tables | Purpose |
|----------|--------|---------|
| Core Identity | 5 | Users, profiles, resumes |
| Job Sourcing | 5 | Companies, job posts, tags |
| Sessions | 2 | Application sessions, events |
| Applications | 4 | Applications, questions, steps, history |
| Events | 4 | Application events, CAPTCHAs, 2FA, rate limits |
| LLM Tracking | 2 | Providers, usage |
| QA | 2 | Checks, issues |
| Email (Saturnus) | 6 | Accounts, threads, emails, classifications, links, actions |
| Interviews | 3 | Interviews, outcomes, prep packages |
| Analytics | 2 | Session digests, company metrics |
| Configuration | 2 | System configs, domain policies |
| Corrections | 1 | Append-only corrections |

**Total: 38 tables**

---

*Document Version: 1.0*
*Last Updated: 2025-12-03*
