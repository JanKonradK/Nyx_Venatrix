"""ORM models aligned with the Nyx Venatrix database schema."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship

from persistence.src.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=True)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("application_sessions.id"), nullable=True)
    job_post_id = Column(PG_UUID(as_uuid=True), nullable=True)
    effort_level = Column(String(16), default="medium")
    effort_hint_source = Column(String(16), default="auto")
    match_score = Column(Float, nullable=True)
    selected_resume_id = Column(PG_UUID(as_uuid=True), nullable=True)
    selected_resume_version_id = Column(PG_UUID(as_uuid=True), nullable=True)
    profile_id = Column(PG_UUID(as_uuid=True), nullable=True)
    cover_letter_template_id = Column(PG_UUID(as_uuid=True), nullable=True)
    cover_letter_text = Column(Text, nullable=True)
    cover_letter_generated_by = Column(String(32), default="none")
    application_status = Column(String(32), default="queued")
    application_started_at = Column(DateTime, nullable=True)
    application_submitted_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    success_flag = Column(Boolean, default=False)
    final_confirmation_type = Column(String(32), nullable=True)
    final_confirmation_screenshot_path = Column(Text, nullable=True)
    failure_reason_code = Column(String(64), nullable=True)
    failure_reason_detail = Column(Text, nullable=True)
    manual_followup_needed = Column(Boolean, default=False)
    domain_name = Column(String(255), nullable=True)
    tokens_input_total = Column(Integer, default=0)
    tokens_output_total = Column(Integer, default=0)
    cost_estimated_total = Column(Numeric(12, 6), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("ApplicationSession", back_populates="applications")


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(PG_UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("application_sessions.id"), nullable=True)
    event_type = Column(String(64), nullable=False)
    event_detail = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApplicationSession(Base):
    __tablename__ = "application_sessions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    session_name = Column(String(255), nullable=True)
    start_datetime = Column(DateTime, default=datetime.utcnow)
    end_datetime = Column(DateTime, nullable=True)
    status = Column(String(32), default="planned")
    max_applications = Column(Integer, default=200)
    max_duration_seconds = Column(Integer, default=7200)
    max_parallel_agents = Column(Integer, default=5)
    config_snapshot = Column(JSONB, default=dict)
    total_applications_attempted = Column(Integer, default=0)
    total_applications_successful = Column(Integer, default=0)
    total_tokens_input = Column(Integer, default=0)
    total_tokens_output = Column(Integer, default=0)
    total_cost_estimated = Column(Numeric(12, 6), default=0)
    num_low_effort = Column(Integer, default=0)
    num_medium_effort = Column(Integer, default=0)
    num_high_effort = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    applications = relationship("Application", back_populates="session")


class SessionEvent(Base):
    __tablename__ = "session_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("application_sessions.id"), nullable=False)
    event_type = Column(String(64), nullable=False)
    message = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionDigest(Base):
    __tablename__ = "session_digests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("application_sessions.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    summary_text = Column(Text, nullable=False)
    applications_total = Column(Integer, default=0)
    applications_successful = Column(Integer, default=0)
    applications_failed = Column(Integer, default=0)
    num_low_effort = Column(Integer, default=0)
    num_medium_effort = Column(Integer, default=0)
    num_high_effort = Column(Integer, default=0)
    tokens_input_total = Column(Integer, default=0)
    tokens_output_total = Column(Integer, default=0)
    cost_estimated_total = Column(Numeric(12, 6), default=0)
    avg_match_score = Column(Float, default=0)
    per_domain_stats = Column(JSONB, default=dict)
    per_company_tier_stats = Column(JSONB, default=dict)
    digest_email_sent = Column(Boolean, default=False)
    digest_email_id = Column(PG_UUID(as_uuid=True), nullable=True)


class DomainRateLimit(Base):
    __tablename__ = "domain_rate_limits"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_name = Column(String(255), nullable=False)
    date = Column(Date, default=datetime.utcnow)
    applications_attempted = Column(Integer, default=0)
    applications_successful = Column(Integer, default=0)
    applications_failed = Column(Integer, default=0)
    last_block_timestamp = Column(DateTime, nullable=True)
    is_temporarily_blocked = Column(Boolean, default=False)
    blocked_until = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
