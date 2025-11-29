# Backend Service

Orchestrates the agent pipeline, manages state persistence, and provides HTTP API for frontend and external integrations.

## Features

- HTTP API for job submissions
- Embedded Telegram bot
- Job queue management (BullMQ + Redis)
- LLM orchestration (Grok, OpenAI)
- PostgreSQL state management


## 🔄 Lifecycle Pipeline

The system tracks the full lifecycle of the target entity (e.g., a "Job Application"):

1.  **Discovery (Pre-Interaction)**:
    -   Entities are scraped or manually ingested into a "Saved" state.
    -   Deduplication logic ensures uniqueness based on URL or content hash.

2.  **Execution (Active)**:
    -   The **Agent** is dispatched to interact with the target URL.
    -   State transitions are logged (e.g., `STARTED` -> `FORM_DETECTED` -> `SUBMITTED`).

3.  **Tracking (Post-Interaction)**:
    -   **Interaction Logging**: All external communications (emails, status updates) are recorded in the `InteractionLog`.
    -   **Sentiment Analysis**: Incoming messages are analyzed for sentiment (Positive/Negative) to gauge success probability.
    -   **Metrics**: Response times (latency between submission and first reply) are calculated for heuristic optimization.

## 🔌 API Endpoints

### `POST /ingest`
Triggers the vector embedding pipeline for the Agent's RAG engine.

### `POST /apply`
Dispatches the Agent to a specific target URL.
-   **Payload**: `{ "url": "https://target.com/..." }`

### `GET /metrics`
Exposes Prometheus-compatible metrics for monitoring queue depth and throughput.
