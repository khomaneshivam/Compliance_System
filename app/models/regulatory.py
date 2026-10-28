"""
Regulatory Update and Change Review Models
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Date, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel


class RegulatoryUpdate(TimestampedModel):
    __tablename__ = "regulatory_updates"
    
    authority_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_authorities.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notification_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., S.O. 1234(E)
    published_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    summary_plain_language: Mapped[str] = mapped_column(Text, nullable=False)
    key_changes_summary: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    who_may_be_affected: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    official_source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)  # NEW, UNDER_REVIEW, REVIEWED, ARCHIVED
    
    # Relationships
    authority: Mapped["RegulatoryAuthority"] = relationship("RegulatoryAuthority")
    affected_maps: Mapped[List["AffectedRequirementMap"]] = relationship("AffectedRequirementMap", back_populates="regulatory_update", cascade="all, delete-orphan")
    reviews: Mapped[List["RegulatoryReview"]] = relationship("RegulatoryReview", back_populates="regulatory_update", cascade="all, delete-orphan")


class AffectedRequirementMap(TimestampedModel):
    __tablename__ = "affected_requirement_maps"
    
    regulatory_update_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_updates.id", ondelete="CASCADE"), nullable=False, index=True)
    statutory_requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("statutory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)  # THRESHOLD_REVISED, NEW_OBLIGATION, FORM_AMENDED
    change_impact_summary: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    regulatory_update: Mapped["RegulatoryUpdate"] = relationship("RegulatoryUpdate", back_populates="affected_maps")
    statutory_requirement: Mapped["StatutoryRequirement"] = relationship("StatutoryRequirement")


class RegulatoryReview(TimestampedModel):
    __tablename__ = "regulatory_reviews"
    
    regulatory_update_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_updates.id", ondelete="CASCADE"), nullable=False, index=True)
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewed_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # APPLIES_TO_PLANT, DOES_NOT_APPLY, REQUIRES_OPERATIONAL_CHANGE
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    regulatory_update: Mapped["RegulatoryUpdate"] = relationship("RegulatoryUpdate", back_populates="reviews")
    plant: Mapped["Plant"] = relationship("Plant")
    reviewer: Mapped["User"] = relationship("User")
