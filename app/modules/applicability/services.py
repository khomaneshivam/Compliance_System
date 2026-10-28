"""
Regulatory Applicability Engine Service Layer
Orchestrates fact assembly, deterministic AST evaluation, assessment runs,
change reviews, gap analysis, and admin rule versioning.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.core.exceptions import (
    EntityNotFoundError,
    TenantAccessDeniedError,
    ConflictError,
    ImmutableRecordError,
)
from app.core.audit import record_audit_log
from app.models.tenancy import Plant, User
from app.models.profile import PlantProfile, PlantEquipment
from app.models.catalog import (
    StatutoryRequirement,
    ApplicabilityRule,
    RegulatoryAct,
    RegulatoryAuthority,
)
from app.models.master_data import Jurisdiction
from app.models.requirements import PlantRequirement, EvidenceLink
from app.models.assessments import (
    AssessmentRun,
    AssessmentFinding,
    ProposedRequirementChange,
)
from app.modules.applicability.engine import engine, EvalResult
from app.modules.applicability.schemas import (
    CompanyRequirementResponse,
    CompanyGapsResponse,
    MissingFactGap,
    MissingEvidenceGap,
    RuleCreateRequest,
    RuleSupersedeRequest,
    CompanyProfileUpdateRequest,
    ProfileAttributeDiff,
    ProposedRequirementDiffItem,
    ProfileReassessmentSimulationResponse,
)


def assemble_company_facts(db: Session, plant: Plant) -> Dict[str, Any]:
    """
    Gathers all operational parameters from plant facility, operational profile, and equipment.
    Computes derived indicators (total workers, equipment presence).
    """
    facts: Dict[str, Any] = {
        "jurisdiction": plant.jurisdiction,
        "district": plant.district,
        "pincode": plant.pincode,
        "plant_name": plant.name,
        "plant_code": plant.code,
    }

    # Fetch profile
    profile_stmt = select(PlantProfile).where(PlantProfile.plant_id == plant.id)
    profile = db.scalars(profile_stmt).first()

    if profile:
        facts.update({
            "industry_category": profile.industry_category,
            "sector": profile.sector,
            "employee_count": profile.employee_count,
            "contract_labour_count": profile.contract_labour_count,
            "total_workers": (profile.employee_count or 0) + (profile.contract_labour_count or 0),
            "built_up_area_sqm": float(profile.built_up_area_sqm or 0.0),
            "capital_investment_inr": float(profile.capital_investment_inr or 0.0),
            "connected_power_kw": float(profile.connected_power_kw or 0.0),
            "dg_set_capacity_kva": float(profile.dg_set_capacity_kva or 0.0),
            "hazardous_waste_tpa": float(profile.hazardous_waste_tpa or 0.0),
            "effluent_discharge_kld": float(profile.effluent_discharge_kld or 0.0),
            "boiler_count": profile.boiler_count or 0,
            "steam_capacity_tph": float(profile.steam_capacity_tph or 0.0),
        })
        if profile.raw_attributes:
            facts.update(profile.raw_attributes)

    # Equipment facts
    equip_stmt = select(PlantEquipment).where(PlantEquipment.plant_id == plant.id)
    equipment_items = list(db.scalars(equip_stmt).all())
    equipment_types = [e.equipment_type for e in equipment_items]
    facts["equipment_types"] = equipment_types
    facts["has_boiler"] = "BOILER" in equipment_types or facts.get("boiler_count", 0) > 0
    facts["has_dg_set"] = "DG_SET" in equipment_types or facts.get("dg_set_capacity_kva", 0) > 0
    facts["has_etp"] = "ETP" in equipment_types or facts.get("effluent_discharge_kld", 0) > 0

    return facts


def run_applicability_assessment(
    db: Session,
    plant: Plant,
    evaluated_by_user_id: Optional[str] = None,
    assessment_date: Optional[date] = None,
    auto_approve_initial: bool = False,
) -> AssessmentRun:
    """
    Executes the deterministic applicability evaluation engine for a plant.
    Respects jurisdiction, active dates, and rule approval status.
    Generates explainable findings and queues proposed changes without silently altering active registers.
    """
    check_date = assessment_date or date.today()
    facts = assemble_company_facts(db, plant)

    # Calculate monotonic assessment run version
    version_stmt = select(func.coalesce(func.max(AssessmentRun.assessment_version), 0)).where(
        AssessmentRun.plant_id == plant.id
    )
    next_version = (db.scalar(version_stmt) or 0) + 1

    assessment_run = AssessmentRun(
        plant_id=plant.id,
        tenant_id=plant.tenant_id,
        assessment_version=next_version,
        assessed_at=datetime.now(timezone.utc),
        evaluated_by_user_id=evaluated_by_user_id,
        profile_snapshot=facts,
        total_rules_evaluated=0,
        applicable_count=0,
        not_applicable_count=0,
        needs_review_count=0,
    )
    db.add(assessment_run)
    db.flush()

    # Fetch all statutory requirements
    reqs_stmt = select(StatutoryRequirement).order_by(StatutoryRequirement.code)
    requirements = list(db.scalars(reqs_stmt).all())

    # Map existing active obligations
    existing_obligations_stmt = select(PlantRequirement).where(PlantRequirement.plant_id == plant.id)
    existing_obligations = {
        ob.statutory_requirement_id: ob for ob in db.scalars(existing_obligations_stmt).all()
    }

    total_evaluated = 0
    applicable_count = 0
    not_applicable_count = 0
    needs_review_count = 0

    for req in requirements:
        # Fetch active, effective rule for this requirement
        rule_stmt = select(ApplicabilityRule).where(
            and_(
                ApplicabilityRule.statutory_requirement_id == req.id,
                ApplicabilityRule.status == "ACTIVE",
                ApplicabilityRule.effective_from <= check_date,
            )
        ).order_by(ApplicabilityRule.rule_version.desc())
        
        # Filter for active dates
        candidate_rules = list(db.scalars(rule_stmt).all())
        active_rule = None
        for r in candidate_rules:
            if r.effective_to is None or r.effective_to >= check_date:
                active_rule = r
                break

        if not active_rule:
            continue

        total_evaluated += 1

        # 1. Check Jurisdiction Compatibility
        jurisdiction_match = True
        jurisdiction_explanation = ""
        if req.act and req.act.jurisdiction_id:
            jurisdiction = db.get(Jurisdiction, req.act.jurisdiction_id)
            if jurisdiction and jurisdiction.level != "CENTRAL":
                plant_j = str(plant.jurisdiction).strip().lower()
                act_j = str(jurisdiction.name).strip().lower()
                act_code = str(jurisdiction.code).strip().lower()
                if act_j not in plant_j and plant_j not in act_j and act_code not in plant_j:
                    jurisdiction_match = False
                    jurisdiction_explanation = (
                        f"Governed under {jurisdiction.name} jurisdiction ({jurisdiction.code}); "
                        f"not applicable to facility operating in {plant.jurisdiction}."
                    )

        if not jurisdiction_match:
            outcome_status = "NOT_APPLICABLE"
            explanation = jurisdiction_explanation
            matched = {}
            missing = []
            trace = {"jurisdiction_check": "MISMATCH", "plant_jurisdiction": plant.jurisdiction}
            not_applicable_count += 1
        else:
            # 2. Evaluate AST through engine
            eval_result = engine.evaluate_rule(
                active_rule.expression_ast,
                facts,
                pass_template=active_rule.pass_explanation_template,
                fail_template=active_rule.fail_explanation_template,
            )
            outcome_status = eval_result.status
            explanation = eval_result.explanation
            matched = eval_result.matched_facts
            missing = eval_result.missing_facts
            trace = eval_result.condition_trace

            if outcome_status == "APPLICABLE":
                applicable_count += 1
            elif outcome_status == "NOT_APPLICABLE":
                not_applicable_count += 1
            else:
                needs_review_count += 1

        # Record Finding
        finding = AssessmentFinding(
            assessment_run_id=assessment_run.id,
            statutory_requirement_id=req.id,
            rule_version_id=active_rule.id if active_rule else None,
            evaluation_outcome=outcome_status,
            explanation=explanation,
            matched_facts=matched,
            missing_facts=missing,
            condition_results=trace,
        )
        db.add(finding)

        # 3. Handle Active Register & Proposed Changes (No silent overwriting)
        existing = existing_obligations.get(req.id)
        if not existing:
            # New requirement discovered
            if auto_approve_initial and outcome_status == "APPLICABLE":
                new_obligation = PlantRequirement(
                    plant_id=plant.id,
                    statutory_requirement_id=req.id,
                    rule_version_id=active_rule.id,
                    applicability_status=outcome_status,
                    applicability_rationale=explanation,
                    evidence_status="MISSING",
                    last_evaluated_at=datetime.now(timezone.utc),
                )
                db.add(new_obligation)
            else:
                # Propose new requirement change for human review
                change = ProposedRequirementChange(
                    plant_id=plant.id,
                    statutory_requirement_id=req.id,
                    assessment_run_id=assessment_run.id,
                    rule_version_id=active_rule.id,
                    change_type="NEW_REQUIREMENT",
                    previous_status=None,
                    proposed_status=outcome_status,
                    rationale=explanation,
                    review_status="PENDING_REVIEW",
                )
                db.add(change)
        else:
            # Existing obligation: check if status changed
            if existing.applicability_status != outcome_status:
                change = ProposedRequirementChange(
                    plant_id=plant.id,
                    statutory_requirement_id=req.id,
                    assessment_run_id=assessment_run.id,
                    rule_version_id=active_rule.id,
                    change_type="STATUS_MODIFIED",
                    previous_status=existing.applicability_status,
                    proposed_status=outcome_status,
                    rationale=explanation,
                    review_status="PENDING_REVIEW",
                )
                db.add(change)
            else:
                # Status unchanged: refresh evaluation timestamp and rule link
                existing.last_evaluated_at = datetime.now(timezone.utc)
                existing.rule_version_id = active_rule.id

    # Update summary counts
    assessment_run.total_rules_evaluated = total_evaluated
    assessment_run.applicable_count = applicable_count
    assessment_run.not_applicable_count = not_applicable_count
    assessment_run.needs_review_count = needs_review_count

    db.commit()
    db.refresh(assessment_run)
    return assessment_run


def get_company_requirements(
    db: Session,
    plant: Plant,
    status_filter: Optional[str] = None,
) -> List[CompanyRequirementResponse]:
    """Retrieves all evaluated company obligations with calculated evidence statuses."""
    stmt = (
        select(PlantRequirement)
        .where(PlantRequirement.plant_id == plant.id)
        .order_by(PlantRequirement.current_due_date.asc().nulls_last())
    )
    if status_filter:
        stmt = stmt.where(PlantRequirement.applicability_status == status_filter.upper())

    obligations = list(db.scalars(stmt).all())
    today = date.today()
    results = []

    for ob in obligations:
        req = ob.statutory_requirement
        act = req.act if req else None
        auth = act.authority if act else None
        owner = ob.owner

        # Calculate evidence status deterministically
        evidence_status = ob.evidence_status
        if ob.current_due_date and ob.applicability_status == "APPLICABLE":
            grace_days = req.grace_period_days if req else 30
            warning_window = today + timedelta(days=grace_days)
            if ob.current_due_date < today:
                evidence_status = "EXPIRED"
            elif ob.current_due_date <= warning_window:
                evidence_status = "EXPIRING_SOON"

        results.append(
            CompanyRequirementResponse(
                id=ob.id,
                requirement_code=req.code if req else "UNKNOWN",
                requirement_title=req.title if req else "Unknown Obligation",
                authority_code=auth.code if auth else None,
                authority_name=auth.name if auth else None,
                act_title=act.title if act else None,
                obligation_type=req.obligation_type if req else "CERTIFICATE",
                applicability_status=ob.applicability_status,
                applicability_rationale=ob.applicability_rationale,
                evidence_status=evidence_status,
                current_due_date=ob.current_due_date,
                owner_name=owner.full_name if owner else None,
                owner_email=owner.email if owner else None,
                rule_version=1,
                is_custom=ob.is_custom,
                last_evaluated_at=ob.last_evaluated_at,
            )
        )

    return results


def get_company_gaps(db: Session, plant: Plant) -> CompanyGapsResponse:
    """Aggregates missing profile facts and missing/expiring evidence into an actionable gap report."""
    # 1. Missing Facts from latest assessment
    latest_run_stmt = (
        select(AssessmentRun)
        .where(AssessmentRun.plant_id == plant.id)
        .order_by(AssessmentRun.assessment_version.desc())
    )
    latest_run = db.scalars(latest_run_stmt).first()

    missing_fact_map: Dict[str, List[str]] = {}
    if latest_run:
        findings_stmt = select(AssessmentFinding).where(
            and_(
                AssessmentFinding.assessment_run_id == latest_run.id,
                AssessmentFinding.evaluation_outcome == "NEEDS_REVIEW",
            )
        )
        for finding in db.scalars(findings_stmt).all():
            req_code = finding.statutory_requirement.code if finding.statutory_requirement else "UNKNOWN"
            for fact in finding.missing_facts:
                if fact not in missing_fact_map:
                    missing_fact_map[fact] = []
                missing_fact_map[fact].append(req_code)

    missing_fact_gaps = [
        MissingFactGap(
            field_name=fact,
            description=f"Operational parameter '{fact}' is required to evaluate statutory obligations.",
            affected_requirements=reqs,
        )
        for fact, reqs in missing_fact_map.items()
    ]

    # 2. Missing or Expiring Evidence
    ob_stmt = select(PlantRequirement).where(
        and_(
            PlantRequirement.plant_id == plant.id,
            PlantRequirement.applicability_status == "APPLICABLE",
            PlantRequirement.evidence_status.in_(["MISSING", "EXPIRING_SOON", "EXPIRED"]),
        )
    )
    evidence_gaps = [
        MissingEvidenceGap(
            requirement_id=ob.id,
            requirement_code=ob.statutory_requirement.code if ob.statutory_requirement else "UNKNOWN",
            requirement_title=ob.statutory_requirement.title if ob.statutory_requirement else "Unknown Obligation",
            evidence_status=ob.evidence_status,
            due_date=ob.current_due_date,
            authority_code=ob.statutory_requirement.act.authority.code if (ob.statutory_requirement and ob.statutory_requirement.act and ob.statutory_requirement.act.authority) else None,
        )
        for ob in db.scalars(ob_stmt).all()
    ]

    return CompanyGapsResponse(
        company_id=plant.id,
        company_name=plant.name,
        missing_profile_facts=missing_fact_gaps,
        missing_or_expiring_evidence=evidence_gaps,
        total_gaps=len(missing_fact_gaps) + len(evidence_gaps),
    )


def review_proposed_change(
    db: Session,
    change_id: str,
    decision: str,
    user: User,
    review_notes: Optional[str] = None,
) -> ProposedRequirementChange:
    """
    Applies a human review decision to a proposed register change.
    Updates the active PlantRequirement upon approval.
    """
    change = db.get(ProposedRequirementChange, change_id)
    if not change:
        raise EntityNotFoundError("ProposedRequirementChange", change_id)

    plant = db.get(Plant, change.plant_id)
    if not plant or plant.tenant_id != user.tenant_id and user.role != "SUPER_ADMIN":
        raise TenantAccessDeniedError("Access denied to proposed requirement change.")

    now = datetime.now(timezone.utc)
    clean_decision = decision.upper().strip()

    if clean_decision == "APPROVE":
        change.review_status = "APPROVED"
        change.reviewed_by_user_id = user.id
        change.reviewed_at = now
        change.review_notes = review_notes

        # Upsert active PlantRequirement
        stmt = select(PlantRequirement).where(
            and_(
                PlantRequirement.plant_id == change.plant_id,
                PlantRequirement.statutory_requirement_id == change.statutory_requirement_id,
            )
        )
        existing = db.scalars(stmt).first()
        if existing:
            existing.applicability_status = change.proposed_status
            existing.applicability_rationale = change.rationale
            existing.rule_version_id = change.rule_version_id
            existing.last_evaluated_at = now
        else:
            new_req = PlantRequirement(
                plant_id=change.plant_id,
                statutory_requirement_id=change.statutory_requirement_id,
                rule_version_id=change.rule_version_id,
                applicability_status=change.proposed_status,
                applicability_rationale=change.rationale,
                evidence_status="MISSING",
                last_evaluated_at=now,
            )
            db.add(new_req)

        record_audit_log(
            db,
            tenant_id=plant.tenant_id,
            user_id=user.id,
            action="APPROVE_REQUIREMENT_CHANGE",
            entity_type="PlantRequirement",
            entity_id=change.statutory_requirement_id,
            new_state={"status": change.proposed_status, "change_id": change.id},
            previous_state={"previous_status": change.previous_status},
        )
    else:
        change.review_status = "REJECTED"
        change.reviewed_by_user_id = user.id
        change.reviewed_at = now
        change.review_notes = review_notes

        record_audit_log(
            db,
            tenant_id=plant.tenant_id,
            user_id=user.id,
            action="REJECT_REQUIREMENT_CHANGE",
            entity_type="ProposedRequirementChange",
            entity_id=change.id,
            new_state={"decision": "REJECTED", "notes": review_notes},
        )

    db.commit()
    db.refresh(change)
    return change


# ------------------------------------------------------------------------------
# Admin Rule Bench Services
# ------------------------------------------------------------------------------

def list_rules(
    db: Session,
    requirement_code: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[ApplicabilityRule]:
    """Lists rules with version and status."""
    stmt = select(ApplicabilityRule).order_by(ApplicabilityRule.rule_version.desc())
    if requirement_code:
        req = db.scalars(
            select(StatutoryRequirement).where(StatutoryRequirement.code == requirement_code)
        ).first()
        if req:
            stmt = stmt.where(ApplicabilityRule.statutory_requirement_id == req.id)
    if status_filter:
        stmt = stmt.where(ApplicabilityRule.status == status_filter.upper())
    return list(db.scalars(stmt).all())


def create_rule_version(db: Session, request: RuleCreateRequest, user: User) -> ApplicabilityRule:
    """Creates a new rule version in PROPOSED status with full provenance."""
    req = db.scalars(
        select(StatutoryRequirement).where(StatutoryRequirement.code == request.statutory_requirement_code)
    ).first()
    if not req:
        raise EntityNotFoundError("StatutoryRequirement", request.statutory_requirement_code)

    version_stmt = select(func.coalesce(func.max(ApplicabilityRule.rule_version), 0)).where(
        ApplicabilityRule.statutory_requirement_id == req.id
    )
    next_ver = (db.scalar(version_stmt) or 0) + 1

    rule = ApplicabilityRule(
        statutory_requirement_id=req.id,
        rule_version=next_ver,
        expression_ast=request.expression_ast,
        pass_explanation_template=request.pass_explanation_template,
        fail_explanation_template=request.fail_explanation_template,
        status="PROPOSED",
        effective_from=request.effective_from or date.today(),
        change_rationale=request.change_rationale,
        is_immutable=False,
        publication_date=request.publication_date,
        instrument_identifier=request.instrument_identifier,
        clause_reference=request.clause_reference,
        official_source_url=request.official_source_url,
        source_document_id=request.source_document_id,
        source_fingerprint=request.source_fingerprint,
        source_verification_status=request.source_verification_status or "PROPOSED",
    )
    db.add(rule)
    db.flush()

    record_audit_log(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="RULE_PROPOSED",
        entity_type="ApplicabilityRule",
        entity_id=rule.id,
        new_state={
            "rule_version": rule.rule_version,
            "statutory_requirement_code": req.code,
            "change_rationale": rule.change_rationale,
            "instrument_identifier": rule.instrument_identifier,
        },
    )

    db.commit()
    db.refresh(rule)
    return rule


def approve_rule(db: Session, rule_id: str, user: User) -> ApplicabilityRule:
    """Approves a proposed rule version, locking it as immutable with audit provenance."""
    rule = db.get(ApplicabilityRule, rule_id)
    if not rule:
        raise EntityNotFoundError("ApplicabilityRule", rule_id)

    if rule.is_immutable and rule.status == "ACTIVE":
        raise ImmutableRecordError("ApplicabilityRule", rule.rule_version)

    # Supersede older active versions of the same statutory requirement
    old_active_stmt = select(ApplicabilityRule).where(
        and_(
            ApplicabilityRule.statutory_requirement_id == rule.statutory_requirement_id,
            ApplicabilityRule.id != rule.id,
            ApplicabilityRule.status == "ACTIVE",
        )
    )
    for old_rule in db.scalars(old_active_stmt).all():
        old_rule.status = "SUPERSEDED"
        old_rule.effective_to = rule.effective_from or date.today()

    rule.status = "ACTIVE"
    rule.is_immutable = True
    rule.approved_by_user_id = user.id
    rule.approved_at = datetime.now(timezone.utc)
    if rule.source_verification_status in ("PROPOSED", "UNVERIFIED_DEMO"):
        rule.source_verification_status = "VERIFIED"

    record_audit_log(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="RULE_APPROVED",
        entity_type="ApplicabilityRule",
        entity_id=rule.id,
        new_state={
            "rule_version": rule.rule_version,
            "status": "ACTIVE",
            "statutory_requirement_id": rule.statutory_requirement_id,
            "approved_at": rule.approved_at.isoformat() if rule.approved_at else None,
            "source_verification_status": rule.source_verification_status,
        },
    )

    db.commit()
    db.refresh(rule)
    return rule


def supersede_rule(db: Session, rule_id: str, request: RuleSupersedeRequest, user: User) -> ApplicabilityRule:
    """Supersedes an active rule by creating version N + 1 with review rationale and provenance."""
    old_rule = db.get(ApplicabilityRule, rule_id)
    if not old_rule:
        raise EntityNotFoundError("ApplicabilityRule", rule_id)

    old_rule.status = "SUPERSEDED"
    old_rule.effective_to = request.effective_from or date.today()

    new_rule = ApplicabilityRule(
        statutory_requirement_id=old_rule.statutory_requirement_id,
        rule_version=old_rule.rule_version + 1,
        expression_ast=request.new_expression_ast,
        pass_explanation_template=request.pass_explanation_template,
        fail_explanation_template=request.fail_explanation_template,
        status="ACTIVE",
        effective_from=request.effective_from or date.today(),
        change_rationale=request.change_rationale,
        is_immutable=True,
        approved_by_user_id=user.id,
        approved_at=datetime.now(timezone.utc),
        publication_date=request.publication_date or old_rule.publication_date,
        instrument_identifier=request.instrument_identifier or old_rule.instrument_identifier,
        clause_reference=request.clause_reference or old_rule.clause_reference,
        official_source_url=request.official_source_url or old_rule.official_source_url,
        source_document_id=request.source_document_id or old_rule.source_document_id,
        source_fingerprint=request.source_fingerprint or old_rule.source_fingerprint,
        source_verification_status=request.source_verification_status or "VERIFIED",
    )
    db.add(new_rule)
    db.flush()

    record_audit_log(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="RULE_SUPERSEDED",
        entity_type="ApplicabilityRule",
        entity_id=new_rule.id,
        previous_state={
            "superseded_rule_id": old_rule.id,
            "superseded_rule_version": old_rule.rule_version,
            "superseded_status": "SUPERSEDED",
        },
        new_state={
            "new_rule_version": new_rule.rule_version,
            "new_status": "ACTIVE",
            "change_rationale": request.change_rationale,
        },
    )

    db.commit()
    db.refresh(new_rule)
    return new_rule


def simulate_profile_reassessment(
    db: Session, plant: Plant, proposed_updates: CompanyProfileUpdateRequest
) -> ProfileReassessmentSimulationResponse:
    """
    Simulates the regulatory applicability engine against proposed company profile updates.
    Returns what changed and what obligations would become newly applicable or exempt,
    WITHOUT committing changes or mutating active registers.
    """
    current_facts = assemble_company_facts(db, plant)
    prospective_facts = dict(current_facts)

    attribute_diffs: List[ProfileAttributeDiff] = []
    update_data = proposed_updates.model_dump(exclude_unset=True)

    for field, new_val in update_data.items():
        if new_val is not None:
            old_val = current_facts.get(field)
            if old_val != new_val:
                attribute_diffs.append(
                    ProfileAttributeDiff(
                        field_name=field,
                        previous_value=old_val,
                        proposed_value=new_val,
                    )
                )
            prospective_facts[field] = new_val

    # Recompute derived facts in prospective_facts
    if "employee_count" in prospective_facts:
        contract = prospective_facts.get("contract_labour_count", 0) or 0
        prospective_facts["total_workers"] = (prospective_facts["employee_count"] or 0) + contract
    if "boiler_count" in prospective_facts:
        prospective_facts["has_boiler"] = (prospective_facts.get("boiler_count", 0) or 0) > 0
    if "dg_set_capacity_kva" in prospective_facts:
        prospective_facts["has_dg_set"] = (prospective_facts.get("dg_set_capacity_kva", 0) or 0) > 0
    if "effluent_discharge_kld" in prospective_facts:
        prospective_facts["has_etp"] = (prospective_facts.get("effluent_discharge_kld", 0) or 0) > 0

    # Fetch existing active plant obligations
    existing_stmt = select(PlantRequirement).where(PlantRequirement.plant_id == plant.id)
    existing_map = {ob.statutory_requirement_id: ob for ob in db.scalars(existing_stmt).all()}

    # Fetch all statutory requirements
    reqs_stmt = select(StatutoryRequirement).order_by(StatutoryRequirement.code)
    requirements = list(db.scalars(reqs_stmt).all())

    check_date = date.today()
    diff_items: List[ProposedRequirementDiffItem] = []
    newly_applicable = 0
    no_longer_applicable = 0
    unchanged_applicable = 0
    needs_review = 0

    for req in requirements:
        rule_stmt = select(ApplicabilityRule).where(
            and_(
                ApplicabilityRule.statutory_requirement_id == req.id,
                ApplicabilityRule.status == "ACTIVE",
                ApplicabilityRule.effective_from <= check_date,
            )
        ).order_by(ApplicabilityRule.rule_version.desc())

        candidates = list(db.scalars(rule_stmt).all())
        active_rule = None
        for r in candidates:
            if r.effective_to is None or r.effective_to >= check_date:
                active_rule = r
                break

        if not active_rule:
            continue

        # Check jurisdiction
        jurisdiction_match = True
        jurisdiction_explanation = ""
        if req.act and req.act.jurisdiction_id:
            jurisdiction = db.get(Jurisdiction, req.act.jurisdiction_id)
            if jurisdiction and jurisdiction.level != "CENTRAL":
                plant_j = str(plant.jurisdiction).strip().lower()
                act_j = str(jurisdiction.name).strip().lower()
                act_code = str(jurisdiction.code).strip().lower()
                if act_j not in plant_j and plant_j not in act_j and act_code not in plant_j:
                    jurisdiction_match = False
                    jurisdiction_explanation = (
                        f"Governed under {jurisdiction.name} jurisdiction ({jurisdiction.code}); "
                        f"not applicable to facility operating in {plant.jurisdiction}."
                    )

        if not jurisdiction_match:
            projected_status = "NOT_APPLICABLE"
            reason = jurisdiction_explanation
        else:
            eval_outcome = engine.evaluate_rule(
                active_rule.expression_ast,
                prospective_facts,
                pass_template=active_rule.pass_explanation_template,
                fail_template=active_rule.fail_explanation_template,
            )
            projected_status = eval_outcome.status
            reason = eval_outcome.explanation

        existing_ob = existing_map.get(req.id)
        current_status = existing_ob.applicability_status if existing_ob else "ABSENT"

        impact_type = "UNCHANGED"
        if projected_status == "APPLICABLE" and current_status != "APPLICABLE":
            impact_type = "NEWLY_APPLICABLE"
            newly_applicable += 1
        elif projected_status == "NOT_APPLICABLE" and current_status == "APPLICABLE":
            impact_type = "NO_LONGER_APPLICABLE"
            no_longer_applicable += 1
        elif projected_status == "APPLICABLE" and current_status == "APPLICABLE":
            impact_type = "UNCHANGED"
            unchanged_applicable += 1
        elif projected_status == "NEEDS_REVIEW":
            impact_type = "STATUS_CHANGE"
            needs_review += 1

        if impact_type != "UNCHANGED" or projected_status == "APPLICABLE":
            diff_items.append(
                ProposedRequirementDiffItem(
                    requirement_code=req.code,
                    requirement_title=req.title,
                    authority_code=req.act.authority.code if req.act and req.act.authority else None,
                    obligation_type=req.obligation_type,
                    previous_status=current_status,
                    projected_status=projected_status,
                    reason=reason,
                    impact_type=impact_type,
                )
            )

    guidance = (
        f"Reassessment simulation indicates {newly_applicable} newly applicable obligations, "
        f"{no_longer_applicable} obligations no longer applicable, and {needs_review} items requiring manual confirmation."
    )

    return ProfileReassessmentSimulationResponse(
        plant_id=plant.id,
        attribute_changes=attribute_diffs,
        newly_applicable_count=newly_applicable,
        no_longer_applicable_count=no_longer_applicable,
        unchanged_applicable_count=unchanged_applicable,
        needs_review_count=needs_review,
        impacted_requirements=diff_items,
        summary_guidance=guidance,
    )
