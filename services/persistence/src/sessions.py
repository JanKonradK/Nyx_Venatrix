"""
Session Persistence Operations
CRUD operations for application_sessions, session_events, session_digests
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import logging

from .database import get_db

logger = logging.getLogger(__name__)


class SessionRepository:
    """Handles all session-related database operations"""

    def __init__(self):
        self.db = get_db()

    def create_session(
        self,
        user_id: UUID,
        session_name: Optional[str] = None,
        max_applications: Optional[int] = None,
        max_duration_seconds: Optional[int] = None,
        max_parallel_agents: int = 5,
        config_snapshot: Optional[Dict] = None
    ) -> UUID:
        """Create a new application session"""
        query = """
            INSERT INTO application_sessions (
                user_id, session_name, max_applications, max_duration_seconds,
                max_parallel_agents, config_snapshot, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'planned')
            RETURNING id
        """

        import json
        config_json = json.dumps(config_snapshot or {})

        result = self.db.execute_query(
            query,
            (user_id, session_name, max_applications, max_duration_seconds, max_parallel_agents, config_json)
        )

        session_id = result[0]['id']
        logger.info(f"Created session {session_id}")
        return session_id

    def get_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        query = "SELECT * FROM application_sessions WHERE id = %s"
        result = self.db.execute_query(query, (session_id,))
        return result[0] if result else None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions with status 'running'"""
        query = """
            SELECT * FROM application_sessions
            WHERE status = 'running'
            ORDER BY start_datetime DESC
        """
        return self.db.execute_query(query)

    def update_session_status(self, session_id: UUID, status: str, end_datetime: Optional[datetime] = None):
        """Update session status"""
        if end_datetime:
            query = """
                UPDATE application_sessions
                SET status = %s, end_datetime = %s, updated_at = now()
                WHERE id = %s
            """
            self.db.execute_query(query, (status, end_datetime, session_id), fetch=False)
        else:
            query = """
                UPDATE application_sessions
                SET status = %s, updated_at = now()
                WHERE id = %s
            """
            self.db.execute_query(query, (status, session_id), fetch=False)

        logger.info(f"Session {session_id} status updated to {status}")

    def update_session_metrics(
        self,
        session_id: UUID,
        total_applications_attempted: Optional[int] = None,
        total_applications_successful: Optional[int] = None,
        total_tokens_input: Optional[int] = None,
        total_tokens_output: Optional[int] = None,
        total_cost_estimated: Optional[float] = None,
        num_low_effort: Optional[int] = None,
        num_medium_effort: Optional[int] = None,
        num_high_effort: Optional[int] = None
    ):
        """Update session metrics (partial update)"""
        updates = []
        params = []

        if total_applications_attempted is not None:
            updates.append("total_applications_attempted = %s")
            params.append(total_applications_attempted)
        if total_applications_successful is not None:
            updates.append("total_applications_successful = %s")
            params.append(total_applications_successful)
        if total_tokens_input is not None:
            updates.append("total_tokens_input = %s")
            params.append(total_tokens_input)
        if total_tokens_output is not None:
            updates.append("total_tokens_output = %s")
            params.append(total_tokens_output)
        if total_cost_estimated is not None:
            updates.append("total_cost_estimated = %s")
            params.append(total_cost_estimated)
        if num_low_effort is not None:
            updates.append("num_low_effort = %s")
            params.append(num_low_effort)
        if num_medium_effort is not None:
            updates.append("num_medium_effort = %s")
            params.append(num_medium_effort)
        if num_high_effort is not None:
            updates.append("num_high_effort = %s")
            params.append(num_high_effort)

        if updates:
            updates.append("updated_at = now()")
            params.append(session_id)

            query = f"""
                UPDATE application_sessions
                SET {', '.join(updates)}
                WHERE id = %s
            """
            self.db.execute_query(query, tuple(params), fetch=False)

    def increment_session_counts(self, session_id: UUID, effort_level: str):
        """Increment application counts for session"""
        effort_field_map = {
            'low': 'num_low_effort',
            'medium': 'num_medium_effort',
            'high': 'num_high_effort'
        }

        effort_field = effort_field_map.get(effort_level.lower())
        if not effort_field:
            logger.warning(f"Unknown effort level: {effort_level}")
            return

        query = f"""
            UPDATE application_sessions
            SET total_applications_attempted = total_applications_attempted + 1,
                {effort_field} = {effort_field} + 1,
                updated_at = now()
            WHERE id = %s
        """
        self.db.execute_query(query, (session_id,), fetch=False)

    def mark_application_successful(self, session_id: UUID):
        """Increment successful application count"""
        query = """
            UPDATE application_sessions
            SET total_applications_successful = total_applications_successful + 1,
                updated_at = now()
            WHERE id = %s
        """
        self.db.execute_query(query, (session_id,), fetch=False)

    def add_session_event(
        self,
        session_id: UUID,
        event_type: str,
        message: Optional[str] = None,
        payload: Optional[Dict] = None
    ) -> UUID:
        """Add event to session_events"""
        import json

        query = """
            INSERT INTO session_events (session_id, event_type, message, payload)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """

        result = self.db.execute_query(
            query,
            (session_id, event_type, message, json.dumps(payload or {}))
        )

        return result[0]['id']

    def get_session_events(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Get all events for a session"""
        query = """
            SELECT * FROM session_events
            WHERE session_id = %s
            ORDER BY created_at ASC
        """
        return self.db.execute_query(query, (session_id,))

    def create_session_digest(
        self,
        session_id: UUID,
        summary_text: str,
        applications_total: int,
        applications_successful: int,
        applications_failed: int,
        num_low_effort: int,
        num_medium_effort: int,
        num_high_effort: int,
        tokens_input_total: int,
        tokens_output_total: int,
        cost_estimated_total: float,
        avg_match_score: Optional[float] = None,
        per_domain_stats: Optional[Dict] = None,
        per_company_tier_stats: Optional[Dict] = None
    ) -> UUID:
        """Create session digest"""
        import json

        query = """
            INSERT INTO session_digests (
                session_id, summary_text, applications_total, applications_successful,
                applications_failed, num_low_effort, num_medium_effort, num_high_effort,
                tokens_input_total, tokens_output_total, cost_estimated_total,
                avg_match_score, per_domain_stats, per_company_tier_stats
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        result = self.db.execute_query(
            query,
            (
                session_id, summary_text, applications_total, applications_successful,
                applications_failed, num_low_effort, num_medium_effort, num_high_effort,
                tokens_input_total, tokens_output_total, cost_estimated_total,
                avg_match_score,
                json.dumps(per_domain_stats or {}),
                json.dumps(per_company_tier_stats or {})
            )
        )

        digest_id = result[0]['id']
        logger.info(f"Created session digest {digest_id} for session {session_id}")
        return digest_id

    def get_session_digest(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get digest for a session"""
        query = "SELECT * FROM session_digests WHERE session_id = %s"
        result = self.db.execute_query(query, (session_id,))
        return result[0] if result else None
