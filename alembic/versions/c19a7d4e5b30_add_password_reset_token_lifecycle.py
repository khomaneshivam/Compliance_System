"""add password reset token lifecycle and session versioning

Revision ID: c19a7d4e5b30
Revises: b7e3c1a9d540
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c19a7d4e5b30"
down_revision: Union[str, Sequence[str], None] = "b7e3c1a9d540"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add credential versioning and durable one-time password reset tokens."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False)
        )

    op.create_table(
        "user_password_reset_tokens",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("delivery_status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_error_code", sa.String(length=80), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'USED', 'REVOKED', 'EXPIRED')",
            name="ck_password_reset_tokens_status",
        ),
        sa.CheckConstraint(
            "delivery_status IN ('PENDING', 'SENT', 'FAILED')",
            name="ck_password_reset_tokens_delivery_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_user_password_reset_tokens_token_hash"),
    )
    op.create_index(
        "ix_user_password_reset_tokens_user_id",
        "user_password_reset_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_tokens_user_status",
        "user_password_reset_tokens",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_password_reset_tokens_one_pending_per_user",
        "user_password_reset_tokens",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("status = 'PENDING'"),
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    """Forward-only to preserve credential invalidation and reset history."""
    raise RuntimeError(
        "This migration is intentionally irreversible. Revoke pending reset tokens and "
        "use a forward repair migration; do not delete credential history."
    )
