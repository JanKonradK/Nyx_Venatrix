from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from .orchestrator import Orchestrator
from .rag_engine import KnowledgeBase

app = FastAPI(title="Nyx Venatrix Agent API")

# Metrics
AGENT_RUNS = Counter('agent_runs_total', 'Total number of agent runs')
AGENT_ERRORS = Counter('agent_errors_total', 'Total number of agent errors')
AGENT_TOKENS = Counter('agent_tokens_total', 'Total tokens used', ['type'])
AGENT_COST = Counter('agent_cost_usd_total', 'Total cost in USD')
AGENT_DURATION = Histogram('agent_duration_seconds', 'Time spent running the agent')

class JobRequest(BaseModel):
    url: str
    effort_mode: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    keywords: list[str] = []

@app.on_event("startup")
async def startup_event():
    # Validate environment
    required_vars = ['GROK_API_KEY', 'AGENT_MODEL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        raise RuntimeError(f"Missing environment variables: {missing_vars}")
    print("✓ Environment validated")

    # Initialize RAG
    print("📚 Loading embedding model...")
    global kb, orchestrator
    kb = KnowledgeBase()
    orchestrator = Orchestrator()
    print("✅ Agent system ready")


@app.post("/apply")
async def apply_to_job(job: JobRequest):
    """
    Apply to a job using the configured effort mode.

    Effort modes:
    - LOW: Minimal effort (no cover letter, quick fill)
    - MEDIUM: Standard (cover letter, careful fill)
    - HIGH: Maximum (tailored CV + cover letter + review)
    """
    AGENT_RUNS.inc()

    # Validate effort mode
    effort_mode = job.effort_mode.upper()
    if effort_mode not in ["LOW", "MEDIUM", "HIGH"]:
        raise HTTPException(status_code=400, detail="effort_mode must be LOW, MEDIUM, or HIGH")

    with AGENT_DURATION.time():
        try:
            # Get user profile from RAG
            user_profile = kb.search_relevant_info("Complete user profile", limit=3)
            user_profile_text = "\n".join(user_profile)

            # Run orchestrated pipeline
            result = await orchestrator.run_pipeline(
                url=job.url,
                effort_level=effort_mode,
                user_profile=user_profile_text
            )

            # Record metrics (estimate costs)
            estimated_cost = {"LOW": 0.01, "MEDIUM": 0.05, "HIGH": 0.15}.get(effort_mode, 0.05)
            AGENT_COST.inc(estimated_cost)

            return {"status": "success", "effort_mode": effort_mode, "result": result}
        except Exception as e:
            AGENT_ERRORS.inc()
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_data():
    """
    Trigger ingestion of documents from the vault.
    """
    try:
        kb.ingest_profile_data()
        return {"status": "success", "message": "Ingestion complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def health():
    return {"status": "active", "gpu": False}
