"""add domain services table

Revision ID: add_domain_services
Revises: 3cfcd94210c7
Create Date: 2026-01-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_domain_services"
down_revision: Union[str, None] = "3cfcd94210c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "domain_services",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("domains", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("indexes_path_prefix", sa.String(), nullable=True),
        sa.Column("excluded_entities", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("domain_services")
