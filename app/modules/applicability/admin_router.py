"""
Admin Regulatory Rule Authoring & Test Bench Endpoints (/api/v1/admin/rules)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError, ImmutableRecordError
from app.models.tenancy import User
from app.models.catalog import ApplicabilityRule
from app.modules.identity_access.services import get_current_user, require_roles
from app.modules.applicability.schemas import (
    RuleCreateRequest,
    RuleResponse,
    RuleSupersedeRequest,
)
from app.modules.applicability.services import (
    list_rules,
    create_rule_version,
    approve_rule,
    supersede_rule,
)

admin_router = APIRouter(
    prefix="/admin/rules",
    tags=["Admin Rule Authoring & Test Bench"],
    dependencies=[Depends(require_roles(["ADMIN", "SUPER_ADMIN"]))],
)


@admin_router.get("", response_model=List[RuleResponse])
def get_rules(
    requirement_code: Optional[str] = Query(None, description="Filter by requirement code (e.g. MPCB-CTO)"),
    status: Optional[str] = Query(None, description="Filter by status (PROPOSED, ACTIVE, SUPERSEDED, REJECTED)"),
    db: Session = Depends(get_db),
):
    """Lists applicability rule versions with condition ASTs and approval metadata."""
    rules = list_rules(db, requirement_code=requirement_code, status_filter=status)
    return [
        RuleResponse(
            id=r.id,
            statutory_requirement_id=r.statutory_requirement_id,
            statutory_requirement_code=r.statutory_requirement.code if r.statutory_requirement else None,
            rule_version=r.rule_version,
            status=r.status,
            expression_ast=r.expression_ast,
            pass_explanation_template=r.pass_explanation_template,
            fail_explanation_template=r.fail_explanation_template,
            is_immutable=r.is_immutable,
            effective_from=r.effective_from,
            effective_to=r.effective_to,
            change_rationale=r.change_rationale,
            approved_at=r.approved_at,
        )
        for r in rules
    ]


@admin_router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    request: RuleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authors a new applicability rule version in PROPOSED status for regulatory review."""
    rule = create_rule_version(db, request, current_user)
    return RuleResponse(
        id=rule.id,
        statutory_requirement_id=rule.statutory_requirement_id,
        statutory_requirement_code=rule.statutory_requirement.code if rule.statutory_requirement else None,
        rule_version=rule.rule_version,
        status=rule.status,
        expression_ast=rule.expression_ast,
        pass_explanation_template=rule.pass_explanation_template,
        fail_explanation_template=rule.fail_explanation_template,
        is_immutable=rule.is_immutable,
        effective_from=rule.effective_from,
        effective_to=rule.effective_to,
        change_rationale=rule.change_rationale,
        approved_at=rule.approved_at,
    )


@admin_router.get("/{rule_id}/versions", response_model=List[RuleResponse])
def get_rule_versions(
    rule_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves full version history for the statutory requirement governed by this rule."""
    rule = db.get(ApplicabilityRule, rule_id)
    if not rule:
        raise EntityNotFoundError("ApplicabilityRule", rule_id)

    versions_stmt = (
        select(ApplicabilityRule)
        .where(ApplicabilityRule.statutory_requirement_id == rule.statutory_requirement_id)
        .order_by(ApplicabilityRule.rule_version.desc())
    )
    versions = list(db.scalars(versions_stmt).all())

    return [
        RuleResponse(
            id=v.id,
            statutory_requirement_id=v.statutory_requirement_id,
            statutory_requirement_code=v.statutory_requirement.code if v.statutory_requirement else None,
            rule_version=v.rule_version,
            status=v.status,
            expression_ast=v.expression_ast,
            pass_explanation_template=v.pass_explanation_template,
            fail_explanation_template=v.fail_explanation_template,
            is_immutable=v.is_immutable,
            effective_from=v.effective_from,
            effective_to=v.effective_to,
            change_rationale=v.change_rationale,
            approved_at=v.approved_at,
        )
        for v in versions
    ]


@admin_router.post("/{rule_id}/approve", response_model=RuleResponse)
def approve_rule_endpoint(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approves a proposed rule version. Once approved, the rule becomes legally immutable."""
    rule = approve_rule(db, rule_id, current_user)
    return RuleResponse(
        id=rule.id,
        statutory_requirement_id=rule.statutory_requirement_id,
        statutory_requirement_code=rule.statutory_requirement.code if rule.statutory_requirement else None,
        rule_version=rule.rule_version,
        status=rule.status,
        expression_ast=rule.expression_ast,
        pass_explanation_template=rule.pass_explanation_template,
        fail_explanation_template=rule.fail_explanation_template,
        is_immutable=rule.is_immutable,
        effective_from=rule.effective_from,
        effective_to=rule.effective_to,
        change_rationale=rule.change_rationale,
        approved_at=rule.approved_at,
    )


@admin_router.post("/{rule_id}/supersede", response_model=RuleResponse)
def supersede_rule_endpoint(
    rule_id: str,
    request: RuleSupersedeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supersedes an existing rule by creating version N + 1 with change rationale and effective dates."""
    new_rule = supersede_rule(db, rule_id, request, current_user)
    return RuleResponse(
        id=new_rule.id,
        statutory_requirement_id=new_rule.statutory_requirement_id,
        statutory_requirement_code=new_rule.statutory_requirement.code if new_rule.statutory_requirement else None,
        rule_version=new_rule.rule_version,
        status=new_rule.status,
        expression_ast=new_rule.expression_ast,
        pass_explanation_template=new_rule.pass_explanation_template,
        fail_explanation_template=new_rule.fail_explanation_template,
        is_immutable=new_rule.is_immutable,
        effective_from=new_rule.effective_from,
        effective_to=new_rule.effective_to,
        change_rationale=new_rule.change_rationale,
        approved_at=new_rule.approved_at,
    )
