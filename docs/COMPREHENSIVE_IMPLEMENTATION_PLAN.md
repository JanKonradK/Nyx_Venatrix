# Nyx Venatrix - Comprehensive Implementation Plan

## Executive Summary

This document provides the complete implementation plan for making Nyx Venatrix production-ready based on the user's detailed requirements.

### Core Requirements Summary

| Requirement | Solution |
|-------------|----------|
| LLM Model | Grok 4.1 Fast Reasoning (`grok-4-1-fast-reasoning`) via X.AI API |
| Embeddings | OpenAI `text-embedding-3-small` |
| Browser | Chrome (not Chromium) via browser-use |
| Database | Shared PostgreSQL for Nyx + Saturnus |
| Operation Mode | Fully autonomous, pause only for CAPTCHAs/SMS |
| Session Limits | 2 hours OR 200 applications per session |
| Concurrency | 5 Ray workers maximum |
| Daily Limit | 300 applications |

---

## Part 1: User Workflow Specification

### 1.1 Job Discovery Methods

1. **Manual URL Paste** - User pastes job URLs directly
2. **Company Monitor** - YAML/JSON list of company career pages to monitor
3. **Future: Automated Scraper** - Will be separate project

### 1.2 Application Decision Flow

```
Job URL → Scrape Details → Calculate Match Score → Decision:
  - Match > 50%: Apply immediately
  - Match 20-50%: Add to queue for user review
  - Match < 20%: Skip
```

### 1.3 Effort Level Matrix

| Effort | Conditions | Cover Letter | QA Review | Token Budget |
|--------|------------|--------------|-----------|--------------|
| HIGH | Match < 60% + top company OR premium location | Yes, tailored | Yes | High |
| MEDIUM | Match 50-75% OR standard company | Yes, tailored | No | Standard |
| LOW | Match > 75% OR quick-apply | No | No | Minimal |

**Auto-upgrade to MEDIUM:** If LOW effort but match > 75% OR company is top-tier

**Premium Locations:** Switzerland, Germany, Austria, Netherlands, Norway, Sweden, Denmark, Finland

### 1.4 Data Recording (Every Application)

```sql
-- All fields that must be recorded
job_title, job_description, company_name, company_industry,
city, country, posting_source, base_url,effort_level, match_score,
job_url, posting_date, posting_time,
application_date, application_time (to the second),
duration_seconds, cv_used, cv_content (if altered),
cover_letter, effort_level, match_score,
questions_answers (JSON), status, error_message,
session_id, tokens_input, tokens_output, tools_used,tools_used_number
```

### 1.5 Session Management

- **Max Duration:** 2 hours
- **Max Applications:** 200
- **End of Session:** Send digest email with stats
- **Data Retention:** Forever (never delete, only add "Correction" entries)

### 1.6 Notification Strategy

| Event | Notification Type |
|-------|-------------------|
| CAPTCHA failed 3x | Immediate Telegram |
| SMS code needed | Immediate Telegram |
| LinkedIn suspicious activity | Immediate Telegram |
| Session complete | Digest email |
| Application paused/failed | In session digest |

---

## Part 2: Critical Bugs to Fix

### Bug 1: Missing Persistence Module

**Files Affected:**
- `services/agent/src/main.py`
- `services/agent/src/orchestrator.py`
- `services/agent/src/session_manager.py`
- `services/agent/src/application_runner.py`

**Problem:** Imports from non-existent `persistence.src` module

**Solution:** Create `services/agent/persistence/` package with SQLAlchemy repositories

### Bug 2: Wrong Grok API URL

**File:** `services/agent/src/agents/base.py`

**Current:**
```python
base_url='https://api.grok.x.ai/v1'
model='grok-beta'
```

**Fixed:**
```python
base_url='https://api.x.ai/v1'
model='grok-4-1-fast-reasoning'
```

### Bug 3: Database Schema Conflict

**Problem:** Two schemas with different ID types (UUID vs INTEGER)

**Solution:**
- Delete `init.sql`
- Use `001_schema.sql` as primary (renamed from `002_comprehensive_schema.sql`)
- Update backend to use UUID

### Bug 4: Environment Variable Mismatch

**Problem:** `CAPTCHA_API_KEY` vs `TWOCAPTCHA_API_KEY`

**Solution:** Standardize to `TWOCAPTCHA_API_KEY`

### Bug 5: Missing Frontend CSS

**Problem:** Tailwind classes used but not configured

**Solution:** Add Tailwind CSS setup

---

## Part 3: Implementation Phases

### Phase 1: Critical Bug Fixes (Day 1-2)

#### 1.1 Create Persistence Module

**New Files:**
```
services/agent/persistence/
├── __init__.py
├── database.py
├── models/
│   ├── __init__.py
│   ├── application.py
│   ├── session.py
│   ├── event.py
│   └── job_post.py
└── repositories/
    ├── __init__.py
    ├── base.py
    ├── applications.py
    ├── sessions.py
    └── events.py
```

**Key Implementation - database.py:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nyx_venatrix')

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10)
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

#### 1.2 Fix Grok API Configuration

**File:** `services/agent/src/agents/base.py`

```python
self.llm = ChatOpenAI(
    base_url='https://api.x.ai/v1',
    api_key=os.getenv('GROK_API_KEY'),
    model=os.getenv('AGENT_MODEL', 'grok-4-1-fast-reasoning'),
    temperature=0.7,
)
```

#### 1.3 Consolidate Database Schema

- Delete `infrastructure/postgres/init-scripts/init.sql`
- Rename `002_comprehensive_schema.sql` to `001_schema.sql`
- Update all ID references to UUID

#### 1.4 Fix Environment Variables

Update `.env.example`:
```bash
# LLM Configuration
GROK_API_KEY=your_xai_api_key
AGENT_MODEL=grok-4-1-fast-reasoning
OPENAI_API_KEY=your_openai_key
EMBEDDING_MODEL=text-embedding-3-small

# CAPTCHA
TWOCAPTCHA_API_KEY=your_2captcha_key

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nyx_venatrix
```

---

### Phase 2: Database Separation (Day 2-3)

#### 2.1 Create Shared Database Docker Compose

**New File:** `docker-compose.shared-db.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: shared_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
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

networks:
  shared_db_network:
    name: shared_db_network
    driver: bridge
```

#### 2.2 Multi-Database Init Script

**New File:** `infrastructure/postgres/init-scripts/000_create_databases.sh`

```bash
#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE nyx_venatrix;
    CREATE DATABASE saturnus;
    GRANT ALL PRIVILEGES ON DATABASE nyx_venatrix TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE saturnus TO $POSTGRES_USER;
EOSQL
```

#### 2.3 Update Main Docker Compose

Modify `docker-compose.yml` to use external network:

```yaml
services:
  backend:
    # ... existing config
    networks:
      - shared_db_network
      - internal
    depends_on:
      postgres:
        condition: service_healthy

networks:
  shared_db_network:
    external: true
  internal:
    driver: bridge
```

---

### Phase 3: Browser Automation (Day 3-4)

#### 3.1 Chrome Configuration

**File:** `services/agent/src/utils/browser_config.py`

```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class BrowserConfig:
    channel: str = "chrome"  # Use installed Chrome
    headless: bool = False   # Visible for debugging
    disable_automation: bool = True

    @property
    def browser_kwargs(self) -> dict:
        return {
            'channel': self.channel,
            'headless': self.headless,
            'args': [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-dev-shm-usage',
            ] if self.disable_automation else []
        }

def get_browser_config() -> BrowserConfig:
    return BrowserConfig(
        channel=os.getenv('BROWSER_CHANNEL', 'chrome'),
        headless=os.getenv('HEADLESS_BROWSER', 'false').lower() == 'true',
        disable_automation=True
    )
```

#### 3.2 Stealth Timing

**File:** `services/agent/src/stealth/timing.py`

```python
import random
import asyncio

class StealthTiming:
    def __init__(self):
        self.min_keystroke_delay = 50  # ms
        self.max_keystroke_delay = 200
        self.min_click_delay = 100
        self.max_click_delay = 500
        self.min_app_delay = 30  # seconds
        self.max_app_delay = 180
        self.random_pause_probability = 0.1

    async def keystroke_delay(self):
        delay = random.randint(self.min_keystroke_delay, self.max_keystroke_delay)
        await asyncio.sleep(delay / 1000)

    async def click_delay(self):
        delay = random.randint(self.min_click_delay, self.max_click_delay)
        await asyncio.sleep(delay / 1000)

    async def between_applications(self):
        delay = random.randint(self.min_app_delay, self.max_app_delay)
        await asyncio.sleep(delay)

    async def maybe_random_pause(self):
        if random.random() < self.random_pause_probability:
            pause = random.randint(5, 30)
            await asyncio.sleep(pause)
```

---

### Phase 4: Complete Half-Baked Features (Day 4-6)

#### 4.1 Session Management

**Enhanced Session Manager:**

```python
class SessionManager:
    def __init__(self, max_duration_hours: float = 2, max_applications: int = 200):
        self.max_duration = timedelta(hours=max_duration_hours)
        self.max_applications = max_applications
        self.session_id: Optional[UUID] = None
        self.start_time: Optional[datetime] = None
        self.application_count = 0
        self.stats = SessionStats()

    def should_continue(self) -> bool:
        if not self.start_time:
            return False
        elapsed = datetime.utcnow() - self.start_time
        return (
            elapsed < self.max_duration and
            self.application_count < self.max_applications
        )

    async def end_session(self):
        await self.save_stats()
        await self.send_digest_email()
```

#### 4.2 QA Agent Integration

**For HIGH effort applications only:**

```python
class QAAgent:
    async def review_before_submit(self, application_data: dict) -> QAResult:
        # Check for hallucinations
        # Verify all required fields filled
        # Check for consistency with profile
        # Return corrections if needed
        pass
```

#### 4.3 CAPTCHA Integration

```python
class CaptchaHandler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.solver = TwoCaptchaSolver(os.getenv('TWOCAPTCHA_API_KEY'))

    async def handle_captcha(self, page, captcha_type: str) -> bool:
        for attempt in range(self.max_retries):
            try:
                solution = await self.solver.solve(page, captcha_type)
                if solution:
                    return True
            except Exception as e:
                logger.warning(f"CAPTCHA attempt {attempt + 1} failed: {e}")

        # All attempts failed - notify user
        await self.notify_user_captcha_needed()
        return False
```

#### 4.4 Digest Email

```python
class DigestEmailSender:
    async def send_session_digest(self, session: Session, stats: SessionStats):
        subject = f"Nyx Session Complete - {stats.total_applications} Applications"

        body = f"""
        Session Summary
        ===============
        Duration: {stats.duration_minutes} minutes
        Total Applications: {stats.total_applications}

        By Effort Level:
        - High: {stats.high_effort_count}
        - Medium: {stats.medium_effort_count}
        - Low: {stats.low_effort_count}

        By Status:
        - Submitted: {stats.submitted_count}
        - Failed: {stats.failed_count}
        - Paused: {stats.paused_count}

        Token Usage:
        - Total Input: {stats.total_input_tokens:,}
        - Total Output: {stats.total_output_tokens:,}
        - Avg per Application: {stats.avg_tokens_per_app:,}

        Errors:
        {self._format_errors(stats.errors)}
        """

        await self.send_email(subject, body)
```

---

### Phase 5: Frontend Improvements (Day 6-7)

#### 5.1 Add Tailwind CSS

**File:** `services/frontend/tailwind.config.js`

```javascript
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#6366f1',
        secondary: '#8b5cf6',
      }
    }
  },
  plugins: []
}
```

#### 5.2 Job Queue View

Add ability to:
- See queued jobs (20-50% match)
- Batch approve/reject
- View job details
- See application history

#### 5.3 Session Dashboard

- Current session status
- Live application count
- Token usage
- Error log

---

### Phase 6: Production Hardening (Day 7-8)

#### 6.1 Error Handling

```python
class ApplicationError(Exception):
    def __init__(self, message: str, error_type: str, recoverable: bool = True):
        self.message = message
        self.error_type = error_type
        self.recoverable = recoverable

class ErrorHandler:
    async def handle(self, error: Exception, application_id: UUID):
        if isinstance(error, CaptchaError):
            await self.pause_for_captcha(application_id)
        elif isinstance(error, RateLimitError):
            await self.pause_session()
        elif isinstance(error, FormError):
            await self.log_and_continue(error, application_id)
        else:
            await self.log_and_notify(error, application_id)
```

#### 6.2 Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_db_connection(),
        "redis": await check_redis_connection(),
        "session_active": session_manager.is_active(),
        "applications_today": await get_daily_count()
    }
```

#### 6.3 Logging

```python
import structlog

logger = structlog.get_logger()

# Usage
logger.info("application_started",
    job_id=job_id,
    company=company_name,
    effort_level=effort_level
)
```

---

## Part 4: File Changes Summary

### New Files to Create

| File | Purpose |
|------|---------|
| `services/agent/persistence/__init__.py` | Package init |
| `services/agent/persistence/database.py` | DB connection |
| `services/agent/persistence/models/*.py` | SQLAlchemy models |
| `services/agent/persistence/repositories/*.py` | Data access |
| `docker-compose.shared-db.yml` | Standalone DB |
| `infrastructure/postgres/init-scripts/000_create_databases.sh` | Multi-DB init |
| `services/agent/src/stealth/timing.py` | Randomized delays |
| `services/agent/src/notifications/digest_email.py` | Session digest |
| `services/frontend/tailwind.config.js` | CSS config |
| `services/frontend/postcss.config.js` | PostCSS config |

### Files to Modify

| File | Changes |
|------|---------|
| `services/agent/src/agents/base.py` | Fix API URL, model name |
| `services/agent/src/main.py` | Update imports |
| `services/agent/src/orchestrator.py` | Update imports, add session limits |
| `services/agent/src/session_manager.py` | Complete implementation |
| `services/agent/src/application_runner.py` | Add data recording |
| `.env.example` | Standardize variables |
| `docker-compose.yml` | Use external network |
| `services/frontend/package.json` | Add Tailwind |
| `services/frontend/src/App.tsx` | Add features |

### Files to Delete

| File | Reason |
|------|--------|
| `infrastructure/postgres/init-scripts/init.sql` | Redundant schema |
| `infrastructure/postgres/init.sql` | Duplicate |

---

## Part 5: Environment Variables

```bash
# === LLM Configuration ===
GROK_API_KEY=xai-xxxxxxxxxxxx
AGENT_MODEL=grok-4-1-fast-reasoning
OPENAI_API_KEY=sk-xxxxxxxxxxxx
EMBEDDING_MODEL=text-embedding-3-small

# === Database ===
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nyx_venatrix
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# === Redis ===
REDIS_HOST=localhost
REDIS_PORT=6379

# === Browser ===
BROWSER_CHANNEL=chrome
HEADLESS_BROWSER=false

# === CAPTCHA ===
TWOCAPTCHA_API_KEY=xxxxxxxxxxxx

# === Notifications ===
TELEGRAM_BOT_TOKEN=xxxxxxxxxxxx
TELEGRAM_CHAT_ID=xxxxxxxxxxxx
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=app_password
DIGEST_EMAIL_TO=your@email.com

# === Session Limits ===
MAX_SESSION_HOURS=2
MAX_SESSION_APPLICATIONS=200
MAX_DAILY_APPLICATIONS=300
MAX_CONCURRENT_WORKERS=5

# === Stealth ===
MIN_APP_DELAY_SECONDS=30
MAX_APP_DELAY_SECONDS=180
```

---

## Part 6: Success Criteria

1. **Agent starts without errors** - All imports resolve
2. **Applications complete end-to-end** - From URL to submission
3. **All data recorded** - Every field in PostgreSQL
4. **Session limits enforced** - Stops at 2h or 200 apps
5. **Digest emails sent** - After each session
6. **CAPTCHA handling works** - Auto-solve or pause
7. **Chrome browser used** - Not Chromium
8. **Saturnus can connect** - Shared DB accessible
9. **No LinkedIn bans** - Stealth measures effective
10. **Hallucination minimized** - QA catches errors

---

## Part 7: Estimated Timeline

| Phase | Duration | Priority |
|-------|----------|----------|
| Phase 1: Critical Bug Fixes | 2 days | CRITICAL |
| Phase 2: Database Separation | 1 day | HIGH |
| Phase 3: Browser Automation | 1 day | HIGH |
| Phase 4: Complete Features | 2 days | MEDIUM |
| Phase 5: Frontend | 1 day | MEDIUM |
| Phase 6: Production Hardening | 1 day | MEDIUM |

**Total: ~8 days of development**

---

*Document Version: 2.0*
*Last Updated: 2025-12-03*
*Based on detailed user requirements discussion*
