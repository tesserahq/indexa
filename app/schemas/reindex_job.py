from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.constants.reindex_job_status import ReindexJobStatus


class ReindexJobBase(BaseModel):
    """Base reindex job model."""

    domains: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None


class ReindexJobCreate(ReindexJobBase):
    """Schema for creating a new reindex job."""

    pass


class ReindexJobInDB(ReindexJobBase):
    """Schema representing a reindex job stored in the database."""

    id: UUID
    status: ReindexJobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReindexJob(ReindexJobInDB):
    """Schema for reindex job data returned in API responses."""

    pass


class ReindexJobStatusResponse(BaseModel):
    """Schema for reindex job status response."""

    id: UUID
    status: ReindexJobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}
