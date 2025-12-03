"""Session repository for Nyx Venatrix."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from persistence.src.base import BaseRepository
from persistence.src.models import ApplicationSession, SessionDigest, SessionEvent


class SessionRepository(BaseRepository):
    """Provides helpers for managing application sessions."""

    def create_session(
        self,
        *,
        user_id: UUID,
        session_name: Optional[str] = None,
        max_applications: Optional[int] = 200,
        max_duration_seconds: Optional[int] = 7200,
        max_parallel_agents: int = 5,
        config_snapshot: Optional[Dict[str, Any]] = None,
        status: str = "running",
    ) -> UUID:
        session_id = uuid4()
        with self._get_session() as session:
            session.add(
                ApplicationSession(
                    id=session_id,
                    user_id=user_id,
                    session_name=session_name,
                    max_applications=max_applications or 200,
                    max_duration_seconds=max_duration_seconds or 7200,
                    max_parallel_agents=max_parallel_agents,
                    config_snapshot=config_snapshot or {},
                    status=status,
                )
            )
        return session_id

    def add_session_event(
        self,
        session_id: UUID,
        event_type: str,
        message: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        with self._get_session() as session:
            event = SessionEvent(
                id=uuid4(),
                session_id=session_id,
                event_type=event_type,
                message=message,
                payload=payload,
            )
            session.add(event)
            session.flush()
            return event.id

    def update_session_status(self, session_id: UUID, status: str, *, end_datetime: Optional[datetime] = None) -> None:
        with self._get_session() as session:
            record = session.get(ApplicationSession, session_id)
            if not record:
                raise ValueError(f"Session {session_id} not found")
            record.status = status
            if end_datetime:
                record.end_datetime = end_datetime

    def update_status(self, session_id: UUID, status: str) -> None:
        """Alias used by legacy interfaces."""
        self.update_session_status(session_id, status)

    def get_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            record = session.get(ApplicationSession, session_id)
            return self._serialize_session(record) if record else None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = select(ApplicationSession).where(ApplicationSession.status.in_(["planned", "running"]))
            records = session.scalars(stmt).all()
            return [self._serialize_session(record) for record in records]

    def increment_session_counts(self, session_id: UUID, effort_level: str) -> None:
        with self._get_session() as session:
            record = session.get(ApplicationSession, session_id)
            if not record:
                raise ValueError(f"Session {session_id} not found")
            record.total_applications_attempted += 1
            effort_level = (effort_level or "medium").lower()
            if effort_level == "low":
                record.num_low_effort += 1
            elif effort_level == "high":
                record.num_high_effort += 1
            else:
                record.num_medium_effort += 1

    def mark_application_successful(self, session_id: UUID) -> None:
        with self._get_session() as session:
            record = session.get(ApplicationSession, session_id)
            if not record:
                raise ValueError(f"Session {session_id} not found")
            record.total_applications_successful += 1

    def add_token_usage(self, session_id: UUID, tokens_input: int = 0, tokens_output: int = 0) -> None:
        tokens_input = max(tokens_input or 0, 0)
        tokens_output = max(tokens_output or 0, 0)
        if not tokens_input and not tokens_output:
            return

        with self._get_session() as session:
            record = session.get(ApplicationSession, session_id)
            if not record:
                raise ValueError(f"Session {session_id} not found")
            record.total_tokens_input += tokens_input
            record.total_tokens_output += tokens_output

    def create_session_digest(
        self,
        *,
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
        avg_match_score: float,
        per_domain_stats: Dict[str, Any],
        per_company_tier_stats: Dict[str, Any]
    ) -> UUID:
        digest_id = uuid4()
        with self._get_session() as session:
            session.add(
                SessionDigest(
                    id=digest_id,
                    session_id=session_id,
                    summary_text=summary_text,
                    applications_total=applications_total,
                    applications_successful=applications_successful,
                    applications_failed=applications_failed,
                    num_low_effort=num_low_effort,
                    num_medium_effort=num_medium_effort,
                    num_high_effort=num_high_effort,
                    tokens_input_total=tokens_input_total,
                    tokens_output_total=tokens_output_total,
                    cost_estimated_total=cost_estimated_total,
                    avg_match_score=avg_match_score,
                    per_domain_stats=per_domain_stats,
                    per_company_tier_stats=per_company_tier_stats,
                )
            )
        return digest_id

    def get_session_stats(self, session_id: UUID) -> Dict[str, Any]:
        session_data = self.get_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")
        return {
            "total_applications_attempted": session_data["total_applications_attempted"],
            "total_applications_successful": session_data["total_applications_successful"],
            "num_low_effort": session_data["num_low_effort"],
            "num_medium_effort": session_data["num_medium_effort"],
            "num_high_effort": session_data["num_high_effort"],
        }

    @staticmethod
    def _serialize_session(record: Optional[ApplicationSession]) -> Optional[Dict[str, Any]]:
        if not record:
            return None
        return {
            "id": str(record.id),
            "user_id": str(record.user_id),
            "session_name": record.session_name,
            "status": record.status,
            "start_datetime": record.start_datetime.isoformat() if record.start_datetime else None,
            "end_datetime": record.end_datetime.isoformat() if record.end_datetime else None,
            "max_applications": record.max_applications,
            "max_duration_seconds": record.max_duration_seconds,
            "max_parallel_agents": record.max_parallel_agents,
            "config_snapshot": record.config_snapshot or {},
            "total_applications_attempted": record.total_applications_attempted,
            "total_applications_successful": record.total_applications_successful,
            "total_tokens_input": record.total_tokens_input,
            "total_tokens_output": record.total_tokens_output,
            "total_cost_estimated": float(record.total_cost_estimated or 0),
            "num_low_effort": record.num_low_effort,
            "num_medium_effort": record.num_medium_effort,
            "num_high_effort": record.num_high_effort,
        }
