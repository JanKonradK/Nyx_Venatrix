# Nyx Venatrix Architecture - Modular Monolith

## Overview

Nyx Venatrix uses a **Modular Monolith + Worker** architecture:
- **1 Backend Service** (Node.js) - Orchestrator and API
- **1 Agent Service** (Python) - Browser automation worker
- **Infrastructure** (Postgres, Redis, Qdrant) - Datastores

This architecture provides:
- ✅ **Simplicity**: 2 business services instead of 6+ microservices
- ✅ **Maintainability**: Single codebase with clear module boundaries
- ✅ **Performance**: No inter-service HTTP overhead for internal operations
- ✅ **Flexibility**: Easy to extract modules into services if needed later

---

## Backend Service (Modular Monolith)

**Location**: `services/backend/`

### Responsibilities
- HTTP API for frontend
- Embedded Telegram bot
- Job queue management (BullMQ)
- LLM orchestration (Grok, OpenAI)
- Agent service coordination
- Database operations (Postgres)

### Module Structure

```
src/
├── app.ts                    # Main application entry point
├── domain/                   # Business logic (DDD style)
│   ├── job/                  # Job domain
│   │   ├── entities.ts       # Job entity, status enum, state machine
│   │   ├── repository.ts     # Database operations
│   │   ├── service.ts        # Business logic orchestration
│   │   └── index.ts
│   ├── profile/              # User profile domain (future)
│   └── application/          # Application lifecycle (future)
├── llm/                      # LLM clients
│   ├── client.ts             # Grok & OpenAI unified client
│   └── index.ts
├── integrations/             # External service clients
│   ├── agent.ts              # Python agent service client
│   ├── telegram.ts           # Embedded Telegram bot
│   ├── kdb.ts                # Salary Oracle (future)
│   ├── qdrant.ts             # Vector DB (future)
│   └── index.ts
├── queues/                   # Queue management
│   ├── job-queue.ts          # BullMQ worker and queue
│   └── index.ts
└── infra/                    # Infrastructure
    └── index.ts              # DB, Redis, config, env validation
```

### Key Principles

1. **Domain-Driven Design**: Business logic organized by domain (job, profile, application)
2. **Dependency Injection**: Services receive dependencies via constructor
3. **Single Responsibility**: Each module has one clear purpose
4. **Testability**: Modules can be tested in isolation

### Example: Adding a New Feature

To add a "Profile Management" feature:

1. Create `src/domain/profile/`:
   - `entities.ts` - Profile data structure
   - `repository.ts` - DB operations
   - `service.ts` - Business logic

2. Add routes in `app.ts`:
   ```typescript
   fastify.post('/profile', async (request) => {
     return profileService.create(request.body);
   });
   ```

3. No new Docker containers, no inter-service communication!

---

## Agent Service (Worker)

**Location**: `services/agent/`

### Responsibilities
- Browser automation (Playwright)
- ML/RAG logic (LangChain, Qdrant)
- Form understanding and filling
- Long-running, failure-prone tasks

### API

- `POST /apply` - Process job application
- `POST /ingest` - Update knowledge base
- `GET /health` - Health check

### Why Separate?

1. **Different Tech Stack**: Python ecosystem (LangChain, PyTorch)
2. **Different Scaling**: Can run multiple agent workers
3. **Fault Isolation**: Browser crashes don't affect backend
4. **Different Lifecycle**: Long-running (5+ minutes per job)

---

## Infrastructure (Not Business Services)

### Postgres
- **Purpose**: Relational data (jobs, applications) + vector embeddings
- **Type**: Datastore
- **Management**: Treat as infrastructure, not a microservice

### Redis
- **Purpose**: Job queue persistence (BullMQ)
- **Type**: Message broker
- **Management**: Infrastructure

### Qdrant
- **Purpose**: Agent's knowledge base (RAG)
- **Type**: Vector database
- **Management**: Infrastructure

---

## Data Flow

### Job Application Flow

```
1. User/Telegram → Backend API (POST /jobs/apply)
2. Backend → JobService.createAndQueue()
3. JobService → JobRepository.create() → Postgres
4. JobService → BullMQ.add() → Redis
5. Worker picks job from Redis
6. Worker → AgentClient.applyToJob() → Agent Service (HTTP)
7. Agent → Playwright + LLM + Qdrant
8. Agent → Returns result with cost data
9. Worker → JobService.updateStatus() → Postgres
10. Frontend polls → Backend API (GET /jobs/:id)
```

### Key Design Decisions

1. **Backend orchestrates everything**: Single source of truth for job lifecycle
2. **Agent is stateless**: Only executes tasks, doesn't manage state
3. **Queue decouples**: Backend and Agent don't need to be online simultaneously
4. **Database is authoritative**: Postgres holds canonical job status

---

## Deployment

### Development
```bash
docker-compose up
```

**Result**:
- 1 Backend container (inc. Telegram bot)
- 1 Agent container
- 1 Frontend container
- 3 Infrastructure containers (Postgres, Redis, Qdrant)

**Total: 6 containers** (down from 8+)

### Production

**Option A - Same as Dev**:
- Keep all 6 containers
- Scale agent horizontally: `docker-compose up --scale agent=3`

**Option B - Further Simplification**:
- Build frontend static files: `npm run build`
- Serve from backend via `@fastify/static`
- **Total: 5 containers**

---

## Migration from Microservices

### What Changed

**Before**:
- ❌ 6+ separate services (backend, browser-worker, telegram-bot, analytics, etc.)
- ❌ Complex inter-service communication
- ❌ Distributed tracing needed
- ❌ Multiple deployment units

**After**:
- ✅ 1 Backend monolith (with internal modules)
- ✅ 1 Agent worker
- ✅ Simple HTTP between backend ↔ agent
- ✅ 2 deployment units

### What Stayed the Same

- ✅ Agent still in Python (justified by tech stack difference)
- ✅ Frontend still separate (for dev convenience)
- ✅ Infrastructure services unchanged

---

## When to Extract a Module into a Service

Consider extracting a module into a separate service if:

1. **Different tech stack** is significantly better (like Agent/Python)
2. **Different scaling needs** (e.g., Agent needs GPU, Backend doesn't)
3. **Team boundaries** (different teams own different services)
4. **Deployment independence** (need to deploy without touching other code)

**Rule of Thumb**: Start as a module, extract only when necessary.

---

## Benefits of This Architecture

### Development Velocity
- ✅ Single codebase for most features
- ✅ No inter-service contracts to manage
- ✅ Easy refactoring within modules
- ✅ Faster feedback loop (no service restarts)

### Operations
- ✅ Fewer containers to manage
- ✅ Simpler logging (single log stream per service)
- ✅ Easier debugging (no distributed traces)
- ✅ Lower infrastructure cost

### Code Quality
- ✅ Shared types across modules
- ✅ Consistent error handling
- ✅ Single test suite
- ✅ Reusable utilities

---

## FAQ

**Q: Is this a monolith or microservices?**
A: It's a **modular monolith** with one worker service. Best of both worlds.

**Q: Can I still extract services later?**
A: Yes! Modules are designed with clear boundaries. Extract `domain/profile` → `profile-service` if needed.

**Q: Why not split backend into jobs-service, profile-service, etc.?**
A: No need. These aren't separate products. They're facets of one system (job application automation).

**Q: What about the A/B test between Agent and Browser-Worker?**
A: Keep it simple. The Agent won. Browser-worker is disabled (can remove entirely).

**Q: Should Telegram bot be in backend or separate?**
A: **In backend**. It's ~100 lines of code, same failure domain, no scaling difference. Embedding it is simpler.

---

## References

- Martin Fowler: [MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html)
- Sam Newman: [Monolith to Microservices](https://samnewman.io/books/monolith-to-microservices/)
- Shopify: [Deconstructing the Monolith](https://shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity)
