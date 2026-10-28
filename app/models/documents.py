"""
Compliance Document, Extracted Field, Validation Check, and Audit Models
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Numeric,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel


class ComplianceDocument(TimestampedModel):
    """
    Evidence document uploaded by plant operators or compliance managers.
    Stores metadata, private vault storage keys, extraction status, and review state.
    """
    __tablename__ = "compliance_documents"
    
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Original metadata & Private vault storage
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Document type & lifecycle
    document_type_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True)
    document_type_detected: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Extraction state machine
    extraction_status: Mapped[str] = mapped_column(String(50), nullable=False, default="QUEUED", index=True)  # QUEUED, PROCESSING, EXTRACTED, EXTRACTION_FAILED
    extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Deterministic dates & duplicate flags
    detected_issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    detected_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    expiry_reminder_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Human-in-the-loop review workflow
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING_REVIEW")  # PENDING_REVIEW, APPROVED, REJECTED, EDITED_AND_APPROVED
    uploaded_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # File retention & archiving
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    document_type: Mapped[Optional["DocumentType"]] = relationship("DocumentType")
    plant: Mapped["Plant"] = relationship("Plant")
    tenant: Mapped["Tenant"] = relationship("Tenant")
    uploaded_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[uploaded_by_user_id])
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])
    extracted_fields: Mapped[List["ExtractedField"]] = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    validation_checks: Mapped[List["ValidationCheck"]] = relationship("ValidationCheck", back_populates="document", cascade="all, delete-orphan")
    audits: Mapped[List["ComplianceDocumentAudit"]] = relationship("ComplianceDocumentAudit", back_populates="document", cascade="all, delete-orphan")
    evidence_links: Mapped[List["EvidenceLink"]] = relationship("EvidenceLink", back_populates="document", cascade="all, delete-orphan")


class ExtractedField(TimestampedModel):
    """
    Extracted certificate parameters with provenance grounding, source page,
    verbatim snippet, and confidence band.
    """
    __tablename__ = "extracted_fields"
    
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)  # certificate_number, valid_until, authority, etc.
    extracted_value: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_value: Mapped[str] = mapped_column(Text, nullable=False)
    
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.900)
    confidence_band: Mapped[str] = mapped_column(String(20), nullable=False, default="HIGH")  # HIGH, MEDIUM, LOW
    
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    field_type: Mapped[str] = mapped_column(String(50), default="string", nullable=False)  # date, identifier, authority, string, numeric
    
    is_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    document: Mapped["ComplianceDocument"] = relationship("ComplianceDocument", back_populates="extracted_fields")


class ValidationCheck(TimestampedModel):
    """
    Deterministic rule-based consistency check applied after extraction.
    """
    __tablename__ = "validation_checks"
    
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    check_code: Mapped[str] = mapped_column(String(50), nullable=False)  # DOC_TYPE_MATCH, VALID_DATE_WINDOW, CERT_FORMAT_VALID, AUTHORITY_RECOGNIZED, NO_EXPIRY_PERMANENT
    check_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PASSED")  # PASSED, FAILED, WARNING
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    document: Mapped["ComplianceDocument"] = relationship("ComplianceDocument", back_populates="validation_checks")


class ComplianceDocumentAudit(TimestampedModel):
    """
    Tamper-evident audit trail for all document ingestion, extraction, field overrides,
    approvals, and evidence linking events.
    """
    __tablename__ = "compliance_document_audits"

    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # DOCUMENT_UPLOADED, EXTRACTION_QUEUED, EXTRACTION_COMPLETED, EXTRACTION_FAILED,
    # FIELD_OVERRIDDEN, DOCUMENT_APPROVED, DOCUMENT_REJECTED, EVIDENCE_LINKED, DOCUMENT_ARCHIVED
    performed_by: Mapped[str] = mapped_column(String(100), default="SYSTEM", nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    document: Mapped["ComplianceDocument"] = relationship("ComplianceDocument", back_populates="audits")
