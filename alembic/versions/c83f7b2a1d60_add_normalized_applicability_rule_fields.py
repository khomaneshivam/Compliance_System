"""add normalized expression and explanation fields to applicability rules

Revision ID: c83f7b2a1d60
Revises: b72d1f9a4c30
Create Date: 2026-11-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c83f7b2a1d60"
down_revision: Union[str, Sequence[str], None] = "b72d1f9a4c30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Preserve legacy rule logic/rationale while adding the normalized current fields."""
    with op.batch_alter_table("applicability_rules", schema=None) as batch_op:
        batch_op.add_column(sa.Column("expression_ast", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("pass_explanation_template", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("fail_explanation_template", sa.Text(), nullable=True))

    # Preserve the exact legacy JSON expression. The historical rationale is
    # reused as both display templates because the old schema had one rationale
    # field and no distinct pass/fail explanation semantics.
    op.execute(
        """
        UPDATE applicability_rules
        SET expression_ast = rule_logic
        WHERE expression_ast IS NULL
        """
    )
    op.execute(
        """
        UPDATE applicability_rules
        SET pass_explanation_template =
            COALESCE(NULLIF(TRIM(rationale_template), ''), 'Legacy rule rationale requires review.')
        WHERE pass_explanation_template IS NULL
        """
    )
    op.execute(
        """
        UPDATE applicability_rules
        SET fail_explanation_template =
            COALESCE(NULLIF(TRIM(rationale_template), ''), 'Legacy rule rationale requires review.')
        WHERE fail_explanation_template IS NULL
        """
    )

    with op.batch_alter_table("applicability_rules", schema=None) as batch_op:
        batch_op.alter_column(
            "expression_ast", existing_type=sa.JSON(), nullable=False
        )
        batch_op.alter_column(
            "pass_explanation_template", existing_type=sa.Text(), nullable=False
        )
        batch_op.alter_column(
            "fail_explanation_template", existing_type=sa.Text(), nullable=False
        )
        # Retain legacy data but permit newly normalized rows to omit retired fields.
        batch_op.alter_column(
            "rule_logic", existing_type=sa.JSON(), nullable=True
        )
        batch_op.alter_column(
            "rationale_template", existing_type=sa.Text(), nullable=True
        )


def downgrade() -> None:
    """Forward-only: do not remove migrated rule expression/explanation data."""
    raise RuntimeError(
        "This migration is intentionally irreversible. Restore a verified backup or "
        "create a forward repair migration; do not drop retained rule data."
    )
