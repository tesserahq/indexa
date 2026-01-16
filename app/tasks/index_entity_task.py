"""
Celery task for indexing entities from events.
"""

from uuid import UUID

from app.core.celery_app import celery_app
from app.core.logging_config import get_logger
from app.db import SessionLocal
from app.commands.index_entity_command import IndexEntityCommand
from app.services.event_service import EventService

logger = get_logger("index_entity_task")


@celery_app.task
def index_entity_task(event_id: str) -> None:
    """Index an entity from an event."""
    logger.info(f"Starting indexing for event: {event_id}")

    db = SessionLocal()
    try:
        # Retrieve the event from the database
        event_service = EventService(db)
        event = event_service.get_event(UUID(event_id))

        if not event:
            logger.error(f"Event not found: {event_id}")
            return

        # Execute indexing command
        indexing_command = IndexEntityCommand(db)
        indexing_command.execute(event)

        logger.info(f"Indexing completed for event: {event_id}")
    except Exception as e:
        logger.error(f"Indexing failed for event {event_id}: {e}", exc_info=True)
        raise
    finally:
        db.close()
