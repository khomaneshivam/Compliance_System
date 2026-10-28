"""
Pydantic v2 Schemas for Secure Document & Evidence Management
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ExtractedFieldData(BaseModel):
    key: str
    value: str
    confidence_score: float = Field(default=0.90, ge=0.0, le=1.0)
    confidence_band: str = "HIGH"  # HIGH, MEDIUM, LOW
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    field_type: str = "string"  # date, identifier, authority, string, numeric
    is_mandatory: bool = False
    model_config = ConfigDict(from_attributes=True)


class ValidationCheckData(BaseModel):
    check_code: str
    check_name: str
    status: str  # PASSED, FAILED, WARNING
    details: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class DocumentAIExtractionOutput(BaseModel):
    document_type_detected: str
    confidence_score: float
    provider_name: str
    provider_mode: str = "FIXTURE"  # FIXTURE, LIVE_OCR, DISABLED, FAILED
    model_version: str
    schema_version: str = "v1.0"
    extracted_at: datetime
    fields: List[ExtractedFieldData]
    validation_checks: List[ValidationCheckData]
    detected_issue_date: Optional[date] = None
    detected_expiry_date: Optional[date] = None
    has_expiry: bool = True
    raw_text_summary: str


class ExtractedFieldResponse(BaseModel):
    id: str
    field_key: str
    extracted_value: str
    confirmed_value: str
    confidence_score: float
    confidence_band: str
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    field_type: str
    is_overridden: bool
    is_mandatory: bool
    model_config = ConfigDict(from_attributes=True)


class ValidationCheckResponse(BaseModel):
    id: str
    check_code: str
    check_name: str
    status: str
    details: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    id: str
    plant_id: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    content_hash: str
    page_count: int
    storage_key: str
    extraction_status: str
    extraction_provider_mode: str = "FIXTURE"  # FIXTURE, LIVE_OCR, DISABLED, FAILED
    error_category: Optional[str] = None
    review_status: str
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LinkedRequirementSummary(BaseModel):
    evidence_link_id: str
    plant_requirement_id: str
    statutory_code: str
    statutory_title: str
    evidence_status: str


class DocumentDetailResponse(BaseModel):
    id: str
    plant_id: str
    plant_name: Optional[str] = None
    tenant_id: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    content_hash: str
    page_count: int
    storage_key: str
    document_type_detected: Optional[str] = None
    extraction_status: str
    extraction_provider_mode: str = "FIXTURE"  # FIXTURE, LIVE_OCR, DISABLED, FAILED
    extraction_error: Optional[str] = None
    error_category: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    review_status: str
    detected_issue_date: Optional[date] = None
    detected_expiry_date: Optional[date] = None
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    expiry_reminder_days: int
    uploaded_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    extracted_fields: List[ExtractedFieldResponse] = []
    validation_checks: List[ValidationCheckResponse] = []
    linked_requirements: List[LinkedRequirementSummary] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FieldUpdateRequest(BaseModel):
    fields: Dict[str, str] = Field(description="Dictionary of field_key -> new confirmed_value")


class DocumentReviewDecisionRequest(BaseModel):
    decision: str = Field(description="APPROVE, EDIT_AND_APPROVE, or REJECT")
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    link_to_statutory_requirement_id: Optional[str] = None
    expiry_reminder_days: Optional[int] = 30
    field_overrides: Optional[Dict[str, str]] = None


class DocumentAuditLogResponse(BaseModel):
    id: str
    action: str
    performed_by: str
    details: Dict[str, Any]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
