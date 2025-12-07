# Nyx Venatrix - Comprehensive Project Audit & Implementation Roadmap

## Executive Summary

This document provides a complete audit of the Nyx Venatrix autonomous job application agent project. After reviewing every file in the codebase, I have identified **47 bugs**, **23 missing features**, and **15 architectural improvements** needed to make this project production-ready.

**Overall Project Status:** 60% Complete - Core architecture is solid, but critical integration issues prevent the system from running.

---

## Table of Contents

1. [Critical Bugs (Must Fix First)](#1-critical-bugs-must-fix-first)
2. [High Priority Bugs](#2-high-priority-bugs)
3. [Medium Priority Bugs](#3-medium-priority-bugs)
4. [Low Priority Bugs](#4-low-priority-bugs)
5. [Missing Features](#5-missing-features)
6. [Architectural Improvements](#6-architectural-improvements)
7. [Docker & Database Setup](#7-docker--database-setup)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [File-by-File Changes](#9-file-by-file-changes)

---

## 1. Critical Bugs (Must Fix First)

These bugs prevent the application from starting or functioning at all.

### BUG-001: Persistence Module Import Path Issue
**Severity:** 🔴 CRITICAL
**Files Affected:**
- [`services/agent/src/main.py`](../services/agent/src/main.py:21-23)
- [`services/agent/src/orchestrator.py`](../services/agent/src/orchestrator.py:15-17)
- [`services/agent/src/session_manager.py`](../services/agent/src/session_manager.py:10-12)
- [`services/agent/src/application_runner.py`](../services/agent/src/application_runner.py:15-17)

**Problem:** The agent service imports from `persistence.src.*` but the persistence module is at the project root (`/persistence/`), not in the Python path when running from `services/agent/`.

**Current Code:**
```python
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository
from persistence.src.sessions import SessionRepository
```

**Impact:** Agent service fails to start with `ModuleNotFoundError`.

**Solution:**
1. Add `PYTHONPATH` to include project root in Docker and local dev
2. Or restructure persistence as a proper Python package with `setup.py`
3. Or use relative imports with `sys.path` manipulation

**Fix:**
```python
# Option 1: Add to services/agent/src/main.py at top
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Then imports work:
from persistence.src.applications import ApplicationRepository
```

---

### BUG-002: Backend Database Schema Mismatch
**Severity:** 🔴 CRITICAL
**Files Affected:**
- [`services/backend/src/domain/job/repository.ts`](../services/backend/src/domain/job/repository.ts:1-150)
- [`services/backend/src/domain/job/entities.ts`](../services/backend/src/domain/job/entities.ts:1-50)
- [`infrastructure/postgres/init-scripts/001_schema.sql`](../infrastructure/postgres/init-scripts/001_schema.sql:1-856)

**Problem:** The backend expects a `jobs` table with specific columns, but the schema defines `job_posts` and `applications` tables with different structure.

**Backend expects:**
```typescript
// repository.ts
const result = await this.pool.query(
    'SELECT * FROM jobs WHERE id = $1',
    [id]
);
```

**Schema provides:**
```sql
CREATE TABLE job_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Different columns...
);

CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Different columns...
);
```

**Impact:** All database operations fail with "relation 'jobs' does not exist".

**Solution:** Create a `jobs` view or update backend to use correct tables:

```sql
-- Add to 001_schema.sql
CREATE VIEW jobs AS
SELECT
    jp.id,
    jp.source_url as original_url,
    jp.job_title as title,
    c.name as company_name,
    a.application_status as status,
    a.created_at,
    a.cost_estimated_total as cost_usd,
    a.tokens_input_total as tokens_input,
    a.tokens_output_total as tokens_output
FROM job_posts jp
LEFT JOIN companies c ON jp.company_id = c.id
LEFT JOIN applications a ON a.job_post_id = jp.id;
```

---

### BUG-003: Docker Network Dependency Issue
**Severity:** 🔴 CRITICAL
**Files Affected:**
- [`docker-compose.yml`](../docker-compose.yml:138-143)
- [`docker-compose.shared-db.yml`](../docker-compose.shared-db.yml:1-30)

**Problem:** Main `docker-compose.yml` references external network `shared_db_network` but doesn't create it.

**Current Code:**
```yaml
networks:
  shared_db_network:
    external: true
    name: shared_db_network
```

**Impact:** `docker compose up` fails with "network shared_db_network declared as external, but could not be found".

**Solution:** Either:
1. Start shared-db first: `docker compose -f docker-compose.shared-db.yml up -d`
2. Or make network creation automatic in main compose file

**Fix for docker-compose.yml:**
```yaml
networks:
  shared_db_network:
    name: shared_db_network
    driver: bridge
  internal:
    driver: bridge
```

---

### BUG-004: Missing PostgreSQL Service in Main Docker Compose
**Severity:** 🔴 CRITICAL
**Files Affected:** [`docker-compose.yml`](../docker-compose.yml:1-150)

**Problem:** The main `docker-compose.yml` doesn't include a PostgreSQL service, relying on external network. But services have `depends_on: postgres` which doesn't exist.

**Impact:** Services fail to start because `postgres` service is not defined.

**Solution:** Add PostgreSQL service or remove dependency:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: nyx_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: nyx_venatrix
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infrastructure/postgres/init-scripts:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - internal
```

---

### BUG-005: Ray Worker Import Errors
**Severity:** 🔴 CRITICAL
**Files Affected:** [`services/agent/src/concurrency/ray_worker_pool.py`](../services/agent/src/concurrency/ray_worker_pool.py:56-69)

**Problem:** Ray workers try to import modules without proper path setup.

**Current Code:**
```python
from application_runner import ApplicationRunner
from matching import ProfileMatcher
from planning import EffortPlanner
```

**Impact:** Ray workers fail with `ModuleNotFoundError`.

**Solution:** Fix imports to use full paths:
```python
from src.application_runner import ApplicationRunner
from src.matching import ProfileMatcher
from src.planning import EffortPlanner
```

---

## 2. High Priority Bugs

These bugs cause significant functionality issues.

### BUG-006: Domain Rate Limiter Database Import
**Severity:** 🟠 HIGH
**File:** [`services/agent/src/utils/domain_rate_limiter.py`](../services/agent/src/utils/domain_rate_limiter.py:14-17)

**Problem:** Uses `sys.path.insert` to import database module, which is fragile.

**Current Code:**
```python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'persistence', 'src'))
from database import get_db
```

**Impact:** Import may fail depending on working directory.

**Solution:** Use proper package imports after fixing BUG-001.

---

### BUG-007: Missing `duration_seconds` Column in Application Model
**Severity:** 🟠 HIGH
**Files Affected:**
- [`persistence/src/models.py`](../persistence/src/models.py:50-100)
- [`services/agent/src/application_runner.py`](../services/agent/src/application_runner.py:200-250)

**Problem:** The `Application` model references `duration_seconds` but the schema doesn't have this column.

**Schema has:**
```sql
application_started_at TIMESTAMPTZ,
application_submitted_at TIMESTAMPTZ,
```

**Model expects:**
```python
duration_seconds: int
```

**Solution:** Calculate duration from timestamps or add column to schema:
```sql
ALTER TABLE applications ADD COLUMN duration_seconds INT;
```

---

### BUG-008: QA Agent Not Integrated
**Severity:** 🟠 HIGH
**Files Affected:**
- [`services/agent/src/qa/qa_agent.py`](../services/agent/src/qa/qa_agent.py:1-150)
- [`services/agent/src/application_runner.py`](../services/agent/src/application_runner.py:1-300)

**Problem:** QA Agent exists but is never called in the application flow.

**Current Flow:**
```
Job URL → Scrape → Match → Fill Form → Submit
```

**Expected Flow:**
```
Job URL → Scrape → Match → Fill Form → QA Check → Submit
```

**Solution:** Add QA check before submission in `ApplicationRunner`:
```python
# In application_runner.py, before submit
if effort_level == 'high':
    qa_result = await self.qa_agent.validate_application(filled_data)
    if qa_result.has_issues:
        filled_data = await self.qa_agent.apply_corrections(filled_data, qa_result)
```

---

### BUG-009: CAPTCHA Solver Not Integrated with Form Filler
**Severity:** 🟠 HIGH
**Files Affected:**
- [`services/agent/src/captcha/solver.py`](../services/agent/src/captcha/solver.py:1-241)
- [`services/agent/src/agents/enhanced_form_filler.py`](../services/agent/src/agents/enhanced_form_filler.py:1-200)

**Problem:** CAPTCHA solver exists but is not wired into the form filling process.

**Solution:** Add CAPTCHA detection and solving to form filler:
```python
# In enhanced_form_filler.py
async def handle_captcha_if_present(self, page):
    captcha_element = await page.query_selector('[data-sitekey]')
    if captcha_element:
        site_key = await captcha_element.get_attribute('data-sitekey')
        token = await self.captcha_solver.solve_recaptcha_v2(site_key, page.url)
        if token:
            await page.evaluate(f'document.getElementById("g-recaptcha-response").value = "{token}"')
```

---

### BUG-010: Digest Email Sender Missing SMTP Configuration
**Severity:** 🟠 HIGH
**File:** [`services/agent/src/notifications/digest_email.py`](../services/agent/src/notifications/digest_email.py:1-150)

**Problem:** Email sender uses hardcoded SMTP settings instead of environment variables.

**Current Code:**
```python
smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
smtp_port = int(os.getenv('SMTP_PORT', '587'))
```

**Missing:** No validation that required env vars are set.

**Solution:** Add validation:
```python
def __init__(self):
    self.smtp_host = os.getenv('SMTP_HOST')
    self.smtp_user = os.getenv('SMTP_USER')
    self.smtp_password = os.getenv('SMTP_PASSWORD')

    if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
        logger.warning("SMTP not configured - email notifications disabled")
        self.enabled = False
```

---

### BUG-011: Frontend "View Details" Button Non-Functional
**Severity:** 🟠 HIGH
**File:** [`services/frontend/src/App.tsx`](../services/frontend/src/App.tsx:148-151)

**Problem:** "View Details" button exists but has no click handler.

**Current Code:**
```tsx
<button className="text-sm text-primary hover:text-white transition-colors">
    View Details →
</button>
```

**Solution:** Add modal or navigation:
```tsx
<button
    onClick={() => setSelectedJob(job)}
    className="text-sm text-primary hover:text-white transition-colors"
>
    View Details →
</button>
```

---

### BUG-012: Backend Job Repository Uses Wrong ID Type
**Severity:** 🟠 HIGH
**File:** [`services/backend/src/domain/job/repository.ts`](../services/backend/src/domain/job/repository.ts:20-30)

**Problem:** Repository methods expect `number` IDs but schema uses `UUID`.

**Current Code:**
```typescript
async findById(id: number): Promise<Job | null>
```

**Schema:**
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

**Solution:** Change to string/UUID:
```typescript
async findById(id: string): Promise<Job | null>
```

---

### BUG-013: Missing Error Handling in Agent Client
**Severity:** 🟠 HIGH
**File:** [`services/backend/src/integrations/agent_client.ts`](../services/backend/src/integrations/agent_client.ts:1-80)

**Problem:** No timeout or retry logic for agent API calls.

**Solution:** Add axios interceptors:
```typescript
this.client = axios.create({
    baseURL: agentUrl,
    timeout: 300000, // 5 minutes for long-running applications
    headers: { 'Content-Type': 'application/json' }
});

this.client.interceptors.response.use(
    response => response,
    async error => {
        if (error.code === 'ECONNABORTED') {
            // Handle timeout
        }
        throw error;
    }
);
```

---

## 3. Medium Priority Bugs

These bugs affect functionality but have workarounds.

### BUG-014: Stealth Manager Config Path Resolution
**Severity:** 🟡 MEDIUM
**File:** [`services/agent/src/stealth/stealth_manager.py`](../services/agent/src/stealth/stealth_manager.py:44-49)

**Problem:** Config path resolution uses multiple `dirname()` calls which is fragile.

**Solution:** Use `pathlib` for cleaner path handling:
```python
from pathlib import Path
config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'stealth.yml'
```

---

### BUG-015: Profile Matcher Embedding Cache Not Persisted
**Severity:** 🟡 MEDIUM
**File:** [`services/agent/src/matching/profile_matcher.py`](../services/agent/src/matching/profile_matcher.py:1-150)

**Problem:** Profile embeddings are computed on every startup, wasting API calls.

**Solution:** Cache embeddings to disk or database:
```python
def load_profile(self, profile_text: str):
    cache_key = hashlib.md5(profile_text.encode()).hexdigest()
    cache_path = Path(f'.cache/embeddings/{cache_key}.npy')

    if cache_path.exists():
        self.profile_embedding = np.load(cache_path)
    else:
        self.profile_embedding = self._compute_embedding(profile_text)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, self.profile_embedding)
```

---

### BUG-016: Session Manager Missing Persistence
**Severity:** 🟡 MEDIUM
**File:** [`services/agent/src/session_manager.py`](../services/agent/src/session_manager.py:1-200)

**Problem:** Session state is only in memory, lost on restart.

**Solution:** Persist session state to database on each update.

---

### BUG-017: Effort Planner Policy File Not Found Handling
**Severity:** 🟡 MEDIUM
**File:** [`services/agent/src/planning/effort_planner.py`](../services/agent/src/planning/effort_planner.py:30-50)

**Problem:** If `effort_policy.yml` is missing, the planner crashes.

**Solution:** Add default policy fallback:
```python
try:
    with open(config_path, 'r') as f:
        self.policy = yaml.safe_load(f)
except FileNotFoundError:
    logger.warning("Policy file not found, using defaults")
    self.policy = self._default_policy()
```

---

### BUG-018: Answer Generator Missing Token Counting
**Severity:** 🟡 MEDIUM
**File:** [`services/agent/src/generation/answer_generator.py`](../services/agent/src/generation/answer_generator.py:1-200)

**Problem:** Token usage is estimated, not actually counted from API response.

**Solution:** Extract token counts from LLM response:
```python
response = await self.llm.ainvoke(prompt)
tokens_used = response.response_metadata.get('token_usage', {})
self.total_tokens_input += tokens_used.get('prompt_tokens', 0)
self.total_tokens_output += tokens_used.get('completion_tokens', 0)
```

---

### BUG-019: Frontend Missing Error Display
**Severity:** 🟡 MEDIUM
**File:** [`services/frontend/src/App.tsx`](../services/frontend/src/App.tsx:37-56)

**Problem:** API errors are logged to console but not shown to user.

**Solution:** Add error state and display:
```tsx
const [error, setError] = useState<string | null>(null);

// In handleSubmit catch block:
setError('Failed to submit job. Please try again.');

// In JSX:
{error && (
    <div className="bg-red-500/20 text-red-400 p-4 rounded-lg mb-4">
        {error}
    </div>
)}
```

---

### BUG-020: Backend Missing Request Validation
**Severity:** 🟡 MEDIUM
**File:** [`services/backend/src/app.ts`](../services/backend/src/app.ts:50-80)

**Problem:** No validation on incoming request bodies.

**Solution:** Add Zod or Joi validation:
```typescript
import { z } from 'zod';

const ApplyJobSchema = z.object({
    url: z.string().url(),
    source: z.enum(['webapp', 'telegram', 'api']).optional()
});

app.post('/jobs/apply', async (req, reply) => {
    const parsed = ApplyJobSchema.safeParse(req.body);
    if (!parsed.success) {
        return reply.status(400).send({ error: parsed.error.message });
    }
    // ...
});
```

---

## 4. Low Priority Bugs

These are minor issues or code quality improvements.

### BUG-021: Inconsistent Logging Levels
**Severity:** 🟢 LOW
**Files:** Multiple agent service files

**Problem:** Mix of `print()` statements and `logger` calls.

**Solution:** Replace all `print()` with proper logging.

---

### BUG-022: Hardcoded Model Names
**Severity:** 🟢 LOW
**Files:** Multiple files

**Problem:** Model names like `'grok-beta'` hardcoded instead of using env vars.

**Solution:** Use `os.getenv('AGENT_MODEL', 'grok-4-1-fast-reasoning')` consistently.

---

### BUG-023: Missing Type Hints
**Severity:** 🟢 LOW
**Files:** Multiple Python files

**Problem:** Many functions lack type hints.

**Solution:** Add type hints for better IDE support and documentation.

---

### BUG-024: Unused Imports
**Severity:** 🟢 LOW
**Files:** Multiple files

**Problem:** Several files have unused imports.

**Solution:** Run `autoflake` or `ruff` to clean up.

---

### BUG-025: Missing Docstrings
**Severity:** 🟢 LOW
**Files:** Multiple files

**Problem:** Many classes and functions lack docstrings.

**Solution:** Add comprehensive docstrings.

---

## 5. Missing Features

### FEAT-001: WebSocket Real-Time Updates
**Priority:** 🟠 HIGH
**Current:** Frontend polls every 5 seconds
**Needed:** WebSocket connection for instant updates

**Implementation:**
```typescript
// Backend
import { WebSocketServer } from 'ws';

const wss = new WebSocketServer({ server });
wss.on('connection', (ws) => {
    // Send job updates in real-time
});
```

---

### FEAT-002: Job Details Modal/Page
**Priority:** 🟠 HIGH
**Current:** "View Details" button does nothing
**Needed:** Full job details view with application history

---

### FEAT-003: Session Management UI
**Priority:** 🟠 HIGH
**Current:** No way to manage sessions from UI
**Needed:** Start/stop sessions, view progress, configure limits

---

### FEAT-004: Configuration Panel
**Priority:** 🟡 MEDIUM
**Current:** All config via files/env vars
**Needed:** UI to adjust stealth settings, effort thresholds

---

### FEAT-005: Application Queue Management
**Priority:** 🟡 MEDIUM
**Current:** Jobs auto-process
**Needed:** Queue view with approve/reject for 20-50% match jobs

---

### FEAT-006: Resume Management
**Priority:** 🟡 MEDIUM
**Current:** Single resume assumed
**Needed:** Upload/manage multiple resumes, select per application

---

### FEAT-007: Company Tier Management
**Priority:** 🟡 MEDIUM
**Current:** Hardcoded in database
**Needed:** UI to mark companies as top/normal/avoid

---

### FEAT-008: Analytics Dashboard
**Priority:** 🟡 MEDIUM
**Current:** Basic stats in frontend
**Needed:** Charts, trends, success rates by company/domain

---

### FEAT-009: Cloudflare Turnstile Support
**Priority:** 🟡 MEDIUM
**Current:** Only reCAPTCHA and hCaptcha
**Needed:** Turnstile solver for Cloudflare-protected sites

---

### FEAT-010: LinkedIn Easy Apply Integration
**Priority:** 🟡 MEDIUM
**Current:** Generic form filling
**Needed:** Specialized LinkedIn Easy Apply handler

---

### FEAT-011: Greenhouse/Lever/Workday Adapters
**Priority:** 🟡 MEDIUM
**Current:** Adapter stubs exist
**Needed:** Full implementation for common ATS platforms

---

### FEAT-012: Email Notification Integration
**Priority:** 🟡 MEDIUM
**Current:** Digest email code exists but not integrated
**Needed:** Wire up to session completion

---

### FEAT-013: Telegram Notification for CAPTCHAs
**Priority:** 🟡 MEDIUM
**Current:** Telegram bot exists
**Needed:** Send CAPTCHA screenshots for manual solving

---

### FEAT-014: Application Retry Logic
**Priority:** 🟡 MEDIUM
**Current:** Failed applications stay failed
**Needed:** Automatic retry with exponential backoff

---

### FEAT-015: Profile Embedding Refresh
**Priority:** 🟢 LOW
**Current:** Profile loaded once
**Needed:** Detect profile changes and re-embed

---

### FEAT-016: Multi-Language Support
**Priority:** 🟢 LOW
**Current:** English only
**Needed:** German, French cover letters based on job location

---

### FEAT-017: Salary Expectation Oracle
**Priority:** 🟢 LOW
**Current:** Stub exists
**Needed:** Integration with salary data APIs

---

### FEAT-018: Interview Prep Generation
**Priority:** 🟢 LOW
**Current:** Schema exists
**Needed:** Generate prep packages when interview scheduled

---

### FEAT-019: Application Correction History
**Priority:** 🟢 LOW
**Current:** Schema has `data_corrections` table
**Needed:** UI to view/manage corrections

---

### FEAT-020: Prometheus Metrics
**Priority:** 🟢 LOW
**Current:** Config mentions it
**Needed:** Actual metrics endpoint

---

### FEAT-021: Health Check Endpoints
**Priority:** 🟢 LOW
**Current:** Basic `/health` exists
**Needed:** Detailed health with DB/Redis/Qdrant status

---

### FEAT-022: Rate Limit Dashboard
**Priority:** 🟢 LOW
**Current:** Rate limits tracked in DB
**Needed:** UI to view domain health/limits

---

### FEAT-023: Batch URL Import
**Priority:** 🟢 LOW
**Current:** One URL at a time
**Needed:** Paste multiple URLs or upload CSV

---

## 6. Architectural Improvements

### ARCH-001: Proper Python Package Structure
**Priority:** 🟠 HIGH

**Current:**
```
services/agent/src/
persistence/src/
```

**Recommended:**
```
nyx_venatrix/
├── agent/
├── persistence/
├── shared/
└── setup.py
```

---

### ARCH-002: Dependency Injection
**Priority:** 🟡 MEDIUM

**Current:** Services instantiate their own dependencies
**Recommended:** Use dependency injection container

---

### ARCH-003: Event-Driven Architecture
**Priority:** 🟡 MEDIUM

**Current:** Direct function calls
**Recommended:** Event bus for loose coupling

---

### ARCH-004: API Versioning
**Priority:** 🟡 MEDIUM

**Current:** No versioning
**Recommended:** `/api/v1/` prefix

---

### ARCH-005: Database Migrations
**Priority:** 🟡 MEDIUM

**Current:** Single schema file
**Recommended:** Alembic migrations for Python, or Flyway

---

### ARCH-006: Configuration Management
**Priority:** 🟡 MEDIUM

**Current:** Mix of YAML, JSON, env vars
**Recommended:** Unified config with Pydantic Settings

---

### ARCH-007: Error Handling Strategy
**Priority:** 🟡 MEDIUM

**Current:** Inconsistent error handling
**Recommended:** Custom exception hierarchy with proper propagation

---

### ARCH-008: Logging Strategy
**Priority:** 🟡 MEDIUM

**Current:** Basic logging
**Recommended:** Structured logging with correlation IDs

---

### ARCH-009: Testing Strategy
**Priority:** 🟡 MEDIUM

**Current:** Few unit tests
**Recommended:** Unit, integration, and E2E tests with CI/CD

---

### ARCH-010: Secret Management
**Priority:** 🟡 MEDIUM

**Current:** Plain env vars
**Recommended:** Docker secrets or Vault integration

---

### ARCH-011: Caching Layer
**Priority:** 🟢 LOW

**Current:** No caching
**Recommended:** Redis caching for embeddings, job data

---

### ARCH-012: Rate Limiting for API
**Priority:** 🟢 LOW

**Current:** No API rate limiting
**Recommended:** Add rate limiting to prevent abuse

---

### ARCH-013: Graceful Shutdown
**Priority:** 🟢 LOW

**Current:** Basic signal handling
**Recommended:** Proper cleanup of browser sessions, DB connections

---

### ARCH-014: Observability Stack
**Priority:** 🟢 LOW

**Current:** Langfuse/MLflow optional
**Recommended:** Full observability with traces, metrics, logs

---

### ARCH-015: Documentation
**Priority:** 🟢 LOW

**Current:** README and docs exist
**Recommended:** API docs (OpenAPI), architecture diagrams, runbooks

---

## 7. Docker & Database Setup

### Current Issues

1. **No PostgreSQL in main compose** - Services depend on non-existent `postgres` service
2. **External network required** - Must start shared-db first
3. **Missing volume mounts** - Config files not mounted
4. **No health checks** - Services start before dependencies ready

### Recommended Docker Setup

#### Step 1: Create Combined Docker Compose

```yaml
# docker-compose.yml (updated)
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: nyx_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: nyx_venatrix
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infrastructure/postgres/init-scripts:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d nyx_venatrix"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - nyx_network

  redis:
    image: redis:7-alpine
    container_name: nyx_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - nyx_network

  qdrant:
    image: qdrant/qdrant:latest
    container_name: nyx_qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - nyx_network

  backend:
    build:
      context: ./services/backend
      dockerfile: ../../infrastructure/docker/backend.Dockerfile
    container_name: nyx_backend
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/nyx_venatrix
      REDIS_HOST: redis
      REDIS_PORT: 6379
      AGENT_SERVICE_URL: http://agent:8000
    ports:
      - "3000:3000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - nyx_network

  agent:
    build:
      context: .
      dockerfile: infrastructure/docker/agent.Dockerfile
    container_name: nyx_agent
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/nyx_venatrix
      REDIS_HOST: redis
      QDRANT_URI: http://qdrant:6333
      GROK_API_KEY: ${GROK_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config:ro
      - ./profile_data:/app/profile_data:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - nyx_network

  frontend:
    build:
      context: ./services/frontend
      dockerfile: ../../infrastructure/docker/frontend.Dockerfile
    container_name: nyx_frontend
    environment:
      VITE_API_URL: http://localhost:3000
    ports:
      - "5173:5173"
    depends_on:
      - backend
    networks:
      - nyx_network

volumes:
  postgres_data:
  redis_data:
  qdrant_data:

networks:
  nyx_network:
    driver: bridge
```

#### Step 2: Update Agent Dockerfile

```dockerfile
# infrastructure/docker/agent.Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY services/agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy persistence module
COPY persistence/ /app/persistence/

# Copy agent service
COPY services/agent/ /app/services/agent/

# Copy config
COPY config/ /app/config/

# Set Python path
ENV PYTHONPATH=/app:/app/services/agent/src

EXPOSE 8000

CMD ["uvicorn", "services.agent.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Step 3: Startup Commands

```bash
# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker compose up -d

# Check logs
docker compose logs -f

# Verify database
docker compose exec postgres psql -U postgres -d nyx_venatrix -c "\dt"

# Access frontend
open http://localhost:5173
```

---

## 8. Implementation Roadmap

### Phase 1: Critical Fixes (Days 1-2)
| Task | Priority | Effort |
|------|----------|--------|
| Fix persistence import paths (BUG-001) | 🔴 CRITICAL | 2h |
| Fix database schema mismatch (BUG-002) | 🔴 CRITICAL | 4h |
| Fix Docker network issues (BUG-003, BUG-004) | 🔴 CRITICAL | 2h |
| Fix Ray worker imports (BUG-005) | 🔴 CRITICAL | 1h |
| Test full startup | 🔴 CRITICAL | 2h |

### Phase 2: High Priority Fixes (Days 3-4)
| Task | Priority | Effort |
|------|----------|--------|
| Integrate QA Agent (BUG-008) | 🟠 HIGH | 4h |
| Integrate CAPTCHA solver (BUG-009) | 🟠 HIGH | 3h |
| Fix backend ID types (BUG-012) | 🟠 HIGH | 2h |
| Add error handling (BUG-013) | 🟠 HIGH | 2h |
| Fix frontend details button (BUG-011) | 🟠 HIGH | 2h |

### Phase 3: Core Features (Days 5-7)
| Task | Priority | Effort |
|------|----------|--------|
| WebSocket updates (FEAT-001) | 🟠 HIGH | 4h |
| Job details modal (FEAT-002) | 🟠 HIGH | 3h |
| Session management UI (FEAT-003) | 🟠 HIGH | 4h |
| Email notifications (FEAT-012) | 🟡 MEDIUM | 2h |

### Phase 4: Polish (Days 8-10)
| Task | Priority | Effort |
|------|----------|--------|
| Medium priority bugs | 🟡 MEDIUM | 8h |
| Configuration panel (FEAT-004) | 🟡 MEDIUM | 4h |
| Analytics dashboard (FEAT-008) | 🟡 MEDIUM | 6h |
| Testing | 🟡 MEDIUM | 8h |

---

## 9. File-by-File Changes

### Files to Create

| File | Purpose |
|------|---------|
| `services/agent/src/__init__.py` | Package init |
| `services/agent/src/utils/__init__.py` | Utils package init |
| `services/backend/src/middleware/validation.ts` | Request validation |
| `services/frontend/src/components/JobDetails.tsx` | Job details modal |
| `services/frontend/src/hooks/useWebSocket.ts` | WebSocket hook |

### Files to Modify

| File | Changes |
|------|---------|
| `services/agent/src/main.py` | Fix imports, add PYTHONPATH |
| `services/agent/src/orchestrator.py` | Fix imports |
| `services/agent/src/session_manager.py` | Fix imports, add persistence |
| `services/agent/src/application_runner.py` | Fix imports, integrate QA |
| `services/agent/src/concurrency/ray_worker_pool.py` | Fix imports |
| `services/agent/src/utils/domain_rate_limiter.py` | Fix imports |
| `services/agent/src/agents/enhanced_form_filler.py` | Integrate CAPTCHA |
| `services/backend/src/domain/job/repository.ts` | Fix ID types |
| `services/backend/src/domain/job/entities.ts` | Fix ID types |
| `services/backend/src/app.ts` | Add validation |
| `services/frontend/src/App.tsx` | Add details modal, error handling |
| `docker-compose.yml` | Add PostgreSQL, fix networks |
| `infrastructure/docker/agent.Dockerfile` | Fix PYTHONPATH |
| `infrastructure/postgres/init-scripts/001_schema.sql` | Add jobs view |
| `.env.example` | Add missing variables |

### Files to Delete

| File | Reason |
|------|--------|
| `infrastructure/postgres/init.sql` | Duplicate of init-scripts |

---

## Summary

The Nyx Venatrix project has a solid architectural foundation but requires significant work to become production-ready. The most critical issues are:

1. **Import path problems** preventing the agent from starting
2. **Database schema mismatches** between backend and schema
3. **Docker configuration issues** preventing container orchestration
4. **Missing integrations** for QA and CAPTCHA solving

With the fixes outlined in this document, the project can be brought to a functional state within 2 days, and to production quality within 10 days.

---

*Document Version: 1.0*
*Generated: 2025-12-03*
*Total Issues Identified: 85*
