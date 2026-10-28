"""add_rule_provenance_and_gazette_traceability

Revision ID: 3676f6b1caec
Revises: 921912ca7670
Create Date: 2026-10-28 22:18:56.505639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3676f6b1caec'
down_revision: Union[str, Sequence[str], None] = '921912ca7670'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('applicability_rules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('publication_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('instrument_identifier', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('clause_reference', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('official_source_url', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('source_document_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('source_fingerprint', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('source_verification_status', sa.String(length=50), server_default='UNVERIFIED_DEMO', nullable=False))
        batch_op.create_foreign_key(
            'fk_applicability_rules_source_doc',
            'regulatory_documents',
            ['source_document_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('applicability_rules', schema=None) as batch_op:
        batch_op.drop_constraint('fk_applicability_rules_source_doc', type_='foreignkey')
        batch_op.drop_column('source_verification_status')
        batch_op.drop_column('source_fingerprint')
        batch_op.drop_column('source_document_id')
        batch_op.drop_column('official_source_url')
        batch_op.drop_column('clause_reference')
        batch_op.drop_column('instrument_identifier')
        batch_op.drop_column('publication_date')
