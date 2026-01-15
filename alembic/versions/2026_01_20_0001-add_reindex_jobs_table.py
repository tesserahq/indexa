"""add reindex jobs table

Revision ID: add_reindex_jobs
Revises: add_domain_services
Create Date: 2026-01-20 00:01:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_reindex_jobs"
down_revision: Union[str, None] = "add_domain_services"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "reindex_jobs",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("domains", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("entity_types", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("providers", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("updated_after", sa.DateTime(), nullable=True),
        sa.Column("updated_before", sa.DateTime(), nullable=True),
        sa.Column(
            "mode",
            sa.Enum("upsert", "replace", name="reindexjobmode"),
            nullable=False,
            server_default="upsert",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="reindexjobstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("reindex_jobs")
    sa.Enum(name="reindexjobstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="reindexjobmode").drop(op.get_bind(), checkfirst=True)
