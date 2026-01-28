from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.models.mixins import TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, DateTime
import uuid

from app.db import Base
from app.constants.reindex_job_status import ReindexJobStatus


class ReindexJob(Base, TimestampMixin, SoftDeleteMixin):
    """ReindexJob model for tracking reindexing operations."""

    __tablename__ = "reindex_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domains = Column(ARRAY(String), nullable=True)  # Filter by domain prefixes
    entity_types = Column(ARRAY(String), nullable=True)  # Filter by entity types
    updated_after = Column(DateTime, nullable=True)  # Date range filter
    updated_before = Column(DateTime, nullable=True)  # Date range filter
    status = Column(String, nullable=False, default=ReindexJobStatus.PENDING)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
