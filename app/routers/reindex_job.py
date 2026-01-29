from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, Params  # type: ignore[import-not-found]
from fastapi_pagination.ext.sqlalchemy import paginate  # type: ignore[import-not-found]
from sqlalchemy.orm import Session

from app.commands.execute_reindex_command import ExecuteReindexCommand
from app.db import get_db
from app.routers.utils.dependencies import get_reindex_job_by_id
from app.schemas.reindex_job import (
    ReindexJob,
    ReindexJobCreate,
    ReindexJobStatusResponse,
)
from app.services.reindex_service import ReindexService
from app.models.reindex_job import ReindexJob as ReindexJobModel, ReindexJobStatus
from app.auth.rbac import build_rbac_dependencies
from app.tasks.reindex_task import reindex_task
from fastapi import Request

router = APIRouter(
    prefix="/reindex-jobs",
    tags=["reindex-jobs"],
    responses={404: {"description": "Not found"}},
)


async def infer_domain(_request: Request) -> Optional[str]:
    """Infer domain for RBAC."""
    return "*"


RESOURCE = "reindex_job"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.post("", response_model=ReindexJob, status_code=status.HTTP_201_CREATED)
def create_reindex_job(
    job_data: ReindexJobCreate,
    db: Session = Depends(get_db),
    _authorized: bool = Depends(rbac["create"]),
) -> ReindexJob:
    """Create and trigger a reindex job."""
    service = ReindexService(db)
    created_job = service.create_reindex_job(job_data)

    # Trigger async task
    reindex_task.delay(str(created_job.id))

    return created_job


@router.get("", response_model=Page[ReindexJob], status_code=status.HTTP_200_OK)
def list_reindex_jobs(
    params: Params = Depends(),
    db: Session = Depends(get_db),
    _authorized: bool = Depends(rbac["read"]),
) -> Page[ReindexJob]:
    """List all reindex jobs."""
    service = ReindexService(db)
    return paginate(db, service.get_reindex_jobs_query(), params)


@router.get(
    "/{job_id}",
    response_model=ReindexJobStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_reindex_job(
    job: ReindexJobModel = Depends(get_reindex_job_by_id),
    _authorized: bool = Depends(rbac["read"]),
) -> ReindexJobStatusResponse:
    """Get a specific reindex job by ID."""
    return ReindexJobStatusResponse.model_validate(job)


@router.post("/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_reindex_job(
    job: ReindexJobModel = Depends(get_reindex_job_by_id),
    db: Session = Depends(get_db),
    _authorized: bool = Depends(rbac["update"]),
) -> None:
    """Cancel a running reindex job."""
    if job.status not in (ReindexJobStatus.PENDING, ReindexJobStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status {job.status}",
        )

    ReindexService(db).update_reindex_job_status(job.id, ReindexJobStatus.CANCELLED)
    # TODO: Cancel the Celery task if running


@router.post("/{job_id}/run", status_code=status.HTTP_204_NO_CONTENT)
def run_reindex_job(
    job: ReindexJobModel = Depends(get_reindex_job_by_id),
    db: Session = Depends(get_db),
    _authorized: bool = Depends(rbac["update"]),
) -> None:
    """Run a reindex job."""
    command = ExecuteReindexCommand(db)
    command.execute(job.id)
