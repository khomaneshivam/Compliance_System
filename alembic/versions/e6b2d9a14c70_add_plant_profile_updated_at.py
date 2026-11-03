"""add plant profile update timestamp

Revision ID: e6b2d9a14c70
Revises: f3a91c7d2e60
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6b2d9a14c70"
down_revision: Union[str, Sequence[str], None] = "f3a91c7d2e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at without rewriting or dropping existing plant profile data."""
    with op.batch_alter_table("plant_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.current_timestamp(),
                nullable=False,
            )
        )


def downgrade() -> None:
    """Forward-only: keep the persisted update timestamp once introduced."""
    raise RuntimeError(
        "This migration is intentionally irreversible to preserve persisted lifecycle metadata. "
        "Restore a verified backup or create a forward repair migration."
    )
