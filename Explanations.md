# DeepApply System Explanations

This document provides a comprehensive overview of the DeepApply system, detailing the architecture, data flow, and the purpose of each component. It serves as a guide for developers and stakeholders to understand the "why" and "how" of the project.

## System Architecture

DeepApply follows a **Microservices Architecture** orchestrated via Docker Compose. This ensures modularity, scalability, and isolation of concerns.

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
