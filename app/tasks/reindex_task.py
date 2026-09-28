"""
Celery task for executing reindex jobs.
"""

from uuid import UUID
from app.core.celery_app import celery_app
from app.core.logging_config import get_logger
from app.db import session_scope
from app.commands.execute_reindex_command import ExecuteReindexCommand
from app.models.reindex_job import ReindexJobStatus
from app.repositories.reindex_repository import ReindexRepository

logger = get_logger("reindex_task")


@celery_app.task
def reindex_task(job_id: str) -> None:
    """Execute a reindex job."""
    logger.info(f"Starting reindex job: {job_id}")
    job_uuid = UUID(job_id)

    try:
        with session_scope() as db:
            ExecuteReindexCommand(db).execute(job_uuid)
        logger.info(f"Reindex job {job_id} completed successfully")
    except Exception as e:
        logger.error(f"Reindex job {job_id} failed: {e}", exc_info=True)
        # The job's transaction has rolled back; record the failure in a
        # transaction of its own.
        with session_scope() as db:
            ReindexRepository(db).update_reindex_job_status(
                job_uuid, ReindexJobStatus.FAILED, error_message=str(e)
            )
        raise
