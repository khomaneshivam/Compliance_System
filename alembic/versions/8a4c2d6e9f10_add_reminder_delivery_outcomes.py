"""add delivery outcome tracking to reminder notifications

Revision ID: 8a4c2d6e9f10
Revises: d3a0c6e4f210
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a4c2d6e9f10"
down_revision: Union[str, Sequence[str], None] = "d3a0c6e4f210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add durable delivery metadata without inventing historical email outcomes."""
    with op.batch_alter_table("reminder_notifications", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "delivery_status",
                sa.String(length=20),
                server_default="PENDING",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "delivery_attempt_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("delivery_attempted_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("delivery_error_code", sa.String(length=80), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_reminder_notifications_delivery_status",
            "delivery_status IN ('PENDING', 'DELIVERED', 'FAILED')",
        )

    # An in-app notification is delivered when it is durably written to the
    # notification store. Historical email delivery cannot be inferred, so
    # existing email rows remain PENDING until explicitly reconciled.
    op.execute(
        """
        UPDATE reminder_notifications
        SET delivery_status = 'DELIVERED',
            delivered_at = sent_at
        WHERE channel = 'IN_APP'
        """
    )


def downgrade() -> None:
    """Forward-only: retain delivery outcomes as part of the notification audit history."""
    raise RuntimeError(
        "This migration is intentionally irreversible. Preserve delivery history and "
        "use a forward repair migration rather than dropping notification outcomes."
    )
