from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class DomainServiceBase(BaseModel):
    """Base domain service model containing common attributes."""

    name: str = Field(validation_alias="name")
    """Name of the domain service. Required field."""

    domains: list[str]
    """Array of domain prefixes owned by this service (e.g., ['com.identies']). Required field."""

    base_url: str
    """Base URL for the domain service's indexing API. Required field."""

    indexes_path_prefix: Optional[str] = None
    """Path prefix for indexing endpoints. Defaults to 'indexes'. Can be customized per service."""

    excluded_entities: Optional[list[str]] = None
    """Optional list of entity types to exclude from indexing. Indexes all entities by default."""

    enabled: bool = True
    """Whether the service is enabled. Defaults to True."""


class DomainServiceCreate(DomainServiceBase):
    """Schema for creating a new domain service."""

    pass


class DomainServiceUpdate(BaseModel):
    """Schema for updating an existing domain service."""

    name: Optional[str] = Field(default=None, validation_alias="name")
    domains: Optional[list[str]] = None
    base_url: Optional[str] = None
    indexes_path_prefix: Optional[str] = None
    excluded_entities: Optional[list[str]] = None
    enabled: Optional[bool] = None


class DomainServiceInDB(DomainServiceBase):
    """Schema representing a domain service stored in the database."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DomainService(DomainServiceInDB):
    """Schema for domain service data returned in API responses."""

    pass
