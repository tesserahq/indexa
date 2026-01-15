from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.models.mixins import TimestampMixin, SoftDeleteMixin
from sqlalchemy import Boolean, Column, String
import uuid

from app.db import Base


class DomainService(Base, TimestampMixin, SoftDeleteMixin):
    """DomainService model for service registration.
    This model represents a domain service that owns one or more event domains.
    """

    __tablename__ = "domain_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    domains = Column(ARRAY(String), nullable=False)
    base_url = Column(String, nullable=False)
    indexes_path_prefix = Column(String, nullable=True)
    excluded_entities = Column(ARRAY(String), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
