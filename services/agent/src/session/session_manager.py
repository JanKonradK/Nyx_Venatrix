"""
Session Management API
Handles creation, control, and monitoring of AP application sessions
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from persistence.src.sessions import SessionRepository
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository

logger = logging.getLogger(__name__)


class SessionManager:
    """High-level session management"""

    def __init__(self):
        self.session_repo = SessionRepository()
        self.app_repo = ApplicationRepository()
        self.event_repo = EventRepository()
        logger.info("SessionManager initialized")

    def create_session(
        self,
        user_id: UUID,
        session_name: Optional[str] = None,
        max_applications: Optional[int] = None,
        max_duration_seconds: Optional[int] = None,
        max_parallel_agents: int = 5,
        config_snapshot: Optional[Dict] = None
    ) -> UUID:
        """
        Create a new application session.

        Args:
            user_id: User UUID
            session_name: Optional name for the session
            max_applications: Max number of applications to process
            max_duration_seconds: Max session duration
            max_parallel_agents: Max concurrent workers
            config_snapshot: Snapshot of current configuration

        Returns:
            Session UUID
        """
        session_id = self.session_repo.create_session(
            user_id=user_id,
            session_name=session_name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            max_applications=max_applications,
            max_duration_seconds=max_duration_seconds,
            max_parallel_agents=max_parallel_agents,
            config_snapshot=config_snapshot or {}
        )

        logger.info(f"Created session {session_id} for user {user_id}")

        # Log session creation event
        self.event_repo.log_session_event(
            session_id=session_id,
            event_type='session_created',
            message=f"Session created: {session_name}",
            payload={
                'max_applications': max_applications,
                'max_parallel_agents': max_parallel_agents
            }
        )

        return session_id

    def start_session(self, session_id: UUID):
        """Mark session as running"""
        self.session_repo.update_status(session_id, 'running')

        self.event_repo.log_session_event(
            session_id=session_id,
            event_type='session_started',
            message='Session execution started'
        )

        logger.info(f"Session {session_id} started")

    def complete_session(self, session_id: UUID, success: bool = True):
        """Mark session as completed"""
        status = 'completed' if success else 'failed'
        self.session_repo.update_status(session_id, status)

        # Generate digest
        stats = self.session_repo.get_session_stats(session_id)

        self.event_repo.log_session_event(
            session_id=session_id,
            event_type='session_completed',
            message=f'Session completed with status: {status}',
            payload=stats
        )

        logger.info(f"Session {session_id} completed: {stats}")

        return stats

    def pause_session(self, session_id: UUID):
        """Pause a running session"""
        self.session_repo.update_status(session_id, 'paused')

        self.event_repo.log_session_event(
            session_id=session_id,
            event_type='session_paused',
            message='Session paused by user or system'
        )

        logger.info(f"Session {session_id} paused")

    def get_session_status(self, session_id: UUID) -> Dict[str, Any]:
        """Get current session status and stats"""
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        stats = self.session_repo.get_session_stats(session_id)

        return {
            'session_id': session_id,
            'status': session['status'],
            'start_datetime': session['start_datetime'],
            'end_datetime': session.get('end_datetime'),
            'stats': stats
        }

    def add_applications_to_session(
        self,
        session_id: UUID,
        job_configs: List[Dict[str, Any]]
    ) -> List[UUID]:
        """
        Add applications to a session.

        Args:
            session_id: Session UUID
            job_configs: List of job configurations

        Returns:
            List of created application IDs
        """
        application_ids = []

        for config in job_configs:
            app_id = self.app_repo.create_application(
                user_id=config['user_id'],
                job_post_id=config['job_post_id'],
                session_id=session_id,
                effort_level=config.get('effort_level', 'medium'),
                match_score=config.get('match_score'),
                selected_resume_version_id=config.get('resume_version_id'),
                profile_id=config.get('profile_id')
            )
            application_ids.append(app_id)

        logger.info(f"Added {len(application_ids)} applications to session {session_id}")

        return application_ids

    def get_queued_applications(
        self,
        session_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get queued applications for a session"""
        return self.app_repo.get_queued_applications(session_id, limit)
