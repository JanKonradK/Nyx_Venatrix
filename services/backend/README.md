# Backend Service: Orchestration & Lifecycle Management

This service acts as the central nervous system of the Nyx Venatrix framework, managing the event loop, state persistence, and the "Lifecycle Pipeline" of the target entities.

## 🏗️ Architecture

The backend is built as a **Modular Monolith** using Node.js and TypeScript. It is designed to be event-driven, decoupling the API layer from the background processing logic.

### Modules
-   **Domain**: Core business logic (Entities, Value Objects).
-   **Infrastructure**: Database adapters (PostgreSQL), Queue adapters (Redis).
-   **API**: REST endpoints for the frontend and external webhooks.

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
