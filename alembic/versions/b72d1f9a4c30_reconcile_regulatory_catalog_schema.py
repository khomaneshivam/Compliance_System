"""reconcile regulatory catalog models with legacy schema

Revision ID: b72d1f9a4c30
Revises: a61c2e8f4b90
Create Date: 2026-11-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b72d1f9a4c30"
down_revision: Union[str, Sequence[str], None] = "a61c2e8f4b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add current catalog fields and preserve the initial schema's legacy values."""
    # The old free-text jurisdiction is superseded by jurisdiction_level +
    # jurisdiction_id. Preserve existing values but do not require it for new rows.
    with op.batch_alter_table("regulatory_authorities", schema=None) as batch_op:
        batch_op.alter_column(
            "jurisdiction",
            existing_type=sa.String(length=100),
            nullable=True,
        )

    # Keep legacy code/description while adding the current short_name field.
    with op.batch_alter_table("regulatory_acts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("short_name", sa.String(length=100), nullable=True))
        batch_op.alter_column(
            "enactment_year",
            new_column_name="year",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "code",
            existing_type=sa.String(length=50),
            nullable=True,
        )

    op.execute(
        """
        UPDATE regulatory_acts
        SET short_name = COALESCE(NULLIF(TRIM(code), ''), SUBSTR(title, 1, 100))
        WHERE short_name IS NULL OR TRIM(short_name) = ''
        """
    )
    with op.batch_alter_table("regulatory_acts", schema=None) as batch_op:
        batch_op.alter_column(
            "short_name",
            existing_type=sa.String(length=100),
            nullable=False,
        )
        batch_op.create_index("ix_regulatory_acts_authority_id", ["authority_id"], unique=False)

    # Add the normalized current requirement fields and backfill from retained
    # legacy fields. Do not drop statutory_reference or previous validity data.
    with op.batch_alter_table("statutory_requirements", schema=None) as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("validity_period_months", sa.Integer(), server_default="12", nullable=True)
        )
        batch_op.add_column(
            sa.Column("grace_period_days", sa.Integer(), server_default="30", nullable=True)
        )
        batch_op.alter_column(
            "code",
            existing_type=sa.String(length=50),
            type_=sa.String(length=100),
            nullable=False,
        )
        batch_op.alter_column(
            "plain_language_summary",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.alter_column(
            "statutory_reference",
            existing_type=sa.String(length=255),
            nullable=True,
        )

    op.execute(
        """
        UPDATE statutory_requirements
        SET description = COALESCE(plain_language_summary, title)
        WHERE description IS NULL
        """
    )
    op.execute(
        """
        UPDATE statutory_requirements
        SET validity_period_months =
            CASE
                WHEN standard_validity_days IS NULL OR standard_validity_days <= 0 THEN 12
                ELSE CAST((standard_validity_days + 15) / 30 AS INTEGER)
            END
        WHERE validity_period_months IS NULL
        """
    )
    op.execute(
        """
        UPDATE statutory_requirements
        SET grace_period_days = 30
        WHERE grace_period_days IS NULL
        """
    )
    with op.batch_alter_table("statutory_requirements", schema=None) as batch_op:
        batch_op.alter_column("description", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column(
            "validity_period_months",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="12",
        )
        batch_op.alter_column(
            "grace_period_days",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="30",
        )
        batch_op.create_index("ix_statutory_requirements_act_id", ["act_id"], unique=False)


def downgrade() -> None:
    """This revision is forward-only to preserve migrated data and historical provenance."""
    raise RuntimeError(
        "This migration is intentionally irreversible. Restore a verified backup or "
        "create a forward repair migration; do not drop retained data."
    )
