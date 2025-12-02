# Nyx Venatrix

**Autonomous Job Application System with AI-Powered Browser Automation**

[![CI](https://github.com/JanKonradK/Nyx_Venatrix/workflows/CI/badge.svg)](https://github.com/JanKonradK/Nyx_Venatrix/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A production-ready autonomous agent for intelligent job applications using browser automation, AI matching, and policy-driven decision making.

---

## 🚀 Quick Start

```bash
# 1. Start shared database infrastructure
docker compose -f docker-compose.db.yml up -d

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run migrations
python run_migrations.py

# 4. Start application services
docker compose up -d

# 5. Test the system
python cli_test_ingestion.py <job_url>
```

---

## ✨ Features

### Core Capabilities
- 🤖 **AI-Powered Matching** - OpenAI embeddings for job-profile similarity (0.0-1.0 scores)
- 📋 **Policy-Driven Decisions** - Configurable effort planning (low/medium/high)
- 🔄 **Ray Concurrency** - Up to 5 parallel browser agents
- 🛡️ **Quality Assurance** - Hallucination prevention and answer validation
- 📊 **Full Observability** - MLflow experiments + Langfuse LLM tracing
- 🎭 **Stealth Features** - Per-domain rate limiting and anti-detection

### Supported ATS Platforms
- ✅ Greenhouse
- ✅ Workday
- 🔜 Lever, SmartRecruiters, others via extensible adapter pattern

---

## 🏗️ Architecture

```
Browser Agents (Ray Workers)
    ↓
Job Ingestion → AI Matching → Effort Planning → Form Filling → QA Validation
    ↓                                                              ↓
PostgreSQL + Redis + Qdrant ← Event Logging ← MLflow + Langfuse
```

**Key Components:**
- **Orchestration**: Ray for parallel execution
- **Storage**: PostgreSQL (40+ tables), Redis (caching), Qdrant (vectors)
- **Observability**: MLflow (experiments), Langfuse (LLM tracing)
- **Browser**: Playwright + browser-use for automation

---

## 📦 Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.12
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/JanKonradK/Nyx_Venatrix.git
cd Nyx_Venatrix

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r services/agent/requirements.txt
playwright install chromium

# Start database infrastructure (runs independently)
docker compose -f docker-compose.db.yml up -d

# Run migrations
python run_migrations.py

# Start application services
docker compose up -d
```

---

## 🔧 Configuration

### Environment Variables

See `.env.example` for all configuration options. Key variables:

```bash
# Required
GROK_API_KEY=your-key           # Primary LLM
OPENAI_API_KEY=your-key         # Embeddings

# Database (auto-configured for Docker)
DATABASE_URL=postgresql://postgres:postgres@shared_postgres:5432/nyx_venatrix
REDIS_HOST=shared_redis
QDRANT_URI=http://shared_qdrant:6333

# Optional
LANGFUSE_SECRET_KEY=your-key    # LLM tracing
MLF LOW_TRACKING_URI=http://...  # Experiment tracking
```

### Policy Files

Configure behavior via YAML:
- `config/effort_policy.yml` - Effort level decisions
- `config/stealth.yml` - Rate limiting per domain
- `config/profile.json` - User profile truth data

---

## 📊 Usage

### Run Job Application

```bash
# Test single job URL
python cli_test_ingestion.py https://example.com/job/123

# Start TUI dashboard
python dashboard.py

# Run simulation
python simulate_workflow.py
```

### Manage Database

```bash
# Access PostgreSQL
docker exec -it shared_postgres psql -U postgres -d nyx_venatrix

# Run migrations
python run_migrations.py

# Check tables
\dt
SELECT COUNT(*) FROM applications;
```

### Monitoring

- **MLflow UI**: http://localhost:5000 (if deployed)
- **Langfuse**: https://cloud.langfuse.com
- **Qdrant Dashboard**: http://localhost:6334/dashboard

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific suite
pytest tests/test_qa_agent.py -v

# With coverage
pytest tests/ --cov=services/agent/src --cov-report=html
```

**Current Status**: 35/35 tests passing (100%)

---

## 📚 Documentation

- `README.md` - This file
- `TODO.md` - Development roadmap
- `BUGS.md` - Known issues and fixes
- `CONTRIBUTING.md` - Contribution guidelines

---

## 🤝 Contributing

Contributions welcome! Please read `CONTRIBUTING.md` for guidelines.

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- [browser-use](https://github.com/browser-use/browser-use) - Browser automation framework
- [Ray](https://www.ray.io/) - Distributed computing
- [MLflow](https://mlflow.org/) - Experiment tracking
- [Langfuse](https://langfuse.com/) - LLM observability

---

## 📧 Contact

**Project**: [github.com/JanKonradK/Nyx_Venatrix](https://github.com/JanKonradK/Nyx_Venatrix)

---

**Built with ❤️ using Python, Ray, PostgreSQL, and AI**
