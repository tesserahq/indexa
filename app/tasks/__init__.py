# Import celery app first
from app.core.celery_app import celery_app
from app.tasks.process_nats_event import process_nats_event_task
from app.tasks.index_entity_task import index_entity_task
from app.tasks.reindex_task import reindex_task

# Initialize logging configuration for Celery workers
from app.core.logging_config import LoggingConfig

LoggingConfig()  # Initialize logging

__all__ = ["celery_app", "process_nats_event_task", "index_entity_task", "reindex_task"]
