"""
Schemas for provider-related API responses.
"""

from pydantic import BaseModel


class ProviderStatus(BaseModel):
    """Status information for a search provider."""

    name: str
    enabled: bool
    healthy: bool
