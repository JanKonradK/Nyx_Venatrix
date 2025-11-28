from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from .agent_logic import DeepApplyAgent
from .rag_engine import KnowledgeBase

app = FastAPI(title="DeepApply Agent API")

# Metrics
AGENT_RUNS = Counter('agent_runs_total', 'Total number of agent runs')
AGENT_ERRORS = Counter('agent_errors_total', 'Total number of agent errors')
AGENT_TOKENS = Counter('agent_tokens_total', 'Total tokens used', ['type']) # type: input, output
AGENT_COST = Counter('agent_cost_usd_total', 'Total cost in USD')
AGENT_DURATION = Histogram('agent_duration_seconds', 'Time spent running the agent')

from .definitions import UserProfile

class JobRequest(BaseModel):
    url: str
    keywords: list[str] = []
    profile: UserProfile

@app.on_event("startup")
async def startup_event():
    # Validate required environment variables
    required_vars = ['GROK_API_KEY', 'AGENT_MODEL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file and ensure all required variables are set.")
        raise RuntimeError(f"Missing environment variables: {missing_vars}")
    print("✓ All required environment variables validated")

    # Initialize RAG on startup (Load PyTorch model)
    print("Loading Embedding Model (MiniLM-L6)...")
    global kb
    kb = KnowledgeBase()
    print("Model Loaded")


@app.post("/apply")
async def apply_to_job(job: JobRequest):
    """
    Trigger the agent to apply for a job.
    """
    AGENT_RUNS.inc()
    with AGENT_DURATION.time():
        try:
            agent = DeepApplyAgent(kb=kb)
            result = await agent.run(job.url, job.profile)

            # Record metrics
            if "tokens_input" in result:
                AGENT_TOKENS.labels(type='input').inc(result["tokens_input"])
            if "tokens_output" in result:
                AGENT_TOKENS.labels(type='output').inc(result["tokens_output"])
            if "cost_usd" in result:
                AGENT_COST.inc(result["cost_usd"])

            return {"status": "success", "data": result}
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
