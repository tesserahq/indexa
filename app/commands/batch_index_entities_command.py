"""
Command for batch indexing entities from a domain service.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.domain_service import DomainService
from app.utils.domain_service_client import DomainServiceClient
from app.utils.document_builder import build_document_from_api_response
from app.providers.factory import get_providers
from app.config import get_settings
from app.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class BatchIndexEntitiesCommand:
    """Command to batch index entities from a domain service."""

    def __init__(self, db: Session):
        """
        Initialize the batch index entities command.

        Args:
            db: Database session
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.domain_client = DomainServiceClient()
        self.settings = get_settings()
        self.settings_manager = SettingsManager(db)

    def execute(
        self,
        service: DomainService,
        entity_type: str,
        updated_after: Optional[datetime] = None,
        updated_before: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> Dict[str, Any]:
        """
        Execute batch indexing for a specific entity type.

        Args:
            service: The domain service to query
            entity_type: The entity type to index
            updated_after: Optional datetime filter
            updated_before: Optional datetime filter
            page: Page number (default: 1)
            per_page: Items per page (default: 100)

        Returns:
            Dict with batch indexing results (entities indexed, etc.)
        """
        # Format datetime filters as ISO 8601 strings
        updated_after_str = updated_after.isoformat() if updated_after else None
        updated_before_str = updated_before.isoformat() if updated_before else None

        # Call domain service batch ingest API
        response = self.domain_client.get_entities_batch(
            base_url=service.base_url,
            indexes_path_prefix=service.indexes_path_prefix,
            entity_type=entity_type,
            updated_after=updated_after_str,
            updated_before=updated_before_str,
            page=page,
            per_page=per_page,
        )

        # Extract entities from response
        # Response format depends on domain service, but typically:
        # {"data": [...], "pagination": {...}} or similar
        entities = response.get("data", response.get("items", []))
        if not entities:
            self.logger.warning(
                f"No entities returned from batch ingest for {entity_type}"
            )
            return {"indexed": 0, "failed": 0, "entities": []}

        # Get enabled providers
        providers = get_providers(self.settings, self.settings_manager)
        if not providers:
            self.logger.warning("No search providers enabled")
            return {"indexed": 0, "failed": 0, "entities": []}

        # Build documents and upsert to providers
        indexed_count = 0
        failed_count = 0
        indexed_entities = []

        for entity in entities:
            # Assume entity has an "id" field
            entity_id = str(entity.get("id", ""))
            if not entity_id:
                self.logger.warning(f"Entity missing ID, skipping: {entity}")
                failed_count += 1
                continue

            try:
                # Build document from entity (entity is already the full response)
                document = build_document_from_api_response(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    domain_response=entity,
                )

                # Upsert to all providers
                for provider in providers:
                    try:
                        provider.upsert(document)
                        indexed_count += 1
                        indexed_entities.append(document.get("id"))
                    except Exception as e:
                        self.logger.error(
                            f"Failed to index entity {entity_type}/{entity_id} to {provider.name}: {e}",
                            exc_info=True,
                        )
                        failed_count += 1

            except Exception as e:
                self.logger.error(
                    f"Failed to build document for entity {entity_type}/{entity_id}: {e}",
                    exc_info=True,
                )
                failed_count += 1

        return {
            "indexed": indexed_count,
            "failed": failed_count,
            "entities": indexed_entities,
            "total_in_page": len(entities),
        }
