"""reconcile legacy document, extraction and regulatory schemas

Revision ID: d3a0c6e4f210
Revises: d2e7a4c91f60
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3a0c6e4f210"
down_revision: Union[str, Sequence[str], None] = "d2e7a4c91f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Preserve legacy columns and add the current normalized schema side by side."""

    # Regulatory maps: these columns have direct semantic equivalents; rename
    # them in place so the original values remain attached to each record.
    with op.batch_alter_table("affected_requirement_maps", schema=None) as batch_op:
        batch_op.alter_column(
            "update_id",
            new_column_name="regulatory_update_id",
            existing_type=sa.String(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "impact_type",
            new_column_name="change_type",
            existing_type=sa.String(length=50),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "impact_description",
            new_column_name="change_impact_summary",
            existing_type=sa.Text(),
            existing_nullable=True,
        )

    with op.batch_alter_table("regulatory_reviews", schema=None) as batch_op:
        batch_op.alter_column(
            "update_id",
            new_column_name="regulatory_update_id",
            existing_type=sa.String(length=36),
            existing_nullable=False,
        )
        # Prior review_status is retained independently. Decision cannot be
        # reliably inferred from statuses such as PENDING/APPROVED.
        batch_op.add_column(sa.Column("decision", sa.String(length=50), nullable=True))

    with op.batch_alter_table("regulatory_updates", schema=None) as batch_op:
        batch_op.alter_column(
            "publication_date",
            new_column_name="published_date",
            existing_type=sa.Date(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "summary",
            new_column_name="summary_plain_language",
            existing_type=sa.Text(),
            existing_nullable=False,
        )
        # Do not infer a structured authority link from free-text authority.
        # The source string remains mapped in the ORM for manual reconciliation.
        batch_op.add_column(sa.Column("authority_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("key_changes_summary", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("who_may_be_affected", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_regulatory_updates_authority",
            "regulatory_authorities",
            ["authority_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Compliance documents: new vault metadata is optional for historic rows
    # until each legacy file_path has been reviewed and migrated to controlled
    # private storage. Legacy document columns remain present and mapped.
    with op.batch_alter_table("compliance_documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("storage_path", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("document_type_detected", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))
        batch_op.alter_column(
            "file_size_bytes",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )

    # Tasks keep the legacy tenant_id column. New task creation writes the
    # tenant copied from the owning plant; no old ownership data is discarded.
    with op.batch_alter_table("compliance_tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    # Extraction: a missing field key or human confirmation remains NULL. Do
    # not promote extracted values to confirmed_value automatically.
    with op.batch_alter_table("extracted_fields", schema=None) as batch_op:
        batch_op.add_column(sa.Column("field_key", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("confirmed_value", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("confidence_band", sa.String(length=20), nullable=True))
        batch_op.add_column(
            sa.Column("is_overridden", sa.Boolean(), server_default=sa.false(), nullable=False)
        )

    # Validation: preserve old check_status and severity. The new status is
    # copied as a normalized string, while check_code stays unknown until
    # reviewed because check_name is not a stable code registry.
    with op.batch_alter_table("validation_checks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("check_code", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=True))
        batch_op.alter_column(
            "check_name",
            existing_type=sa.String(length=100),
            type_=sa.String(length=255),
            existing_nullable=False,
        )

    op.execute(
        """
        UPDATE validation_checks
        SET status = UPPER(TRIM(check_status))
        WHERE status IS NULL AND check_status IS NOT NULL
        """
    )

    # Add indexes declared by the current ORM. The source schema has foreign
    # keys but did not consistently index the corresponding lookup columns.
    index_specs = [
        ("ix_affected_requirement_maps_regulatory_update_id", "affected_requirement_maps", ["regulatory_update_id"], False),
        ("ix_affected_requirement_maps_statutory_requirement_id", "affected_requirement_maps", ["statutory_requirement_id"], False),
        ("ix_regulatory_reviews_regulatory_update_id", "regulatory_reviews", ["regulatory_update_id"], False),
        ("ix_regulatory_reviews_plant_id", "regulatory_reviews", ["plant_id"], False),
        ("ix_regulatory_updates_authority_id", "regulatory_updates", ["authority_id"], False),
        ("ix_regulatory_updates_notification_number", "regulatory_updates", ["notification_number"], False),
        ("ix_compliance_documents_plant_id", "compliance_documents", ["plant_id"], False),
        ("ix_compliance_documents_tenant_id", "compliance_documents", ["tenant_id"], False),
        ("ix_compliance_tasks_plant_id", "compliance_tasks", ["plant_id"], False),
        ("ix_compliance_tasks_tenant_id", "compliance_tasks", ["tenant_id"], False),
        ("ix_extracted_fields_document_id", "extracted_fields", ["document_id"], False),
        ("ix_validation_checks_document_id", "validation_checks", ["document_id"], False),
        ("ix_plants_code", "plants", ["code"], False),
        ("ix_plants_tenant_id", "plants", ["tenant_id"], False),
        ("ix_users_tenant_id", "users", ["tenant_id"], False),
    ]
    for name, table_name, columns, unique in index_specs:
        op.create_index(name, table_name, columns, unique=unique)

    # These mapped columns are both UNIQUE and indexed in the ORM; the table
    # already has unique constraints, so a named unique index is also required
    # for schema metadata parity.
    op.create_index("ix_tenants_code", "tenants", ["code"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_plant_profiles_plant_id", "plant_profiles", ["plant_id"], unique=True)
    op.create_index(
        "ix_applicability_rules_statutory_requirement_id",
        "applicability_rules",
        ["statutory_requirement_id"],
        unique=False,
    )


def downgrade() -> None:
    """Forward-only to preserve regulatory and evidence provenance."""
    raise RuntimeError(
        "This migration is intentionally irreversible. It renames source-backed columns, "
        "adds normalized fields and indexes, and preserves legacy evidence. Use forward "
        "repair migrations rather than removing or reverting historical data."
    )
