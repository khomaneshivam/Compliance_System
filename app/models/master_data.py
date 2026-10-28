"""
Global Reference & Master Data Models
Separates global, jurisdictional, and regulatory reference data from tenant-scoped data.
"""

from datetime import date
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, Date, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel


class Jurisdiction(TimestampedModel):
    """Jurisdiction and geographical regulatory hierarchy (Central -> State -> District/Local)."""
    __tablename__ = "jurisdictions"
    
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # e.g., IN-CENTRAL, IN-MH, IN-GJ
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="STATE")  # CENTRAL, STATE, LOCAL
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Hierarchy relationships
    parent: Mapped[Optional["Jurisdiction"]] = relationship("Jurisdiction", remote_side="Jurisdiction.id", back_populates="children")
    children: Mapped[List["Jurisdiction"]] = relationship("Jurisdiction", back_populates="parent")


class IndustryCategory(TimestampedModel):
    """CPCB / SPCB Industrial pollution classification (Red, Orange, Green, White)."""
    __tablename__ = "industry_categories"
    
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)  # RED, ORANGE, GREEN, WHITE
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cpcb_score_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cpcb_score_max: Mapped[int] = mapped_column(Integer, default=100, nullable=False)


class BusinessActivity(TimestampedModel):
    """Standardized manufacturing activities and process classification."""
    __tablename__ = "business_activities"
    
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # Chemicals, Metallurgy, Manufacturing, Textile
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DocumentType(TimestampedModel):
    """Standardized document and evidence types required by statutes."""
    __tablename__ = "document_types"
    
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    standard_validity_months: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    requires_inspection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    issuing_authority_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("regulatory_authorities.id", ondelete="SET NULL"), nullable=True)


class OfficialSource(TimestampedModel):
    """Official statutory source portals and gazette publications."""
    __tablename__ = "official_sources"
    
    authority_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_authorities.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="GAZETTE")  # GAZETTE, PORTAL, CIRCULAR
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    scrape_frequency: Mapped[str] = mapped_column(String(50), default="DAILY", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RegulationVersion(TimestampedModel):
    """
    Immutable versioned snapshot of a regulation/act.
    Approved regulatory versions cannot be modified; amendments require a new version.
    """
    __tablename__ = "regulation_versions"
    
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_acts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    publication_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gazette_number: Mapped[str] = mapped_column(String(100), nullable=False)
    official_url: Mapped[str] = mapped_column(String(500), nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default="PROPOSED", nullable=False)  # PROPOSED, ACCEPTED, SUPERSEDED, REJECTED
    provenance: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("act_id", "version_number", name="uq_regulation_act_version"),
    )


class RequirementVersion(TimestampedModel):
    """
    Immutable versioned requirement template.
    Maintains provenance and historical rationale when statutory criteria change.
    """
    __tablename__ = "requirement_versions"
    
    statutory_requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("statutory_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    plain_language_summary: Mapped[str] = mapped_column(Text, nullable=False)
    act_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("statutory_requirement_id", "version_number", name="uq_requirement_statutory_version"),
    )
