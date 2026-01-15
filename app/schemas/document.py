from datetime import datetime
from pydantic import BaseModel


class SearchDocument(BaseModel):
    """
    Search document schema - a flexible structure that preserves domain service JSON.

    Domain services return the complete document structure they want indexed.
    Indexa only adds core fields: id, type, schema_version, updated_at.
    All other fields come directly from domain service response (preserves JSON structure).
    """

    id: str
    """Deterministic document ID: {entity_type}_{entity_id}"""

    type: str
    """Entity type (e.g., 'pets')"""

    schema_version: str = "1.0"
    """Schema version for document structure"""

    updated_at: datetime
    """Timestamp when the document was last updated"""

    model_config = {"extra": "allow"}
    """Allow additional fields from domain service response"""
