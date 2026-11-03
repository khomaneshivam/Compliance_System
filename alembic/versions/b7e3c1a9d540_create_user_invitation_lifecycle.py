"""create tenant user invitation lifecycle

Revision ID: b7e3c1a9d540
Revises: a4d8e1c7b350
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e3c1a9d540"
down_revision: Union[str, Sequence[str], None] = "a4d8e1c7b350"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create invitation records with hashed tokens and one pending invite per tenant/email."""
    op.create_table(
        "user_invitations",
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("delivery_status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("invited_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("accepted_user_id", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_error_code", sa.String(length=80), nullable=True),
        sa.Column("resend_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'REVOKED', 'EXPIRED')",
            name="ck_user_invitations_status",
        ),
        sa.CheckConstraint(
            "delivery_status IN ('PENDING', 'SENT', 'FAILED')",
            name="ck_user_invitations_delivery_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["accepted_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_user_invitations_token_hash"),
    )
    op.create_index("ix_user_invitations_tenant_id", "user_invitations", ["tenant_id"])
    op.create_index("ix_user_invitations_email", "user_invitations", ["email"])
    op.create_index(
        "uq_user_invitations_pending_tenant_email",
        "user_invitations",
        ["tenant_id", "email"],
        unique=True,
        sqlite_where=sa.text("status = 'PENDING'"),
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    """Forward-only: do not delete invitation security/audit metadata in rollback."""
    raise RuntimeError(
        "This migration is intentionally irreversible. Revoke pending invitations and "
        "use a forward repair migration; do not drop invitation history."
    )
