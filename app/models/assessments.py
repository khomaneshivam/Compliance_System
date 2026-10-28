"""
Assessment Run, Assessment Finding, and Proposed Requirement Change Models
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel, utc_now


class AssessmentRun(TimestampedModel):
    """
    Immutable historical record of a deterministic applicability evaluation run.
    Stores the facts used, rule versions, and counts.
    """
    __tablename__ = "assessment_runs"
    
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    evaluated_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    profile_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    total_rules_evaluated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applicable_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_applicable_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    needs_review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    plant: Mapped["Plant"] = relationship("Plant")
    findings: Mapped[List["AssessmentFinding"]] = relationship("AssessmentFinding", back_populates="assessment_run", cascade="all, delete-orphan")


class AssessmentFinding(TimestampedModel):
    """
    Individual evaluation outcome for a statutory requirement during an assessment run.
    Contains matched facts, missing facts, and explainable rationale.
    """
    __tablename__ = "assessment_findings"
    
    assessment_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("assessment_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    statutory_requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("statutory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("applicability_rules.id", ondelete="SET NULL"), nullable=True)
    evaluation_outcome: Mapped[str] = mapped_column(String(50), nullable=False)  # APPLICABLE, NOT_APPLICABLE, NEEDS_REVIEW
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    matched_facts: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    missing_facts: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    condition_results: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # Relationships
    assessment_run: Mapped["AssessmentRun"] = relationship("AssessmentRun", back_populates="findings")
    statutory_requirement: Mapped["StatutoryRequirement"] = relationship("StatutoryRequirement")
    rule_version: Mapped[Optional["ApplicabilityRule"]] = relationship("ApplicabilityRule")


class ProposedRequirementChange(TimestampedModel):
    """
    Human-in-the-loop review queue for proposed register changes.
    Prevents silent alteration of enterprise obligations when rules or facts change.
    """
    __tablename__ = "proposed_requirement_changes"
    
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    statutory_requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("statutory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_run_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assessment_runs.id", ondelete="SET NULL"), nullable=True)
    rule_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("applicability_rules.id", ondelete="SET NULL"), nullable=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)  # NEW_REQUIREMENT, STATUS_MODIFIED, DECOMMISSIONED
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    proposed_status: Mapped[str] = mapped_column(String(50), nullable=False)  # APPLICABLE, NOT_APPLICABLE, NEEDS_REVIEW
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default="PENDING_REVIEW", nullable=False)  # PENDING_REVIEW, APPROVED, REJECTED
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    plant: Mapped["Plant"] = relationship("Plant")
    statutory_requirement: Mapped["StatutoryRequirement"] = relationship("StatutoryRequirement")
    rule_version: Mapped[Optional["ApplicabilityRule"]] = relationship("ApplicabilityRule")
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])
