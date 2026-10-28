"""
Company & Applicability Engine Endpoints (/api/v1/companies)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError, TenantAccessDeniedError, ConflictError
from app.models.tenancy import User, Plant
from app.models.profile import PlantProfile
from app.models.requirements import PlantRequirement
from app.modules.identity_access.services import get_current_user, require_roles
from app.modules.applicability.schemas import (
    CompanyCreateRequest,
    CompanyProfileUpdateRequest,
    CompanyResponse,
    AssessmentRunResponse,
    AssessmentFindingResponse,
    CompanyRequirementResponse,
    CompanyGapsResponse,
    ProposedChangeResponse,
    ReviewDecisionRequest,
    ProfileReassessmentSimulationResponse,
    ProfileReassessmentApplyRequest,
    ProfileReassessmentApplyResponse,
)
from app.modules.applicability.services import (
    run_applicability_assessment,
    get_company_requirements,
    get_company_gaps,
    review_proposed_change,
    simulate_profile_reassessment,
)
from app.models.tasks import AuditLog
from app.models.assessments import ProposedRequirementChange

router = APIRouter(prefix="/companies", tags=["Companies & Applicability Engine"])


def resolve_company_plant(db: Session, company_id: str, user: User) -> Plant:
    """
    Resolves company_id to the authorized manufacturing plant facility within the tenant.
    Enforces strict server-side tenant isolation.
    """
    plant = db.get(Plant, company_id)
    if not plant:
        # Check if company_id is tenant_id, then resolve to first plant of that tenant
        plant = db.scalars(
            select(Plant).where(Plant.tenant_id == company_id)
        ).first()

    if not plant:
        raise EntityNotFoundError("Company", company_id)

    if plant.tenant_id != user.tenant_id and user.role != "SUPER_ADMIN":
        raise TenantAccessDeniedError("Access denied: facility belongs to another organization.")

    return plant


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company_facility(
    request: CompanyCreateRequest,
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER"])),
    db: Session = Depends(get_db),
):
    """Registers a new manufacturing plant facility under the authenticated tenant organization."""
    # Check code uniqueness
    existing = db.scalars(select(Plant).where(Plant.code == request.code)).first()
    if existing:
        raise ConflictError(f"Facility with code '{request.code}' already exists.")

    plant = Plant(
        tenant_id=current_user.tenant_id,
        name=request.name,
        code=request.code,
        jurisdiction=request.jurisdiction,
        district=request.district,
        pincode=request.pincode,
    )
    db.add(plant)
    db.flush()

    # Initialize empty profile
    profile = PlantProfile(
        plant_id=plant.id,
        industry_category="WHITE",
        sector="General Manufacturing",
        employee_count=0,
        contract_labour_count=0,
        boiler_count=0,
    )
    db.add(profile)
    db.commit()
    db.refresh(plant)

    return CompanyResponse(
        id=plant.id,
        tenant_id=plant.tenant_id,
        name=plant.name,
        code=plant.code,
        jurisdiction=plant.jurisdiction,
        district=plant.district,
        pincode=plant.pincode,
        profile={"industry_category": profile.industry_category},
    )


@router.patch("/{company_id}/profile", response_model=CompanyResponse)
def update_company_profile(
    company_id: str,
    request: CompanyProfileUpdateRequest,
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
    db: Session = Depends(get_db),
):
    """Updates operational facts and manufacturing parameters for applicability evaluation."""
    plant = resolve_company_plant(db, company_id, current_user)
    
    profile_stmt = select(PlantProfile).where(PlantProfile.plant_id == plant.id)
    profile = db.scalars(profile_stmt).first()
    if not profile:
        profile = PlantProfile(plant_id=plant.id)
        db.add(profile)

    update_dict = request.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        if k == "activities":
            raw = profile.raw_attributes or {}
            raw["activities"] = v
            profile.raw_attributes = raw
        elif hasattr(profile, k):
            setattr(profile, k, v)

    db.commit()
    db.refresh(plant)
    db.refresh(profile)

    return CompanyResponse(
        id=plant.id,
        tenant_id=plant.tenant_id,
        name=plant.name,
        code=plant.code,
        jurisdiction=plant.jurisdiction,
        district=plant.district,
        pincode=plant.pincode,
        profile={
            "industry_category": profile.industry_category,
            "employee_count": profile.employee_count,
            "boiler_count": profile.boiler_count,
            "hazardous_waste_tpa": float(profile.hazardous_waste_tpa or 0.0),
            "steam_capacity_tph": float(profile.steam_capacity_tph or 0.0),
        },
    )


@router.post("/{company_id}/assessments", response_model=AssessmentRunResponse)
def run_assessment(
    company_id: str,
    auto_approve_initial: bool = Query(False, description="Automatically accept initial baseline obligations"),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
    db: Session = Depends(get_db),
):
    """
    Executes the deterministic regulatory applicability engine against company operational facts.
    Returns explainable outcomes and queues proposed changes for reviewer confirmation.
    """
    plant = resolve_company_plant(db, company_id, current_user)
    assessment_run = run_applicability_assessment(
        db,
        plant,
        evaluated_by_user_id=current_user.id,
        auto_approve_initial=auto_approve_initial,
    )

    findings_response = [
        AssessmentFindingResponse(
            id=f.id,
            requirement_code=f.statutory_requirement.code if f.statutory_requirement else "UNKNOWN",
            requirement_title=f.statutory_requirement.title if f.statutory_requirement else "Unknown Obligation",
            obligation_type=f.statutory_requirement.obligation_type if f.statutory_requirement else "CONSENT",
            authority_code=f.statutory_requirement.act.authority.code if (f.statutory_requirement and f.statutory_requirement.act and f.statutory_requirement.act.authority) else None,
            rule_version=f.rule_version.rule_version if f.rule_version else 1,
            evaluation_outcome=f.evaluation_outcome,
            explanation=f.explanation,
            matched_facts=f.matched_facts,
            missing_facts=f.missing_facts,
        )
        for f in assessment_run.findings
    ]

    return AssessmentRunResponse(
        id=assessment_run.id,
        plant_id=assessment_run.plant_id,
        assessment_version=assessment_run.assessment_version,
        assessed_at=assessment_run.assessed_at,
        total_rules_evaluated=assessment_run.total_rules_evaluated,
        applicable_count=assessment_run.applicable_count,
        not_applicable_count=assessment_run.not_applicable_count,
        needs_review_count=assessment_run.needs_review_count,
        profile_facts_used=assessment_run.profile_snapshot,
        findings=findings_response,
    )


@router.get("/{company_id}/requirements", response_model=List[CompanyRequirementResponse])
def list_company_requirements(
    company_id: str,
    status: Optional[str] = Query(None, description="Filter by APPLICABLE, NOT_APPLICABLE, NEEDS_REVIEW"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists company statutory obligations with evidence status, renewal dates, and rationale."""
    plant = resolve_company_plant(db, company_id, current_user)
    return get_company_requirements(db, plant, status_filter=status)


@router.get("/{company_id}/requirements/{requirement_id}", response_model=CompanyRequirementResponse)
def get_company_requirement_detail(
    company_id: str,
    requirement_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves single obligation details with evidence linkage and applicability rationale."""
    plant = resolve_company_plant(db, company_id, current_user)
    
    # Try finding by PlantRequirement.id or by StatutoryRequirement.id / code
    ob = db.get(PlantRequirement, requirement_id)
    if not ob or ob.plant_id != plant.id:
        # Search by statutory_requirement_id or code
        stmt = (
            select(PlantRequirement)
            .join(PlantRequirement.statutory_requirement)
            .where(
                PlantRequirement.plant_id == plant.id,
                (PlantRequirement.statutory_requirement_id == requirement_id)
                | (PlantRequirement.statutory_requirement.has(code=requirement_id)),
            )
        )
        ob = db.scalars(stmt).first()

    if not ob:
        raise EntityNotFoundError("CompanyRequirement", requirement_id)

    req = ob.statutory_requirement
    act = req.act if req else None
    auth = act.authority if act else None

    return CompanyRequirementResponse(
        id=ob.id,
        requirement_code=req.code if req else "UNKNOWN",
        requirement_title=req.title if req else "Unknown Obligation",
        authority_code=auth.code if auth else None,
        authority_name=auth.name if auth else None,
        act_title=act.title if act else None,
        obligation_type=req.obligation_type if req else "CERTIFICATE",
        applicability_status=ob.applicability_status,
        applicability_rationale=ob.applicability_rationale,
        evidence_status=ob.evidence_status,
        current_due_date=ob.current_due_date,
        owner_name=ob.owner.full_name if ob.owner else None,
        owner_email=ob.owner.email if ob.owner else None,
        rule_version=1,
        is_custom=ob.is_custom,
        last_evaluated_at=ob.last_evaluated_at,
    )


@router.get("/{company_id}/gaps", response_model=CompanyGapsResponse)
def get_compliance_gaps(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Summarizes missing profile facts and missing/expiring evidence into actionable gaps."""
    plant = resolve_company_plant(db, company_id, current_user)
    return get_company_gaps(db, plant)


@router.get("/{company_id}/changes", response_model=List[ProposedChangeResponse])
def list_proposed_changes(
    company_id: str,
    review_status: str = Query("PENDING_REVIEW", description="PENDING_REVIEW, APPROVED, REJECTED"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists proposed register changes awaiting human reviewer approval."""
    plant = resolve_company_plant(db, company_id, current_user)
    stmt = (
        select(ProposedRequirementChange)
        .where(
            ProposedRequirementChange.plant_id == plant.id,
            ProposedRequirementChange.review_status == review_status.upper(),
        )
        .order_by(ProposedRequirementChange.created_at.desc())
    )
    changes = list(db.scalars(stmt).all())

    return [
        ProposedChangeResponse(
            id=c.id,
            company_id=c.plant_id,
            requirement_code=c.statutory_requirement.code if c.statutory_requirement else "UNKNOWN",
            requirement_title=c.statutory_requirement.title if c.statutory_requirement else "Unknown Obligation",
            change_type=c.change_type,
            previous_status=c.previous_status,
            proposed_status=c.proposed_status,
            rationale=c.rationale,
            review_status=c.review_status,
            created_at=c.created_at,
            reviewed_at=c.reviewed_at,
            review_notes=c.review_notes,
        )
        for c in changes
    ]


@router.post("/{company_id}/changes/{change_id}/review", response_model=ProposedChangeResponse)
def decide_proposed_change(
    company_id: str,
    change_id: str,
    request: ReviewDecisionRequest,
    current_user: User = Depends(require_roles(["ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
    db: Session = Depends(get_db),
):
    """Approves or rejects a proposed obligation change, updating the active register upon approval."""
    plant = resolve_company_plant(db, company_id, current_user)
    change = review_proposed_change(
        db,
        change_id,
        decision=request.decision,
        user=current_user,
        review_notes=request.review_notes,
    )
    return ProposedChangeResponse(
        id=change.id,
        company_id=change.plant_id,
        requirement_code=change.statutory_requirement.code if change.statutory_requirement else "UNKNOWN",
        requirement_title=change.statutory_requirement.title if change.statutory_requirement else "Unknown Obligation",
        change_type=change.change_type,
        previous_status=change.previous_status,
        proposed_status=change.proposed_status,
        rationale=change.rationale,
        review_status=change.review_status,
        created_at=change.created_at,
        reviewed_at=change.reviewed_at,
        review_notes=change.review_notes,
    )


@router.post(
    "/{company_id}/simulate-reassessment",
    response_model=ProfileReassessmentSimulationResponse,
    summary="Simulate Profile Update Reassessment",
)
def simulate_reassessment_endpoint(
    company_id: str,
    request: CompanyProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dry-run simulation: Evaluates the regulatory applicability engine against proposed
    profile attributes, returning a "what changed" diff of newly applicable and exempt obligations
    without mutating the active facility database records.
    """
    plant = resolve_company_plant(db, company_id, current_user)
    return simulate_profile_reassessment(db=db, plant=plant, proposed_updates=request)


@router.put(
    "/{company_id}/profile-with-reassessment",
    response_model=ProfileReassessmentApplyResponse,
    summary="Apply Profile Updates with Proposed Reassessment",
)
def update_profile_with_reassessment_endpoint(
    company_id: str,
    request: ProfileReassessmentApplyRequest,
    current_user: User = Depends(require_roles(["ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
    db: Session = Depends(get_db),
):
    """
    Applies confirmed facility operational updates, triggers an official applicability reassessment,
    records an audit log entry, and returns both the simulation diff and the new assessment run.
    """
    plant = resolve_company_plant(db, company_id, current_user)

    # 1. Compute simulation diff first
    sim_diff = simulate_profile_reassessment(db=db, plant=plant, proposed_updates=request.profile_updates)

    # 2. Apply profile updates to DB
    profile = db.scalars(select(PlantProfile).where(PlantProfile.plant_id == plant.id)).first()
    if not profile:
        profile = PlantProfile(plant_id=plant.id)
        db.add(profile)

    update_dict = request.profile_updates.model_dump(exclude_unset=True)
    prev_state = {
        "industry_category": profile.industry_category,
        "employee_count": profile.employee_count,
        "boiler_count": profile.boiler_count,
        "hazardous_waste_tpa": float(profile.hazardous_waste_tpa or 0.0),
        "steam_capacity_tph": float(profile.steam_capacity_tph or 0.0),
    }

    for k, v in update_dict.items():
        if k == "activities":
            raw = profile.raw_attributes or {}
            raw["activities"] = v
            profile.raw_attributes = raw
        elif hasattr(profile, k):
            setattr(profile, k, v)

    db.commit()
    db.refresh(profile)

    # 3. Run real assessment
    assessment_run = run_applicability_assessment(
        db=db,
        plant=plant,
        evaluated_by_user_id=current_user.id,
        auto_approve_initial=request.auto_approve_changes,
    )

    # 4. Record audit log
    audit_entry = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PROFILE_REASSESSMENT_APPLIED",
        entity_type="PLANT_PROFILE",
        entity_id=plant.id,
        previous_state=prev_state,
        new_state={
            "updated_attributes": update_dict,
            "newly_applicable_count": sim_diff.newly_applicable_count,
            "exempt_count": sim_diff.no_longer_applicable_count,
            "rationale": request.rationale,
        },
    )
    db.add(audit_entry)
    db.commit()

    findings_response = [
        AssessmentFindingResponse(
            id=f.id,
            requirement_code=f.statutory_requirement.code if f.statutory_requirement else "UNKNOWN",
            requirement_title=f.statutory_requirement.title if f.statutory_requirement else "Unknown Obligation",
            obligation_type=f.statutory_requirement.obligation_type if f.statutory_requirement else "CONSENT",
            authority_code=f.statutory_requirement.act.authority.code if (f.statutory_requirement and f.statutory_requirement.act and f.statutory_requirement.act.authority) else None,
            rule_version=f.rule_version.rule_version if f.rule_version else 1,
            evaluation_outcome=f.evaluation_outcome,
            explanation=f.explanation,
            matched_facts=f.matched_facts,
            missing_facts=f.missing_facts,
        )
        for f in assessment_run.findings
    ]

    run_resp = AssessmentRunResponse(
        id=assessment_run.id,
        plant_id=assessment_run.plant_id,
        assessment_version=assessment_run.assessment_version,
        assessed_at=assessment_run.assessed_at,
        total_rules_evaluated=assessment_run.total_rules_evaluated,
        applicable_count=assessment_run.applicable_count,
        not_applicable_count=assessment_run.not_applicable_count,
        needs_review_count=assessment_run.needs_review_count,
        profile_facts_used=assessment_run.profile_snapshot,
        findings=findings_response,
    )

    return ProfileReassessmentApplyResponse(
        plant_id=plant.id,
        simulation_diff=sim_diff,
        assessment_run=run_resp,
    )
