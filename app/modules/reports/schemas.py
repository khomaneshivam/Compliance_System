"""
Pydantic Schemas for Readiness & Evidence Reports
Reports are operational readiness assessments, NEVER legal certifications or guarantees.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

LEGAL_DISCLAIMER = (
    "DISCLAIMER: This document is an operational readiness and compliance-evidence summary "
    "prepared by the PlantProof system for enterprise management and internal audit readiness. "
    "It is NOT a formal legal opinion, statutory certification, or absolute guarantee of regulatory compliance. "
    "Statutory obligations are subject to jurisdictional authority interpretation and human verification."
)


class ReportCreateRequest(BaseModel):
    plant_id: str
    report_title: str = Field(..., min_length=3, max_length=255)
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    file_format: str = Field("JSON", pattern="^(JSON|HTML)$")
    include_evidence_items: bool = True
    include_missing_items: bool = True


class ReportJobResponse(BaseModel):
    id: str
    plant_id: str
    plant_name: Optional[str] = None
    report_title: str
    status: str  # QUEUED, GENERATING, COMPLETED, FAILED
    error_message: Optional[str] = None
    prepared_at: datetime
    data_as_of: date
    file_format: str
    file_size_bytes: int
    summary_metrics: Dict[str, Any] = Field(default_factory=dict)
    download_url: Optional[str] = None
    created_at: datetime


class PaginatedReportJobsResponse(BaseModel):
    items: List[ReportJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EvidenceSummaryItem(BaseModel):
    document_id: str
    original_filename: str
    authority_name: Optional[str] = None
    document_type: Optional[str] = None
    verification_status: str
    valid_until: Optional[date] = None


class MissingEvidenceItem(BaseModel):
    requirement_code: str
    requirement_title: str
    authority: str
    obligation_type: str
    severity: str
    remediation_guidance: str


class ReadinessReportRequirementDetail(BaseModel):
    requirement_code: str
    title: str
    authority: str
    jurisdiction: str
    obligation_type: str
    applicability_status: str
    evidence_status: str
    valid_until: Optional[date] = None
    review_state: str
    sources: List[str] = Field(default_factory=list)
    evidence: List[EvidenceSummaryItem] = Field(default_factory=list)


class ReadinessReportContent(BaseModel):
    report_title: str = "Facility Regulatory Readiness & Evidence Dossier"
    disclaimer: str = LEGAL_DISCLAIMER
    prepared_on: datetime
    data_as_of: date
    generated_by_email: Optional[str] = None
    tenant_name: str
    plant_id: str
    plant_name: str
    jurisdiction: str
    industry_type: str
    summary_metrics: Dict[str, Any]
    requirements: List[ReadinessReportRequirementDetail] = Field(default_factory=list)
    missing_items: List[MissingEvidenceItem] = Field(default_factory=list)
    open_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    regulatory_sources: List[Dict[str, Any]] = Field(default_factory=list)
