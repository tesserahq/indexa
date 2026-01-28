import enum


class ReindexJobStatus(str, enum.Enum):
    """Status enum for reindex jobs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
