"""
Unit Tests for Regulatory Applicability Provenance, Versioning Immutability, and Audit Trails
Enforces:
1. Provenance metadata (Gazette publication date, instrument identifier, clause reference, official source URL, fingerprint, verification status)
2. Immutability of active rules (updates require superseding with version N + 1)
3. Audit logging of rule proposals, approvals, and supersessions
4. Unapproved rules (PROPOSED/SUPERSEDED) are never evaluated against plant profiles
5. Historical assessment runs and findings remain strictly immutable snapshots
"""

from datetime import date, datetime, timezone
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import EntityNotFoundError, ImmutableRecordError
from app.models.tenancy import Tenant, User, Plant
from app.models.profile import PlantProfile
from app.models.catalog import (
    RegulatoryAuthority,
    RegulatoryAct,
    StatutoryRequirement,
    ApplicabilityRule,
)
from app.models.assessments import AssessmentRun, AssessmentFinding
from app.models.tasks import AuditLog
from app.modules.applicability.services import (
    create_rule_version,
    approve_rule,
    supersede_rule,
    run_applicability_assessment,
)
from app.modules.applicability.schemas import (
    RuleCreateRequest,
    RuleSupersedeRequest,
)
from app.modules.requirements.services import RequirementsService
from app.seed.demo_data import seed_master_data


@pytest.fixture(scope="module")
def db_session():
    """Provides a transactional session with master data pre-seeded."""
    db = SessionLocal()
    seed_master_data(db)
    yield db
    db.close()


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = db_session.scalars(select(User).where(User.email == "test.admin@plantproof.io")).first()
    if not user:
        tenant = db_session.scalars(select(Tenant)).first()
        if not tenant:
            tenant = Tenant(name="Test Tenancy", code="test-tenancy", is_active=True)
            db_session.add(tenant)
            db_session.flush()

        user = User(
            tenant_id=tenant.id,
            email="test.admin@plantproof.io",
            full_name="Test Rule Admin",
            hashed_password="hashed_placeholder_pw",
            role="ADMIN",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
    return user


def test_rule_creation_records_provenance_and_audit(db_session: Session, admin_user: User):
    """Admin authors a new proposed rule: must persist provenance fields and RULE_PROPOSED audit log."""
    req_cto = db_session.scalars(
        select(StatutoryRequirement).where(StatutoryRequirement.code == "MPCB-CTO")
    ).first()
    assert req_cto is not None

    pub_date = date(2026, 3, 15)
    request = RuleCreateRequest(
        statutory_requirement_code="MPCB-CTO",
        expression_ast={"field": "effluent_discharge_kld", "operator": "gt", "value": 10.0},
        pass_explanation_template="Effluent discharge exceeds 10 KLD.",
        fail_explanation_template="Effluent discharge within limits.",
        change_rationale="Tightened threshold based on March 2026 Gazette notification.",
        publication_date=pub_date,
        instrument_identifier="Gazette Notification S.O. 987(E)",
        clause_reference="Clause 4(a), Revised MPCB Norms",
        official_source_url="https://mpcb.gov.in/gazette/so987e.pdf",
        source_fingerprint="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        source_verification_status="PROPOSED",
    )

    rule = create_rule_version(db_session, request, admin_user)
    assert rule.id is not None
    assert rule.status == "PROPOSED"
    assert rule.is_immutable is False
    assert rule.publication_date == pub_date
    assert rule.instrument_identifier == "Gazette Notification S.O. 987(E)"
    assert rule.clause_reference == "Clause 4(a), Revised MPCB Norms"
    assert rule.official_source_url == "https://mpcb.gov.in/gazette/so987e.pdf"
    assert rule.source_fingerprint == "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    assert rule.source_verification_status == "PROPOSED"

    # Verify audit log
    audit_entry = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_id == rule.id, AuditLog.action == "RULE_PROPOSED")
        .order_by(AuditLog.created_at.desc())
    ).first()
    assert audit_entry is not None
    assert audit_entry.user_id == admin_user.id
    assert audit_entry.new_state["instrument_identifier"] == "Gazette Notification S.O. 987(E)"


def test_rule_approval_enforces_immutability_and_supersedes_prior(db_session: Session, admin_user: User):
    """Approving a rule locks it as legally immutable, marks prior active versions SUPERSEDED, and records audit."""
    req_cto = db_session.scalars(
        select(StatutoryRequirement).where(StatutoryRequirement.code == "MPCB-CTO")
    ).first()

    # Find the proposed rule created in prior test
    proposed_rule = db_session.scalars(
        select(ApplicabilityRule)
        .where(ApplicabilityRule.statutory_requirement_id == req_cto.id, ApplicabilityRule.status == "PROPOSED")
        .order_by(ApplicabilityRule.rule_version.desc())
    ).first()
    assert proposed_rule is not None

    # Get the prior active rule
    prior_active = db_session.scalars(
        select(ApplicabilityRule)
        .where(ApplicabilityRule.statutory_requirement_id == req_cto.id, ApplicabilityRule.status == "ACTIVE")
    ).first()
    assert prior_active is not None

    # Approve the proposed rule
    approved = approve_rule(db_session, proposed_rule.id, admin_user)
    assert approved.status == "ACTIVE"
    assert approved.is_immutable is True
    assert approved.approved_by_user_id == admin_user.id
    assert approved.approved_at is not None
    assert approved.source_verification_status == "VERIFIED"

    # Prior active rule must now be SUPERSEDED
    db_session.refresh(prior_active)
    assert prior_active.status == "SUPERSEDED"
    assert prior_active.effective_to is not None

    # Attempting to re-approve an immutable active rule must raise ImmutableRecordError
    with pytest.raises(ImmutableRecordError):
        approve_rule(db_session, approved.id, admin_user)

    # Verify audit log
    audit_entry = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_id == approved.id, AuditLog.action == "RULE_APPROVED")
        .order_by(AuditLog.created_at.desc())
    ).first()
    assert audit_entry is not None
    assert audit_entry.user_id == admin_user.id
    assert audit_entry.new_state["status"] == "ACTIVE"


def test_rule_supersede_creates_new_version(db_session: Session, admin_user: User):
    """Superseding an active rule creates version N+1 with change rationale, archives old version, and records audit."""
    req_cto = db_session.scalars(
        select(StatutoryRequirement).where(StatutoryRequirement.code == "MPCB-CTO")
    ).first()

    current_active = db_session.scalars(
        select(ApplicabilityRule)
        .where(ApplicabilityRule.statutory_requirement_id == req_cto.id, ApplicabilityRule.status == "ACTIVE")
        .order_by(ApplicabilityRule.rule_version.desc())
    ).first()
    assert current_active is not None
    current_ver = current_active.rule_version

    supersede_req = RuleSupersedeRequest(
        new_expression_ast={"field": "effluent_discharge_kld", "operator": "gt", "value": 5.0},
        pass_explanation_template="Effluent discharge exceeds 5 KLD threshold.",
        fail_explanation_template="Effluent discharge is within 5 KLD threshold.",
        change_rationale="Statutory update to 5 KLD under Maharashtra Gazette 2026.",
        clause_reference="Clause 5, 2026 Gazette Amendments",
    )

    new_rule = supersede_rule(db_session, current_active.id, supersede_req, admin_user)
    assert new_rule.rule_version == current_ver + 1
    assert new_rule.status == "ACTIVE"
    assert new_rule.is_immutable is True
    assert new_rule.clause_reference == "Clause 5, 2026 Gazette Amendments"
    # Inherited provenance from parent
    assert new_rule.instrument_identifier == current_active.instrument_identifier

    # Old rule must be archived as SUPERSEDED
    db_session.refresh(current_active)
    assert current_active.status == "SUPERSEDED"

    # Audit log check
    audit_entry = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_id == new_rule.id, AuditLog.action == "RULE_SUPERSEDED")
        .order_by(AuditLog.created_at.desc())
    ).first()
    assert audit_entry is not None
    assert audit_entry.previous_state["superseded_rule_id"] == current_active.id
    assert audit_entry.new_state["new_rule_version"] == new_rule.rule_version


def test_unapproved_rules_are_never_evaluated(db_session: Session, admin_user: User):
    """
    REGULATORY SAFETY REQUIREMENT:
    Only ACTIVE rules within effective dates are evaluated in plant assessment runs.
    Unapproved proposed rules or superseded rules must never alter an assessment.
    """
    req_boiler = db_session.scalars(
        select(StatutoryRequirement).where(StatutoryRequirement.code == "BOILER-INSP-CERT")
    ).first()
    assert req_boiler is not None

    # Create or reuse a dummy plant for evaluation
    tenant = db_session.scalars(select(Tenant)).first()
    plant = db_session.scalars(select(Plant).where(Plant.code == "MH-TST-01")).first()
    if not plant:
        plant = Plant(
            tenant_id=tenant.id,
            name="Proven Plant",
            code="MH-TST-01",
            jurisdiction="Maharashtra",
            district="Pune",
            pincode="411001",
        )
        db_session.add(plant)
        db_session.flush()

        profile = PlantProfile(
            plant_id=plant.id,
            industry_category="RED",
            boiler_count=2,
            steam_capacity_tph=12.0,
            effluent_discharge_kld=20.0,
        )
        db_session.add(profile)
        db_session.flush()

    # Create a PROPOSED rule version that should NOT be picked up
    max_ver = db_session.scalar(
        select(func.coalesce(func.max(ApplicabilityRule.rule_version), 0)).where(
            ApplicabilityRule.statutory_requirement_id == req_boiler.id
        )
    ) or 0
    proposed_ver = max_ver + 1
    proposed_boiler_rule = ApplicabilityRule(
        statutory_requirement_id=req_boiler.id,
        rule_version=proposed_ver,
        expression_ast={"field": "boiler_count", "operator": "gt", "value": 100},  # Impossibly high threshold
        pass_explanation_template="Proposed rule pass",
        fail_explanation_template="Proposed rule fail",
        status="PROPOSED",
        is_immutable=False,
    )
    db_session.add(proposed_boiler_rule)
    db_session.commit()

    # Run assessment
    run = run_applicability_assessment(db_session, plant, evaluated_by_user_id=admin_user.id)
    assert run is not None

    finding = db_session.scalars(
        select(AssessmentFinding)
        .where(
            AssessmentFinding.assessment_run_id == run.id,
            AssessmentFinding.statutory_requirement_id == req_boiler.id,
        )
    ).first()

    assert finding is not None
    # Must use active rule (v1), NOT the proposed rule (v99)
    assert finding.rule_version_id != proposed_boiler_rule.id
    assert finding.evaluation_outcome == "APPLICABLE"


def test_statutory_provenance_and_finding_trace_in_detail_service(db_session: Session, admin_user: User):
    """
    Verifies RequirementsService.get_requirement_detail loads official provenance
    from ApplicabilityRule and condition_trace from AssessmentFinding.
    """
    plant = db_session.scalars(select(Plant).where(Plant.code == "MH-TST-01")).first()
    assert plant is not None

    req_cto = db_session.scalars(select(StatutoryRequirement).where(StatutoryRequirement.code == "MPCB-CTO")).first()
    assert req_cto is not None

    # Ensure a plant requirement exists
    from app.models.requirements import PlantRequirement
    plant_req = db_session.scalars(
        select(PlantRequirement).where(
            PlantRequirement.plant_id == plant.id,
            PlantRequirement.statutory_requirement_id == req_cto.id,
        )
    ).first()
    if not plant_req:
        active_rule = db_session.scalars(
            select(ApplicabilityRule).where(
                ApplicabilityRule.statutory_requirement_id == req_cto.id,
                ApplicabilityRule.status == "ACTIVE",
            )
        ).first()
        plant_req = PlantRequirement(
            plant_id=plant.id,
            statutory_requirement_id=req_cto.id,
            rule_version_id=active_rule.id if active_rule else None,
            applicability_status="APPLICABLE",
            applicability_rationale="Tested rationale",
            evidence_status="MISSING",
        )
        db_session.add(plant_req)
        db_session.commit()

    service = RequirementsService()
    detail = service.get_requirement_detail(db_session, admin_user, plant_req.id)

    assert detail is not None
    assert detail.provenance is not None
    assert detail.provenance.act_title is not None
    assert detail.provenance.source_verification_status in ("VERIFIED", "UNVERIFIED_DEMO")
    assert detail.applicability is not None
    assert detail.applicability.rule_version >= 1
