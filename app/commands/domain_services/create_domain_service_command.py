"""
Command for creating a domain service.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.domain_service import DomainService
from app.models.user import User
from app.schemas.domain_service import DomainServiceCreate
from app.services.domain_service_service import DomainServiceService
from app.events.domain_service_events import build_domain_service_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher

logger = logging.getLogger(__name__)


class CreateDomainServiceCommand:
    """Command to create a new domain service."""

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        """
        Initialize the create domain service command.

        Args:
            db: Database session
            nats_publisher: Optional NATS publisher for emitting events
        """
        self.db = db
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)
        self.service = DomainServiceService(db)

    def execute(
        self, service_data: DomainServiceCreate, created_by: User
    ) -> DomainService:
        """
        Execute the create domain service command.

        Args:
            service_data: The domain service data to create
            created_by: User who created the service

        Returns:
            DomainService: The created domain service

        Raises:
            Exception: If the service creation fails
        """
        try:
            self.logger.info(f"Creating domain service: {service_data.name}")
            created_service = self.service.register_service(service_data)
            self.logger.info(
                f"Successfully created domain service with id: {created_service.id}"
            )

            # Emit created event
            created_event = build_domain_service_created_event(
                created_service, created_by=created_by
            )
            self.nats_publisher.publish_sync(created_event, created_event.event_type)

            return created_service
        except Exception as e:
            self.logger.error(
                f"Failed to create domain service: {e}",
                exc_info=True,
            )
            raise
