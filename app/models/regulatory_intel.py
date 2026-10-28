"""
Regulatory Intelligence Ingestion & Change Review Database Models
"""

from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Date, DateTime, ForeignKey, Text, JSON, Boolean, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel


class RegulatorySource(TimestampedModel):
    """
    Official regulatory sources and scrapers (Gazette, MPCB, CPCB, DISH, Local Fixture).
    Tracks health, schedule, and authorized access configuration.
    """
    __tablename__ = "regulatory_sources"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    authority_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("regulatory_authorities.id", ondelete="SET NULL"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="OFFICIAL_GAZETTE")  # OFFICIAL_GAZETTE, REGULATOR_PORTAL, LOCAL_FIXTURE
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(50), nullable=False, default="HTTP_SCRAPER")  # HTTP_SCRAPER, RSS_FEED, LOCAL_FIXTURE
    scrape_frequency: Mapped[str] = mapped_column(String(50), default="DAILY", nullable=False)  # DAILY, WEEKLY, MONTHLY, ON_DEMAND
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    health_status: Mapped[str] = mapped_column(String(50), default="HEALTHY", nullable=False)  # HEALTHY, STALE, UNAVAILABLE, DEGRADED
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    authority: Mapped[Optional["RegulatoryAuthority"]] = relationship("RegulatoryAuthority")
    documents: Mapped[List["RegulatoryDocument"]] = relationship("RegulatoryDocument", back_populates="source", cascade="all, delete-orphan")
    change_reviews: Mapped[List["RegulatoryChangeReview"]] = relationship("RegulatoryChangeReview", back_populates="source", cascade="all, delete-orphan")


class RegulatoryDocument(TimestampedModel):
    """
    Captured raw and safely extracted regulatory documents/gazettes.
    Stores cryptographic hashes, raw content, and section breakdown.
    """
    __tablename__ = "regulatory_documents"

    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., Gazette Notification S.O. 1234(E)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_url: Mapped[str] = mapped_column(String(500), nullable=False)
    published_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sections: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(50), default="FETCHED", nullable=False)  # FETCHED, EXTRACTED, EXTRACTION_FAILED
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    source: Mapped["RegulatorySource"] = relationship("RegulatorySource", back_populates="documents")
    change_review: Mapped[Optional["RegulatoryChangeReview"]] = relationship("RegulatoryChangeReview", back_populates="document", uselist=False)


class RegulatoryChangeReview(TimestampedModel):
    """
    Human-in-the-Loop Change Review item with 8 lifecycle states:
    detected, extraction_failed, draft_analysis, needs_review, approved, rejected, published, superseded
    """
    __tablename__ = "regulatory_change_reviews"

    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("regulatory_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    statutory_requirement_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("statutory_requirements.id", ondelete="SET NULL"), nullable=True, index=True)
    
    notification_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    published_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # AI draft proposals
    summary_plain_language: Mapped[str] = mapped_column(Text, nullable=False)
    key_changes_summary: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    who_may_be_affected: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_snippets: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)  # [{section, page, text, clause}]
    proposed_categories: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.90, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(20), default="HIGH", nullable=False)  # HIGH, MEDIUM, LOW
    detected_change_type: Mapped[str] = mapped_column(String(50), default="AMENDMENT", nullable=False)  # ADDITION, AMENDMENT, REPEAL_SUPERSEDED, DATE_EXTENSION
    
    # Text comparisons
    old_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diff_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Review workflow state machine
    status: Mapped[str] = mapped_column(String(50), default="needs_review", nullable=False, index=True)
    # detected, extraction_failed, draft_analysis, needs_review, approved, rejected, published, superseded
    
    review_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # APPROVE, REJECT
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Published/Approved metadata
    approved_effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    approved_applicability_ast: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    superseded_rule_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    published_rule_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Relationships
    source: Mapped["RegulatorySource"] = relationship("RegulatorySource", back_populates="change_reviews")
    document: Mapped[Optional["RegulatoryDocument"]] = relationship("RegulatoryDocument", back_populates="change_review")
    statutory_requirement: Mapped[Optional["StatutoryRequirement"]] = relationship("StatutoryRequirement")
    reviewer: Mapped[Optional["User"]] = relationship("User")
    impacts: Mapped[List["RegulatoryChangeImpact"]] = relationship("RegulatoryChangeImpact", back_populates="change_review", cascade="all, delete-orphan")


class RegulatoryChangeImpact(TimestampedModel):
    """
    Facility-specific impact calculated after human review approval.
    """
    __tablename__ = "regulatory_change_impacts"

    change_review_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulatory_change_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    impact_status: Mapped[str] = mapped_column(String(50), nullable=False)  # POTENTIALLY_APPLICABLE, REQUIRES_REVIEW, NOT_APPLICABLE
    matched_facts: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    missing_facts: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Relationships
    change_review: Mapped["RegulatoryChangeReview"] = relationship("RegulatoryChangeReview", back_populates="impacts")
    plant: Mapped["Plant"] = relationship("Plant")
    tenant: Mapped["Tenant"] = relationship("Tenant")


class RegulatorySourceAuditLog(TimestampedModel):
    """
    Immutable audit trail for all source retrieval, extraction, AI drafting, and review events.
    """
    __tablename__ = "regulatory_source_audit_logs"

    source_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    change_review_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # POLL_ATTEMPT, DOCUMENT_FETCHED, HASH_VERIFIED, EXTRACTION_FAILED, AI_DRAFT_ANALYSIS,
    # REVIEW_SAVED, REVIEW_APPROVED, REVIEW_REJECTED, RULE_SUPERSEDED, IMPACT_EVALUATED
    performed_by: Mapped[str] = mapped_column(String(100), default="SYSTEM", nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
