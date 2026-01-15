"""
Celery task for executing reindex jobs.
"""

from uuid import UUID
from app.core.celery_app import celery_app
from app.core.logging_config import get_logger
from app.db import SessionLocal
from app.commands.execute_reindex_command import ExecuteReindexCommand

logger = get_logger("reindex_task")


@celery_app.task
def reindex_task(job_id: str) -> None:
    """Execute a reindex job."""
    logger.info(f"Starting reindex job: {job_id}")

    db = SessionLocal()
    try:
        command = ExecuteReindexCommand(db)
        command.execute(UUID(job_id))
        logger.info(f"Reindex job {job_id} completed successfully")
    except Exception as e:
        logger.error(f"Reindex job {job_id} failed: {e}", exc_info=True)
        raise
    finally:
        db.close()
