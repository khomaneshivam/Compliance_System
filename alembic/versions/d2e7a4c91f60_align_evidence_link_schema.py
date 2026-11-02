"""align evidence-link schema with current evidence provenance model

Revision ID: d2e7a4c91f60
Revises: c19a7d4e5b30
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e7a4c91f60"
down_revision: Union[str, Sequence[str], None] = "c19a7d4e5b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename the legacy FK column without dropping its data and add link attribution."""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                "ALTER TABLE evidence_links "
                "RENAME COLUMN compliance_document_id TO document_id"
            )
        )
    else:
        op.alter_column(
            "evidence_links",
            "compliance_document_id",
            new_column_name="document_id",
            existing_type=sa.String(length=36),
            existing_nullable=False,
        )

    # Keep the table-rebuild operation separate from the rename. This avoids
    # SQLite batch reflection constructing indexes before the renamed column
    # has entered the reflected table definition.
    with op.batch_alter_table("evidence_links", schema=None) as batch_op:
        batch_op.add_column(sa.Column("linked_by_user_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_evidence_links_linked_by_user",
            "users",
            ["linked_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_evidence_links_plant_requirement_id",
        "evidence_links",
        ["plant_requirement_id"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_links_document_id",
        "evidence_links",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Forward-only: do not discard evidence attribution or rename history."""
    raise RuntimeError(
        "This migration is intentionally irreversible. Existing document links and "
        "attribution must be preserved; use a forward repair migration."
    )
