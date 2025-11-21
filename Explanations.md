# DeepApply System Explanations

This document provides a comprehensive overview of the DeepApply system, detailing the architecture, data flow, and the purpose of each component. It serves as a guide for developers and stakeholders to understand the "why" and "how" of the project.

## System## Architecture Overview

DeepApply uses a **Modular Monolith + Worker** architecture:

1.  **Backend (Modular Monolith)**: Node.js service that handles:
    -   API for Frontend
    -   Embedded Telegram Bot
    -   Job Queue Orchestration
    -   LLM Integration (Grok/OpenAI)
    -   Database Management
2.  **Agent (Worker)**: Python service for:
    -   Browser Automation (Playwright)
    -   ML/RAG Logic
    -   Job Application Execution
3.  **Frontend**: React SPA (Vite)
4.  **Infrastructure**: Postgres (Data), Redis (Queues), Qdrant (Vector DB)

This architecture simplifies deployment and maintenance while keeping the heavy AI/Browser logic isolated in a dedicated Python worker.

### 1. Frontend (`services/frontend`)
-   **Tech Stack**: React, TypeScript, Vite, TailwindCSS, Framer Motion.
-   **Purpose**: The user interface for the system. It allows users to:
    -   Submit new job URLs.
    -   View the status of applications (Queued, In Progress, Applied, Failed).
    -   Monitor real-time analytics (Cost, Total Applications).
-   **Key Files**:
    -   `App.tsx`: Main dashboard logic and UI layout.
    -   `index.css`: Global styles and Tailwind directives.

### 2. Backend (`services/backend`)
-   **Tech Stack**: Node.js, Fastify, PostgreSQL (pg), BullMQ (Redis).
-   **Purpose**: The central orchestrator. It exposes the API used by the frontend and manages the job lifecycle.
-   **Key Files**:
    -   `src/index.ts`: Entry point, server setup, and route registration.
    -   `src/routes/jobs.ts`: API endpoints for job management (`POST /jobs/apply`, `GET /jobs`).
    -   `src/queue/index.ts`: Defines the BullMQ worker. **Crucially**, this worker delegates the heavy lifting of browser automation to the **Agent** service via HTTP. This decoupling allows us to scale the agent independently or switch implementations (A/B testing).
    -   `src/services/llm.ts`: (Legacy/Shared) Utilities for interacting with LLMs directly from the backend, primarily for the RAG ingestion process.

### 3. Agent (`services/agent`)
-   **Tech Stack**: Python, FastAPI, LangChain, Browser-Use.
-   **Purpose**: The "Brain" and "Hands" of the operation. It autonomously navigates websites and applies for jobs.
-   **Why Python?**: The Python ecosystem is superior for AI/ML agents (`langchain`, `browser-use`, `pytorch`).
-   **Key Files**:
    -   `src/main.py`: FastAPI entry point. Exposes `/apply` and `/ingest` endpoints.
    -   `src/agent_logic.py`: Contains the `DeepApplyAgent` class which wraps `browser-use`. It handles the LLM initialization (Grok) and executes the browser task. **Cost tracking logic resides here.**
    -   `src/rag_engine.py`: Manages the connection to the Vector DB (Qdrant) and handles document embedding/retrieval.

### 4. Infrastructure
-   **PostgreSQL (`infrastructure/postgres`)**:
    -   Stores relational data (`jobs`, `applications`) and vector embeddings (`embeddings` table) for the backend's legacy RAG.
    -   Uses `pgvector` extension.
-   **Redis**:
    -   Message broker for BullMQ. Handles the job queue persistence.
-   **Qdrant**:
    -   Dedicated Vector Database for the Python Agent. Optimized for high-performance vector search, used by the Agent to retrieve user profile info during the application process.

## End-to-End Process Flow

1.  **Submission**: User pastes a URL in the Frontend.
2.  **Queueing**: Frontend calls `POST /jobs/apply` on Backend. Backend saves the job to Postgres (`status: queued`) and adds it to the Redis Queue.
3.  **Processing**:
    -   The Backend Worker picks up the job from Redis.
    -   It sends a `POST /apply` request to the **Agent Service**.
4.  **Execution**:
    -   The Agent receives the URL.
    -   It initializes a `browser-use` agent with Grok 4.1 Fast.
    -   The Agent navigates to the URL, analyzes the page, and queries Qdrant for relevant user info (Bio, CV).
    -   It fills the form and submits.
    -   It calculates the cost of the operation based on token usage.
5.  **Completion**:
    -   The Agent returns the result and cost data to the Backend.
    -   The Backend updates the Postgres database with the final status and cost.
    -   The Frontend polls for updates and reflects the new status and analytics.

## Design Decisions

-   **Playwright vs. Browser-Use**: We originally considered a raw Playwright implementation (Node.js) to save costs by avoiding heavy agent frameworks. However, `browser-use` (Python) provides a higher level of abstraction and reasoning capability, which is critical for complex, non-standard job forms. We are A/B testing this trade-off.
-   **Local-First**: All data stays local. Docker Compose makes it easy to spin up the entire stack without external dependencies (other than LLM APIs).
-   **Cost Tracking**: Implemented to ensure users are aware of the spend. Real-time analytics help in making informed decisions about the volume of applications.

## File-by-File Guide

### Root Directory

-   **`docker-compose.yml`**: Orchestrates all services. Defines network, volumes, and inter-service dependencies.
-   **`README.md`**: User-facing documentation. Quick start guide and feature overview.
-   **`IMPLEMENTATION_PLAN.md`**: Developer guide for setup, A/B testing, and deployment workflows.
-   **`AB_TESTS.md`**: Logs and tracks A/B test results. Documents hypotheses, metrics, and conclusions.
-   **`Explanations.md`**: This file. Comprehensive system architecture and design rationale.
-   **`fixlater.txt`**: Technical debt tracker. Lists temporary implementations and hardcoded values.
-   **`.env.example`**: Template for environment variables. Users copy this to `.env` and fill in their API keys.

### `services/frontend/`

-   **`src/App.tsx`**: Main React component. Handles job submission, status polling, and analytics display.
-   **`src/index.css`**: Global styles using Tailwind CSS. Defines glassmorphism effects, animations, and the dark theme.
-   **`src/vite-env.d.ts`**: TypeScript definitions for Vite environment variables (e.g., `VITE_API_URL`).
-   **`package.json`**: Dependencies (React, TailwindCSS, Framer Motion) and build scripts.

### `services/backend/`

-   **`src/index.ts`**: Server entry point. Sets up Fastify, connects to Postgres, registers routes, and initializes the BullMQ worker.
-   **`src/routes/jobs.ts`**: Defines REST API endpoints (`/jobs/apply`, `/jobs/:id`, `/jobs/generate-answers`).
-   **`src/queue/index.ts`**: BullMQ worker definition. Delegates job processing to the Agent service and updates the database with cost data.
-   **`src/services/llm.ts`**: LLM utilities. Used for legacy RAG-based answer generation. Configured with Grok API.
-   **`src/services/rag.ts`**: Postgres + pgvector RAG implementation. Generates and searches embeddings for user profile data.
-   **`src/services/resolution.ts`**: URL canonicalization and platform detection logic.
-   **`scripts/ingest_profile.ts`**: Script to ingest user profile data (from `profile_data/`) into Postgres embeddings.
-   **`package.json`**: Node.js dependencies (Fastify, BullMQ, OpenAI SDK, pg).

### `services/agent/`

-   **`src/main.py`**: FastAPI application. Exposes `/apply` (triggers job application) and `/ingest` (loads profile data into Qdrant).
-   **`src/agent_logic.py`**: Core agent logic. Wraps `browser-use`, initializes the LLM, executes the task, and tracks costs.
-   **`src/rag_engine.py`**: Qdrant integration. Manages embeddings for user profile data using SentenceTransformers.
-   **`tests/test_agent.py`**: Pytest suite for the agent. Tests initialization, cost tracking, and error handling.
-   **`requirements.txt`**: Python dependencies (browser-use, langchain, pytorch, transformers, qdrant-client, pytest).
-   **`Dockerfile`**: Multi-stage build. Installs Playwright browsers and Python dependencies.

### `services/analytics/`

-   **`main.py`**: FastAPI analytics service. Provides real-time analytics endpoints (`/analytics/summary`, `/analytics/trends`, `/analytics/export`).
-   **`requirements.txt`**: Minimal dependencies (pandas, psycopg2, fastapi, uvicorn).
-   **`Dockerfile`**: Lightweight Python image optimized for analytics workloads.

### `services/browser-worker/` (Legacy - Currently Disabled)

-   **`src/worker.ts`**: Custom Playwright worker. Scrapes jobs, extracts forms, and fills them using LLM-generated answers.
-   **`src/automation/form.ts`**: Form extraction and filling utilities.
-   **Purpose**: This was the original implementation before the Python Agent. Preserved for A/B testing.

### `infrastructure/`

-   **`postgres/init.sql`**: Database schema. Defines tables (`jobs`, `embeddings`, `applications`, `salary_cache`) and enables pgvector.
-   **`sql/`**: Additional SQL scripts for migrations or manual queries.

### `.github/workflows/`

-   **`ci.yml`**: GitHub Actions CI pipeline. Builds and tests Backend, Frontend, and Agent on every push/PR.

## DevOps & MLOps Features

### Continuous Integration (CI)
-   **GitHub Actions**: Automated builds and tests for all services.
-   **Multi-language support**: Node.js (Backend, Frontend) and Python (Agent, Analytics).
-   **Caching**: npm and pip caches for faster builds.

### Cost Tracking & Analytics
-   **Real-time metrics**: Total cost, applications sent, average cost per application.
-   **Database fields**: `cost_usd`, `tokens_input`, `tokens_output` tracked per job.
-   **Analytics API**: Dedicated Python service exposing endpoints for dashboards and ML pipelines.

### Data Export for ML
-   **`/analytics/export`**: Exports job data with features (platform, time of day, success rate) ready for ML model training.
-   **Future enhancements**: Predict success rates, optimize application timing, detect failing platforms.

### Observability
-   **Logs**: All services log to stdout (Docker Compose captures these).
-   **Database**: Every job state change is persisted.
-   **Screenshots**: Agent can capture screenshots at key steps (configured in agent logic).

### Testing
-   **Unit tests**: `services/agent/tests/test_agent.py` validates cost tracking and error handling.
-   **Future**: Integration tests using pytest-docker or testcontainers.

## Why Python for the Agent?

1.  **Ecosystem**: Best-in-class libraries for LLM agents (LangChain, LlamaIndex, Browser-Use).
2.  **Playwright Support**: Python Playwright is mature and well-documented.
3.  **ML/AI Integration**: Natural fit for future ML enhancements (e.g., reinforcement learning for optimal application strategies).
4.  **Cost vs. Benefit**: While raw Playwright (Node.js) was considered to save LLM costs, the engineering overhead of maintaining custom scraping logic for every ATS platform outweighs the token cost of using an intelligent agent. The agent adapts to any website without code changes.

## Cost Savings Strategy

-   **RAG before LLM**: The agent queries Qdrant first to retrieve relevant profile info, minimizing the need for the LLM to "guess."
-   **Reasoning Models**: Grok 4.1 Fast (Reasoning) is used because it's cost-effective compared to other reasoning models while maintaining high accuracy.
-   **Batch Processing**: Jobs are queued and processed asynchronously, allowing for rate limiting and cost control.
