"""
Ray Worker Pool - Multi-Agent Concurrency
Manages up to 5 parallel application agents using Ray
"""

import ray
import logging
import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
import os

logger = logging.getLogger(__name__)


@ray.remote
class ApplicationWorker:
    """
    Ray actor for running applications in parallel.
    Each worker is isolated and runs independently.
    """

    def __init__(self, worker_id: int):
        """
        Initialize worker.

        Args:
            worker_id: Worker number (0-4)
        """
        self.worker_id = worker_id
        self.applications_completed = 0
        self.applications_failed = 0

        logger.info(f"Worker {worker_id} initialized")

    async def run_application(
        self,
        application_id: str,
        job_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run single application.

        Args:
            application_id: Application UUID as string
            job_data: Job information dict
            config: Configuration dict

        Returns:
            Result dict with status, metrics
        """
        logger.info(f"Worker {self.worker_id}: Starting application {application_id}")

        try:
            # Import here to avoid serialization issues
            from application_runner import ApplicationRunner
            from matching import ProfileMatcher
            from planning import EffortPlanner
            from generation import AnswerGenerator
            from agents.enhanced_form_filler import EnhancedFormFiller
            from qa import QAAgent

            # Import persistence
            import sys
            sys.path.insert(0, config.get('persistence_path'))
            from applications import ApplicationRepository
            from events import EventRepository
            from sessions import SessionRepository

            # Initialize services (per worker)
            matcher = ProfileMatcher()
            matcher.load_profile(config.get('profile_text', ''))

            planner = EffortPlanner()
            answer_gen = AnswerGenerator(model=config.get('model', 'grok-beta'))
            form_filler = EnhancedFormFiller(answer_gen)

            # Initialize persistence
            app_repo = ApplicationRepository()
            event_repo = EventRepository()
            session_repo = SessionRepository() if config.get('session_id') else None

            # Initialize runner
            runner = ApplicationRunner(
                profile_matcher=matcher,
                effort_planner=planner,
                answer_generator=answer_gen,
                form_filler=form_filler,
                application_repo=app_repo,
                event_repo=event_repo,
                session_repo=session_repo
            )

            # Run application
            result = await runner.run_application(
                application_id=UUID(application_id),
                job_url=job_data['url'],
                job_title=job_data['title'],
                company_name=job_data['company'],
                job_description=job_data['description'],
                user_profile=config.get('user_profile', {}),
                user_effort_hint=job_data.get('effort_hint', 'medium'),
                company_tier=job_data.get('company_tier', 'normal'),
                session_id=UUID(config['session_id']) if config.get('session_id') else None,
                resume_path=config.get('resume_path')
            )

            if result.get('status') == 'success':
                self.applications_completed += 1
            else:
                self.applications_failed += 1

            logger.info(f"Worker {self.worker_id}: Application {application_id} completed with status {result.get('status')}")

            return result

        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Application {application_id} failed with error: {e}")
            self.applications_failed += 1

            return {
                'status': 'error',
                'error': str(e),
                'worker_id': self.worker_id
            }

    def get_stats(self) -> Dict[str, int]:
        """Get worker statistics"""
        return {
            'worker_id': self.worker_id,
            'completed': self.applications_completed,
            'failed': self.applications_failed,
            'total': self.applications_completed + self.applications_failed
        }


class RayWorkerPool:
    """
    Manages pool of Ray workers for parallel application processing.

    Features:
    - Up to 5 concurrent workers
    - Work queue management
    - Error isolation per worker
    - Graceful shutdown
    """

    def __init__(self, max_workers: int = 5):
        """
        Initialize Ray worker pool.

        Args:
            max_workers: Maximum number of concurrent workers (default: 5)
        """
        self.max_workers = max_workers
        self.workers: List[ray.ObjectRef] = []
        self.active_tasks: Dict[ray.ObjectRef, str] = {}

        # Initialize Ray if not already initialized
        if not ray.is_initialized():
            ray.init(
                num_cpus=max_workers,
                ignore_reinit_error=True,
                logging_level=logging.INFO
            )
            logger.info(f"Ray initialized with {max_workers} CPUs")

        # Create workers
        self.workers = [ApplicationWorker.remote(i) for i in range(max_workers)]
        logger.info(f"Created {max_workers} Ray workers")

    async def process_applications(
        self,
        applications: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple applications in parallel.

        Args:
            applications: List of application dicts with {id, job_data}
            config: Shared configuration dict

        Returns:
            List of results
        """
        logger.info(f"Processing {len(applications)} applications with {self.max_workers} workers")

        results = []
        pending_apps = applications.copy()
        active_tasks = {}

        while pending_apps or active_tasks:
            # Submit new tasks if workers available
            while len(active_tasks) < self.max_workers and pending_apps:
                app = pending_apps.pop(0)
                worker_idx = len(active_tasks) % self.max_workers
                worker = self.workers[worker_idx]

                # Submit task
                task = worker.run_application.remote(
                    application_id=str(app['id']),
                    job_data=app['job_data'],
                    config=config
                )

                active_tasks[task] = app['id']
                logger.info(f"Submitted application {app['id']} to worker {worker_idx}")

            if not active_tasks:
                break

            # Wait for any task to complete
            ready, not_ready = ray.wait(list(active_tasks.keys()), timeout=1.0)

            for task_ref in ready:
                app_id = active_tasks.pop(task_ref)
                result = ray.get(task_ref)
                result['application_id'] = app_id
                results.append(result)

                logger.info(f"Application {app_id} completed: {result.get('status')}")

            # Small delay to avoid tight loop
            await asyncio.sleep(0.1)

        logger.info(f"All {len(applications)} applications processed")
        return results

    async def get_worker_stats(self) -> List[Dict]:
        """Get statistics from all workers"""
        stats_refs = [worker.get_stats.remote() for worker in self.workers]
        stats = ray.get(stats_refs)
        return stats

    def shutdown(self):
        """Shutdown Ray and all workers"""
        logger.info("Shutting down Ray worker pool...")
        ray.shutdown()
        logger.info("Ray worker pool shut down")
