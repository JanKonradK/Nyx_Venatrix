from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

from .agent_logic import DeepApplyAgent
from .rag_engine import KnowledgeBase

app = FastAPI(title="DeepApply Agent API")

class JobRequest(BaseModel):
    url: str
    keywords: list[str] = []

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
    agent = DeepApplyAgent(kb=kb)
    result = await agent.run(job.url)
    return {"status": "success", "data": result}

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

@app.get("/health")
def health():
    return {"status": "active", "gpu": False}
