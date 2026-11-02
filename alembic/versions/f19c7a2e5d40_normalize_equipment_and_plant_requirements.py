"""normalize equipment and plant requirement register fields

Revision ID: f19c7a2e5d40
Revises: e6b2d9a14c70
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f19c7a2e5d40"
down_revision: Union[str, Sequence[str], None] = "e6b2d9a14c70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add normalized fields and preserve every legacy value in its original column."""

    # ------------------------------------------------------------------
    # Plant equipment: preserve identifier, numeric capacity, unit and
    # operating_parameters. Add a tag/display representation for the UI.
    # ------------------------------------------------------------------
    with op.batch_alter_table("plant_equipment", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tag_number", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("capacity_display", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("manufacturer", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("installation_date", sa.Date(), nullable=True))

    op.execute(
        """
        UPDATE plant_equipment
        SET tag_number = identifier
        WHERE tag_number IS NULL
        """
    )
    op.execute(
        """
        UPDATE plant_equipment
        SET capacity_display =
            CASE
                WHEN capacity IS NULL THEN NULL
                WHEN capacity_unit IS NULL OR TRIM(capacity_unit) = ''
                    THEN CAST(capacity AS VARCHAR(100))
                ELSE CAST(capacity AS VARCHAR(100)) || ' ' || TRIM(capacity_unit)
            END
        WHERE capacity_display IS NULL
        """
    )

    # Legacy identifier is retained but no longer mandatory for new records.
    # Old identifiers remain unchanged and tag_number has been backfilled.
    with op.batch_alter_table("plant_equipment", schema=None) as batch_op:
        batch_op.alter_column(
            "tag_number",
            existing_type=sa.String(length=100),
            nullable=False,
        )
        batch_op.alter_column(
            "identifier",
            existing_type=sa.String(length=100),
            nullable=True,
        )
        batch_op.create_index("ix_plant_equipment_plant_id", ["plant_id"], unique=False)

    # ------------------------------------------------------------------
    # Plant compliance register: map old compliance status and validity
    # into the normalized evidence status and due-date fields. Retain
    # compliance_status, valid_until and owner_title for historical data.
    # ------------------------------------------------------------------
    with op.batch_alter_table("plant_requirements", schema=None) as batch_op:
        batch_op.add_column(sa.Column("evidence_status", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("current_due_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("owner_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column("is_custom", sa.Boolean(), server_default=sa.false(), nullable=True)
        )

    op.execute(
        """
        UPDATE plant_requirements
        SET evidence_status = CASE
            WHEN UPPER(TRIM(COALESCE(compliance_status, ''))) IN
                ('VALID', 'COMPLIANT', 'COMPLIANT_VALID', 'COMPLETE', 'COMPLETED', 'CURRENT')
                THEN 'VALID'
            WHEN UPPER(TRIM(COALESCE(compliance_status, ''))) = 'EXPIRING_SOON'
                THEN 'EXPIRING_SOON'
            WHEN UPPER(TRIM(COALESCE(compliance_status, ''))) = 'EXPIRED'
                THEN 'EXPIRED'
            WHEN UPPER(TRIM(COALESCE(compliance_status, ''))) IN
                ('NOT_REQUIRED', 'NOT APPLICABLE', 'NOT_APPLICABLE', 'EXEMPTED')
                THEN 'NOT_REQUIRED'
            WHEN UPPER(TRIM(COALESCE(compliance_status, ''))) IN
                ('MISSING', 'NON_COMPLIANT', 'NOT_SUBMITTED')
                THEN 'MISSING'
            ELSE 'UNDER_REVIEW'
        END
        WHERE evidence_status IS NULL
        """
    )
    op.execute(
        """
        UPDATE plant_requirements
        SET current_due_date = valid_until
        WHERE current_due_date IS NULL AND valid_until IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE plant_requirements
        SET is_custom = FALSE
        WHERE is_custom IS NULL
        """
    )

    with op.batch_alter_table("plant_requirements", schema=None) as batch_op:
        batch_op.alter_column(
            "evidence_status",
            existing_type=sa.String(length=50),
            nullable=False,
            server_default="MISSING",
        )
        batch_op.alter_column(
            "is_custom",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        )
        batch_op.create_foreign_key(
            "fk_plant_requirements_owner_user",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_plant_requirements_plant_id", ["plant_id"], unique=False)
        batch_op.create_index(
            "ix_plant_requirements_statutory_requirement_id",
            ["statutory_requirement_id"],
            unique=False,
        )
        batch_op.create_index("ix_plant_requirements_owner_user_id", ["owner_user_id"], unique=False)


def downgrade() -> None:
    """Forward-only: normalized values and compatibility mappings are retained."""
    raise RuntimeError(
        "This migration is intentionally irreversible to preserve migrated equipment "
        "identifiers, capacity values and compliance history. Restore a verified backup "
        "or create a forward repair migration; do not drop retained data."
    )
