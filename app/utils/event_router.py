"""
Event routing utility for resolving domain services from events.
"""

from typing import Optional

from app.models.event import Event
from app.models.domain_service import DomainService
from app.services.domain_service_service import DomainServiceService


def route_event(
    event: Event, domain_service_service: DomainServiceService
) -> Optional[DomainService]:
    """
    Route an event to its owning domain service.

    Extracts the domain prefix from the event_type and matches against registered services.

    Args:
        event: The event to route
        domain_service_service: The domain service service for lookups

    Returns:
        Optional[DomainService]: The matching service or None if not found (dead-letter)
    """
    return domain_service_service.resolve_service_for_event(event.event_type)
