from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi_pagination import Page, Params  # type: ignore[import-not-found]
from fastapi_pagination.ext.sqlalchemy import paginate  # type: ignore[import-not-found]
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.domain_service import (
    DomainService,
    DomainServiceCreate,
    DomainServiceUpdate,
)
from app.services.domain_service_service import DomainServiceService
from app.auth.rbac import build_rbac_dependencies
from app.commands.domain_services.create_domain_service_command import (
    CreateDomainServiceCommand,
)
from app.commands.domain_services.update_domain_service_command import (
    UpdateDomainServiceCommand,
)
from app.commands.domain_services.delete_domain_service_command import (
    DeleteDomainServiceCommand,
)
from app.routers.utils.dependencies import get_domain_service_by_id
from app.models.domain_service import DomainService as DomainServiceModel
from app.models.user import User
from tessera_sdk.utils.auth import get_current_user

router = APIRouter(
    prefix="/domain-services",
    tags=["domain-services"],
    responses={404: {"description": "Not found"}},
)


async def infer_domain(request: Request) -> Optional[str]:
    """Infer domain for RBAC."""
    return "*"


RESOURCE = "domain_service"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.post("", response_model=DomainService, status_code=status.HTTP_201_CREATED)
def create_domain_service(
    service_data: DomainServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _authorized: bool = Depends(rbac["create"]),
) -> DomainService:
    """Register a new domain service."""
    command = CreateDomainServiceCommand(db)
    created_service = command.execute(service_data, created_by=current_user)
    return created_service


@router.get("", response_model=Page[DomainService], status_code=status.HTTP_200_OK)
def list_domain_services(
    params: Params = Depends(),
    db: Session = Depends(get_db),
    _authorized: bool = Depends(rbac["read"]),
) -> Page[DomainService]:
    """List all registered domain services."""
    service = DomainServiceService(db)
    query = service.get_services_query()
    return paginate(db, query, params)


@router.get(
    "/{service_id}",
    response_model=DomainService,
    status_code=status.HTTP_200_OK,
)
def get_domain_service(
    domain_service: DomainServiceModel = Depends(get_domain_service_by_id),
    _authorized: bool = Depends(rbac["read"]),
) -> DomainService:
    """Get a specific domain service by ID."""
    return domain_service


@router.put(
    "/{service_id}",
    response_model=DomainService,
    status_code=status.HTTP_200_OK,
)
def update_domain_service(
    service_data: DomainServiceUpdate,
    domain_service: DomainServiceModel = Depends(get_domain_service_by_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _authorized: bool = Depends(rbac["update"]),
) -> DomainService:
    """Update an existing domain service."""
    command = UpdateDomainServiceCommand(db)
    updated_service = command.execute(
        domain_service.id, service_data, updated_by=current_user  # type: ignore[arg-type]
    )
    return updated_service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain_service(
    domain_service: DomainServiceModel = Depends(get_domain_service_by_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _authorized: bool = Depends(rbac["delete"]),
) -> None:
    """Unregister a domain service (soft delete)."""
    command = DeleteDomainServiceCommand(db)
    command.execute(domain_service.id, deleted_by=current_user)  # type: ignore[arg-type]
