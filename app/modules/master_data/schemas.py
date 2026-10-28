"""
Master Data Pydantic v2 Request/Response Schemas
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class JurisdictionResponse(BaseModel):
    id: str
    code: str
    name: str
    level: str
    parent_id: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class IndustryCategoryResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str
    cpcb_score_min: int
    cpcb_score_max: int

    model_config = {"from_attributes": True}


class BusinessActivityResponse(BaseModel):
    id: str
    code: str
    name: str
    category: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentTypeResponse(BaseModel):
    id: str
    code: str
    name: str
    standard_validity_months: int
    requires_inspection: bool
    issuing_authority_id: Optional[str] = None

    model_config = {"from_attributes": True}


class RegulatoryAuthorityResponse(BaseModel):
    id: str
    code: str
    name: str
    jurisdiction_level: str
    jurisdiction_id: Optional[str] = None
    website_url: Optional[str] = None

    model_config = {"from_attributes": True}


class RegulatoryActResponse(BaseModel):
    id: str
    authority_id: str
    title: str
    short_name: str
    year: int
    jurisdiction_id: Optional[str] = None

    model_config = {"from_attributes": True}


class ApplicabilityRuleSummary(BaseModel):
    id: str
    rule_version: int
    status: str
    expression_ast: Dict[str, Any]
    pass_explanation_template: str
    fail_explanation_template: str
    is_immutable: bool
    effective_from: Optional[date] = None

    model_config = {"from_attributes": True}


class StatutoryRequirementSummary(BaseModel):
    id: str
    act_id: str
    code: str
    title: str
    description: str
    obligation_type: str
    validity_period_months: int
    grace_period_days: int

    model_config = {"from_attributes": True}


class StatutoryRequirementDetail(StatutoryRequirementSummary):
    act_title: Optional[str] = None
    authority_code: Optional[str] = None
    rules: List[ApplicabilityRuleSummary] = []
