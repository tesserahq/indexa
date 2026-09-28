"""
Command for indexing a single entity from an event.
"""

from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.event import Event
from app.repositories.domain_service_repository import DomainServiceRepository
from app.utils.event_router import route_event
from app.utils.domain_service_client import DomainServiceClient
from app.utils.document_builder import (
    build_document_from_api_response,
    extract_entity_type_from_subject,
    extract_entity_id_from_subject,
)
from app.providers.base import SearchProvider
from app.providers.factory import get_providers
from app.config import get_settings
from app.settings_manager import SettingsManager
from tessera_sdk.infra.events.nats_router import NatsEventPublisher
from app.core.logging_config import get_logger


class IndexEntityCommand:
    """Command to index a single entity from an event."""

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        """
        Initialize the index entity command.

        Args:
            db: Database session
            nats_publisher: Optional NATS publisher for emitting events
        """
        self.db = db
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = get_logger()
        self.domain_service_repository = DomainServiceRepository(db)
        self.domain_client = DomainServiceClient()
        self.settings = get_settings()
        self.settings_manager = SettingsManager(db)

    def execute(self, event: Event) -> None:
        """
        Execute the indexing command for an event.

        Args:
            event: The event to process
        """
        plan = self.prepare(event)
        if plan is not None:
            self.index(plan)

    def prepare(self, event: Event) -> Optional["IndexPlan"]:
        """
        Everything indexing needs from the database: the owning domain
        service and the enabled providers. Makes no external calls, so the
        caller can end its transaction before ``index``.

        Returns None when the event should not be indexed.
        """
        # Route event to domain service
        domain_service = route_event(event, self.domain_service_repository)
        if not domain_service:
            self.logger.warning(
                f"No domain service found for event type: {event.event_type}"
            )
            return None

        # Extract entity type and ID from subject
        entity_type = extract_entity_type_from_subject(event.subject)
        entity_id = extract_entity_id_from_subject(event.subject)

        if not entity_type or not entity_id:
            self.logger.warning(
                f"Could not extract entity type or ID from subject: {event.subject}"
            )
            return None

        # Check if entity type is excluded
        if (
            domain_service.excluded_entities
            and entity_type in domain_service.excluded_entities
        ):
            self.logger.debug(
                f"Entity type {entity_type} is excluded for service {domain_service.name}"
            )
            return None

        # Get enabled providers
        providers = get_providers(self.settings, self.settings_manager)

        if not providers:
            raise ValueError("No providers enabled")

        return IndexPlan(
            source=event.source,
            entity_type=entity_type,
            entity_id=entity_id,
            base_url=domain_service.base_url,
            indexes_path_prefix=domain_service.indexes_path_prefix,
            providers=providers,
        )

    def index(self, plan: "IndexPlan") -> None:
        """Fetch the entity from its domain service and upsert it to every
        provider. No database access."""
        # Call domain service to get entity data
        domain_response = self.domain_client.get_entity(
            base_url=plan.base_url,
            indexes_path_prefix=plan.indexes_path_prefix,
            entity_type=plan.entity_type,
            entity_id=plan.entity_id,
        )

        # Build document
        document = build_document_from_api_response(
            source=plan.source,
            entity_type=plan.entity_type,
            entity_id=plan.entity_id,
            domain_response=domain_response,
        )

        self.logger.info("Indexing entity %s/%s", plan.entity_type, plan.entity_id)
        # Upsert to all enabled providers
        for provider in plan.providers:
            provider.upsert(document)
            self.logger.info(
                f"Indexed entity {plan.entity_type}/{plan.entity_id} to {provider.name}"
            )


@dataclass(frozen=True)
class IndexPlan:
    """What ``IndexEntityCommand.index`` needs, detached from the session."""

    source: str
    entity_type: str
    entity_id: str
    base_url: str
    indexes_path_prefix: Optional[str]
    providers: List[SearchProvider]
