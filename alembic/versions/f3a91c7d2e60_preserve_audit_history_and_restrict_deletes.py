"""preserve legacy audit payloads and enforce restrictive audit ownership

Revision ID: f3a91c7d2e60
Revises: c83f7b2a1d60
Create Date: 2026-11-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a91c7d2e60"
down_revision: Union[str, Sequence[str], None] = "c83f7b2a1d60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add current audit payload aliases without removing original audit evidence."""
    bind = op.get_bind()

    orphan_tenants = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM audit_logs AS a
            LEFT JOIN tenants AS t ON t.id = a.tenant_id
            WHERE a.tenant_id IS NOT NULL AND t.id IS NULL
            """
        )
    ).scalar_one()
    orphan_users = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM audit_logs AS a
            LEFT JOIN users AS u ON u.id = a.user_id
            WHERE a.user_id IS NOT NULL AND u.id IS NULL
            """
        )
    ).scalar_one()
    if orphan_tenants or orphan_users:
        raise RuntimeError(
            "Cannot add restrictive audit ownership constraints: "
            f"{orphan_tenants} orphan tenant references and {orphan_users} orphan user references. "
            "Reconcile these references explicitly before retrying; audit rows were not modified."
        )

    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("previous_state", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("new_state", sa.JSON(), nullable=True))
        batch_op.create_index("ix_audit_logs_action", ["action"], unique=False)
        batch_op.create_index("ix_audit_logs_entity_type", ["entity_type"], unique=False)
        batch_op.create_index("ix_audit_logs_entity_id", ["entity_id"], unique=False)
        batch_op.create_index("ix_audit_logs_tenant_id", ["tenant_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_audit_logs_tenant_restrict",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_audit_logs_user_restrict",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Copy payloads to the current field names while retaining before_state and
    # after_state unchanged. Empty historical payloads remain NULL, not fabricated.
    op.execute(
        """
        UPDATE audit_logs
        SET previous_state = before_state
        WHERE previous_state IS NULL AND before_state IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE audit_logs
        SET new_state = after_state
        WHERE new_state IS NULL AND after_state IS NOT NULL
        """
    )


def downgrade() -> None:
    """Forward-only: audit payload aliases and restrictive ownership are retained."""
    raise RuntimeError(
        "This audit migration is intentionally irreversible. Restore a verified backup "
        "or create a forward repair migration; do not remove retained audit history."
    )
