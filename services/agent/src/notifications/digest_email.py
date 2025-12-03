"""Session digest email utility."""
from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Iterable, List, Mapping

logger = logging.getLogger(__name__)


@dataclass
class SessionStats:
    duration_minutes: int = 0
    total_applications: int = 0
    high_effort_count: int = 0
    medium_effort_count: int = 0
    low_effort_count: int = 0
    submitted_count: int = 0
    failed_count: int = 0
    paused_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    avg_tokens_per_app: int = 0
    errors: List[str] = field(default_factory=list)


class DigestEmailSender:
    """Lightweight SMTP client that ships end-of-session summaries."""

    def __init__(self) -> None:
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER') or 'notifications@nyx.local'
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.recipients = self._parse_recipients(os.getenv('DIGEST_EMAIL_TO', ''))

    @staticmethod
    def _parse_recipients(raw: str) -> List[str]:
        return [item.strip() for item in raw.split(',') if item.strip()]

    @property
    def enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_password and self.recipients)

    async def send_session_digest(
        self,
        session: Mapping[str, object] | None,
        stats: SessionStats,
    ) -> None:
        if not self.enabled:
            logger.info("Digest email disabled: missing SMTP credentials or recipients")
            return

        subject = f"Nyx Session Complete - {stats.total_applications} Applications"
        body = self._build_body(session, stats)
        await self._send_email(subject, body)

    def _build_body(self, session: Mapping[str, object] | None, stats: SessionStats) -> str:
        session_name = session.get('session_name') if session else 'Unknown Session'
        return (
            f"Session Summary\n"
            f"===============\n"
            f"Name: {session_name}\n"
            f"Duration: {stats.duration_minutes} minutes\n"
            f"Total Applications: {stats.total_applications}\n\n"
            f"By Effort Level:\n"
            f"- High: {stats.high_effort_count}\n"
            f"- Medium: {stats.medium_effort_count}\n"
            f"- Low: {stats.low_effort_count}\n\n"
            f"By Status:\n"
            f"- Submitted: {stats.submitted_count}\n"
            f"- Failed: {stats.failed_count}\n"
            f"- Paused: {stats.paused_count}\n\n"
            f"Token Usage:\n"
            f"- Total Input: {stats.total_input_tokens:,}\n"
            f"- Total Output: {stats.total_output_tokens:,}\n"
            f"- Avg per Application: {stats.avg_tokens_per_app:,}\n\n"
            f"Errors:\n{self._format_errors(stats.errors)}"
        )

    def _format_errors(self, errors: Iterable[str]) -> str:
        error_list = list(errors)
        if not error_list:
            return "None recorded"
        return '\n'.join(f"- {entry}" for entry in error_list)

    async def _send_email(self, subject: str, body: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._send_email_sync, subject, body)

    def _send_email_sync(self, subject: str, body: str) -> None:
        context = ssl.create_default_context()
        message = EmailMessage()
        message['Subject'] = subject
        message['From'] = self.smtp_user
        message['To'] = ', '.join(self.recipients)
        message.set_content(body)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
                logger.info("Session digest email sent to %s", message['To'])
        except Exception as exc:  # pragma: no cover - depends on SMTP server
            logger.error("Failed to send session digest: %s", exc)
