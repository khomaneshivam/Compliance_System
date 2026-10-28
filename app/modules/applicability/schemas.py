"""
Pydantic v2 Schemas for Regulatory Applicability Engine, Companies & Admin Rules Bench
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator


# ------------------------------------------------------------------------------
# Declarative Rule Condition Schemas
# ------------------------------------------------------------------------------

class LeafCondition(BaseModel):
    field: str = Field(..., description="Target company profile or plant fact attribute")
    operator: str = Field(..., description="Allowlisted operator (eq, gt, gte, lt, lte, in, exists, etc.)")
    value: Optional[Any] = Field(None, description="Comparison threshold or literal value")


class GroupCondition(BaseModel):
    operator: str = Field(..., description="AND, OR, or NOT")
    rules: List[Union[LeafCondition, "GroupCondition"]] = Field(..., description="Nested sub-conditions")


# ------------------------------------------------------------------------------
# Assessment & Finding Schemas
# ------------------------------------------------------------------------------

class AssessmentFindingResponse(BaseModel):
    id: str
    requirement_code: str
    requirement_title: str
    obligation_type: str
    authority_code: Optional[str] = None
    rule_version: Optional[int] = None
    evaluation_outcome: str = Field(..., description="APPLICABLE, NOT_APPLICABLE, or NEEDS_REVIEW")
    explanation: str
    matched_facts: Dict[str, Any]
    missing_facts: List[str]

    model_config = {"from_attributes": True}


class AssessmentRunResponse(BaseModel):
    id: str
    plant_id: str
    assessment_version: int
    assessed_at: datetime
    total_rules_evaluated: int
    applicable_count: int
    not_applicable_count: int
    needs_review_count: int
    profile_facts_used: Dict[str, Any]
    findings: List[AssessmentFindingResponse] = []

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Company / Plant Requirement Register & Gaps
# ------------------------------------------------------------------------------

class CompanyRequirementResponse(BaseModel):
    id: str
    requirement_code: str
    requirement_title: str
    authority_code: Optional[str] = None
    authority_name: Optional[str] = None
    act_title: Optional[str] = None
    obligation_type: str
    applicability_status: str
    applicability_rationale: str
    evidence_status: str = Field(..., description="VALID, EXPIRING_SOON, MISSING, EXPIRED, NOT_REQUIRED")
    current_due_date: Optional[date] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    rule_version: Optional[int] = None
    is_custom: bool = False
    last_evaluated_at: datetime
    matched_facts: Dict[str, Any] = {}
    missing_facts: List[str] = []

    model_config = {"from_attributes": True}


class MissingFactGap(BaseModel):
    field_name: str
    description: str
    affected_requirements: List[str]


class MissingEvidenceGap(BaseModel):
    requirement_id: str
    requirement_code: str
    requirement_title: str
    evidence_status: str
    due_date: Optional[date] = None
    authority_code: Optional[str] = None


class CompanyGapsResponse(BaseModel):
    company_id: str
    company_name: str
    missing_profile_facts: List[MissingFactGap]
    missing_or_expiring_evidence: List[MissingEvidenceGap]
    total_gaps: int


# ------------------------------------------------------------------------------
# Human-in-the-Loop Proposed Requirement Changes
# ------------------------------------------------------------------------------

class ProposedChangeResponse(BaseModel):
    id: str
    company_id: str
    requirement_code: str
    requirement_title: str
    change_type: str = Field(..., description="NEW_REQUIREMENT, STATUS_MODIFIED, DECOMMISSIONED")
    previous_status: Optional[str] = None
    proposed_status: str
    rationale: str
    review_status: str = Field(..., description="PENDING_REVIEW, APPROVED, REJECTED")
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVE or REJECT")
    review_notes: Optional[str] = Field(None, description="Justification and rationale for decision")

    @model_validator(mode="after")
    def validate_decision(self):
        if self.decision.upper() not in ("APPROVE", "REJECT"):
            raise ValueError("Decision must be either 'APPROVE' or 'REJECT'")
        return self


# ------------------------------------------------------------------------------
# Company & Profile API Schemas
# ------------------------------------------------------------------------------

class CompanyCreateRequest(BaseModel):
    name: str = Field(..., description="Company / Facility legal entity name")
    code: str = Field(..., description="Facility unique short code (e.g., MH-PUN-02)")
    jurisdiction: str = Field(..., description="State jurisdiction (e.g., Maharashtra, Gujarat)")
    district: str = Field(..., description="District location (e.g., Pune, Thane, Ahmedabad)")
    pincode: str = Field(..., description="Postal code")


class CompanyProfileUpdateRequest(BaseModel):
    industry_category: Optional[str] = Field(None, description="RED, ORANGE, GREEN, WHITE")
    sector: Optional[str] = Field(None, description="Industry sector")
    employee_count: Optional[int] = Field(None, ge=0)
    contract_labour_count: Optional[int] = Field(None, ge=0)
    built_up_area_sqm: Optional[float] = Field(None, ge=0.0)
    capital_investment_inr: Optional[float] = Field(None, ge=0.0)
    connected_power_kw: Optional[float] = Field(None, ge=0.0)
    dg_set_capacity_kva: Optional[float] = Field(None, ge=0.0)
    hazardous_waste_tpa: Optional[float] = Field(None, ge=0.0)
    effluent_discharge_kld: Optional[float] = Field(None, ge=0.0)
    boiler_count: Optional[int] = Field(None, ge=0)
    steam_capacity_tph: Optional[float] = Field(None, ge=0.0)
    activities: Optional[List[str]] = Field(None, description="Registered industrial activities")
    raw_attributes: Optional[Dict[str, Any]] = Field(None, description="Additional custom facts")


class CompanyResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    code: str
    jurisdiction: str
    district: str
    pincode: str
    profile: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Admin Rule Bench Schemas
# ------------------------------------------------------------------------------

class RuleCreateRequest(BaseModel):
    statutory_requirement_code: str = Field(..., description="Code of requirement this rule governs (e.g. MPCB-CTO)")
    expression_ast: Dict[str, Any] = Field(..., description="Declarative boolean AST")
    pass_explanation_template: str = Field(..., description="Template interpolated when rule evaluates to TRUE")
    fail_explanation_template: str = Field(..., description="Template interpolated when rule evaluates to FALSE")
    effective_from: Optional[date] = Field(default_factory=date.today)
    change_rationale: Optional[str] = Field(None, description="Regulatory rationale for this rule version")


class RuleResponse(BaseModel):
    id: str
    statutory_requirement_id: str
    statutory_requirement_code: Optional[str] = None
    rule_version: int
    status: str
    expression_ast: Dict[str, Any]
    pass_explanation_template: str
    fail_explanation_template: str
    is_immutable: bool
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    change_rationale: Optional[str] = None
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RuleSupersedeRequest(BaseModel):
    new_expression_ast: Dict[str, Any] = Field(..., description="New version boolean AST")
    pass_explanation_template: str
    fail_explanation_template: str
    change_rationale: str = Field(..., description="Mandatory rationale for why this rule supersedes previous version")
    effective_from: Optional[date] = Field(default_factory=date.today)


# ------------------------------------------------------------------------------
# Company Profile Reassessment & What-Changed Simulation Schemas
# ------------------------------------------------------------------------------

class ProfileAttributeDiff(BaseModel):
    field_name: str
    previous_value: Any
    proposed_value: Any


class ProposedRequirementDiffItem(BaseModel):
    requirement_code: str
    requirement_title: str
    authority_code: Optional[str] = None
    obligation_type: str
    previous_status: str
    projected_status: str
    reason: str
    impact_type: str  # NEWLY_APPLICABLE, NO_LONGER_APPLICABLE, STATUS_CHANGE, UNCHANGED


class ProfileReassessmentSimulationResponse(BaseModel):
    plant_id: str
    attribute_changes: List[ProfileAttributeDiff]
    newly_applicable_count: int
    no_longer_applicable_count: int
    unchanged_applicable_count: int
    needs_review_count: int
    impacted_requirements: List[ProposedRequirementDiffItem]
    summary_guidance: str


class ProfileReassessmentApplyRequest(BaseModel):
    profile_updates: CompanyProfileUpdateRequest
    auto_approve_changes: bool = Field(False, description="Automatically accept newly applicable baseline requirements")
    rationale: Optional[str] = Field(None, description="Operational rationale for profile change")


class ProfileReassessmentApplyResponse(BaseModel):
    plant_id: str
    simulation_diff: ProfileReassessmentSimulationResponse
    assessment_run: AssessmentRunResponse
