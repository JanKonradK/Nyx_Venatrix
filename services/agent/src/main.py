from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import os
from typing import Optional, List, Dict
from uuid import uuid4, UUID
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from .orchestrator import get_orchestrator
from .session_manager import SessionManager
from .rag_engine import KnowledgeBase
from .matching import ProfileMatcher, load_profile_from_resume
from .planning import EffortPlanner
from .job_ingestion import JobIngestionService
from .application_runner import ApplicationRunner
from .generation import AnswerGenerator
from .agents.enhanced_form_filler import EnhancedFormFiller
from .qa import QAAgent
from .notifications.digest_email import DigestEmailSender

# Persistence imports
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository
from persistence.src.sessions import SessionRepository

from .utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="Nyx Venatrix Agent API")

# Metrics
AGENT_RUNS = Counter('agent_runs_total', 'Total number of agent runs')
AGENT_ERRORS = Counter('agent_errors_total', 'Total number of agent errors')
AGENT_TOKENS = Counter('agent_tokens_total', 'Total tokens used', ['type'])
AGENT_COST = Counter('agent_cost_usd_total', 'Total cost in USD')
AGENT_DURATION = Histogram('agent_duration_seconds', 'Time spent running the agent')
MATCH_SCORES = Histogram('match_scores', 'Context match scores')

# Global services
profile_matcher: Optional[ProfileMatcher] = None
effort_planner: Optional[EffortPlanner] = None
job_ingestion: Optional[JobIngestionService] = None
kb: Optional[KnowledgeBase] = None
orchestrator = None
application_runner: Optional[ApplicationRunner] = None
qa_agent: Optional[QAAgent] = None


class JobRequest(BaseModel):
    url: str
    effort_mode: Optional[str] = None  # User hint, optional
    company_tier: str = "normal"  # top, normal, avoid
    keywords: List[str] = []
    # Optional metadata if we want to bypass scraping for testing
    title: Optional[str] = None
    company: Optional[str] = None
    description_clean: Optional[str] = None


class JobMetadata(BaseModel):
    """Metadata for testing without browser scraping"""
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description_clean: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize all services on startup"""
    global profile_matcher, effort_planner, job_ingestion, kb, orchestrator, application_runner, qa_agent

    # Validate environment
    required_vars = ['GROK_API_KEY', 'OPENAI_API_KEY', 'AGENT_MODEL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise RuntimeError(f"Missing environment variables: {missing_vars}")
    logger.info("Environment validated")

    # Initialize RAG (for profile data)
    logger.info("Loading RAG engine...")
    try:
        kb = KnowledgeBase()
    except Exception as e:
        logger.warning(f"RAG engine failed to initialize: {e}")
        kb = None

    # Initialize Profile Matcher
    logger.info("Initializing profile matcher...")
    profile_matcher = ProfileMatcher()

    # Load profile from RAG or profile_data
    try:
        # Try to get profile from RAG
        if kb:
            profile_chunks = kb.search_relevant_info("Complete user profile and CV", limit=5)
            profile_text = "\n\n".join(profile_chunks)
        else:
            # Fallback: Load from profile_data/CVs directory
            profile_text = ""
            cv_path = os.path.join("profile_data", "CVs")
            if os.path.exists(cv_path):
                for filename in os.listdir(cv_path):
                    if filename.endswith((".md", ".txt")):
                        with open(os.path.join(cv_path, filename), 'r') as f:
                            profile_text += f.read() + "\n\n"
                if profile_text:
                    logger.info(f"Loaded profile from {cv_path} directory")

        if profile_text:
            profile_matcher.load_profile(profile_text)
            logger.info(f"Profile loaded ({len(profile_text)} chars)")
        else:
            logger.warning("No profile found in RAG or profile_data, matcher not initialized")
    except Exception as e:
        logger.warning(f"Could not load profile: {e}")

    # Initialize Effort Planner
    logger.info("Initializing effort planner...")
    try:
        effort_planner = EffortPlanner()
        logger.info("Effort planner loaded")
    except Exception as e:
        logger.warning(f"Could not load effort planner: {e}")
        effort_planner = None

    # Initialize Job Ingestion Service
    if profile_matcher and effort_planner:
        job_ingestion = JobIngestionService(profile_matcher, effort_planner)
        logger.info("Job ingestion service initialized")

    # Initialize QA Agent
    logger.info("Initializing QA Agent...")
    try:
        qa_agent = QAAgent()
        logger.info("QA Agent loaded")
    except Exception as e:
        logger.warning(f"Could not load QA Agent: {e}")

    # Initialize Application Runner Components
    logger.info("Initializing Application Runner...")
    try:
        answer_gen = AnswerGenerator(model=os.getenv('AGENT_MODEL', 'grok-beta'))
        form_filler = EnhancedFormFiller(answer_gen)

        # Persistence Repos
        # Persistence Repos
        try:
            # Try to initialize real repositories
            # We attempt a simple operation or just init to see if DB is reachable if init does connection checks
            app_repo = ApplicationRepository()
            event_repo = EventRepository()
            session_repo = SessionRepository()
            logger.info("Persistence repositories initialized")
        except Exception as db_err:
            logger.warning(f"Database connection failed: {db_err}. Using MOCK repositories.")
            from .mocks import MockApplicationRepository, MockEventRepository, MockSessionRepository
            app_repo = MockApplicationRepository()
            event_repo = MockEventRepository()
            session_repo = MockSessionRepository()

        if profile_matcher and effort_planner:
            application_runner = ApplicationRunner(
                profile_matcher=profile_matcher,
                effort_planner=effort_planner,
                answer_generator=answer_gen,
                form_filler=form_filler,
                application_repo=app_repo,
                event_repo=event_repo,
                session_repo=session_repo
            )
            logger.info("Application Runner initialized")
        else:
            logger.warning("Application Runner skipped (dependencies missing)")

    except Exception as e:
        logger.error(f"Failed to initialize Application Runner: {e}")

    # Initialize Orchestrator
    orchestrator = get_orchestrator()

    # Initialize Session Manager
    global session_manager
    try:
        digest_sender = DigestEmailSender()
        session_manager = SessionManager(digest_sender=digest_sender)
        recovered_sessions = session_manager.recover_active_sessions()
        if recovered_sessions:
            logger.info("Session Manager initialized and recovered %d interrupted sessions", len(recovered_sessions))
        else:
            logger.info("Session Manager initialized")
    except Exception as e:
        logger.warning(f"Session Manager failed to initialize: {e}. Sessions disabled.")
        session_manager = None

    if session_manager and application_runner:
        application_runner.set_session_manager(session_manager)

    logger.info("Agent system ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    logger.info("Shutting down agent...")
    try:
        from persistence.src.database import close_db
        close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


class SessionCreateRequest(BaseModel):
    user_id: str
    session_name: str
    max_applications: int = 100
    max_duration_seconds: int = 3600
    max_parallel_agents: int = 5
    config: Optional[Dict] = None


@app.post("/sessions")
async def create_session(request: SessionCreateRequest):
    """Start a new application session"""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session Manager not initialized")

    try:
        session_id = session_manager.create_session(
            user_id=UUID(request.user_id),
            session_name=request.session_name,
            max_applications=request.max_applications,
            max_duration_seconds=request.max_duration_seconds,
            max_parallel_agents=request.max_parallel_agents,
            config=request.config
        )
        return {"status": "success", "session_id": str(session_id)}
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a running session"""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session Manager not initialized")

    try:
        session_manager.stop_session(UUID(session_id))
        return {"status": "success", "message": "Session stopped"}
    except Exception as e:
        logger.error(f"Failed to stop session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/apply")
async def apply_to_job(job: JobRequest):
    """
    Execute the full automation workflow: match → plan → execute.

    This endpoint:
    1. Analyzes the target context (via URL or provided metadata).
    2. Computes a relevance score.
    3. Plans the execution effort (Low/Medium/High).
    4. Generates content and interacts with the target site.
    """
    AGENT_RUNS.inc()

    if not application_runner:
        raise HTTPException(status_code=503, detail="Application Runner not initialized")

    # Determine effort level hint
    effort_hint = "MEDIUM"
    if job.effort_mode:
        effort_hint = job.effort_mode.upper()
        if effort_hint not in ["LOW", "MEDIUM", "HIGH"]:
            raise HTTPException(status_code=400, detail="effort_mode must be LOW, MEDIUM, or HIGH")

    with AGENT_DURATION.time():
        try:
            # Create a new application ID
            app_id = uuid4()

            # In a real scenario, we might scrape the description if not provided.
            # For v0.1, we require description_clean or title to be passed for matching,
            # or we assume the runner handles scraping (which it does via form filler, but matching happens first).
            # For this endpoint, let's assume metadata is passed or we use a placeholder if missing to allow the runner to proceed.

            description = job.description_clean or f"Target: {job.title} at {job.company}"

            # Get user profile (simplified for now, usually fetched from DB/Context)
            # We'll use the profile loaded in the matcher as the base
            user_profile = {
                "name": os.getenv("USER_FULL_NAME", "Default User"),
                "email": os.getenv("USER_EMAIL", "user@example.com")
            }

            result = await application_runner.run_application(
                application_id=app_id,
                job_url=job.url,
                job_title=job.title or "Unknown Target",
                company_name=job.company or "Unknown Entity",
                job_description=description,
                user_profile=user_profile,
                user_effort_hint=effort_hint,
                company_tier=job.company_tier
            )

            if result.get('status') == 'success':
                return {"status": "success", "data": result}
            else:
                # We return 200 even on failure to indicate the *request* was processed,
                # but the *workflow* failed.
                return {"status": "workflow_failed", "data": result}

        except Exception as e:
            AGENT_ERRORS.inc()
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze_job(url: str, metadata: JobMetadata):
    """
    Analyze a target context: compute match score and suggest effort level.

    This is a read-only endpoint that plans but does not execute.
    """
    if not job_ingestion:
        raise HTTPException(
            status_code=503,
            detail="Job ingestion service not initialized. Check profile matcher and effort planner."
        )

    if not metadata.description_clean:
        raise HTTPException(
            status_code=400,
            detail="description_clean required for analysis"
        )

    try:
        # Process through pipeline
        result = job_ingestion.process_job_url(
            url=url,
            user_effort_hint="medium",  # Default hint
            company_tier="normal",  # Default tier
            job_metadata=metadata.dict()
        )

        # Record metrics
        if result['status'] == 'processed':
            MATCH_SCORES.observe(result['match_score'])

        return result

    except Exception as e:
        AGENT_ERRORS.inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_data():
    """
    Trigger ingestion of documents from profile_data/ into RAG.
    This rebuilds the vector store with user profile data.
    """
    try:
        kb.ingest_profile_data()

        # Reload profile in matcher
        if profile_matcher:
            profile_chunks = kb.search_relevant_info("Complete user profile and CV", limit=5)
            profile_text = "\n\n".join(profile_chunks)
            profile_matcher.load_profile(profile_text)

        return {
            "status": "success",
            "message": "Ingestion complete, profile reloaded"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "active",
        "services": {
            "profile_matcher": profile_matcher is not None and profile_matcher.profile_embedding is not None,
            "effort_planner": effort_planner is not None,
            "job_ingestion": job_ingestion is not None,
            "rag": kb is not None,
            "orchestrator": orchestrator is not None,
            "application_runner": application_runner is not None,
            "qa_agent": qa_agent is not None,
            "session_manager": session_manager is not None
        }
    }
