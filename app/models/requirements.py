"""
Plant Requirements Register and Evidence Link Models
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint, Float, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel, utc_now


class PlantRequirement(TimestampedModel):
    __tablename__ = "plant_requirements"

    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    statutory_requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("statutory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    applicability_status: Mapped[str] = mapped_column(String(50), nullable=False, default="APPLICABLE")
    applicability_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Current normalized evidence state, due date and owner.
    evidence_status: Mapped[str] = mapped_column(String(50), nullable=False, default="MISSING", server_default="MISSING")
    current_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Legacy register fields are retained for backward compatibility and audit.
    compliance_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    owner_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    rule_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("applicability_rules.id", ondelete="SET NULL"), nullable=True)
    requirement_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("requirement_versions.id", ondelete="SET NULL"), nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=True)
    
    # Relationships
    plant: Mapped["Plant"] = relationship("Plant", back_populates="requirements")
    statutory_requirement: Mapped["StatutoryRequirement"] = relationship("StatutoryRequirement")
    owner: Mapped[Optional["User"]] = relationship("User")
    evidence_links: Mapped[List["EvidenceLink"]] = relationship("EvidenceLink", back_populates="plant_requirement", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("plant_id", "statutory_requirement_id", name="uq_plant_statutory_requirement"),
    )


class EvidenceLink(TimestampedModel):
    __tablename__ = "evidence_links"

    plant_requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("plant_requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("compliance_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    linked_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Legacy evidence-link metadata retained from the initial schema.
    verification_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="LINKED", server_default="LINKED"
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    plant_requirement: Mapped["PlantRequirement"] = relationship("PlantRequirement", back_populates="evidence_links")
    document: Mapped["ComplianceDocument"] = relationship("ComplianceDocument")
