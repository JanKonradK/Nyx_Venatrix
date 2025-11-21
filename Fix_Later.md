# Temporary Items and Technical Debt to Fix Later

This file tracks temporary implementations, hardcoded values, and items that need refinement for a production-ready environment.

## ✅ Completed

- ~~services/backend/src/services/llm.ts: Model names are configurable via AGENT_MODEL and EMBEDDING_MODEL environment variables, but should validate these exist on startup.~~ **FIXED**: Added environment variable validation in `services/backend/src/index.ts` with clear error messages on startup.
- ~~services/agent/src/agent_logic.py: Cost calculation is currently using placeholder estimates. Need to implement precise token counting when browser-use library exposes token metadata.~~ **FIXED**: Implemented LangChain `get_openai_callback()` for accurate token tracking and cost calculation.
- ~~docker-compose.yml: Missing AGENT_MODEL and EMBEDDING_MODEL environment variables.~~ **FIXED**: Added to both backend and agent services with defaults.

## 🔄 Pending Architectural Decisions

- **services/backend/src/queue/index.ts**: The worker currently delegates to the 'agent' service via HTTP. This is a temporary A/B test setup. We should decide on a final architecture (microservices vs monolith) and clean this up once we have enough data from AB_Tests.md.
- **services/backend/src/routes/jobs.ts**: The '/jobs/generate-answers' endpoint is used by the legacy browser-worker. If we switch fully to the Python agent, this endpoint and the 'generateAnswers' service might become obsolete.
- **docker-compose.yml**: The 'browser-worker' service is commented out for A/B testing. Remove it if the Python agent proves superior (track results in AB_Tests.md).

## 📝 Nice-to-Have Improvements

- Add integration tests for the full job application flow (backend → agent → database).
- Implement retries with exponential backoff for failed agent runs.
- Add Prometheus metrics collection for observability (see MONITORING.md).
- Consider implementing a circuit breaker pattern for agent service calls.
- Add database migrations framework (e.g., `node-pg-migrate` or `Alembic`).
