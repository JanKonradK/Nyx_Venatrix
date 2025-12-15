# Nyx Venatrix

**Advanced Distributed Agent System & Technical Showcase**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

> A sophisticated distributed system demonstrating the convergence of browser automation, microservices architecture, and Large Language Models (LLMs) to solve complex, non-deterministic workflows.

---

## Technical Stack

This project leverages a modern, high-performance stack designed for scalability and resilience:

### Core Infrastructure
*   **Language**: Python 3.12 (Agents/ML), TypeScript/Node.js (Backend/API)
*   **Orchestration**: **Ray** - For distributed computing and managing parallel agent workers.
*   **Containerization**: **Docker & Docker Compose** - Full microservices encapsulation.

### Data & Persistence
*   **Relational**: **PostgreSQL** - Primary data store for structured transaction data.
*   **Vector**: **Qdrant** - High-performance vector search for semantic matching and retrieval-augmented generation (RAG).
*   **Caching/Queue**: **Redis** - High-speed caching and task queue management.

### AI & Automation
*   **LLMs**: Integration with **OpenAI** and **Grok** APIs for reasoning and decision making.
*   **Automation**: **Playwright** & **Browser-use** for headless browser control and interaction.
*   **Observability**: **MLflow** for experiment tracking and **Langfuse** for LLM trace monitoring.

---

## Engineering Challenges & Learnings

Building Nyx Venatrix presented several significant engineering hurdles that provided deep insights into distributed systems and AI agent design.

### 1. Distributed State Management
**Challenge**: Coordinating state across multiple independent browser agents (Ray workers) and a central Node.js backend without race conditions or data inconsistency.
**Solution**: Implemented a robust event-driven architecture using Redis as a message broker and PostgreSQL for transactional integrity.
**Learning**: The importance of idempotency in distributed systems, especially when dealing with non-deterministic agent behaviors.

### 2. AI Agent Reliability
**Challenge**: LLMs can be unpredictable. Ensuring agents follow strict policies and don't "hallucinate" actions in a browser environment was critical.
**Solution**: Developed a "Policy-Driven" architecture where agent actions are validated against strict configuration files (`effort_policy.yml`, `stealth.yml`) before execution.
**Learning**: "Trust but verify" is the golden rule of AI agents. Implementing a separate QA layer to validate agent outputs significantly increased system reliability.

### 3. Vector Search Optimization
**Challenge**: Accurately matching unstructured text data against complex, multi-dimensional profiles.
**Solution**: Utilized Qdrant with hybrid search strategies, combining dense vector embeddings with sparse keyword matching.
**Learning**: The nuances of embedding models (e.g., `text-embedding-3-small`) and how preprocessing text data impacts retrieval quality.

---

## Setup & Installation

### Prerequisites
*   Docker & Docker Compose
*   Python 3.12+
*   Node.js 20+

### Quick Start (Docker)

The easiest way to explore the system is via Docker:

```bash
# 1. Configure Environment
cp .env.example .env
# Edit .env and add your API keys (OPENAI_API_KEY, GROK_API_KEY)

# 2. Start the shared PostgreSQL stack (accessible by Nyx + Saturnus)
docker compose -f docker-compose.shared-db.yml up -d

# 3. Launch Nyx services (backend, agent, frontend)
docker compose up -d

# 4. Access Services
# Backend API: http://localhost:3000
# Agent Service: http://localhost:8000
# Frontend: http://localhost:5173
```

### Local Development Setup

For deep inspection and modification:

```bash
# 1. Start Infrastructure (DB, Redis, Qdrant)
docker compose -f docker-compose.db.yml up -d
# (or run only the shared PostgreSQL stack via docker-compose.shared-db.yml)

# 2. Install Dependencies
./scripts/dev-setup.sh

# 3. Start Services Locally
./scripts/start-local.sh
```

---

## 📄 License

GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2025 Jan Konrad

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

---

This project is licensed under the **GNU General Public License v3.0**.

### What this means:
- **For learning & evaluation**: Freely view, use, and modify this code for
  educational purposes and portfolio review
- **For employers**: You can evaluate this work as a demonstration of my skills
- **For commercial use**: Not permitted without explicit permission. Any
  commercial derivative must also be released under GPL v3

This license protects my work while keeping it open for legitimate review and
learning. Make sure that this is added to the project and letting others contribute will be limited too.
