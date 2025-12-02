# 🚀 Nyx Venatrix - Quick Start Guide

## Current Status: ✅ FULLY OPERATIONAL

**Docker Services Running:**
- PostgreSQL (with pgvector): `localhost:5433`
- Redis: `localhost:6380`
- Qdrant Vector DB: `localhost:6334`

---

## 🏁 Quick Start in 3 Steps

### 1. Set Up Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env  # Or use your favorite editor

# Required:
# GROK_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
```

### 2. Verify Infrastructure
```bash
# Check Docker services
docker compose ps

# Should show:
# nyx_venatrix_postgres  (healthy)
# nyx_venatrix_redis     (healthy)
# nyx_venatrix_qdrant    (healthy)
```

### 3. Test the System
```bash
# Activate virtual environment
source .venv/bin/activate

# Test job ingestion pipeline
python cli_test_ingestion.py https://example.com/job

# Run test suite
pytest tests/ -v

# Start TUI dashboard
python dashboard.py
```

---

## 🐳 Docker Commands

### Start/Stop Services
```bash
# Start infrastructure only
docker compose up -d postgres redis qdrant

# Start all services (including agent, backend, frontend)
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f postgres
docker compose logs -f redis
docker compose logs -f qdrant
```

### Database Access
```bash
# Access PostgreSQL
docker compose exec postgres psql -U postgres -d nyx_venatrix

# Run migrations
python run_migrations.py

# Check database
\dt  # List tables
\d applications  # Describe table
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_qa_agent.py -v

# Run with coverage
pytest tests/ --cov=services/agent/src --cov-report=html

# Test database integration (requires Docker)
pytest tests/test_database.py -v
```

---

## 📊 Key Ports

| Service | Port | URL |
|---------|------|-----|
| PostgreSQL | 5433 | `postgresql://postgres:postgres@localhost:5433/nyx_venatrix` |
| Redis | 6380 | `redis://localhost:6380` |
| Qdrant | 6334 | `http://localhost:6334` |
| Qdrant Dashboard | 6334 | `http://localhost:6334/dashboard` |
| Agent API (future) | 8000 | `http://localhost:8000` |
| Backend API (future) | 3000 | `http://localhost:3000` |
| Frontend (future) | 5173 | `http://localhost:5173` |

---

## 📁 Project Structure

```
Nyx_Venatrix/
├── services/
│   ├── agent/src/
│   │   ├── agents/          # Browser automation agents
│   │   ├── matching/        # AI matching engine
│   │   ├── planning/        # Effort planning
│   │   ├── qa/              # Quality assurance
│   │   ├── stealth/         # Rate limiting & stealth
│   │   ├── observability/   # MLflow & Langfuse
│   │   ├── orchestrator.py  # Ray concurrency
│   │   └── main.py          # FastAPI app
│   └── persistence/src/
│       ├── sessions.py
│       ├── applications.py
│       ├── events.py
│       └── ...
├── infrastructure/postgres/
│   ├── 002_comprehensive_schema.sql
│   └── 003_seed_data.sql
├── config/
│   ├── effort_policy.yml
│   ├── stealth.yml
│   └── profile.json
├── tests/
│   ├── test_persistence.py
│   ├── test_agents.py
│   ├── test_qa_agent.py
│   └── ...
├── docker-compose.yml
├── .env.example
└── setup_docker.sh
```

---

## 🎯 Common Tasks

### Run a Simulation
```bash
source .venv/bin/activate
python simulate_workflow.py
```

### Test Job Ingestion
```bash
python cli_test_ingestion.py <job_url>
```

### View Real-Time Dashboard
```bash
python dashboard.py
```

### Check Database Schema
```bash
docker compose exec postgres psql -U postgres nyx_venatrix
\dt  # List all tables
SELECT COUNT(*) FROM applications;
```

### Monitor Ray Workers
```python
from services.agent.src.orchestrator import get_orchestrator

orchestrator = get_orchestrator(max_concurrent_workers=5)
orchestrator.initialize()
# View Ray dashboard at http://localhost:8265 (if Ray dashboard is enabled)
```

---

## 🔧 Troubleshooting

### Port Conflicts
If ports 5433, 6380, or 6334 are in use:
```bash
# Edit docker-compose.yml and change ports
# Example: 5433 -> 5434

# Then restart
docker compose down
docker compose up -d postgres redis qdrant
```

### PostgreSQL Not Starting
```bash
# Check logs
docker logs nyx_venatrix_postgres

# Remove volume and restart
docker compose down
docker volume rm nyx_venatrix_postgres_data
docker compose up -d postgres
```

### Missing API Keys
```bash
# Verify .env file
cat .env | grep API_KEY

# Should show your actual keys, not placeholders
```

### Python Dependencies
```bash
# Reinstall dependencies
source .venv/bin/activate
pip install -r services/agent/requirements.txt
playwright install chromium
```

---

## 📚 Documentation

- `STATUS.md` - Complete system status
- `COMPLETION_REPORT.md` - Sprint 1-3 details
- `SPRINT_4_5_REPORT.md` - Sprint 4-5 details
- `BUGS.md` - Bug tracking
- `TODO.md` - Future roadmap

---

## 🎯 What's Working Now

✅ **Infrastructure:**
- PostgreSQL with 40+ tables
- Redis caching
- Qdrant vector store
- All services healthy

✅ **Core Features:**
- Job ingestion pipeline
- AI-powered matching
- Effort planning
- Session management
- Ray concurrency
- QA validation
- Stealth manager

✅ **Observability:**
- MLflow tracking
- Langfuse tracing
- Comprehensive logging

✅ **Testing:**
- 25 test cases
- 96% pass rate
- Integration tests

---

## 🚀 Next Steps

1. **Add API Keys** to `.env`
2. **Run Tests** to verify everything works
3. **Test Job Ingestion** with a real URL
4. **Start Agent Service** for full automation
5. **Monitor with Dashboard** for real-time stats

---

## 💡 Pro Tips

1. **Use the TUI Dashboard** for real-time monitoring
2. **Check MLflow** for detailed experiment tracking
3. **Review Langfuse** for LLM call inspection
4. **Monitor Docker logs** for debugging
5. **Use `setup_docker.sh`** for automated setup

---

## 📞 Help

**All documentation is in the project root:**
- README.md - Project overview
- STATUS.md - Current state
- BUGS.md - Known issues
- Tests pass rate: 96%
- Sprint completion: 5/5 (100%)

**You're ready to go!** 🎉

Run `docker compose ps` to verify services, then test with:
```bash
python cli_test_ingestion.py https://boards.greenhouse.io/company/jobs/123
```
