# DeepApply Implementation & A/B Testing Plan

## Current Status: ✅ Modular Monolith Architecture Complete

The project has been successfully refactored from microservices to a **Modular Monolith + Worker** architecture.
- **Backend**: Node.js Modular Monolith (API, Telegram, Queues, LLM)
- **Agent**: Python Worker (Browser Automation, RAG)
- **Infrastructure**: Postgres, Redis, Qdrant

All core features are implemented and functional.

This document outlines the steps to deploy and test the new Agent-based architecture (Plan B) vs the legacy Browser-Worker architecture (Plan A).

- **Backend**: Delegates job processing to the Agent service via HTTP.
- **Agent**: Uses `browser-use` and `langchain` with Grok 4.1 Fast to autonomously navigate and apply.
- **Browser Worker**: Currently disabled in `docker-compose.yml`.

## Setup Instructions

1.  **Environment Variables**
    Ensure your `.env` file contains:
    ```bash
    GROK_API_KEY=your_key_here
    OPENAI_API_KEY=your_key_here
    AGENT_MODEL=grok-beta
    EMBEDDING_MODEL=text-embedding-3-small
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    POSTGRES_DB=deepapply
    ```

2.  **Profile Data**
    -   Place your bio and experience documents in `knowledge_base/obsidian_vault/` (for the Agent).
    -   (Legacy) Place documents in `profile_data/` (for the Backend RAG).

3.  **Ingestion**
    Start the services and trigger ingestion for the Agent:
    ```bash
    docker-compose up -d
    curl -X POST http://localhost:8000/ingest
    ```

4.  **Running the System**
    ```bash
    docker-compose up --build
    ```
    Access the frontend at `http://localhost:5173`.

## A/B Testing Strategy

To switch back to the **Legacy Browser Worker (Plan A)**:

1.  **Edit `docker-compose.yml`**:
    -   Uncomment the `browser-worker` service.
    -   (Optional) Comment out the `agent` service to save resources.

2.  **Edit `services/backend/src/queue/index.ts`**:
    -   Revert the worker processing logic to process the job locally (or simply point it to a different queue if we were running both simultaneously, but for now, code reversion is required).
    -   *Note: The legacy logic is preserved in git history.*

3.  **Rebuild**:
    ```bash
    docker-compose up -d --build
    ```

## Debugging & Logs

-   **Backend Logs**: `docker logs -f deepapply_backend`
-   **Agent Logs**: `docker logs -f deepapply_agent`
-   **Agent Screenshots**: Check `services/agent/screenshots` (if configured) or observe the browser if running in non-headless mode (requires X11 forwarding or VNC, currently headless).

## Known Issues & Technical Debt

See `fixlater.txt` for a list of temporary items and TODOs.
