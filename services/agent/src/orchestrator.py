"""
Ray-based Orchestrator for Multi-Agent Concurrency
Manages parallel application execution with up to 5 concurrent workers
"""
import os
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncio

try:
    import ray
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    logging.warning("Ray not available - concurrency disabled")

from .application_runner import ApplicationRunner
from .matching import ProfileMatcher
from .planning import EffortPlanner
from .generation import AnswerGenerator
from .agents.enhanced_form_filler import EnhancedFormFiller
from .qa import QAAgent
from .utils.logger import get_logger

logger = get_logger(__name__)


@ray.remote
class ApplicationWorker:
    """Ray actor for running a single application"""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        logger.info(f"Worker {worker_id} initialized")

        # Initialize agent components
        self.matcher = ProfileMatcher()
        self.planner = EffortPlanner()
        self.answer_gen = AnswerGenerator()
        self.form_filler = EnhancedFormFiller(self.answer_gen)
        self.qa_agent = QAAgent()

        # Mock repositories for now (will use actual in production)
        from persistence.repositories import ApplicationRepository, EventRepository

        self.app_repo = ApplicationRepository()
        self.event_repo = EventRepository()

        self.runner = ApplicationRunner(
            profile_matcher=self.matcher,
            effort_planner=self.planner,
            answer_generator=self.answer_gen,
            form_filler=self.form_filler,
            application_repo=self.app_repo,
            event_repo=self.event_repo,
            qa_agent=self.qa_agent
        )

    async def run_application(self, app_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single application"""
        try:
            logger.info(f"Worker {self.worker_id} starting application {app_config['application_id']}")

            result = await self.runner.run_application(**app_config)

            logger.info(f"Worker {self.worker_id} completed application {app_config['application_id']}: {result['status']}")
            return result

        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'application_id': app_config.get('application_id')
            }


class RayOrchestrator:
    """Orchestrates parallel application execution using Ray"""

    def __init__(self, max_concurrent_workers: int = 5):
        if not RAY_AVAILABLE:
            raise RuntimeError("Ray is not installed. Install with: pip install ray")

        self.max_workers = max_concurrent_workers
        self.initialized = False
        self.workers = []
        logger.info(f"RayOrchestrator created with max_workers={max_concurrent_workers}")

    def initialize(self):
        """Initialize Ray runtime and worker pool"""
        if not self.initialized:
            if not ray.is_initialized():
                ray.init(ignore_reinit_error=True, logging_level=logging.INFO)

            # Create worker pool
            self.workers = [ApplicationWorker.remote(i) for i in range(self.max_workers)]
            self.initialized = True
            logger.info(f"Ray runtime initialized with {len(self.workers)} workers")

    def shutdown(self):
        """Shutdown Ray runtime"""
        if self.initialized:
            # Kill workers (optional, ray.shutdown handles it usually)
            for worker in self.workers:
                ray.kill(worker)
            self.workers = []

            ray.shutdown()
            self.initialized = False
            logger.info("Ray runtime shutdown")

    async def run_session(
        self,
        session_id: UUID,
        applications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run a batch of applications in parallel.

        Args:
            session_id: Session UUID
            applications: List of application configs

        Returns:
            List of results
        """
        self.initialize()

        logger.info(f"Starting session {session_id} with {len(applications)} applications")

        # Distribute work
        results = []
        pending_tasks = []

        for i, app_config in enumerate(applications):
            # Assign to worker (round-robin)
            worker = self.workers[i % len(self.workers)]

            # Add session_id to config
            app_config['session_id'] = session_id

            # Submit task
            task = worker.run_application.remote(app_config)
            pending_tasks.append(task)

        # Wait for all tasks to complete
        logger.info(f"Submitted {len(pending_tasks)} tasks, waiting for completion...")
        results = await asyncio.gather(*[asyncio.create_task(self._ray_to_asyncio(task)) for task in pending_tasks])

        logger.info(f"Session {session_id} completed: {len(results)} results")

        # Aggregate stats
        successful = sum(1 for r in results if r.get('status') == 'success')
        failed = sum(1 for r in results if r.get('status') == 'failed')
        errors = sum(1 for r in results if r.get('status') == 'error')

        logger.info(f"Session stats - Success: {successful}, Failed: {failed}, Errors: {errors}")

        return results

    async def _ray_to_asyncio(self, ray_task):
        """Convert Ray task to asyncio-compatible awaitable"""
        # Ray's get() is blocking, so we run it in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, ray.get, ray_task)


class SingleThreadOrchestrator:
    """Fallback orchestrator when Ray is not available"""

    def __init__(self):
        logger.warning("Using single-threaded orchestrator (Ray not available)")

        # Initialize single runner
        from persistence.repositories import ApplicationRepository, EventRepository

        self.matcher = ProfileMatcher()
        self.planner = EffortPlanner()
        self.answer_gen = AnswerGenerator()
        self.form_filler = EnhancedFormFiller(self.answer_gen)
        self.qa_agent = QAAgent()

        self.app_repo = ApplicationRepository()
        self.event_repo = EventRepository()

        self.runner = ApplicationRunner(
            profile_matcher=self.matcher,
            effort_planner=self.planner,
            answer_generator=self.answer_gen,
            form_filler=self.form_filler,
            application_repo=self.app_repo,
            event_repo=self.event_repo,
            qa_agent=self.qa_agent
        )

    async def run_session(
        self,
        session_id: UUID,
        applications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run applications sequentially"""
        logger.info(f"Starting single-threaded session {session_id} with {len(applications)} applications")

        results = []
        for app_config in applications:
            app_config['session_id'] = session_id
            result = await self.runner.run_application(**app_config)
            results.append(result)

        return results


def get_orchestrator(max_concurrent_workers: int = 5):
    """Factory function to get appropriate orchestrator"""
    if RAY_AVAILABLE:
        return RayOrchestrator(max_concurrent_workers)
    else:
        return SingleThreadOrchestrator()
