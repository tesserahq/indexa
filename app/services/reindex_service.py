"""
Service for managing reindex jobs (database-only).
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.reindex_job import ReindexJob, ReindexJobStatus
from app.schemas.reindex_job import ReindexJobCreate
from app.services.soft_delete_service import SoftDeleteService


class ReindexService(SoftDeleteService[ReindexJob]):
    """Service for managing reindex job CRUD operations."""

    def __init__(self, db: Session):
        """
        Initialize the reindex service.

        Args:
            db: Database session
        """
        super().__init__(db, ReindexJob)

    def create_reindex_job(self, job_data: ReindexJobCreate) -> ReindexJob:
        """
        Create a new reindex job.

        Args:
            job_data: The reindex job data to create

        Returns:
            ReindexJob: The created reindex job
        """
        db_job = ReindexJob(**job_data.model_dump())
        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def get_reindex_job(self, job_id: UUID) -> Optional[ReindexJob]:
        """
        Get a single reindex job by ID.

        Args:
            job_id: The ID of the job to retrieve

        Returns:
            Optional[ReindexJob]: The job or None if not found
        """
        return self.db.query(ReindexJob).filter(ReindexJob.id == job_id).first()

    def update_reindex_job_progress(
        self, job_id: UUID, progress: float, status: Optional[ReindexJobStatus] = None
    ) -> None:
        """
        Update reindex job progress.

        Args:
            job_id: The ID of the job
            progress: Progress value (0.0 to 1.0)
            status: Optional status to update
        """
        job = self.get_reindex_job(job_id)
        if job:
            job.progress = progress
            if status:
                job.status = status
            self.db.commit()

    def update_reindex_job_status(
        self,
        job_id: UUID,
        status: ReindexJobStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Update reindex job status.

        Args:
            job_id: The ID of the job
            status: The new status
            error_message: Optional error message if status is FAILED
        """
        job = self.get_reindex_job(job_id)
        if job:
            job.status = status
            job.error_message = error_message

            if status == ReindexJobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.now(timezone.utc)

            if status in (
                ReindexJobStatus.COMPLETED,
                ReindexJobStatus.FAILED,
                ReindexJobStatus.CANCELLED,
            ):
                job.completed_at = datetime.now(timezone.utc)

            self.db.commit()
