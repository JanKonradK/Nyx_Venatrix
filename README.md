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

DeepApply is built as a set of microservices orchestrated by Docker Compose:

-   **frontend**: React + TypeScript + Vite SPA for managing jobs and viewing status.
-   **backend**: Node.js + Fastify API that acts as the orchestrator. It manages the job queue and integrates with the LLM.
-   **agent**: Python + FastAPI service using `browser-use` and `langchain` for autonomous job applications.
-   **postgres**: The primary database, utilizing pgvector for storing text embeddings and relational data.
-   **qdrant**: Vector database for the Agent's knowledge base.
-   **redis**: Handles the job queues and inter-service messaging.
-   **kdb**: A high-performance time-series database used as the Salary Oracle.
-   **telegram-bot**: A simple interface to forward URLs from Telegram to the backend.

## Getting Started

### Prerequisites

-   Docker and Docker Compose
-   Node.js (optional, for local script execution)
-   API Keys:
    -   Grok API Key
    -   OpenAI API Key

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/JanKonradK/DeepApply.git
    cd DeepApply
    ```

2.  **Configure Environment**
    Copy the example environment file and add your keys.
    ```bash
    cp .env.example .env
    # Edit .env and add:
    # GROK_API_KEY, OPENAI_API_KEY, AGENT_MODEL, EMBEDDING_MODEL
    ```

3.  **Setup Profile Data**
    -   **For Backend (Postgres)**: Create `profile_data` directory and add your documents.
    -   **For Agent (Qdrant)**: Add your documents to `knowledge_base/obsidian_vault`.
    ```bash
    mkdir profile_data
    mkdir -p knowledge_base/obsidian_vault
    # Add your files, e.g., bio.txt, experience.md
    ```

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
