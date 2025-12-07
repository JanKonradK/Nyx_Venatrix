from sqlalchemy import Column, String, Boolean, DateTime, Numeric, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base

class Application(Base):
    __tablename__ = 'applications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey('application_sessions.id'), nullable=True)
    job_post_id = Column(UUID(as_uuid=True), ForeignKey('job_posts.id'), nullable=False)

    effort_level = Column(Text, nullable=False, default='medium')
    effort_hint_source = Column(Text, default='user')
    match_score = Column(Numeric, nullable=True)

    selected_resume_id = Column(UUID(as_uuid=True), ForeignKey('resumes.id'), nullable=True)
    selected_resume_version_id = Column(UUID(as_uuid=True), ForeignKey('resume_versions.id'), nullable=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'), nullable=True)

    cover_letter_template_id = Column(UUID(as_uuid=True), ForeignKey('cover_letter_templates.id'), nullable=True)
    cover_letter_text = Column(Text, nullable=True)
    cover_letter_generated_by = Column(Text, nullable=True)

    application_status = Column(Text, nullable=False, default='queued')
    application_started_at = Column(DateTime(timezone=True), nullable=True)
    application_submitted_at = Column(DateTime(timezone=True), nullable=True)
    success_flag = Column(Boolean, default=False)

    final_confirmation_type = Column(Text, nullable=True)
    final_confirmation_screenshot_path = Column(Text, nullable=True)

    failure_reason_code = Column(Text, nullable=True)
    failure_reason_detail = Column(Text, nullable=True)
    manual_followup_needed = Column(Boolean, default=False)

    mlflow_run_id = Column(Text, nullable=True)
    langfuse_trace_id = Column(Text, nullable=True)

    domain_name = Column(Text, nullable=True)
    tokens_input_total = Column(Integer, default=0)
    tokens_output_total = Column(Integer, default=0)
    cost_estimated_total = Column(Numeric, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    job_post = relationship("JobPost", back_populates="applications")
    # session = relationship("ApplicationSession", back_populates="applications")

    @property
    def duration_seconds(self):
        if self.application_submitted_at and self.application_started_at:
            delta = self.application_submitted_at - self.application_started_at
            return int(delta.total_seconds())
        return 0
