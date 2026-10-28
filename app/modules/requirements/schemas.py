"""
Pydantic Schemas for Requirements Register, Saved Views, and Provenance Details
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StatutoryProvenance(BaseModel):
    authority_code: Optional[str] = None
    authority_name: Optional[str] = None
    act_title: Optional[str] = None
    act_short_name: Optional[str] = None
    act_year: Optional[int] = None
    jurisdiction: Optional[str] = None
    section_clause: Optional[str] = None
    gazette_reference: Optional[str] = None
    official_source_url: Optional[str] = None


class EvidenceSummary(BaseModel):
    evidence_link_id: str
    document_id: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    storage_key: Optional[str] = None
    upload_date: datetime
    detected_expiry_date: Optional[date] = None
    evidence_status: str
    review_status: str
    verified_by: Optional[str] = None


class ApplicabilityProvenance(BaseModel):
    applicability_status: str
    applicability_rationale: str
    rule_version: int = 1
    matched_facts: Dict[str, Any] = Field(default_factory=dict)
    missing_facts: List[str] = Field(default_factory=list)
    last_evaluated_at: datetime


class RequirementHistoryItem(BaseModel):
    id: str
    action: str
    performed_by: str
    timestamp: datetime
    details: Dict[str, Any] = Field(default_factory=dict)
    summary_text: str


class RequirementItemResponse(BaseModel):
    id: str
    statutory_requirement_id: str
    code: str
    title: str
    description: Optional[str] = None
    obligation_type: str
    authority_code: Optional[str] = None
    authority_name: Optional[str] = None
    jurisdiction: Optional[str] = None
    applicability_status: str
    evidence_status: str
    current_due_date: Optional[date] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    evidence_count: int = 0
    tasks_count: int = 0
    is_custom: bool = False
    last_evaluated_at: datetime


class PaginatedRequirementsResponse(BaseModel):
    items: List[RequirementItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RequirementDetailResponse(RequirementItemResponse):
    provenance: StatutoryProvenance
    applicability: ApplicabilityProvenance
    evidence_list: List[EvidenceSummary] = Field(default_factory=list)
    history: List[RequirementHistoryItem] = Field(default_factory=list)


class SavedViewPreset(BaseModel):
    id: str
    name: str
    description: str
    filter_params: Dict[str, Any]
    count: int
