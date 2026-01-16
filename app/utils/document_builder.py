"""
Utilities for building search documents from domain service API responses.
"""

from typing import Dict, Any
from datetime import datetime, timezone


def build_document_from_api_response(
    source: str, entity_type: str, entity_id: str, domain_response: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build a search document from a domain service API response.

    Takes the full response from domain service indexing API (preserves JSON structure),
    generates a deterministic ID, and merges with Indexa core fields.

    Args:
        entity_type: The type of entity (e.g., "pets")
        entity_id: The ID of the entity
        domain_response: The complete response from the domain service indexing API

    Returns:
        Dict[str, Any]: Merged dictionary with domain service fields + Indexa core fields
    """
    document_id = entity_id

    # Build core Indexa fields
    core_fields = {
        "id": document_id,
        "objectID": document_id,
        "schema_version": "1.0",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }

    # Merge domain service response with core fields
    # Domain service response takes precedence for any overlapping keys
    document = {**core_fields, **domain_response}

    # Ensure core fields are set (in case domain_response overwrote them)
    document["id"] = document_id
    document["objectID"] = document_id
    document["type"] = entity_type
    document["schema_version"] = core_fields["schema_version"]
    document["source"] = source

    return document


def extract_entity_type_from_subject(subject: str) -> str:
    """
    Extract entity type from event subject.

    Handles patterns like:
    - "pets/:uuid" -> "pets"
    - "pets/123" -> "pets"
    - "com.example.pets/123" -> "com.example.pets" (if there's a slash)
    - "/pets/:uuid/" -> "pets"

    Args:
        subject: Event subject (e.g., "pets/:uuid" or "pets/123" or "/pets/:uuid/")

    Returns:
        str: Extracted entity type
    """
    # Strip leading and trailing slashes to handle cases like "/pets/:uuid/"
    subject = subject.strip("/")

    # Split by "/" and take the first part
    parts = subject.split("/")
    entity_type = parts[0]

    # Remove ":uuid" or similar placeholders if present
    if entity_type.startswith(":"):
        entity_type = entity_type[1:]

    return entity_type


def extract_entity_id_from_subject(subject: str) -> str:
    """
    Extract entity ID from event subject.

    Handles patterns like:
    - "pets/:uuid" -> ":uuid" (returns placeholder as-is)
    - "pets/123" -> "123"
    - "pets/abc-def-123" -> "abc-def-123"
    - "/pets/123" -> "123"
    - "/pets/:uuid" -> ":uuid"

    Args:
        subject: Event subject (e.g., "pets/:uuid" or "pets/123" or "/pets/123")

    Returns:
        str: Extracted entity ID
    """
    # Strip leading and trailing slashes to handle cases like "/pets/:uuid/" or "/pets/123"
    subject = subject.strip("/")

    # Split by "/" and take the second part (if exists)
    parts = subject.split("/", 1)
    if len(parts) > 1:
        return parts[1]

    # If no "/" found, return empty string (shouldn't happen in practice)
    return ""
