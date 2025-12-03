"""Event persistence helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from persistence.src.base import BaseRepository
from persistence.src.models import ApplicationEvent, SessionEvent


class EventRepository(BaseRepository):
    """Stores application-level and session-level events."""

    def append_event(
        self,
        event_type: str,
        *,
        application_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        event_detail: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Persist an application event and return its ID."""
        with self._get_session() as session:
            event = ApplicationEvent(
                id=uuid4(),
                application_id=application_id,
                session_id=session_id,
                event_type=event_type,
                event_detail=event_detail,
                payload=payload,
            )
            session.add(event)
            session.flush()
            return event.id

    def log_session_event(
        self,
        *,
        session_id: UUID,
        event_type: str,
        message: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Persist a session event and return its ID."""
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
