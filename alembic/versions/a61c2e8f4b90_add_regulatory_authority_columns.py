"""add missing regulatory authority columns

Revision ID: a61c2e8f4b90
Revises: 3676f6b1caec
Create Date: 2026-11-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a61c2e8f4b90"
down_revision: Union[str, Sequence[str], None] = "3676f6b1caec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bring clean Alembic databases in line with the active RegulatoryAuthority model."""
    with op.batch_alter_table("regulatory_authorities", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "jurisdiction_level",
                sa.String(length=20),
                server_default="STATE",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("website_url", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """This revision is forward-only to preserve migrated data and historical provenance."""
    raise RuntimeError(
        "This migration is intentionally irreversible. Restore a verified backup or "
        "create a forward repair migration; do not drop retained data."
    )
