"""
Command for updating a domain service.
"""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.domain_service import DomainService
from app.models.user import User
from app.schemas.domain_service import DomainServiceUpdate
from app.services.domain_service_service import DomainServiceService
from app.exceptions.handlers import ResourceNotFoundError
from app.events.domain_service_events import build_domain_service_updated_event
from tessera_sdk.events.nats_router import NatsEventPublisher

logger = logging.getLogger(__name__)


class UpdateDomainServiceCommand:
    """Command to update an existing domain service."""

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        """
        Initialize the update domain service command.

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
        self,
        service_id: UUID,
        service_data: DomainServiceUpdate,
        updated_by: User,
    ) -> DomainService:
        """
        Execute the update domain service command.

        Args:
            service_id: The ID of the service to update
            service_data: The updated service data
            updated_by: User who updated the service

        Returns:
            DomainService: The updated domain service

        Raises:
            ResourceNotFoundError: If the service is not found
            Exception: If the service update fails
        """
        try:
            self.logger.info(f"Updating domain service with id: {service_id}")
            updated_service = self.service.update_service(service_id, service_data)
            if not updated_service:
                raise ResourceNotFoundError(
                    f"Domain service with id {service_id} not found"
                )
            self.logger.info(
                f"Successfully updated domain service with id: {service_id}"
            )

            # Emit updated event
            updated_event = build_domain_service_updated_event(
                updated_service, updated_by=updated_by
            )
            self.nats_publisher.publish_sync(updated_event, updated_event.event_type)

            return updated_service
        except ResourceNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to update domain service {service_id}: {e}",
                exc_info=True,
            )
            raise
