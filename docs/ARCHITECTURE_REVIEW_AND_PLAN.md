# Nyx Venatrix - Architecture Review & Production Readiness Plan

## Executive Summary

This document provides a comprehensive analysis of the Nyx Venatrix project, identifying bugs, incomplete features, and architectural issues. It also outlines a detailed plan to make the project production-ready while accommodating the requirements for:

1. **Standalone PostgreSQL** - Accessible by the future Saturnus email management project
2. **Chrome-based automation** - Using browser-use, browser-use/web-ui, and vibesurf.ai instead of Playwright
3. **Production readiness** - Professional code quality, error handling, and deployment configuration

---

## Part 1: Critical Bugs Identified

### 1.1 Missing Persistence Module (CRITICAL)

**Location:** Multiple files in `services/agent/src/`

**Problem:** The code imports from a non-existent `persistence` module:

```python
# Found in: main.py, orchestrator.py, session_manager.py, application_runner.py
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository
from persistence.src.sessions import SessionRepository
```

**Impact:** The agent service will fail to start with `ModuleNotFoundError`.

**Current Workaround:** Mock repositories exist in [`mocks.py`](../services/agent/src/mocks.py) but are only used as fallback when DB connection fails.

**Solution:** Create a proper `persistence` package with SQLAlchemy-based repositories.

---

### 1.2 Incorrect browser_use LLM Configuration (CRITICAL)

**Location:** [`services/agent/src/agents/base.py`](../services/agent/src/agents/base.py:8)

**Problem:** The base URL for Grok API is incorrect:

```python
self.llm = ChatOpenAI(
    base_url='https://api.grok.x.ai/v1',  # WRONG - should be https://api.x.ai/v1
    api_key=os.getenv('GROK_API_KEY'),
    ...
)
```

**Impact:** All browser automation will fail with connection errors.

**Solution:** Fix the base URL to `https://api.x.ai/v1`.

---

### 1.3 Database Schema Mismatch (HIGH)

**Location:**
- Legacy [`infrastructure/postgres/init-scripts/init.sql`](../infrastructure/postgres/init-scripts/init.sql) (now removed)
- [`infrastructure/postgres/init-scripts/001_schema.sql`](../infrastructure/postgres/init-scripts/001_schema.sql)

**Problem:** Two conflicting schemas existed:
- `init.sql` - Simple schema with `jobs` table using `UUID` primary key
- `001_schema.sql` (renamed from `002_comprehensive_schema.sql`) - Full schema with `applications`, `job_posts`, etc.

The backend repository expects `jobs` table with `id` as `INTEGER`:

```typescript
// services/backend/src/domain/job/repository.ts
async findById(id: number): Promise<Job | null>  // Expects number, but schema uses UUID
```

**Impact:** Database queries will fail due to type mismatch.

**Solution:** Consolidate schemas and ensure consistent ID types.

---

### 1.4 Environment Variable Inconsistency (MEDIUM)

**Location:** Multiple files

**Problems:**
1. `.env.example` uses `CAPTCHA_API_KEY` but code uses `TWOCAPTCHA_API_KEY`
2. Backend requires `GROK_API_KEY` but agent uses it differently
3. Database URL format differs between services

**Solution:** Standardize all environment variable names.

---

### 1.5 Missing CSS/Tailwind Configuration (MEDIUM)

**Location:** [`services/frontend/`](../services/frontend/)

**Problem:** The frontend uses Tailwind-like classes (`glass-panel`, `btn-primary`, etc.) but there's no Tailwind configuration or CSS file defining these classes.

**Impact:** Frontend will render without proper styling.

**Solution:** Add Tailwind CSS configuration or define custom CSS classes.

---

## Part 2: Half-Baked Features

### 2.1 Session Management

**Status:** Partially implemented

**What exists:**
- [`SessionManager`](../services/agent/src/session_manager.py) class with create/stop/digest methods
- Database schema for `application_sessions`

**What's missing:**
- No actual session persistence (imports non-existent module)
- No session recovery on startup
- No session timeout handling

---

### 2.2 Ray Orchestrator

**Status:** Partially implemented

**What exists:**
- [`RayOrchestrator`](../services/agent/src/orchestrator.py) class with worker pool
- Fallback `SingleThreadOrchestrator`

**What's missing:**
- Workers import non-existent persistence module
- No proper error handling for Ray failures
- No worker health monitoring

---

### 2.3 QA Agent

**Status:** Partially implemented

**What exists:**
- [`QAAgent`](../services/agent/src/qa/qa_agent.py) with validation logic

**What's missing:**
- Not integrated into the application flow
- No database persistence for QA results
- `apply_corrections` method is a stub

---

### 2.4 CAPTCHA Solving

**Status:** Partially implemented

**What exists:**
- [`CaptchaSolver`](../services/agent/src/utils/captcha_solver.py) with 2captcha integration

**What's missing:**
- Not integrated with browser automation
- No hCaptcha support (only reCAPTCHA)
- No Cloudflare Turnstile support

---

### 2.5 Frontend Dashboard

**Status:** Basic implementation

**What exists:**
- Job submission form
- Job list display
- Basic analytics

**What's missing:**
- Job details view (button exists but no functionality)
- Real-time updates (polling every 5s, no WebSocket)
- Session management UI
- Configuration management

---

## Part 3: Architecture Improvements

### 3.1 Standalone PostgreSQL for Multi-Project Access

**Requirement:** Separate PostgreSQL to be accessible by Saturnus (email management) project.

**Current State:** PostgreSQL is defined in both `docker-compose.yml` and `docker-compose.db.yml` with the same configuration.

**Proposed Solution:**

Create a dedicated `docker-compose.shared-db.yml`:

```yaml
# Shared database infrastructure for Nyx Venatrix and Saturnus
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: shared_postgres
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-postgres}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
      - POSTGRES_MULTIPLE_DATABASES=nyx_venatrix,saturnus
    ports:
      - "5432:5432"
    volumes:
      - shared_postgres_data:/var/lib/postgresql/data
      - ./infrastructure/postgres/init-scripts:/docker-entrypoint-initdb.d
    networks:
      - shared_db_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  shared_postgres_data:
    name: shared_postgres_data
    external: true  # Allows other projects to use it

networks:
  shared_db_network:
    name: shared_db_network
    external: true  # Allows other projects to connect
```

**Benefits:**
- Single PostgreSQL instance for both projects
- Can be started independently: `docker compose -f docker-compose.shared-db.yml up -d`
- Other projects connect via the external network

---

### 3.2 Chrome-Based Automation with browser-use

**Requirement:** Use browser-use, browser-use/web-ui, and vibesurf.ai instead of Playwright.

**Current State:**
- `browser-use` is already in requirements.txt
- Code uses `browser_use.Agent` for automation
- Playwright is installed as a dependency of browser-use

**Analysis:**

1. **browser-use** (v0.9.7) - Already integrated, uses Playwright under the hood
2. **browser-use/web-ui** - A separate project for visual browser control
3. **vibesurf.ai** - AI-powered browser automation service

**Proposed Solution:**

Since browser-use already abstracts Playwright, we should:

1. **Configure browser-use for Chrome** instead of Chromium:

```python
# services/agent/src/agents/enhanced_form_filler.py
browser_agent = BrowserAgent(
    task=task,
    llm=self.llm,
    browser_kwargs={
        'headless': False,  # Use visible Chrome for debugging
        'channel': 'chrome',  # Use installed Chrome instead of Chromium
        'args': [
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
        ]
    }
)
```

2. **Add vibesurf.ai integration** as an alternative automation backend:

```python
# services/agent/src/utils/vibesurf_client.py
class VibeSurfClient:
    """Alternative browser automation using vibesurf.ai API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.vibesurf.ai/v1"

    async def execute_task(self, task: str, url: str) -> dict:
        # Implementation
        pass
```

3. **Create abstraction layer** for browser automation:

```python
# services/agent/src/browser/automation.py
class BrowserAutomation(ABC):
    @abstractmethod
    async def fill_form(self, url: str, task: str) -> dict:
        pass

class BrowserUseAutomation(BrowserAutomation):
    """Uses browser-use library"""
    pass

class VibeSurfAutomation(BrowserAutomation):
    """Uses vibesurf.ai API"""
    pass
```

---

### 3.3 Persistence Layer Architecture

**Proposed Structure:**

```
services/agent/
├── persistence/
│   ├── __init__.py
│   ├── database.py          # SQLAlchemy engine/session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── application.py   # Application model
│   │   ├── session.py       # Session model
│   │   └── event.py         # Event model
│   └── repositories/
│       ├── __init__.py
│       ├── base.py          # Base repository
│       ├── applications.py  # ApplicationRepository
│       ├── sessions.py      # SessionRepository
│       └── events.py        # EventRepository
```

**Example Implementation:**

```python
# services/agent/persistence/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nyx_venatrix')

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

## Part 4: Detailed Implementation Plan

### Phase 1: Critical Bug Fixes (Priority: CRITICAL)

#### 1.1 Create Persistence Module
**Estimated Time:** 4-6 hours

**Tasks:**
1. Create `services/agent/persistence/` directory structure
2. Implement SQLAlchemy models matching the comprehensive schema
3. Implement repository classes with CRUD operations
4. Add database connection management with connection pooling
5. Update all imports in agent service files

**Files to Create:**
- `services/agent/persistence/__init__.py`
- `services/agent/persistence/database.py`
- `services/agent/persistence/models/__init__.py`
- `services/agent/persistence/models/application.py`
- `services/agent/persistence/models/session.py`
- `services/agent/persistence/models/event.py`
- `services/agent/persistence/repositories/__init__.py`
- `services/agent/persistence/repositories/base.py`
- `services/agent/persistence/repositories/applications.py`
- `services/agent/persistence/repositories/sessions.py`
- `services/agent/persistence/repositories/events.py`

**Files to Modify:**
- `services/agent/src/main.py` - Update imports
- `services/agent/src/orchestrator.py` - Update imports
- `services/agent/src/session_manager.py` - Update imports
- `services/agent/src/application_runner.py` - Update imports

---

#### 1.2 Fix browser_use Configuration
**Estimated Time:** 1 hour

**Tasks:**
1. Fix Grok API base URL in `base.py`
2. Add Chrome channel configuration
3. Add proper error handling for LLM initialization

**Files to Modify:**
- `services/agent/src/agents/base.py`

---

#### 1.3 Consolidate Database Schema
**Estimated Time:** 2-3 hours

**Tasks:**
1. Remove `init.sql` (redundant)
2. Promote `001_schema.sql` (renamed from `002_comprehensive_schema.sql`) as the single source of truth
3. Add migration for existing data if needed
4. Update backend repository to use UUID instead of integer IDs

**Files to Modify:**
- `infrastructure/postgres/init-scripts/init.sql` - Delete or rename
- `infrastructure/postgres/init-scripts/001_schema.sql` - Ensure it is primary and up to date
- `services/backend/src/domain/job/entities.ts` - Change id type
- `services/backend/src/domain/job/repository.ts` - Update queries

---

#### 1.4 Fix Environment Variables
**Estimated Time:** 1 hour

**Tasks:**
1. Standardize all environment variable names
2. Update `.env.example` with correct names
3. Add validation in both services

**Files to Modify:**
- `.env.example`
- `services/agent/src/utils/captcha_solver.py`
- `services/backend/src/infra/index.ts`

---

### Phase 2: Database Separation (Priority: HIGH)

#### 2.1 Create Standalone Database Configuration
**Estimated Time:** 2-3 hours

**Tasks:**
1. Create `docker-compose.shared-db.yml` for standalone database
2. Create initialization script for multiple databases
3. Update main `docker-compose.yml` to use external network
4. Create `docker-compose.db.yml` as alias for backward compatibility
5. Document the new setup

**Files to Create:**
- `docker-compose.shared-db.yml`
- `infrastructure/postgres/init-scripts/00_create_databases.sh`

**Files to Modify:**
- `docker-compose.yml`
- `docker-compose.db.yml`
- `README.md`

---

### Phase 3: Browser Automation Improvements (Priority: HIGH)

#### 3.1 Configure Chrome-Based Automation
**Estimated Time:** 3-4 hours

**Tasks:**
1. Update browser-use configuration for Chrome
2. Add stealth mode improvements
3. Create browser automation abstraction layer
4. Add vibesurf.ai client (optional integration)

**Files to Create:**
- `services/agent/src/browser/__init__.py`
- `services/agent/src/browser/automation.py`
- `services/agent/src/browser/browser_use_impl.py`
- `services/agent/src/browser/vibesurf_impl.py` (optional)

**Files to Modify:**
- `services/agent/src/agents/base.py`
- `services/agent/src/agents/enhanced_form_filler.py`
- `services/agent/src/agents/form_filler.py`
- `infrastructure/docker/agent.Dockerfile`

---

### Phase 4: Complete Half-Baked Features (Priority: MEDIUM)

#### 4.1 Complete Session Management
**Estimated Time:** 3-4 hours

**Tasks:**
1. Implement session persistence with new repositories
2. Add session recovery on startup
3. Add session timeout handling
4. Add session statistics tracking

---

#### 4.2 Integrate QA Agent
**Estimated Time:** 2-3 hours

**Tasks:**
1. Integrate QA validation into application flow
2. Add database persistence for QA results
3. Implement correction application

---

#### 4.3 Complete CAPTCHA Integration
**Estimated Time:** 2-3 hours

**Tasks:**
1. Integrate CAPTCHA solver with browser automation
2. Add hCaptcha support
3. Add Cloudflare Turnstile support

---

#### 4.4 Enhance Frontend
**Estimated Time:** 4-6 hours

**Tasks:**
1. Add Tailwind CSS configuration
2. Implement job details modal/page
3. Add WebSocket for real-time updates
4. Add session management UI
5. Add configuration panel

---

### Phase 5: Production Readiness (Priority: MEDIUM)

#### 5.1 Error Handling & Logging
**Estimated Time:** 3-4 hours

**Tasks:**
1. Add structured logging throughout
2. Add proper error handling with recovery
3. Add request/response logging
4. Add performance metrics

---

#### 5.2 Docker Optimization
**Estimated Time:** 2-3 hours

**Tasks:**
1. Optimize Dockerfiles for production
2. Add multi-stage builds
3. Add health checks
4. Add resource limits

---

#### 5.3 Testing
**Estimated Time:** 4-6 hours

**Tasks:**
1. Add unit tests for repositories
2. Add integration tests for API endpoints
3. Add end-to-end tests for critical flows
4. Add CI/CD pipeline configuration

---

#### 5.4 Documentation
**Estimated Time:** 2-3 hours

**Tasks:**
1. Update README with complete setup instructions
2. Add API documentation
3. Add deployment guide
4. Add troubleshooting guide

---

## Part 5: File-by-File Changes Summary

### Files to Create (New)

| File | Purpose |
|------|---------|
| `services/agent/persistence/__init__.py` | Persistence package init |
| `services/agent/persistence/database.py` | Database connection management |
| `services/agent/persistence/models/__init__.py` | Models package init |
| `services/agent/persistence/models/application.py` | Application SQLAlchemy model |
| `services/agent/persistence/models/session.py` | Session SQLAlchemy model |
| `services/agent/persistence/models/event.py` | Event SQLAlchemy model |
| `services/agent/persistence/repositories/__init__.py` | Repositories package init |
| `services/agent/persistence/repositories/base.py` | Base repository class |
| `services/agent/persistence/repositories/applications.py` | Application repository |
| `services/agent/persistence/repositories/sessions.py` | Session repository |
| `services/agent/persistence/repositories/events.py` | Event repository |
| `services/agent/src/browser/__init__.py` | Browser automation package |
| `services/agent/src/browser/automation.py` | Browser automation abstraction |
| `services/agent/src/browser/browser_use_impl.py` | browser-use implementation |
| `docker-compose.shared-db.yml` | Standalone database config |
| `infrastructure/postgres/init-scripts/00_create_databases.sh` | Multi-database init |
| `services/frontend/tailwind.config.js` | Tailwind configuration |
| `services/frontend/postcss.config.js` | PostCSS configuration |

### Files to Modify

| File | Changes |
|------|---------|
| `services/agent/src/main.py` | Update persistence imports |
| `services/agent/src/orchestrator.py` | Update persistence imports |
| `services/agent/src/session_manager.py` | Update persistence imports |
| `services/agent/src/application_runner.py` | Update persistence imports |
| `services/agent/src/agents/base.py` | Fix Grok API URL, add Chrome config |
| `services/agent/src/agents/enhanced_form_filler.py` | Use browser abstraction |
| `services/agent/src/agents/form_filler.py` | Use browser abstraction |
| `services/agent/src/utils/captcha_solver.py` | Fix env var name |
| `services/backend/src/domain/job/entities.ts` | Change id to UUID |
| `services/backend/src/domain/job/repository.ts` | Update for UUID |
| `services/backend/src/infra/index.ts` | Add better validation |
| `services/frontend/package.json` | Add Tailwind dependencies |
| `services/frontend/src/App.tsx` | Add job details, WebSocket |
| `services/frontend/src/index.css` | Add Tailwind imports |
| `.env.example` | Standardize variable names |
| `docker-compose.yml` | Use external network |
| `docker-compose.db.yml` | Reference shared-db |
| `infrastructure/docker/agent.Dockerfile` | Add Chrome installation |
| `README.md` | Update setup instructions |

### Files to Delete/Rename

| File | Action |
|------|--------|
| `infrastructure/postgres/init-scripts/init.sql` | Rename to `001_legacy_schema.sql.disabled` |
| `infrastructure/postgres/init.sql` | Delete (duplicate) |

---

## Part 6: Mermaid Diagrams

### System Architecture

```mermaid
graph TB
    subgraph Frontend
        FE[React SPA]
    end

    subgraph Backend
        BE[Node.js/Fastify]
        TG[Telegram Bot]
        Q[BullMQ Queue]
    end

    subgraph Agent
        AG[FastAPI Agent]
        RA[Ray Workers]
        BU[browser-use]
    end

    subgraph Shared Infrastructure
        PG[(PostgreSQL)]
        RD[(Redis)]
        QD[(Qdrant)]
    end

    FE -->|HTTP| BE
    TG -->|Commands| BE
    BE -->|Queue Jobs| Q
    Q -->|Process| AG
    BE -->|Direct Call| AG
    AG -->|Spawn| RA
    RA -->|Automate| BU

    BE -->|SQL| PG
    AG -->|SQL| PG
    BE -->|Cache| RD
    Q -->|Jobs| RD
    AG -->|Vectors| QD

    style PG fill:#336791
    style RD fill:#DC382D
    style QD fill:#24A1C1
```

### Application Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant Q as Queue
    participant AG as Agent
    participant BR as Browser
    participant DB as PostgreSQL

    U->>FE: Submit Job URL
    FE->>BE: POST /jobs/apply
    BE->>DB: Create Job Record
    BE->>Q: Add to Queue
    BE-->>FE: Job ID + Status

    Q->>AG: Process Job
    AG->>DB: Update Status: in_progress
    AG->>AG: Compute Match Score
    AG->>AG: Decide Effort Level

    alt Skip Application
        AG->>DB: Update Status: skipped
    else Process Application
        AG->>BR: Fill Application Form
        BR-->>AG: Form Result
        AG->>DB: Update Status: applied/failed
    end

    AG-->>Q: Job Complete
    FE->>BE: GET /jobs
    BE->>DB: Fetch Jobs
    BE-->>FE: Job List
```

### Database Separation

```mermaid
graph LR
    subgraph Shared PostgreSQL Container
        PG[(PostgreSQL)]
        DB1[nyx_venatrix DB]
        DB2[saturnus DB]
    end

    subgraph Nyx Venatrix Project
        NV[Nyx Services]
    end

    subgraph Saturnus Project
        SAT[Saturnus Services]
    end

    NV -->|Connect| DB1
    SAT -->|Connect| DB2

    style PG fill:#336791
```

---

## Part 7: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Database migration breaks existing data | Medium | High | Create backup before migration, test on staging |
| browser-use Chrome config incompatible | Low | Medium | Test thoroughly, keep Chromium as fallback |
| Ray workers fail under load | Medium | Medium | Implement proper error handling, add monitoring |
| API rate limits from job sites | High | Medium | Implement stealth features, respect rate limits |
| CAPTCHA solving costs | Medium | Low | Set cost limits, use manual fallback |

---

## Part 8: Success Criteria

1. **Agent service starts without errors** - All imports resolve, database connects
2. **Job applications complete end-to-end** - From URL submission to form filling
3. **Database accessible by multiple projects** - Saturnus can connect to shared PostgreSQL
4. **Chrome-based automation works** - browser-use uses Chrome instead of Chromium
5. **Frontend displays real-time updates** - WebSocket or efficient polling
6. **All tests pass** - Unit, integration, and E2E tests
7. **Documentation complete** - Setup, deployment, and troubleshooting guides

---

## Appendix A: Environment Variables Reference

```bash
# Required
GROK_API_KEY=           # X.AI Grok API key
OPENAI_API_KEY=         # OpenAI API key (for embeddings)
DATABASE_URL=           # PostgreSQL connection string
AGENT_MODEL=grok-beta   # LLM model to use
EMBEDDING_MODEL=text-embedding-3-small

# Optional - External Services
TELEGRAM_BOT_TOKEN=     # Telegram bot for notifications
TELEGRAM_CHAT_ID=       # Telegram chat ID
TWOCAPTCHA_API_KEY=     # 2captcha API key (renamed from CAPTCHA_API_KEY)
VIBESURF_API_KEY=       # vibesurf.ai API key (new)

# Optional - Observability
LANGFUSE_SECRET_KEY=    # Langfuse tracing
LANGFUSE_PUBLIC_KEY=
MLFLOW_TRACKING_URI=    # MLflow experiment tracking

# Infrastructure
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_URI=http://localhost:6333

# Application Settings
MAX_CONCURRENT_WORKERS=5
HEADLESS_BROWSER=true
BROWSER_CHANNEL=chrome  # New: chrome, chromium, msedge
```

---

## Appendix B: Quick Start After Fixes

```bash
# 1. Start shared database (can be used by Saturnus later)
docker compose -f docker-compose.shared-db.yml up -d

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start Nyx Venatrix services
docker compose up -d

# 4. Verify health
curl http://localhost:3000/health  # Backend
curl http://localhost:8000/health  # Agent

# 5. Access frontend
open http://localhost:5173
```

---

*Document Version: 1.0*
*Last Updated: 2025-12-03*
*Author: Architecture Review*
