"""
Router for provider-related endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.provider import ProviderStatus
from app.schemas.common import ListResponse
from app.providers.factory import get_providers, is_provider_enabled
from app.config import get_settings
from app.settings_manager import SettingsManager
from app.auth.rbac import build_rbac_dependencies
from tessera_sdk.utils.auth import get_current_user

router = APIRouter(
    prefix="/providers",
    tags=["providers"],
    responses={404: {"description": "Not found"}},
)


async def infer_domain(request: Request) -> Optional[str]:
    return "*"


RESOURCE = "provider"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get("", response_model=ListResponse[ProviderStatus])
def list_providers(
    db: Session = Depends(get_db),
    _authorized: bool = Depends(rbac["read"]),
    _current_user=Depends(get_current_user),
):
    """
    Get a list of all search providers and their status.

    Returns information about each provider including:
    - name: The provider name (e.g., "algolia", "typesense")
    - enabled: Whether the provider is enabled (has config and enabled flag)
    - healthy: Whether the provider is healthy and reachable (only checked if enabled)
    """
    settings = get_settings()
    settings_manager = SettingsManager(db)

    provider_statuses = []

    # Check all known providers
    known_providers = ["algolia", "typesense"]

    for provider_name in known_providers:
        enabled = is_provider_enabled(provider_name, settings, settings_manager)
        healthy = False

        # Only check health if provider is enabled
        if enabled:
            try:
                # Get enabled providers and find this one
                providers = get_providers(settings, settings_manager)
                provider = next((p for p in providers if p.name == provider_name), None)
                if provider:
                    healthy = provider.healthcheck()
            except Exception:
                # If healthcheck fails, healthy remains False
                healthy = False

        provider_statuses.append(
            ProviderStatus(
                name=provider_name,
                enabled=enabled,
                healthy=healthy,
            )
        )

    return ListResponse(items=provider_statuses)
