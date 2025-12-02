# Nyx Venatrix

**Autonomous GenAI & MLOps Browser Automation Framework**

Nyx Venatrix is a high-performance, stealth-enabled framework for autonomous browser interaction and complex workflow automation. It leverages a multi-agent architecture to analyze context, plan execution strategies, generate tailored content, and interact with web interfaces using human-like behavior.

Built for MLOps engineers and AI researchers, it demonstrates advanced RAG (Retrieval-Augmented Generation), policy-based planning, and distributed agent orchestration using Ray.

---

## 🚀 Key Capabilities

-   **Distributed Multi-Agent System**: Orchestrates up to 5 concurrent agents using Ray for high-throughput automation.
-   **Context-Aware Execution**: Uses OpenAI embeddings to semantically match target content with user-defined profiles and objectives.
-   **Policy-Driven Planning**: Automatically determines "Effort Levels" (Low, Medium, High) based on semantic relevance and configurable policies.
-   **Generative Content Engine**: integrated with Grok/GPT-4 to generate context-specific text responses and form inputs.
-   **Stealth & Anti-Detection**: Implements advanced browser fingerprinting protection, randomized delays, and human-like typing patterns.
-   **Quality Assurance Layer**: Built-in QA agent validates generated content against a "Truth Source" to prevent hallucinations.
-   **Full Observability**: Native integration with MLflow for experiment tracking and Langfuse for LLM trace analysis.

---

## 🛠️ Architecture

The system is structured as a modular monolith, designed for scalability and maintainability:

```
Nyx_Venatrix/
├── services/
│   ├── agent/                 # Core Intelligence Service
│   │   ├── src/
│   │   │   ├── matching/      # Semantic matching engine
│   │   │   ├── planning/      # Policy & effort planning
│   │   │   ├── generation/    # LLM content generation
│   │   │   ├── agents/        # Browser automation agents (browser-use)
│   │   │   ├── qa/            # Validation & Hallucination checks
│   │   │   ├── concurrency/   # Ray actor pool
│   │   │   └── observability/ # MLflow & Langfuse adapters
│   │
│   └── persistence/           # Data Access Layer
│       ├── src/
│       │   ├── database.py    # Connection pooling
│       │   └── ... (repositories for state & events)
│
├── infrastructure/            # Infrastructure as Code
│   └── postgres/              # Vector-enabled Database Schema
│
├── config/                    # System Configuration
│   ├── effort_policy.yml      # Execution policies
│   ├── stealth.yml            # Rate limits & randomization settings
│   └── profile.json           # User context & truth source
```

---

## 📋 Runtime Assumptions

To ensure stability and compatibility, this project adheres to strict runtime constraints:

-   **Python**: **3.12.x** (Required).
    -   *Note: Python 3.13/3.14 are not yet supported due to Ray and MLflow dependencies.*
-   **Database**: PostgreSQL 14+ with `pgvector` extension.
-   **Orchestration**: Ray 2.x cluster (or local mode).
-   **Browser**: Chromium (managed by Playwright).

---

## 🏁 Quick Start

### 1. Prerequisites

-   Python 3.12
-   Docker & Docker Compose
-   API Keys: OpenAI, Grok (xAI), 2Captcha (optional), Langfuse (optional)

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/Nyx_Venatrix.git
    cd Nyx_Venatrix
    ```

2.  **Install Python dependencies:**
    ```bash
    cd services/agent
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    ```bash
    cp .env.example .env
    # Edit .env and add your API keys
    ```

4.  **Initialize Database:**
    ```bash
    docker compose up -d postgres
    # Apply schema
    docker exec -i nyx_venatrix_postgres psql -U postgres -d nyx_venatrix < ../../infrastructure/postgres/002_comprehensive_schema.sql
    ```

### 3. Usage

**Start the Agent Service:**
```bash
cd services/agent
uvicorn src.main:app --reload
```

**Ingest User Context:**
Load your profile/context data into the vector store:
```bash
curl -X POST http://localhost:8000/ingest
```

**Execute a Workflow (Dry Run):**
Analyze a target URL to see how the agent plans execution:
```bash
curl -X POST "http://localhost:8000/analyze?url=https://example.com/target" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Target Page Title",
    "description_clean": "Content of the target page for semantic matching..."
  }'
```

---

## ⚠️ Known Limitations

-   **Target Support**: Currently requires manual URL input. Automated discovery agents are planned for v0.2.
-   **Complex Forms**: While robust, the form filler may require custom adapters for highly dynamic JavaScript frameworks (e.g., complex multi-step wizards).
-   **CI/CD**: Full CI/CD pipelines are currently under development.

---

## ⚙️ Configuration

-   **`config/effort_policy.yml`**: Define thresholds for when the agent should expend high computational effort vs. quick execution.
-   **`config/stealth.yml`**: Configure per-domain rate limits and delay distributions to maintain stealth.
-   **`config/profile.json`**: The "Truth Source" for the QA agent. Define `skills_true` and `skills_false` to strictly control generated content accuracy.

---

## 📊 Observability

Nyx Venatrix provides production-grade observability:
-   **MLflow**: Track experiment runs, costs, and success rates.
-   **Langfuse**: Trace every LLM interaction for debugging and prompt optimization.
-   **Prometheus**: System metrics exposed at `/metrics`.

---

## 📄 License

Proprietary. All rights reserved.
