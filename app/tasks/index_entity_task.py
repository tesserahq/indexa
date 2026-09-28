"""
Celery task for indexing entities from events.
"""

from uuid import UUID

from app.core.celery_app import celery_app
from app.core.logging_config import get_logger
from app.db import session_scope
from app.commands.index_entity_command import IndexEntityCommand
from app.repositories.event_repository import EventRepository

logger = get_logger("index_entity_task")


@celery_app.task
def index_entity_task(event_id: str) -> None:
    """Index an entity from an event.

    The event, its domain service and the enabled providers are read in one
    short transaction; the domain service and the search providers are then
    called with no transaction open.
    """
    logger.info(f"Starting indexing for event: {event_id}")

    try:
        with session_scope() as db:
            event = EventRepository(db).get_event(UUID(event_id))
            if not event:
                logger.error(f"Event not found: {event_id}")
                return
            command = IndexEntityCommand(db)
            plan = command.prepare(event)

        if plan is None:
            return
        command.index(plan)

        logger.info(f"Indexing completed for event: {event_id}")
    except Exception as e:
        logger.error(f"Indexing failed for event {event_id}: {e}", exc_info=True)
        raise
