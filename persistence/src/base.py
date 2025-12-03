"""Shared helpers for repository classes."""

from __future__ import annotations

from typing import Callable, ContextManager

from sqlalchemy.orm import Session

from persistence.src.database import session_scope


class BaseRepository:
    """Provides a consistent way to acquire SQLAlchemy sessions."""

    def __init__(self, session_factory: Callable[[], ContextManager[Session]] = session_scope):
        self._session_factory = session_factory

    def _get_session(self) -> ContextManager[Session]:
        return self._session_factory()
