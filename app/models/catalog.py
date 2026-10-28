"""
Master Regulatory Catalog Models
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel


class RegulatoryAuthority(TimestampedModel):
    __tablename__ = "regulatory_authorities"
    
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction_level: Mapped[str] = mapped_column(String(20), nullable=False, default="STATE")  # CENTRAL, STATE, LOCAL
    jurisdiction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    acts: Mapped[List["RegulatoryAct"]] = relationship("RegulatoryAct", back_populates="authority", cascade="all, delete-orphan")


class RegulatoryAct(TimestampedModel):
    __tablename__ = "regulatory_acts"
    
    authority_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_authorities.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    jurisdiction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    authority: Mapped["RegulatoryAuthority"] = relationship("RegulatoryAuthority", back_populates="acts")
    requirements: Mapped[List["StatutoryRequirement"]] = relationship("StatutoryRequirement", back_populates="act", cascade="all, delete-orphan")


class StatutoryRequirement(TimestampedModel):
    __tablename__ = "statutory_requirements"
    
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_acts.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    obligation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # LICENCE, CONSENT, CERTIFICATE, REGISTRATION, RETURN
    validity_period_months: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    
    # Relationships
    act: Mapped["RegulatoryAct"] = relationship("RegulatoryAct", back_populates="requirements")
    rules: Mapped[List["ApplicabilityRule"]] = relationship("ApplicabilityRule", back_populates="statutory_requirement", cascade="all, delete-orphan")


class ApplicabilityRule(TimestampedModel):
    """
    Deterministic rule version applied against plant profile facts.
    Immutable once approved/active: updates must create a subsequent version with change rationale.
    """
    __tablename__ = "applicability_rules"
    
    statutory_requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("statutory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expression_ast: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    pass_explanation_template: Mapped[str] = mapped_column(Text, nullable=False)
    fail_explanation_template: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)  # PROPOSED, ACTIVE, SUPERSEDED, REJECTED
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    change_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    statutory_requirement: Mapped["StatutoryRequirement"] = relationship("StatutoryRequirement", back_populates="rules")

    __table_args__ = (
        UniqueConstraint("statutory_requirement_id", "rule_version", name="uq_requirement_rule_version"),
    )
