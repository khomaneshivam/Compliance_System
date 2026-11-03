"""add plant profile verification and unknown-fact state

Revision ID: a4d8e1c7b350
Revises: f19c7a2e5d40
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4d8e1c7b350"
down_revision: Union[str, Sequence[str], None] = "f19c7a2e5d40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Existing profiles require review; never assume old zero/default values were verified."""
    with op.batch_alter_table("plant_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("profile_status", sa.String(length=20), server_default="INCOMPLETE", nullable=False)
        )
        batch_op.add_column(sa.Column("updated_by_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("verified_by_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("verification_notes", sa.Text(), nullable=True))
        batch_op.create_check_constraint(
            "ck_plant_profiles_status",
            "profile_status IN ('INCOMPLETE', 'VERIFIED', 'DEMO_FIXTURE')",
        )
        batch_op.create_foreign_key(
            "fk_plant_profiles_updated_by_user",
            "users",
            ["updated_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_plant_profiles_verified_by_user",
            "users",
            ["verified_by_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Explicitly backfill historical profile state as INCOMPLETE. Existing
    # values are retained but are not trusted as applicability inputs until reviewed.
    op.execute(
        """
        UPDATE plant_profiles
        SET profile_status = 'INCOMPLETE'
        WHERE profile_status IS NULL
        """
    )


def downgrade() -> None:
    """Forward-only: verification provenance and profile-quality state are retained."""
    raise RuntimeError(
        "This migration is intentionally irreversible. Restore a verified backup "
        "or create a forward repair migration; do not remove verification metadata."
    )
