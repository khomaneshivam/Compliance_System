"""
Pydantic v2 Schemas for Regulatory Intelligence & Change Review Workflow
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SourceResponse(BaseModel):
    id: str
    code: str
    name: str
    authority_name: Optional[str] = None
    source_type: str
    url: str
    adapter_type: str
    adapter_mode: str = "FIXTURE"  # FIXTURE, LIVE_HTTP, DISABLED, FAILED
    scrape_frequency: str
    rate_limit_per_minute: int
    health_status: str
    last_checked_at: Optional[datetime] = None
    last_successful_check_at: Optional[datetime] = None
    consecutive_failures: int
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class SourceHealthResponse(BaseModel):
    source_id: str
    code: str
    name: str
    health_status: str
    adapter_mode: str = "FIXTURE"  # FIXTURE, LIVE_HTTP, DISABLED, FAILED
    consecutive_failures: int
    last_checked_at: Optional[datetime] = None
    last_successful_check_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    total_documents_ingested: int
    pending_change_reviews: int


class EvidenceSnippetSchema(BaseModel):
    section: str
    page: int
    text: str
    clause: str = ""


class ChangeReviewItemResponse(BaseModel):
    id: str
    source_code: str
    source_adapter_mode: str = "FIXTURE"  # FIXTURE, LIVE_HTTP, DISABLED, FAILED
    notification_number: str
    title: str
    published_date: Optional[date] = None
    effective_date: Optional[date] = None
    summary_plain_language: str
    confidence_score: float
    confidence_band: str
    detected_change_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChangeReviewDetailResponse(BaseModel):
    id: str
    source_id: str
    source_code: str
    source_adapter_mode: str = "FIXTURE"  # FIXTURE, LIVE_HTTP, DISABLED, FAILED
    document_id: Optional[str] = None
    statutory_requirement_id: Optional[str] = None
    statutory_requirement_code: Optional[str] = None
    notification_number: str
    title: str
    published_date: Optional[date] = None
    effective_date: Optional[date] = None
    summary_plain_language: str
    key_changes_summary: List[str]
    who_may_be_affected: List[str]
    evidence_snippets: List[EvidenceSnippetSchema]
    proposed_categories: List[str]
    confidence_score: float
    confidence_band: str
    detected_change_type: str
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    diff_summary: Optional[str] = None
    status: str
    review_decision: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    approved_effective_date: Optional[date] = None
    approved_applicability_ast: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}



class ChangeReviewDraftUpdateRequest(BaseModel):
    summary_plain_language: Optional[str] = Field(None, description="Edited human-readable summary")
    effective_date: Optional[date] = Field(None, description="Verified legal effective date")
    proposed_categories: Optional[List[str]] = Field(None, description="Mapped regulatory domains")
    statutory_requirement_id: Optional[str] = Field(None, description="Target mapped requirement ID")
    approved_applicability_ast: Optional[Dict[str, Any]] = Field(None, description="Proposed or amended applicability rule AST")


class ChangeReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVE or REJECT")
    review_notes: str = Field(..., min_length=5, description="Legal review rationale and audit justification")
    effective_date: Optional[date] = Field(None, description="Approved effective date (if approving)")
    applicability_ast: Optional[Dict[str, Any]] = Field(None, description="Approved rule AST condition tree (if approving)")
    target_requirement_code: Optional[str] = Field(None, description="Target statutory requirement code e.g. MPCB-CTO")


class ChangeImpactResponse(BaseModel):
    id: str
    change_review_id: str
    plant_id: str
    plant_name: str
    plant_code: str
    tenant_name: str
    impact_status: str  # POTENTIALLY_APPLICABLE, REQUIRES_REVIEW, NOT_APPLICABLE
    matched_facts: Dict[str, Any]
    missing_facts: List[str]
    explanation: str


class AuditLogResponse(BaseModel):
    id: str
    action: str
    performed_by: str
    details: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
