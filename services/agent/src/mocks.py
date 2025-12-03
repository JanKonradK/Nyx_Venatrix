import logging
from uuid import UUID
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class MockApplicationRepository:
    def mark_started(self, application_id: UUID):
        logger.info(f"[MOCK DB] Application {application_id} marked STARTED")

    def mark_submitted(self, application_id: UUID, success_flag: bool = True, confirmation_type: str = 'unknown'):
        logger.info(f"[MOCK DB] Application {application_id} marked SUBMITTED (Success: {success_flag})")

    def mark_failed(self, application_id: UUID, failure_reason_code: str, failure_reason_detail: str):
        logger.info(f"[MOCK DB] Application {application_id} marked FAILED: {failure_reason_code} - {failure_reason_detail}")

class MockEventRepository:
    def append_event(self, event_type: str, application_id: Optional[UUID] = None, session_id: Optional[UUID] = None, event_detail: Optional[str] = None, payload: Optional[Dict] = None):
        logger.info(f"[MOCK DB] Event: {event_type} | App: {application_id} | Detail: {event_detail}")

class MockSessionRepository:
    def increment_session_counts(self, session_id: UUID, effort_level: str):
        logger.info(f"[MOCK DB] Session {session_id} incremented count for {effort_level}")

    def mark_application_successful(self, session_id: UUID):
        logger.info(f"[MOCK DB] Session {session_id} marked application successful")
