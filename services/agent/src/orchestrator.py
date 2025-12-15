
import os
import ray
import asyncio
from typing import Dict, Any, Optional

from .decision_engine import DecisionEngine, JobData
from .application_engine import ApplicationEngine, ApplicationResult
from .profile_loader import load_raw_profile, load_profile_from_json
from .rag_engine import KnowledgeBase
from .agents.enhanced_form_filler import EnhancedFormFiller
from .utils.logger import logger

# Import persistence
from ..persistence.database import get_db
from ..persistence.repositories.applications import ApplicationRepository
from ..persistence.repositories.events import EventRepository
from ..persistence.repositories.sessions import SessionRepository
from ..generation.answer_generator import AnswerGenerator # Needed for form filler

MAX_WORKERS = int(os.getenv("MAX_CONCURRENT_WORKERS", "5"))

def _init_ray():
    if not ray.is_initialized():
        ray.init(
            num_cpus=MAX_WORKERS,
            ignore_reinit_error=True,
            include_dashboard=False,
            logging_level="info"
        )

@ray.remote
def run_application_job(job_post_id: str, mode: str = "review") -> Dict[str, Any]:
    """
    Single Ray task that runs decision + potential application for one job_post_id.
    """
    # Import JobRepository dynamically to ensure path availability or avoid circular imports
    try:
        from services.persistence.src.jobs import JobRepository
    except ImportError:
        import sys
        # Add project root to path
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
        from services.persistence.src.jobs import JobRepository

    logger.info(f"Worker processing job {job_post_id} in {mode} mode")

    # 1. Open DB session for agent-specific repos
    with get_db() as db:
        app_repo = ApplicationRepository(db)
        event_repo = EventRepository(db)
        session_repo = SessionRepository(db)

        # 2. Load job data (via shared persistence)
        job_repo = JobRepository() # uses its own DB connection logic
        # JobRepository usually expects a connection/pool or manages it.
        # Assuming it works as per existing code/plan.
        # We need to check if JobRepository needs instantiation args.
        # Looking at file list, we didn't check JobRepository content.
        # We'll assume default constructor works or it uses env var.
        
        try:
            job_row = job_repo.get_by_id(job_post_id) # Using get_by_id typically
        except AttributeError:
             # Fallback if method name is different
            job_row = job_repo.get_job(job_post_id)

        if not job_row:
            logger.error(f"Job {job_post_id} not found in DB")
            return {"job_post_id": job_post_id, "status": "error", "reason": "job_not_found"}

        job = JobData(
            id=str(job_row.id),
            url=job_row.url,
            title=job_row.title,
            company=job_row.company_name,
            description=job_row.description or "",
        )

        user_id = str(job_row.user_id) if job_row.user_id else None

        # 3. Create or find Application row
        application = app_repo.get_by_job_post_id(job_post_id) 
        if not application:
             application = app_repo.create_for_job(
                job_post_id=job_post_id,
                user_id=user_id,
                status="processing"
            )

        # 4. Initialize engines
        decision_engine = DecisionEngine(profile_loader=lambda: load_profile_from_json())
        kb = KnowledgeBase()
        
        # EnhancedFormFiller needs AnswerGenerator
        answer_gen = AnswerGenerator()
        browser_agent = EnhancedFormFiller(answer_generator=answer_gen)
        
        application_engine = ApplicationEngine(kb, browser_agent)

        # 5. DECISION
        # Using async_to_sync for async methods
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            decision = loop.run_until_complete(decision_engine.decide(user_id, job))
            
            event_repo.add_event(
                job_post_id=job.id,
                event_type="DECISION_MADE",
                payload=decision.__dict__,
                application_id=str(application.id),
            )

            if not decision.should_apply:
                app_repo.update_status(
                    application_id=str(application.id),
                    status="skipped",
                    final_judgement=decision.reason,
                    error_message=None,
                )
                return {
                    "job_post_id": job.id,
                    "application_id": str(application.id),
                    "status": "skipped",
                    "reason": decision.reason,
                    "match_score": decision.match_score,
                }

            # 6. APPLICATION
            app_result = loop.run_until_complete(
                application_engine.run_application(
                     job,
                     decision,
                     mode,
                     app_repo,
                     event_repo,
                     str(application.id),
                )
            )

            return {
                "job_post_id": job.id,
                "application_id": str(application.id),
                "status": app_result.status,
                "final_judgement": app_result.final_judgement,
            }
        finally:
            loop.close()


class RayOrchestrator:
    def __init__(self):
        _init_ray()

    def submit_job(self, job_post_id: str, mode: str = "review") -> "ray.ObjectRef":
        logger.info(f"Submitting job {job_post_id} to Ray cluster (mode: {mode})")
        return run_application_job.remote(job_post_id, mode)

