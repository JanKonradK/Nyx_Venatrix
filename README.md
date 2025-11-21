# DeepApply

**The Local-First, Autonomous AI Agent for Job Applications.**

DeepApply is a Dockerized system designed to automate the process of applying for jobs. It accepts job URLs, intelligently fills out applications using your personal profile data, and manages the lifecycle of your job search. It runs locally on your machine for privacy and control.

## Powered by Grok 4.1 Fast

At the core of DeepApply is **Grok 4.1 Fast (Reasoning)**. I selected this model for three reasons:

1.  **Reasoning**: Unlike standard chat models, Grok 4.1 Fast excels at decision-making, allowing it to understand nuanced application questions and generate tailored answers.
2.  **Tool Calling**: The model is reliable in calling external tools. This is vital for DeepApply, which relies on the LLM to query the Salary Oracle, search your RAG vector database, and control browser actions.
3.  **Cost**: It provides high performance at a fraction of the cost of other reasoning models, making high-volume automated applications viable.

## Key Features

-   **Local-First Architecture**: Your data (CVs, personal info, application history) stays on your machine in a local PostgreSQL database.
-   **RAG (Retrieval-Augmented Generation)**: The agent reads your CV, bio, and previous work experiences (stored as embeddings) to answer specific questions like "Describe a challenge you overcame."
-   **Intelligent Form Filling**: Uses a headless browser (Playwright) with stealth plugins to navigate job sites, extract form schemas, and fill them out.
-   **Salary Oracle**: A specialized kdb+/q microservice that provides quantitative salary estimations so you don't lowball yourself.
-   **Multi-Platform Support**: Designed to handle various ATS platforms and job boards.
-   **Telegram Integration**: Send job links directly to your agent via a Telegram bot.
-   **Traceability**: Every action, answer, and form submission is logged. Screenshots are captured at key steps.

## Architecture
## 📚 Documentation

- [**Architecture Overview**](docs/ARCHITECTURE.md) - Modular Monolith + Worker design
- [**Implementation Plan**](docs/IMPLEMENTATION_PLAN.md) - Current status and roadmap
- [**Migration Summary**](docs/MODULAR_MONOLITH_MIGRATION.md) - Details on the recent refactor
- [**Explanations**](docs/Explanations.md) - Deep dive into system components
- [**Fix Later**](docs/Fix_Later.md) - Technical debt and future improvements

## 🏗️ Architecture

DeepApply uses a **Modular Monolith + Worker** architecture:

1.  **Backend** (`services/backend`): Node.js modular monolith (API, Telegram, Queues)
2.  **Agent** (`services/agent`): Python worker (Browser Automation, RAG)
3.  **Frontend** (`services/frontend`): React SPA
4.  **Infrastructure**: Postgres, Redis, Qdrant

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local dev)
- Python 3.12+ (for local dev)
- API Keys: `GROK_API_KEY`, `OPENAI_API_KEY`

### Quick Start

1.  **Clone the repository**
    ```bash
    git clone https://github.com/JanKonradK/DeepApply.git
    cd DeepApply
    ```

2.  **Configure Environment**
    ```bash
    cp .env.example .env

4.  **Ingest Data**
    -   **Backend**:
        ```bash
        docker-compose up -d postgres
        cd services/backend && npm install && npm run ingest
        cd ../..
        ```
    -   **Agent**:
        Start the services first, then trigger ingestion.
        ```bash
        docker-compose up -d
        curl -X POST http://localhost:8000/ingest
        ```

5.  **Run the System**
    ```bash
    docker-compose up --build
    ```

## Usage

1.  **Access the Dashboard**: Open http://localhost:5173 in your browser.
2.  **Submit a Job**: Paste a URL (e.g., from LinkedIn or a company careers page) into the input box.
3.  **Watch it Work**:
    -   The job is queued.
    -   The Browser Worker launches a stealth browser.
    -   It scrapes the page and extracts the form fields.
    -   Grok 4.1 Fast analyzes the form and your profile data to generate answers.
    -   The worker fills the form and saves a screenshot (check `services/browser-worker/screenshots`).

## Development

-   **Backend**: `services/backend`
-   **Frontend**: `services/frontend`
-   **Worker**: `services/browser-worker`
-   **Database**: `infrastructure/postgres`

## License

MIT License.
