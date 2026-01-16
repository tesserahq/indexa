from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.models.mixins import TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, DateTime, Float, Enum
import uuid
import enum

from app.db import Base


class ReindexJobStatus(str, enum.Enum):
    """Status enum for reindex jobs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReindexJobMode(str, enum.Enum):
    """Mode enum for reindex jobs."""

    UPSERT = "upsert"
    REPLACE = "replace"


class ReindexJob(Base, TimestampMixin, SoftDeleteMixin):
    """ReindexJob model for tracking reindexing operations."""

    __tablename__ = "reindex_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(String, nullable=False)  # e.g., "domain", "global"
    domains = Column(ARRAY(String), nullable=True)  # Filter by domain prefixes
    entity_types = Column(ARRAY(String), nullable=True)  # Filter by entity types
    providers = Column(ARRAY(String), nullable=False)  # Target providers
    updated_after = Column(DateTime, nullable=True)  # Date range filter
    updated_before = Column(DateTime, nullable=True)  # Date range filter
    mode = Column(Enum(ReindexJobMode), nullable=False, default=ReindexJobMode.UPSERT)
    status = Column(
        Enum(ReindexJobStatus), nullable=False, default=ReindexJobStatus.PENDING
    )
    progress = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
