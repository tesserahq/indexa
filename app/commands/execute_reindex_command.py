"""
Command for executing reindex jobs.
"""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.services.reindex_service import ReindexService
from app.services.domain_service_service import DomainServiceService
from app.commands.batch_index_entities_command import BatchIndexEntitiesCommand
from app.models.reindex_job import ReindexJobStatus
from tessera_sdk.events.nats_router import NatsEventPublisher

logger = logging.getLogger(__name__)


class ExecuteReindexCommand:
    """Command to execute a reindex job."""

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        """
        Initialize the execute reindex command.

        Args:
            db: Database session
            nats_publisher: Optional NATS publisher for emitting events
        """
        self.db = db
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)
        self.reindex_service = ReindexService(db)
        self.domain_service_service = DomainServiceService(db)
        self.batch_command = BatchIndexEntitiesCommand(db)

    def execute(self, job_id: UUID) -> None:
        """
        Execute a reindex job.

        Args:
            job_id: The ID of the reindex job to execute
        """
        job = self.reindex_service.get_reindex_job(job_id)
        if not job:
            raise ValueError(f"Reindex job {job_id} not found")

        try:
            # Get services to process
            services = self._get_services_to_process(job)

            total_indexed = 0
            total_failed = 0

            # Process each service
            for service in services:
                # Get entity types to process
                entity_types = job.entity_types or self._get_all_entity_types(service)

                for entity_type in entity_types:
                    # Process paginated batches
                    page = 1
                    per_page = 100

                    while True:
                        # Execute batch indexing
                        result = self.batch_command.execute(
                            service=service,
                            entity_type=entity_type,
                            updated_after=job.updated_after,
                            updated_before=job.updated_before,
                            page=page,
                            per_page=per_page,
                        )

                        total_indexed += result.get("indexed", 0)
                        total_failed += result.get("failed", 0)

                        # Update progress (rough estimate)
                        # TODO: More accurate progress calculation
                        self.reindex_service.update_reindex_job_progress(
                            job_id,
                            min(0.9, (page * per_page) / 10000.0),  # Rough estimate
                        )

                        # Check if there are more pages
                        total_in_page = result.get("total_in_page", 0)
                        if total_in_page < per_page:
                            break  # Last page

                        page += 1

            # Update status to COMPLETED
            self.reindex_service.update_reindex_job_status(
                job_id, ReindexJobStatus.COMPLETED
            )
            self.reindex_service.update_reindex_job_progress(job_id, 1.0)

            self.logger.info(f"Reindex job {job_id} completed successfully")

        except Exception as e:
            self.logger.error(f"Reindex job {job_id} failed: {e}", exc_info=True)

            # Update status to FAILED
            self.reindex_service.update_reindex_job_status(
                job_id, ReindexJobStatus.FAILED, error_message=str(e)
            )

            raise

    def _get_services_to_process(self, job):
        """Get list of domain services to process for the job."""
        all_services = self.domain_service_service.get_all_enabled_services()

        if job.domains:
            # Filter by domains
            services = []
            for service in all_services:
                for service_domain in service.domains:
                    if any(
                        domain.startswith(service_domain)
                        or service_domain.startswith(domain)
                        for domain in job.domains
                    ):
                        services.append(service)
                        break
            return services

        return all_services

    def _get_all_entity_types(self, service):
        """Get all entity types for a service (placeholder - would need to query domain service)."""
        # TODO: This would ideally query the domain service for available entity types
        # For now, return empty list (user must specify entity_types in job)
        return []
