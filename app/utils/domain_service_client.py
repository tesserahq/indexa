"""
HTTP client for calling domain service indexing APIs.
"""

import logging
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.utils.m2m_token import M2MTokenClient

logger = logging.getLogger(__name__)


class DomainServiceClient:
    """HTTP client for calling domain service indexing APIs."""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize the domain service client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.timeout = timeout
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,  # 1, 2, 4 seconds
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["GET", "POST", "PUT"],  # Only retry safe methods
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers with M2M token.

        Returns:
            Dict with Authorization header
        """
        try:
            m2m_token = M2MTokenClient().get_token_sync().access_token
            return {"Authorization": f"Bearer {m2m_token}"}
        except Exception as e:
            logger.error(f"Failed to get M2M token: {e}", exc_info=True)
            raise

    def _build_index_url(
        self, base_url: str, entity_type: str, indexes_path_prefix: Optional[str] = None
    ) -> str:
        """
        Build URL for indexing endpoints.

        Args:
            base_url: Base URL of the domain service
            entity_type: Type of entity (e.g., "pets")
            indexes_path_prefix: Optional path prefix for indexing endpoints

        Returns:
            Constructed URL string
        """
        if indexes_path_prefix:
            return (
                f"{base_url.rstrip('/')}/{indexes_path_prefix.strip('/')}/{entity_type}"
            )
        else:
            return f"{base_url.rstrip('/')}/{entity_type}"

    def get_entity(
        self,
        base_url: str,
        entity_type: str,
        entity_id: str,
        indexes_path_prefix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a single entity from a domain service.

        Args:
            base_url: Base URL of the domain service
            indexes_path_prefix: Path prefix for indexing endpoints
            entity_type: Type of entity (e.g., "pets")
            entity_id: ID of the entity

        Returns:
            Dict containing the entity data

        Raises:
            requests.RequestException: If the request fails
        """
        base_index_url = self._build_index_url(
            base_url, entity_type, indexes_path_prefix
        )
        url = f"{base_index_url}/{entity_id}"

        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/json"

        try:
            logger.debug(f"Calling domain service: GET {url}")
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to get entity from domain service {url}: {e}", exc_info=True
            )
            raise

    def get_entities_batch(
        self,
        base_url: str,
        entity_type: str,
        indexes_path_prefix: Optional[str] = None,
        updated_after: Optional[str] = None,
        updated_before: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> Dict[str, Any]:
        """
        Get a batch of entities from a domain service (for reindexing).

        Args:
            base_url: Base URL of the domain service
            indexes_path_prefix: Path prefix for indexing endpoints
            entity_type: Type of entity (e.g., "pets")
            updated_after: ISO 8601 datetime string (optional)
            updated_before: ISO 8601 datetime string (optional)
            page: Page number (default: 1)
            per_page: Number of items per page (default: 100)

        Returns:
            Dict containing paginated response with entities

        Raises:
            requests.RequestException: If the request fails
        """
        url = self._build_index_url(base_url, entity_type, indexes_path_prefix)

        params: Dict[str, Any] = {
            "page": page,
            "per_page": per_page,
        }
        if updated_after:
            params["updated_after"] = updated_after
        if updated_before:
            params["updated_before"] = updated_before

        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/json"

        try:
            logger.debug(f"Calling domain service: GET {url} with params {params}")
            response = self.session.get(
                url, headers=headers, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to get entities batch from domain service {url}: {e}",
                exc_info=True,
            )
            raise

    def close(self):
        """Close the HTTP session."""
        self.session.close()
