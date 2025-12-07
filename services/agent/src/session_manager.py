"""
Session Manager Service
Tracks lifecycle of application sessions, enforces runtime limits, and emits digests.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from persistence.repositories import SessionRepository

from .notifications.digest_email import DigestEmailSender, SessionStats

logger = logging.getLogger(__name__)


def _read_positive_float(value: Optional[str], fallback: float) -> float:
    try:
        parsed = float(value) if value is not None else fallback
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _read_positive_int(value: Optional[str], fallback: int) -> int:
    try:
        parsed = int(value) if value is not None else fallback
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


class SessionManager:
    """Manages session persistence and in-memory runtime stats."""

    def __init__(
        self,
        max_duration_hours: float = 2,
        max_applications: int = 200,
        digest_sender: Optional[DigestEmailSender] = None,
        session_repo: Optional[SessionRepository] = None,
    ) -> None:
        env_hours = os.getenv('MAX_SESSION_HOURS')
        env_max_apps = os.getenv('MAX_SESSION_APPLICATIONS')
        self.session_repo = session_repo or SessionRepository()
        self.default_max_duration = timedelta(hours=_read_positive_float(env_hours, max_duration_hours))
        self.default_max_applications = _read_positive_int(env_max_apps, max_applications)
        self.daily_cap = _read_positive_int(os.getenv('MAX_DAILY_APPLICATIONS'), 300)
        self.digest_sender = digest_sender or DigestEmailSender()
        self._reset_runtime_state()

    def _reset_runtime_state(self) -> None:
        self.session_id: Optional[UUID] = None
        self.session_user_id: Optional[UUID] = None
        self.session_name: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.application_count = 0
        self.max_duration = self.default_max_duration
        self.max_applications = self.default_max_applications
        self.stats = SessionStats()

    # ------------------------------------------------------------------
    # Lifecycle operations
    # ------------------------------------------------------------------
    def create_session(
        self,
        user_id: UUID,
        session_name: str,
        max_applications: Optional[int] = None,
        max_duration_seconds: Optional[int] = None,
        max_parallel_agents: int = 5,
        config: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """Create a new application session record and seed runtime tracking."""
        max_apps = max_applications or self.default_max_applications
        duration_seconds = max_duration_seconds or int(self.default_max_duration.total_seconds())

        session_id = self.session_repo.create_session(
            user_id=user_id,
            session_name=session_name,
            max_applications=max_apps,
            max_duration_seconds=duration_seconds,
            max_parallel_agents=max_parallel_agents,
            config_snapshot=config,
        )

        self.session_id = session_id
        self.session_user_id = user_id
        self.session_name = session_name
        self.start_time = datetime.utcnow()
        self.application_count = 0
        self.max_duration = timedelta(seconds=duration_seconds)
        self.max_applications = max_apps
        self.stats = SessionStats()

        self.session_repo.add_session_event(
            session_id,
            'session_started',
            f"Session '{session_name}' started",
        )
        return session_id

    def stop_session(self, session_id: UUID, reason: str = "manual_stop") -> Optional[UUID]:
        """Mark the session as finished and emit a digest/email."""
        self.session_repo.update_session_status(
            session_id,
            'completed',
            end_datetime=datetime.utcnow(),
        )

        self.session_repo.add_session_event(
            session_id,
            'session_stopped',
            f"Session stopped: {reason}",
        )

        digest_id = self._generate_session_digest(session_id)
        if self.session_id == session_id:
            self._reset_runtime_state()
        return digest_id

    def recover_active_sessions(self) -> list[UUID]:
        """Mark lingering sessions as interrupted and emit partial digests."""
        active_sessions = self.session_repo.get_active_sessions()
        recovered_ids: list[UUID] = []

        for session in active_sessions:
            session_id = UUID(session['id'])
            logger.warning("Recovering interrupted session %s", session_id)
            self.session_repo.update_session_status(
                session_id,
                'interrupted',
                end_datetime=datetime.utcnow(),
            )
            self.session_repo.add_session_event(
                session_id,
                'session_recovered',
                "Session marked as interrupted during system startup",
            )
            try:
                self._generate_session_digest(session_id)
            except Exception as exc:
                logger.error("Failed to generate digest for recovered session %s: %s", session_id, exc)
            recovered_ids.append(session_id)

        return recovered_ids

    # ------------------------------------------------------------------
    # Runtime helpers
    # ------------------------------------------------------------------
    def should_continue(self) -> bool:
        """Return whether the current session may keep applying."""
        if not self.start_time:
            return False
        elapsed = datetime.utcnow() - self.start_time
        return elapsed < self.max_duration and self.application_count < self.max_applications

    def register_application(
        self,
        session_id: Optional[UUID],
        effort_level: Optional[str],
        status: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        """Update in-memory and persistent statistics for the active session."""
        if not session_id:
            return

        if not self.session_id or session_id != self.session_id:
            self._ensure_runtime_session(session_id)

        if not self.session_id or session_id != self.session_id:
            logger.debug("Skipping session metrics - runtime session not attached")
            return

        self.application_count += 1
        level = (effort_level or 'medium').lower()
        if level == 'high':
            self.stats.high_effort_count += 1
        elif level == 'low':
            self.stats.low_effort_count += 1
        else:
            self.stats.medium_effort_count += 1

        normalized_status = status.lower()
        if normalized_status == 'submitted':
            self.stats.submitted_count += 1
        elif normalized_status == 'paused':
            self.stats.paused_count += 1
        else:
            self.stats.failed_count += 1
            if error_message:
                self.stats.errors.append(error_message)

        self.stats.total_applications += 1
        safe_tokens_in = max(tokens_input, 0)
        safe_tokens_out = max(tokens_output, 0)
        self.stats.total_input_tokens += safe_tokens_in
        self.stats.total_output_tokens += safe_tokens_out
        tokens_total = self.stats.total_input_tokens + self.stats.total_output_tokens
        if self.stats.total_applications:
            self.stats.avg_tokens_per_app = tokens_total // self.stats.total_applications

        self._persist_session_metrics(
            session_id=session_id,
            effort_level=level,
            normalized_status=normalized_status,
            tokens_input=safe_tokens_in,
            tokens_output=safe_tokens_out,
            error_message=error_message,
        )
        self._enforce_runtime_limits()

    def current_runtime_snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot of the live session state."""
        return {
            "session_id": str(self.session_id) if self.session_id else None,
            "session_name": self.session_name,
            "application_count": self.application_count,
            "max_applications": self.max_applications,
            "elapsed_seconds": self._elapsed_seconds(),
            "max_duration_seconds": int(self.max_duration.total_seconds()),
            "stats": asdict(self.stats),
        }

    def _persist_session_metrics(
        self,
        *,
        session_id: UUID,
        effort_level: str,
        normalized_status: str,
        tokens_input: int,
        tokens_output: int,
        error_message: Optional[str],
    ) -> None:
        try:
            self.session_repo.increment_session_counts(session_id, effort_level)
            if normalized_status == 'submitted':
                self.session_repo.mark_application_successful(session_id)
            self.session_repo.add_token_usage(session_id, tokens_input, tokens_output)
            if normalized_status == 'failed' and error_message:
                self.session_repo.add_session_event(
                    session_id,
                    'application_failed',
                    f"Application failure: {error_message[:240]}",
                    payload={'error': error_message},
                )
        except Exception as exc:  # pragma: no cover - persistence failures are logged
            logger.error("Failed to persist session metrics for %s: %s", session_id, exc)

    def _enforce_runtime_limits(self) -> None:
        if not self.session_id or not self.start_time:
            return

        elapsed_seconds = self._elapsed_seconds()
        if elapsed_seconds >= int(self.max_duration.total_seconds()):
            self._log_limit_event('max_duration_reached', {'elapsed_seconds': elapsed_seconds})
            self.stop_session(self.session_id, reason='max_duration_reached')
            return

        if self.application_count >= self.max_applications:
            self._log_limit_event('max_applications_reached', {'application_count': self.application_count})
            self.stop_session(self.session_id, reason='max_applications_reached')

    def _log_limit_event(self, reason: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if not self.session_id:
            return
        try:
            self.session_repo.add_session_event(
                self.session_id,
                'session_limit',
                f"Session limit triggered: {reason}",
                payload=payload,
            )
        except Exception as exc:
            logger.debug("Failed to log session limit event: %s", exc)


    async def end_session(self, reason: str = "manual_stop") -> Optional[UUID]:
        """Async helper mirroring stop_session for coroutine callers."""
        if not self.session_id:
            return None
        session_id = self.session_id
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.stop_session, session_id, reason)

    def _ensure_runtime_session(self, session_id: UUID) -> None:
        record = self.session_repo.get_session(session_id)
        if not record:
            logger.warning("Session %s not found when attempting to attach runtime state", session_id)
            return

        self.session_id = session_id
        self.session_name = record.get('session_name')
        self.session_user_id = self._safe_uuid(record.get('user_id'))
        self.start_time = self._parse_timestamp(record.get('start_datetime')) or datetime.utcnow()
        self.application_count = record.get('total_applications_attempted', 0) or 0
        duration_seconds = record.get('max_duration_seconds') or int(self.default_max_duration.total_seconds())
        self.max_duration = timedelta(seconds=duration_seconds)
        self.max_applications = record.get('max_applications', self.default_max_applications) or self.default_max_applications
        self.stats = SessionStats()

    def _elapsed_seconds(self) -> int:
        if not self.start_time:
            return 0
        return max(int((datetime.utcnow() - self.start_time).total_seconds()), 0)

    @staticmethod
    def _safe_uuid(value: Optional[str]) -> Optional[UUID]:
        if not value:
            return None
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            logger.debug("Unable to parse UUID value %s", value)
            return None

    # ------------------------------------------------------------------
    # Digest helpers
    # ------------------------------------------------------------------
    def generate_session_digest(self, session_id: UUID) -> UUID:
        """Public entry point used by older callers."""
        return self._generate_session_digest(session_id)

    def _generate_session_digest(self, session_id: UUID) -> UUID:
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        stats, summary_text = self._build_stats_payload(session)
        total_attempted = session.get('total_applications_attempted', 0) or 0
        total_success = session.get('total_applications_successful', 0) or 0

        digest_id = self.session_repo.create_session_digest(
            session_id=session_id,
            summary_text=summary_text,
            applications_total=total_attempted,
            applications_successful=total_success,
            applications_failed=max(total_attempted - total_success, 0),
            num_low_effort=session.get('num_low_effort', 0) or 0,
            num_medium_effort=session.get('num_medium_effort', 0) or 0,
            num_high_effort=session.get('num_high_effort', 0) or 0,
            tokens_input_total=stats.total_input_tokens,
            tokens_output_total=stats.total_output_tokens,
            cost_estimated_total=session.get('total_cost_estimated', 0.0) or 0.0,
            avg_match_score=0.0,
            per_domain_stats={},
            per_company_tier_stats={},
        )

        self._dispatch_digest_email(session, stats)
        return digest_id

    def _build_stats_payload(self, session: Dict[str, Any]) -> tuple[SessionStats, str]:
        stats = SessionStats(
            duration_minutes=self._compute_duration_minutes(session),
            total_applications=session.get('total_applications_attempted', 0) or 0,
            high_effort_count=session.get('num_high_effort', 0) or 0,
            medium_effort_count=session.get('num_medium_effort', 0) or 0,
            low_effort_count=session.get('num_low_effort', 0) or 0,
            submitted_count=session.get('total_applications_successful', 0) or 0,
            failed_count=0,
            paused_count=self.stats.paused_count,
            total_input_tokens=(session.get('total_tokens_input', 0) or 0) + self.stats.total_input_tokens,
            total_output_tokens=(session.get('total_tokens_output', 0) or 0) + self.stats.total_output_tokens,
            avg_tokens_per_app=0,
            errors=list(self.stats.errors),
        )
        stats.failed_count = max(stats.total_applications - stats.submitted_count, 0)
        tokens_total = stats.total_input_tokens + stats.total_output_tokens
        if stats.total_applications:
            stats.avg_tokens_per_app = tokens_total // stats.total_applications

        summary_text = (
            f"Session '{session.get('session_name')}' completed.\n"
            f"Total Applications: {stats.total_applications}\n"
            f"Successful: {stats.submitted_count}\n"
            f"Failed: {stats.failed_count}"
        )
        return stats, summary_text

    def _dispatch_digest_email(self, session: Dict[str, Any], stats: SessionStats) -> None:
        if not self.digest_sender.enabled:
            return

        async def _send() -> None:
            await self.digest_sender.send_session_digest(session, stats)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_send())
        else:
            loop.create_task(_send())

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _compute_duration_minutes(self, session: Dict[str, Any]) -> int:
        start_ts = self._parse_timestamp(session.get('start_datetime'))
        end_ts = self._parse_timestamp(session.get('end_datetime')) or datetime.utcnow()
        if not start_ts:
            return 0
        return max(int((end_ts - start_ts).total_seconds() // 60), 0)

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        sanitized = value.replace('Z', '+00:00') if isinstance(value, str) else value
        try:
            return datetime.fromisoformat(sanitized)
        except ValueError:
            logger.debug("Unable to parse timestamp %s", value)
            return None
