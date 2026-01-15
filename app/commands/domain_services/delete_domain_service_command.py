"""
Command for deleting a domain service.
"""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.domain_service_service import DomainServiceService
from app.exceptions.handlers import ResourceNotFoundError
from app.events.domain_service_events import build_domain_service_deleted_event
from tessera_sdk.events.nats_router import NatsEventPublisher

logger = logging.getLogger(__name__)


class DeleteDomainServiceCommand:
    """Command to delete (soft delete) a domain service."""

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        """
        Initialize the delete domain service command.

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

    def execute(self, service_id: UUID, deleted_by: User) -> None:
        """
        Execute the delete domain service command.

        Args:
            service_id: The ID of the service to delete
            deleted_by: User who deleted the service

        Raises:
            ResourceNotFoundError: If the service is not found
            Exception: If the service deletion fails
        """
        try:
            self.logger.info(f"Deleting domain service with id: {service_id}")

            # Get service info before deletion for the event
            domain_service = self.service.get_service(service_id)
            if not domain_service:
                raise ResourceNotFoundError(
                    f"Domain service with id {service_id} not found"
                )

            deleted = self.service.delete_service(service_id)
            if not deleted:
                raise ResourceNotFoundError(
                    f"Domain service with id {service_id} not found"
                )

            self.logger.info(
                f"Successfully deleted domain service with id: {service_id}"
            )

            # Emit deleted event
            deleted_event = build_domain_service_deleted_event(
                domain_service, deleted_by=deleted_by
            )
            self.nats_publisher.publish_sync(deleted_event, deleted_event.event_type)
        except ResourceNotFoundError:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to delete domain service {service_id}: {e}",
                exc_info=True,
            )
            raise
