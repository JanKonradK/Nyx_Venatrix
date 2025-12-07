from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from .base import Base

class ApplicationEvent(Base):
    __tablename__ = 'application_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey('applications.id', ondelete='CASCADE'), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('application_sessions.id', ondelete='CASCADE'), nullable=True)
    event_type = Column(Text, nullable=False)
    event_detail = Column(Text, nullable=True)
    payload = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
