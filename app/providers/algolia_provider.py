"""
Algolia search provider implementation.
"""

import logging
from typing import Dict, Any, List
from algoliasearch.search_client import SearchClient
from algoliasearch.exceptions import AlgoliaException

from app.providers.base import SearchProvider
from app.config import Settings


logger = logging.getLogger(__name__)


class AlgoliaProvider(SearchProvider):
    """Algolia search provider implementation."""

    def __init__(self, settings: Settings):
        """
        Initialize Algolia provider.

        Args:
            settings: Application settings containing Algolia configuration
        """
        if not settings.algolia_app_id or not settings.algolia_api_key:
            raise ValueError("Algolia app_id and api_key must be configured")

        self.app_id = settings.algolia_app_id
        self.api_key = settings.algolia_api_key

        self.client = SearchClient.create(self.app_id, self.api_key)

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "algolia"

    def upsert(self, document: Dict[str, Any]) -> None:
        """
        Upsert a single document to Algolia.

        Args:
            document: The document to upsert
        """
        entity_type = document.get("type")
        source = document.get("source")
        if not entity_type:
            raise ValueError("Document must have a 'type' field")

        if not source:
            raise ValueError("Document must have a 'source' field")

        index_name = self._get_index_name(source, entity_type)
        index = self.client.init_index(index_name)

        try:
            index.save_object(document).wait()
            logger.debug(
                f"Upserted document {document.get('id')} to Algolia index {index_name}"
            )
        except AlgoliaException as e:
            logger.error(f"Failed to upsert document to Algolia: {e}")
            raise

    def upsert_batch(self, documents: List[Dict[str, Any]]) -> None:
        """
        Upsert multiple documents to Algolia in batch.

        Args:
            documents: List of documents to upsert
        """
        if not documents:
            return

        # Group documents by entity type (index name)
        documents_by_index: Dict[str, List[Dict[str, Any]]] = {}
        for doc in documents:
            entity_type = doc.get("type")
            source = doc.get("source")
            if not entity_type:
                logger.warning(
                    f"Document missing 'type' field, skipping: {doc.get('id')}"
                )
                continue

            if not source:
                logger.warning(
                    f"Document missing 'source' field, skipping: {doc.get('id')}"
                )
                continue

            index_name = self._get_index_name(source, entity_type)
            if index_name not in documents_by_index:
                documents_by_index[index_name] = []
            documents_by_index[index_name].append(doc)

        # Upsert to each index
        for index_name, docs in documents_by_index.items():
            index = self.client.init_index(index_name)
            try:
                index.save_objects(docs).wait()
                logger.debug(
                    f"Upserted {len(docs)} documents to Algolia index {index_name}"
                )
            except AlgoliaException as e:
                logger.error(
                    f"Failed to batch upsert documents to Algolia index {index_name}: {e}"
                )
                raise

    def delete(self, index_name: str, document_id: str) -> None:
        """
        Delete a document from Algolia.

        Args:
            document_id: The ID of the document to delete
        """
        # Note: We need the entity_type to know which index, but document_id format is "{type}_{id}"
        # Extract entity_type from document_id
        parts = document_id.split("_", 1)
        if len(parts) != 2:
            logger.warning(f"Invalid document_id format: {document_id}")
            return

        index = self.client.init_index(index_name)

        try:
            index.delete_object(document_id).wait()
            logger.debug(
                f"Deleted document {document_id} from Algolia index {index_name}"
            )
        except AlgoliaException as e:
            logger.error(f"Failed to delete document from Algolia: {e}")
            raise

    def delete_batch(self, index_name: str, document_ids: List[str]) -> None:
        """
        Delete multiple documents from Algolia in batch.

        Args:
            document_ids: List of document IDs to delete
        """
        if not document_ids:
            return

        # Group document IDs by entity type (index name)
        ids_by_index: Dict[str, List[str]] = {}
        for doc_id in document_ids:
            parts = doc_id.split("_", 1)
            if len(parts) != 2:
                logger.warning(f"Invalid document_id format: {doc_id}")
                continue

            if index_name not in ids_by_index:
                ids_by_index[index_name] = []
            ids_by_index[index_name].append(doc_id)

        # Delete from each index
        for index_name, ids in ids_by_index.items():
            index = self.client.init_index(index_name)
            try:
                index.delete_objects(ids).wait()
                logger.debug(
                    f"Deleted {len(ids)} documents from Algolia index {index_name}"
                )
            except AlgoliaException as e:
                logger.error(
                    f"Failed to batch delete documents from Algolia index {index_name}: {e}"
                )
                raise

    def ensure_index(self, index_name: str) -> None:
        """
        Ensure the index exists in Algolia (create if necessary).

        Args:
            index_name: The name of the index (should include prefix)
        """
        index = self.client.init_index(index_name)
        # Algolia creates indices automatically on first write, so this is mostly a no-op
        # But we can verify it exists
        try:
            index.get_settings()
            logger.debug(f"Algolia index {index_name} exists")
        except AlgoliaException as e:
            logger.warning(f"Algolia index {index_name} may not exist: {e}")

    def healthcheck(self) -> bool:
        """
        Check if Algolia is healthy and reachable.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # Try to list indices as a health check
            self.client.list_indices()
            return True
        except Exception as e:
            logger.error(f"Algolia healthcheck failed: {e}")
            return False
