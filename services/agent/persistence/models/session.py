from sqlalchemy import Column, String, Boolean, DateTime, Numeric, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base

class ApplicationSession(Base):
    __tablename__ = 'application_sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_name = Column(Text, nullable=True)
    start_datetime = Column(DateTime(timezone=True), server_default=func.now())
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    status = Column(Text, nullable=False, default='planned')
    max_applications = Column(Integer, nullable=True)
    max_duration_seconds = Column(Integer, nullable=True)
    max_parallel_agents = Column(Integer, default=5)
    config_snapshot = Column(JSONB, default={})

    total_applications_attempted = Column(Integer, default=0)
    total_applications_successful = Column(Integer, default=0)
    total_tokens_input = Column(Integer, default=0)
    total_tokens_output = Column(Integer, default=0)
    total_cost_estimated = Column(Numeric, default=0)

    num_low_effort = Column(Integer, default=0)
    num_medium_effort = Column(Integer, default=0)
    num_high_effort = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
