from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Query, Session
from app.models.domain_service import DomainService
from app.schemas.domain_service import DomainServiceCreate, DomainServiceUpdate
from app.services.soft_delete_service import SoftDeleteService


class DomainServiceService(SoftDeleteService[DomainService]):
    """Service class for managing domain service CRUD operations."""

    def __init__(self, db: Session):
        """
        Initialize the domain service service.

        Args:
            db: Database session
        """
        super().__init__(db, DomainService)

    def register_service(self, service_data: DomainServiceCreate) -> DomainService:
        """
        Register a new domain service.

        Args:
            service_data: The domain service data to create

        Returns:
            DomainService: The created domain service
        """
        db_service = DomainService(**service_data.model_dump())
        self.db.add(db_service)
        self.db.commit()
        self.db.refresh(db_service)
        return db_service

    def get_service(self, service_id: UUID) -> Optional[DomainService]:
        """
        Get a single domain service by ID.

        Args:
            service_id: The ID of the service to retrieve

        Returns:
            Optional[DomainService]: The service or None if not found
        """
        return (
            self.db.query(DomainService).filter(DomainService.id == service_id).first()
        )

    def get_services_query(self) -> Query:
        """
        Get a query for all domain services.
        This is useful for pagination with fastapi-pagination.

        Returns:
            Query: SQLAlchemy query object for domain services
        """
        return (
            self.db.query(DomainService)
            .filter(DomainService.enabled == True)
            .order_by(DomainService.name)
        )

    def get_all_enabled_services(self) -> List[DomainService]:
        """
        Get all enabled domain services.

        Returns:
            List[DomainService]: List of enabled domain services
        """
        return self.db.query(DomainService).filter(DomainService.enabled == True).all()

    def update_service(
        self, service_id: UUID, service_data: DomainServiceUpdate
    ) -> Optional[DomainService]:
        """
        Update an existing domain service.

        Args:
            service_id: The ID of the service to update
            service_data: The updated service data

        Returns:
            Optional[DomainService]: The updated service or None if not found
        """
        db_service = (
            self.db.query(DomainService).filter(DomainService.id == service_id).first()
        )
        if db_service:
            update_data = service_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_service, key, value)
            self.db.commit()
            self.db.refresh(db_service)
        return db_service

    def delete_service(self, service_id: UUID) -> bool:
        """
        Soft delete a domain service.

        Args:
            service_id: The ID of the service to delete

        Returns:
            bool: True if the service was deleted, False otherwise
        """
        return self.delete_record(service_id)

    def get_service_by_domain(self, domain_prefix: str) -> Optional[DomainService]:
        """
        Get a domain service by matching a domain prefix.
        Matches if any of the service's domains is a prefix of the given domain.

        Args:
            domain_prefix: The domain prefix to match (e.g., "com.identies")

        Returns:
            Optional[DomainService]: The matching service or None if not found
        """
        services = self.get_all_enabled_services()
        for service in services:
            for service_domain in service.domains:
                # Handle wildcard patterns (e.g., "com.identies.*")
                if service_domain.endswith(".*"):
                    prefix = service_domain[:-2]  # Remove ".*"
                    if (
                        domain_prefix.startswith(prefix + ".")
                        or domain_prefix == prefix
                    ):
                        return service
                # Exact match
                elif service_domain == domain_prefix:
                    return service
        return None

    def resolve_service_for_event(self, event_type: str) -> Optional[DomainService]:
        """
        Resolve the domain service for a given event type.
        Extracts the domain prefix from the event_type and matches against registered services.

        Args:
            event_type: The event type (e.g., "com.identies.user.updated")

        Returns:
            Optional[DomainService]: The matching service or None if not found
        """
        # Extract domain prefix (e.g., "com.identies.user.updated" -> "com.identies")
        parts = event_type.split(".")
        if len(parts) < 2:
            return None

        # Try progressively longer prefixes
        for i in range(2, len(parts) + 1):
            domain_prefix = ".".join(parts[:i])
            service = self.get_service_by_domain(domain_prefix)
            if service:
                return service

        return None
