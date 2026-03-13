"""
Repository for tracking indexing operations (database-only).
"""

from sqlalchemy.orm import Session

# This repository is database-only for now
# Future: Could track indexing history, status, etc.
# For now, it's a placeholder for future indexing state tracking


class IndexingRepository:
    """Repository for managing indexing state in the database."""

    def __init__(self, db: Session):
        """
        Initialize the indexing repository.

        Args:
            db: Database session
        """
        self.db = db

    # Future methods could include:
    # - track_indexing_operation()
    # - get_indexing_history()
    # - get_indexing_status()
    # etc.
