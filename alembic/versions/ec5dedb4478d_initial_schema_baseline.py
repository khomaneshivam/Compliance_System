"""Initial schema baseline

Revision ID: ec5dedb4478d
Revises: 
Create Date: 2026-10-24 02:24:12.808255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec5dedb4478d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Tenants
    op.create_table('tenants',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Users
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='VIEWER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Plants
    op.create_table('plants',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('jurisdiction', sa.String(length=100), nullable=False, server_default='Maharashtra'),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('pincode', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Plant Profiles
    op.create_table('plant_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('plant_id', sa.String(length=36), nullable=False),
        sa.Column('industry_category', sa.String(length=50), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('employee_count', sa.Integer(), nullable=True),
        sa.Column('contract_labour_count', sa.Integer(), nullable=True),
        sa.Column('built_up_area_sqm', sa.Float(), nullable=True),
        sa.Column('capital_investment_inr', sa.Float(), nullable=True),
        sa.Column('connected_power_kw', sa.Float(), nullable=True),
        sa.Column('dg_set_capacity_kva', sa.Float(), nullable=True),
        sa.Column('hazardous_waste_tpa', sa.Float(), nullable=True),
        sa.Column('effluent_discharge_kld', sa.Float(), nullable=True),
        sa.Column('boiler_count', sa.Integer(), nullable=True),
        sa.Column('steam_capacity_tph', sa.Float(), nullable=True),
        sa.Column('raw_attributes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plant_id')
    )

    # Plant Equipment
    op.create_table('plant_equipment',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('plant_id', sa.String(length=36), nullable=False),
        sa.Column('equipment_type', sa.String(length=100), nullable=False),
        sa.Column('identifier', sa.String(length=100), nullable=False),
        sa.Column('capacity', sa.Float(), nullable=True),
        sa.Column('capacity_unit', sa.String(length=50), nullable=True),
        sa.Column('operating_parameters', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Regulatory Authorities
    op.create_table('regulatory_authorities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('jurisdiction', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Regulatory Acts
    op.create_table('regulatory_acts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('authority_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('enactment_year', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['authority_id'], ['regulatory_authorities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Statutory Requirements
    op.create_table('statutory_requirements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('act_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('obligation_type', sa.String(length=50), nullable=False),
        sa.Column('plain_language_summary', sa.Text(), nullable=False),
        sa.Column('statutory_reference', sa.String(length=255), nullable=False),
        sa.Column('penalty_summary', sa.Text(), nullable=True),
        sa.Column('standard_validity_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['act_id'], ['regulatory_acts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Applicability Rules
    op.create_table('applicability_rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('statutory_requirement_id', sa.String(length=36), nullable=False),
        sa.Column('rule_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('rule_logic', sa.JSON(), nullable=False),
        sa.Column('rationale_template', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['statutory_requirement_id'], ['statutory_requirements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Compliance Documents
    op.create_table('compliance_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('plant_id', sa.String(length=36), nullable=False),
        sa.Column('uploaded_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('review_status', sa.String(length=50), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('extraction_confidence', sa.String(length=20), nullable=True),
        sa.Column('ocr_extracted_text', sa.Text(), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('issuing_authority', sa.String(length=255), nullable=True),
        sa.Column('certificate_number', sa.String(length=100), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Plant Requirements
    op.create_table('plant_requirements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('plant_id', sa.String(length=36), nullable=False),
        sa.Column('statutory_requirement_id', sa.String(length=36), nullable=False),
        sa.Column('applicability_status', sa.String(length=50), nullable=False, server_default='APPLICABLE'),
        sa.Column('applicability_rationale', sa.Text(), nullable=True),
        sa.Column('compliance_status', sa.String(length=50), nullable=False, server_default='MISSING'),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('owner_title', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['statutory_requirement_id'], ['statutory_requirements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Evidence Links
    op.create_table('evidence_links',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('plant_requirement_id', sa.String(length=36), nullable=False),
        sa.Column('compliance_document_id', sa.String(length=36), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='LINKED'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['compliance_document_id'], ['compliance_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plant_requirement_id'], ['plant_requirements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Compliance Tasks
    op.create_table('compliance_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('plant_id', sa.String(length=36), nullable=False),
        sa.Column('plant_requirement_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='TODO'),
        sa.Column('assigned_to_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plant_requirement_id'], ['plant_requirements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Audit Logs
    op.create_table('audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=True),
        sa.Column('plant_id', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=True),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=True),
        sa.Column('provenance', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Extracted Fields
    op.create_table('extracted_fields',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('extracted_value', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('verified_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['compliance_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Validation Checks
    op.create_table('validation_checks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('check_name', sa.String(length=100), nullable=False),
        sa.Column('check_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['compliance_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Regulatory Updates
    op.create_table('regulatory_updates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('authority', sa.String(length=100), nullable=False),
        sa.Column('notification_number', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('publication_date', sa.Date(), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('official_source_url', sa.String(length=500), nullable=True),
        sa.Column('provenance', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Regulatory Reviews
    op.create_table('regulatory_reviews',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('update_id', sa.String(length=36), nullable=False),
        sa.Column('plant_id', sa.String(length=36), nullable=False),
        sa.Column('review_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['update_id'], ['regulatory_updates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Affected Requirement Maps
    op.create_table('affected_requirement_maps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('update_id', sa.String(length=36), nullable=False),
        sa.Column('statutory_requirement_id', sa.String(length=36), nullable=False),
        sa.Column('impact_type', sa.String(length=50), nullable=False),
        sa.Column('impact_description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['statutory_requirement_id'], ['statutory_requirements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['update_id'], ['regulatory_updates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('affected_requirement_maps')
    op.drop_table('regulatory_reviews')
    op.drop_table('regulatory_updates')
    op.drop_table('validation_checks')
    op.drop_table('extracted_fields')
    op.drop_table('audit_logs')
    op.drop_table('compliance_tasks')
    op.drop_table('evidence_links')
    op.drop_table('plant_requirements')
    op.drop_table('compliance_documents')
    op.drop_table('applicability_rules')
    op.drop_table('statutory_requirements')
    op.drop_table('regulatory_acts')
    op.drop_table('regulatory_authorities')
    op.drop_table('plant_equipment')
    op.drop_table('plant_profiles')
    op.drop_table('plants')
    op.drop_table('users')
    op.drop_table('tenants')
