# DeepApply 🚀

**The Local-First, Autonomous AI Agent for Job Applications.**

DeepApply is a powerful, Dockerized system designed to automate the tedious process of applying for jobs. It accepts job URLs, intelligently fills out applications using your personal profile data, and manages the entire lifecycle of your job search—all running locally on your machine for maximum privacy and control.

---

## 🧠 Powered by Grok 4.1 Fast (Reasoning)

At the core of DeepApply is **Grok 4.1 Fast**, a state-of-the-art reasoning model. We selected this model for three critical reasons:

1.  **Superior Reasoning**: Unlike standard chat models, Grok 4.1 Fast excels at complex decision-making, allowing it to understand nuanced application questions and generate tailored, high-quality answers.
2.  **Exceptional Tool Calling**: The model demonstrates incredible reliability in calling external tools. This is vital for DeepApply, which relies on the LLM to query the Salary Oracle, search your RAG vector database, and control browser actions precisely.
3.  **Cost-Effective Intelligence**: It provides "smart" model performance at a fraction of the cost of other reasoning models, making high-volume automated applications financially viable for individual users.

---

## ✨ Key Features

-   **Local-First Architecture**: Your data (CVs, personal info, application history) stays on your machine in a local PostgreSQL database.
-   **RAG (Retrieval-Augmented Generation)**: The agent "reads" your CV, bio, and project descriptions (stored as embeddings) to answer specific questions like "Describe a challenge you overcame."
-   **Intelligent Form Filling**: Uses a headless browser (Playwright) with stealth plugins to navigate job sites, extract form schemas, and fill them out autonomously.
-   **Salary Oracle**: A specialized **kdb+/q** microservice that provides quantitative salary estimations to ensure you don't lowball yourself in salary expectation fields.
-   **Multi-Platform Support**: Designed to handle various ATS platforms (Lever, Greenhouse, etc.) and job boards.
-   **Telegram Integration**: Send job links directly to your agent via a Telegram bot for on-the-go application queuing.
-   **Traceability**: Every action, answer, and form submission is logged. Screenshots are captured at key steps for verification.

---

## 🏗️ Architecture

DeepApply is built as a set of microservices orchestrated by Docker Compose:

-   **`frontend`**: A premium React + TypeScript + Vite SPA for managing jobs and viewing status.
-   **`backend`**: Node.js + Fastify API that acts as the orchestrator. It manages the job queue (BullMQ) and integrates with the LLM.
-   **`browser-worker`**: A dedicated Node.js + Playwright worker that executes the browser automation tasks (scraping, form filling).
-   **`postgres`**: The primary database, utilizing `pgvector` for storing text embeddings and relational data.
-   **`redis`**: Handles the job queues and inter-service messaging.
-   **`kdb`**: A high-performance time-series database used as the Salary Oracle.
-   **`telegram-bot`**: A simple interface to forward URLs from Telegram to the backend.

---

## 🚀 Getting Started

### Prerequisites

-   **Docker** and **Docker Compose** installed.
-   **Node.js** (for local script execution, optional if using Docker for everything).
-   API Keys:
    -   **Grok API Key** (for the brain).
    -   **OpenAI API Key** (for `text-embedding-3-small` embeddings).

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/JanKonradK/DeepApply.git
    cd DeepApply
    ```

2.  **Configure Environment**
    Copy the example environment file and add your keys.
    ```bash
    cp .env.example .env
    # Edit .env and add your GROK_API_KEY and OPENAI_API_KEY
    ```

3.  **Setup Profile Data (RAG)**
    Create a `profile_data` directory and add your personal documents (`.txt` or `.md`). The agent will use these to answer questions about you.
    ```bash
    mkdir profile_data
    # Add your files, e.g., bio.txt, experience.md
    ```

4.  **Ingest Data**
    Generate embeddings for your profile data so the agent can search them.
    ```bash
    # Start Postgres first
    docker-compose up -d postgres

    # Run the ingestion script
    cd services/backend
    npm install
    npm run ingest
    ```

5.  **Run the System**
    ```bash
    docker-compose up --build
    ```

---

## 🖥️ Usage

1.  **Access the Dashboard**: Open [http://localhost:5173](http://localhost:5173) in your browser.
2.  **Submit a Job**: Paste a URL (e.g., from LinkedIn or a company careers page) into the input box.
3.  **Watch it Work**:
    -   The job is queued.
    -   The **Browser Worker** launches a stealth browser.
    -   It scrapes the page and extracts the form fields.
    -   **Grok 4.1** analyzes the form and your profile data to generate perfect answers.
    -   The worker fills the form and saves a screenshot (check `services/browser-worker/screenshots`).

---

## 🛠️ Development

-   **Backend**: `services/backend` (Fastify, TypeScript)
-   **Frontend**: `services/frontend` (React, Vite, Tailwind/CSS)
-   **Worker**: `services/browser-worker` (Playwright)
-   **Database**: `infrastructure/postgres` (Schema initialization)

## 📝 License

MIT License.
