"""
Session Manager Service
Handles lifecycle of application sessions, including creation, monitoring, and digest generation.
"""
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from persistence.src.sessions import SessionRepository
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages application sessions.
    """

    def __init__(self):
        self.session_repo = SessionRepository()
        self.app_repo = ApplicationRepository()
        self.event_repo = EventRepository()

    def create_session(
        self,
        user_id: UUID,
        session_name: str,
        max_applications: int = 100,
        max_duration_seconds: int = 3600,
        max_parallel_agents: int = 5,
        config: Optional[Dict] = None
    ) -> UUID:
        """Start a new session"""
        session_id = self.session_repo.create_session(
            user_id=user_id,
            session_name=session_name,
            max_applications=max_applications,
            max_duration_seconds=max_duration_seconds,
            max_parallel_agents=max_parallel_agents,
            config_snapshot=config
        )

        self.session_repo.add_session_event(
            session_id,
            'session_started',
            f"Session '{session_name}' started"
        )

        return session_id

    def stop_session(self, session_id: UUID, reason: str = "manual_stop"):
        """Stop a running session"""
        self.session_repo.update_session_status(
            session_id,
            'completed',
            end_datetime=datetime.now()
        )

        self.session_repo.add_session_event(
            session_id,
            'session_stopped',
            f"Session stopped: {reason}"
        )

        # Trigger digest generation
        self.generate_session_digest(session_id)

    def generate_session_digest(self, session_id: UUID) -> UUID:
        """Generate and persist session digest"""
        logger.info(f"Generating digest for session {session_id}")

        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # In a real implementation, we would query the DB for these stats
        # For now, we rely on the counters in the session record

        summary_text = (
            f"Session '{session.get('session_name')}' completed.\n"
            f"Total Applications: {session.get('total_applications_attempted', 0)}\n"
            f"Successful: {session.get('total_applications_successful', 0)}\n"
            f"Cost: ${session.get('total_cost_estimated', 0):.2f}"
        )

        digest_id = self.session_repo.create_session_digest(
            session_id=session_id,
            summary_text=summary_text,
            applications_total=session.get('total_applications_attempted', 0),
            applications_successful=session.get('total_applications_successful', 0),
            applications_failed=session.get('total_applications_attempted', 0) - session.get('total_applications_successful', 0),
            num_low_effort=session.get('num_low_effort', 0),
            num_medium_effort=session.get('num_medium_effort', 0),
            num_high_effort=session.get('num_high_effort', 0),
            tokens_input_total=session.get('total_tokens_input', 0),
            tokens_output_total=session.get('total_tokens_output', 0),
            cost_estimated_total=session.get('total_cost_estimated', 0.0),
            avg_match_score=0.0, # Placeholder
            per_domain_stats={}, # Placeholder
            per_company_tier_stats={} # Placeholder
        )

        return digest_id

    def recover_active_sessions(self) -> List[UUID]:
        """
        Find sessions that were left running (e.g. due to crash) and mark them as interrupted.
        Returns list of recovered session IDs.
        """
        active_sessions = self.session_repo.get_active_sessions()
        recovered_ids = []

        for session in active_sessions:
            session_id = session['id']
            logger.warning(f"Recovering interrupted session {session_id}")

            # Mark as interrupted
            self.session_repo.update_session_status(
                session_id,
                'interrupted',
                end_datetime=datetime.now()
            )

            self.session_repo.add_session_event(
                session_id,
                'session_recovered',
                "Session marked as interrupted during system startup"
            )

            # Generate partial digest
            try:
                self.generate_session_digest(session_id)
            except Exception as e:
                logger.error(f"Failed to generate digest for recovered session {session_id}: {e}")

            recovered_ids.append(session_id)

        return recovered_ids
