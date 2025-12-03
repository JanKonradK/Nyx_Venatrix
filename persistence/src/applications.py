"""Application repository for Nyx Venatrix."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from persistence.src.base import BaseRepository
from persistence.src.models import Application


class ApplicationRepository(BaseRepository):
    """Encapsulates CRUD helpers for the applications table."""

    def _get_or_create(self, session: Session, application_id: UUID) -> Application:
        application = session.get(Application, application_id)
        if application is None:
            application = Application(id=application_id)
            session.add(application)
            session.flush()
        return application

    def create_application(
        self,
        *,
        application_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        job_post_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        effort_level: str = "medium",
        match_score: Optional[float] = None,
        selected_resume_version_id: Optional[UUID] = None,
        profile_id: Optional[UUID] = None,
        status: str = "queued"
    ) -> UUID:
        """Create a new application row and return its ID."""
        if application_id is None:
            application_id = uuid4()
        elif not isinstance(application_id, UUID):
            application_id = UUID(str(application_id))

        with self._get_session() as session:
            session.add(
                Application(
                    id=application_id,
                    user_id=user_id,
                    job_post_id=job_post_id,
                    session_id=session_id,
                    effort_level=effort_level,
                    match_score=match_score,
                    selected_resume_version_id=selected_resume_version_id,
                    profile_id=profile_id,
                    application_status=status,
                )
            )
        return application_id

    def mark_started(self, application_id: UUID) -> None:
        """Mark an application as in progress."""
        with self._get_session() as session:
            app = self._get_or_create(session, application_id)
            app.application_status = "in_progress"
            app.application_started_at = datetime.utcnow()

    def mark_submitted(
        self,
        application_id: UUID,
        *,
        success_flag: bool = True,
        confirmation_type: str = "unknown",
        duration_seconds: Optional[int] = None
    ) -> None:
        """Mark an application as submitted."""
        with self._get_session() as session:
            app = self._get_or_create(session, application_id)
            app.application_status = "submitted"
            app.success_flag = success_flag
            app.final_confirmation_type = confirmation_type
            app.application_submitted_at = datetime.utcnow()
            if app.application_started_at and duration_seconds is None:
                duration_seconds = int((app.application_submitted_at - app.application_started_at).total_seconds())
            if duration_seconds is not None:
                app.duration_seconds = duration_seconds

    def mark_failed(
        self,
        application_id: UUID,
        *,
        failure_reason_code: str,
        failure_reason_detail: str
    ) -> None:
        """Mark an application as failed with reason metadata."""
        with self._get_session() as session:
            app = self._get_or_create(session, application_id)
            app.application_status = "failed"
            app.failure_reason_code = failure_reason_code
            app.failure_reason_detail = failure_reason_detail
            app.application_submitted_at = datetime.utcnow()

    def get_queued_applications(self, session_id: UUID, limit: int = 100) -> List[Dict[str, Any]]:
        """Return queued applications for a session."""
        with self._get_session() as session:
            stmt = (
                select(Application)
                .where(
                    Application.session_id == session_id,
                    Application.application_status == "queued",
                )
                .limit(limit)
            )
            apps = session.scalars(stmt).all()
            return [self._serialize(app) for app in apps]

    @staticmethod
    def _serialize(app: Application) -> Dict[str, Any]:
        return {
            "id": str(app.id),
            "session_id": str(app.session_id) if app.session_id else None,
            "job_post_id": str(app.job_post_id) if app.job_post_id else None,
            "effort_level": app.effort_level,
            "match_score": app.match_score,
            "status": app.application_status,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        }
