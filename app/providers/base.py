"""
Base search provider abstraction.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    def _clean_source(self, source: Optional[str]) -> str:
        """
        Clean the source by removing leading slash.

        Args:
            source: The source string (e.g., "/identies", "/eventa", "/linden") or None

        Returns:
            The cleaned source without leading slash (e.g., "identies", "eventa", "linden"),
            or empty string if source is None
        """
        if source is None:
            return ""
        return source.lstrip("/")

    def _get_index_name(self, source: str, entity_type: str) -> str:
        """
        Get the index name from source and entity type.

        Args:
            source: The source string (e.g., "/identies", "/eventa", "/linden") or None
            entity_type: The entity type

        Returns:
            The index name in the format "{cleaned_source}-{entity_type}"
        """
        cleaned_source = self._clean_source(source)
        return f"{cleaned_source}-{entity_type}"

    @abstractmethod
    def upsert(self, document: Dict[str, Any]) -> None:
        """
        Upsert a single document to the search index.

        Args:
            document: The document to upsert (as dict)
        """
        pass

    @abstractmethod
    def upsert_batch(self, documents: List[Dict[str, Any]]) -> None:
        """
        Upsert multiple documents to the search index in batch.

        Args:
            documents: List of documents to upsert
        """
        pass

    @abstractmethod
    def delete(self, index_name: str, document_id: str) -> None:
        """
        Delete a document from the search index.

        Args:
            document_id: The ID of the document to delete
        """
        pass

    @abstractmethod
    def delete_batch(self, index_name: str, document_ids: List[str]) -> None:
        """
        Delete multiple documents from the search index in batch.

        Args:
            document_ids: List of document IDs to delete
        """
        pass

    @abstractmethod
    def ensure_index(self, index_name: str) -> None:
        """
        Ensure the index exists, creating it if necessary.

        Args:
            index_name: The name of the index
        """
        pass

    @abstractmethod
    def healthcheck(self) -> bool:
        """
        Check if the provider is healthy and reachable.

        Returns:
            bool: True if healthy, False otherwise
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass
