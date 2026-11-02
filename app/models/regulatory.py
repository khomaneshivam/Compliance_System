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

    # Nullable for historic updates whose authority id/source metadata has not
    # yet been reconciled; new records should supply verified authority/source.
    authority_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("regulatory_authorities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notification_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    published_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    summary_plain_language: Mapped[str] = mapped_column(Text, nullable=False)
    key_changes_summary: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    who_may_be_affected: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    official_source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)

    # Legacy source fields retained until every historic source is resolved.
    authority: Mapped[str] = mapped_column(String(100), nullable=False)
    provenance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    authority: Mapped["RegulatoryAuthority"] = relationship("RegulatoryAuthority")
    affected_maps: Mapped[List["AffectedRequirementMap"]] = relationship("AffectedRequirementMap", back_populates="regulatory_update", cascade="all, delete-orphan")
    reviews: Mapped[List["RegulatoryReview"]] = relationship("RegulatoryReview", back_populates="regulatory_update", cascade="all, delete-orphan")


class AffectedRequirementMap(TimestampedModel):
    __tablename__ = "affected_requirement_maps"

    regulatory_update_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_updates.id", ondelete="CASCADE"), nullable=False, index=True)
    statutory_requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("statutory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    change_impact_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    regulatory_update: Mapped["RegulatoryUpdate"] = relationship("RegulatoryUpdate", back_populates="affected_maps")
    statutory_requirement: Mapped["StatutoryRequirement"] = relationship("StatutoryRequirement")


class RegulatoryReview(TimestampedModel):
    __tablename__ = "regulatory_reviews"

    regulatory_update_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_updates.id", ondelete="CASCADE"), nullable=False, index=True)
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Legacy workflow outcome remains available until historic values are mapped.
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", server_default="PENDING")
    
    # Relationships
    regulatory_update: Mapped["RegulatoryUpdate"] = relationship("RegulatoryUpdate", back_populates="reviews")
    plant: Mapped["Plant"] = relationship("Plant")
    reviewer: Mapped["User"] = relationship("User")
