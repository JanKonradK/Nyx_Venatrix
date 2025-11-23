# DeepApply: Autonomous Browser Instrumentation & Inference Framework

<div align="center">

![DeepApply Logo](https://via.placeholder.com/150)

**A High-Throughput, Event-Driven Architecture for Autonomous Agentic Workflows.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://www.docker.com/)

</div>

DeepApply is a containerized, modular monolith designed to orchestrate complex, multi-step browser interactions through autonomous agents. It leverages a local-first vector database for Retrieval-Augmented Generation (RAG) and utilizes advanced Large Language Models (LLMs) for heuristic decision-making and semantic analysis of unstructured web data.

## 🔬 Core Technologies & Paradigms

-   **Autonomous AI Agents**: Implements self-correcting, goal-oriented agents capable of navigating dynamic DOM structures and executing complex workflows without human intervention.
-   **Retrieval-Augmented Generation (RAG)**: Utilizes a high-dimensional vector space (Qdrant) to semantically index and retrieve context-aware data, minimizing hallucination and maximizing inference accuracy.
-   **Inference Engine Agnosticism**: While optimized for **Grok 4.1 Fast (Reasoning)** for its superior chain-of-thought capabilities and tool-use reliability, the architecture supports plug-and-play integration with any OpenAI-compatible LLM endpoint.
-   **Browser Instrumentation & Fingerprint Normalization**: Deploys headless browser instances (Playwright) with advanced user-agent normalization and fingerprint management to ensure consistent, undetectable interaction with target web properties.
-   **Event-Driven Architecture**: Decouples microservices via a Redis-backed message queue, ensuring high availability, fault tolerance, and scalable throughput for asynchronous task processing.
-   **Quantitative Heuristics**: Integrates a kdb+/q microservice for real-time statistical modeling and quantitative estimation, providing data-driven constraints for agent decision logic.

## 🏗️ System Architecture

The system follows a **Modular Monolith + Worker** pattern, ensuring separation of concerns while maintaining development velocity:

1.  **Orchestration Layer** (`services/backend`): Node.js-based API gateway and event dispatcher, managing state persistence and queue telemetry.
2.  **Inference & Execution Worker** (`services/agent`): Python-based autonomous worker handling DOM manipulation, RAG pipeline execution, and LLM reasoning loops.
3.  **Observability Dashboard** (`services/frontend`): React-based SPA for real-time monitoring of agent state, queue depth, and inference logs.
4.  **Persistence Layer**:
    -   **PostgreSQL**: Relational state management.
    -   **Redis**: Ephemeral message brokering.
    -   **Qdrant**: Vector similarity search engine.

### Vector Space Organization (`profile_data/`)
Data is ingested into a hierarchical vector store to optimize semantic retrieval precision:
-   `CVs/`: High-priority biographical embeddings.
-   `Professional_Info/`: Chronological employment vectors.
-   `Academic_Info/`: Educational credential embeddings.
-   `Personal_Info/`: Unstructured semantic context.
-   `Other_Info/`: Auxiliary data points.

## 🚀 Deployment & Instantiation

### Prerequisites

-   Docker Engine & Docker Compose (v2.0+)
-   Node.js 20+ (LTS)
-   Python 3.12+
-   LLM API Credentials (`GROK_API_KEY`, `OPENAI_API_KEY`)

### Initialization Sequence

1.  **Repository Cloning**
    ```bash
    git clone https://github.com/JanKonradK/DeepApply.git
    cd DeepApply
    ```

2.  **Environment Configuration**
    ```bash
    cp .env.example .env
    # Configure API keys and hyper-parameters
    ```

3.  **Data Ingestion Pipeline**
    Populate the `profile_data/` directory with unstructured text corpora.
    ```bash
    docker-compose up -d
    # Trigger vector embedding pipeline
    curl -X POST http://localhost:8000/ingest
    ```

4.  **System Startup**
    ```bash
    docker-compose up --build
    ```

## 📚 Documentation

Detailed technical specifications are available for internal review:
-   [**Architecture Overview**](docs/ARCHITECTURE.md)
-   [**Contributing**](CONTRIBUTING.md)

## 🤝 Contribution

We welcome PRs from engineers interested in advancing the state of autonomous web agents. Please review [CONTRIBUTING.md](CONTRIBUTING.md) for code standards and linting rules.

## 📄 License

MIT License.
