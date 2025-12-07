from sqlalchemy import Column, String, Boolean, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .base import Base

class JobPost(Base):
    __tablename__ = 'job_posts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_source_id = Column(UUID(as_uuid=True), ForeignKey('job_sources.id'), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=True)
    source_url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=True)
    job_title = Column(Text, nullable=True)
    raw_location = Column(Text, nullable=True)
    location_city = Column(Text, nullable=True)
    location_country = Column(Text, nullable=True)
    employment_type = Column(Text, nullable=True)
    seniority_level = Column(Text, nullable=True)
    department = Column(Text, nullable=True)
    posting_datetime = Column(DateTime(timezone=True), nullable=True)
    scraped_html = Column(Text, nullable=True)
    description_raw = Column(Text, nullable=True)
    description_clean = Column(Text, nullable=True)
    embedding_vector_id = Column(Text, nullable=True)
    is_remote_allowed = Column(Boolean, default=False)
    compensation_currency = Column(Text, nullable=True)
    compensation_min = Column(Numeric, nullable=True)
    compensation_max = Column(Numeric, nullable=True)
    compensation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    applications = relationship("Application", back_populates="job_post", cascade="all, delete-orphan")
