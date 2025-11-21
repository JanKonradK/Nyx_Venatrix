# Temporary Items and Technical Debt to Fix Later

This file tracks temporary implementations, hardcoded values, and items that need refinement for a production-ready environment.

## ✅ Completed

- ~~services/backend/src/services/llm.ts: Model names are configurable via AGENT_MODEL and EMBEDDING_MODEL environment variables, but should validate these exist on startup.~~ **FIXED**: Added environment variable validation in new modular architecture.
- ~~services/agent/src/agent_logic.py: Cost calculation is currently using placeholder estimates.~~ **FIXED**: Implemented LangChain `get_openai_callback()` for accurate token tracking.
- ~~docker-compose.yml: Missing AGENT_MODEL and EMBEDDING_MODEL environment variables.~~ **FIXED**: All services properly configured.
- ~~**ARCHITECTURE**: The worker currently delegates to the 'agent' service via HTTP. This is a temporary A/B test setup.~~ **FIXED**: Adopted modular monolith + worker architecture. See ARCHITECTURE.md.
- ~~**TELEGRAM BOT**: Separate service.~~ **FIXED**: Integrated into backend monolith.
- ~~**BROWSER-WORKER**: Commented out for A/B testing.~~ **RESOLVED**: Agent service won. Browser-worker can be removed entirely.

## 🎯 Architectural Decisions Made

✅ **Backend as Modular Monolith**: Single deployable unit with internal modules (domain/job, llm, integrations, queues, infra)
✅ **Single Agent Service**: Kept separate due to different tech stack (Python) and scaling needs
✅ **Telegram Bot Embedded**: Integrated into backend (simpler than separate service)
✅ **Infrastructure vs Services**: Treat Postgres/Redis/Qdrant as infrastructure, not business services

## 🔄 Migration Tasks

- [ ] **Install new dependencies**: `cd services/backend && npm install` (added `axios` and `telegraf`)
- [ ] **Test new backend**: Verify all routes work with modular architecture
- [ ] **Remove old files**: Clean up old `services/backend/src/index.ts`, `routes/jobs.ts`, `services/llm.ts` (superseded by modules)
- [ ] **Remove browser-worker**: Delete `services/browser-worker` directory entirely (A/B test complete, Agent won)
- [ ] **Remove telegram-bot service**: Delete `services/telegram-bot` directory (now embedded in backend)
- [ ] **Update .gitignore**: Already done

## 📝 Nice-to-Have Improvements

- Add integration tests for the full job application flow (backend → agent → database)
- Implement retries with exponential backoff for failed agent runs
- Add Prometheus metrics collection for observability (see MONITORING.md)
- Consider implementing a circuit breaker pattern for agent service calls
- Add database migrations framework (e.g., `node-pg-migrate`)
- Implement profile management domain module (domain/profile)
- Add application lifecycle tracking (domain/application)
