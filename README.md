# DeepApply

DeepApply is a local-first, Dockerized autonomous agent for job applications.

## Architecture

- **Frontend**: React + TypeScript + Vite (Port 5173)
- **Backend**: Node.js + Fastify + BullMQ (Port 3000)
- **Worker**: Node.js + Playwright (Stealth)
- **Database**: PostgreSQL + pgvector
- **Queue**: Redis
- **Salary Oracle**: kdb+/q (Port 5000)

## Setup

1. **Environment Variables**:
   Copy `.env.example` to `.env` and fill in your keys (Grok API, etc.).
   ```bash
   cp .env.example .env
   ```

2. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

3. **Access**:
   - Frontend: [http://localhost:5173](http://localhost:5173)
   - Backend: [http://localhost:3000](http://localhost:3000)

## Usage

1. Open the Frontend.
2. Paste a job URL (e.g., LinkedIn, Indeed).
3. The agent will:
   - Queue the job.
   - Scrape the details.
   - Resolve the application form.
   - (Future) Use Grok + RAG to answer questions and submit.

## Development

- **Backend**: `services/backend`
- **Frontend**: `services/frontend`
- **Worker**: `services/browser-worker`
- **kdb+**: `services/kdb`

## Notes

- **kdb+ License**: Ensure you have a valid `kc.lic` or `q.k` if using a licensed version, or use the 32-bit free version.
- **Stealth**: The worker uses `puppeteer-extra-plugin-stealth` to avoid detection, but some sites may still block automation.
