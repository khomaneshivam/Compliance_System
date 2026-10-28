"""
REST API Router for Regulatory Source Ingestion & Human-Reviewed Change Management
Prefix: /api/v1/regulatory
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.models.tenancy import User, Plant
from app.models.regulatory_intel import (
    RegulatorySource,
    RegulatoryDocument,
    RegulatoryChangeReview,
    RegulatoryChangeImpact,
    RegulatorySourceAuditLog,
)
from app.modules.identity_access.services import get_current_user, require_roles
from app.modules.regulatory_intel.schemas import (
    SourceResponse,
    SourceHealthResponse,
    ChangeReviewItemResponse,
    ChangeReviewDetailResponse,
    ChangeReviewDraftUpdateRequest,
    ChangeReviewDecisionRequest,
    ChangeImpactResponse,
    AuditLogResponse,
)
from app.modules.regulatory_intel.pipeline import pipeline

regulatory_router = APIRouter(
    prefix="/regulatory",
    tags=["Regulatory Intelligence & Change Review"],
)


# ------------------------------------------------------------------------------
# 1. Source Registry & Health Endpoints
# ------------------------------------------------------------------------------

@regulatory_router.get("/sources", response_model=List[SourceResponse])
def get_sources(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by health status (HEALTHY, STALE, UNAVAILABLE)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists official regulatory source registries with current health and scraping status."""
    stmt = select(RegulatorySource).order_by(RegulatorySource.name.asc())
    if status_filter:
        stmt = stmt.where(RegulatorySource.health_status == status_filter.upper())
    sources = list(db.scalars(stmt).all())

    return [
        SourceResponse(
            id=s.id,
            code=s.code,
            name=s.name,
            authority_name=s.authority.name if s.authority else None,
            source_type=s.source_type,
            url=s.url,
            adapter_type=s.adapter_type,
            scrape_frequency=s.scrape_frequency,
            rate_limit_per_minute=s.rate_limit_per_minute,
            health_status=s.health_status,
            last_checked_at=s.last_checked_at,
            last_successful_check_at=s.last_successful_check_at,
            consecutive_failures=s.consecutive_failures,
            error_message=s.error_message,
            is_active=s.is_active,
        )
        for s in sources
    ]


@regulatory_router.get("/sources/{source_id}/health", response_model=SourceHealthResponse)
def get_source_health(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves deep health analytics and document ingestion statistics for a source."""
    source = db.get(RegulatorySource, source_id)
    if not source:
        raise EntityNotFoundError("RegulatorySource", source_id)

    total_docs = db.scalar(
        select(func.count(RegulatoryDocument.id)).where(RegulatoryDocument.source_id == source.id)
    ) or 0

    pending_reviews = db.scalar(
        select(func.count(RegulatoryChangeReview.id)).where(
            and_(
                RegulatoryChangeReview.source_id == source.id,
                RegulatoryChangeReview.status == "needs_review",
            )
        )
    ) or 0

    return SourceHealthResponse(
        source_id=source.id,
        code=source.code,
        name=source.name,
        health_status=source.health_status,
        consecutive_failures=source.consecutive_failures,
        last_checked_at=source.last_checked_at,
        last_successful_check_at=source.last_successful_check_at,
        error_message=source.error_message,
        total_documents_ingested=total_docs,
        pending_change_reviews=pending_reviews,
    )


@regulatory_router.post("/sources/{source_id}/poll", response_model=List[ChangeReviewItemResponse])
def trigger_poll(
    source_id: str,
    scenario: str = Query("default", description="Fixture scenario (default, amendment_revised_hash, malformed, oversized, prompt_injection, unavailable)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "EHS_MANAGER"])),
):
    """Triggers an authorized manual check/poll against a source adapter."""
    reviews = pipeline.trigger_source_poll(db, source_id, scenario=scenario, user=current_user)
    return [
        ChangeReviewItemResponse(
            id=r.id,
            source_code=r.source.code if r.source else "UNKNOWN",
            notification_number=r.notification_number,
            title=r.title,
            published_date=r.published_date,
            effective_date=r.effective_date,
            summary_plain_language=r.summary_plain_language,
            confidence_score=r.confidence_score,
            confidence_band=r.confidence_band,
            detected_change_type=r.detected_change_type,
            status=r.status,
            created_at=r.created_at,
        )
        for r in reviews
    ]


# ------------------------------------------------------------------------------
# 2. Detected Changes Inbox & Detail
# ------------------------------------------------------------------------------

@regulatory_router.get("/changes", response_model=List[ChangeReviewItemResponse])
def list_changes(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by review status (needs_review, approved, rejected, extraction_failed, published)"),
    authority_code: Optional[str] = Query(None, description="Filter by authority (MPCB, DISH, CPCB)"),
    confidence_band: Optional[str] = Query(None, description="Filter by confidence band (HIGH, MEDIUM, LOW)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists detected regulatory changes inbox with status, confidence, and date filters."""
    stmt = select(RegulatoryChangeReview).order_by(RegulatoryChangeReview.created_at.desc())
    if status_filter:
        stmt = stmt.where(RegulatoryChangeReview.status == status_filter.lower())
    if confidence_band:
        stmt = stmt.where(RegulatoryChangeReview.confidence_band == confidence_band.upper())
    if authority_code:
        stmt = stmt.join(RegulatorySource).join(RegulatorySource.authority).where(RegulatoryAuthority.code == authority_code.upper())

    reviews = list(db.scalars(stmt).all())
    return [
        ChangeReviewItemResponse(
            id=r.id,
            source_code=r.source.code if r.source else "UNKNOWN",
            notification_number=r.notification_number,
            title=r.title,
            published_date=r.published_date,
            effective_date=r.effective_date,
            summary_plain_language=r.summary_plain_language,
            confidence_score=r.confidence_score,
            confidence_band=r.confidence_band,
            detected_change_type=r.detected_change_type,
            status=r.status,
            created_at=r.created_at,
        )
        for r in reviews
    ]


@regulatory_router.get("/changes/{change_id}", response_model=ChangeReviewDetailResponse)
def get_change_detail(
    change_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full change review detail with old/new text diff, AI draft summary, and snippets."""
    review = db.get(RegulatoryChangeReview, change_id)
    if not review:
        raise EntityNotFoundError("RegulatoryChangeReview", change_id)

    return ChangeReviewDetailResponse(
        id=review.id,
        source_id=review.source_id,
        source_code=review.source.code if review.source else "UNKNOWN",
        document_id=review.document_id,
        statutory_requirement_id=review.statutory_requirement_id,
        statutory_requirement_code=review.statutory_requirement.code if review.statutory_requirement else None,
        notification_number=review.notification_number,
        title=review.title,
        published_date=review.published_date,
        effective_date=review.effective_date,
        summary_plain_language=review.summary_plain_language,
        key_changes_summary=review.key_changes_summary,
        who_may_be_affected=review.who_may_be_affected,
        evidence_snippets=review.evidence_snippets,
        proposed_categories=review.proposed_categories,
        confidence_score=review.confidence_score,
        confidence_band=review.confidence_band,
        detected_change_type=review.detected_change_type,
        old_text=review.old_text,
        new_text=review.new_text,
        diff_summary=review.diff_summary,
        status=review.status,
        review_decision=review.review_decision,
        reviewed_by=review.reviewer.full_name if review.reviewer else None,
        reviewed_at=review.reviewed_at,
        review_notes=review.review_notes,
        approved_effective_date=review.approved_effective_date,
        approved_applicability_ast=review.approved_applicability_ast,
        created_at=review.created_at,
    )


# ------------------------------------------------------------------------------
# 3. Human Reviewer Workflow: Edit Draft & Decision
# ------------------------------------------------------------------------------

@regulatory_router.patch("/changes/{change_id}/draft", response_model=ChangeReviewDetailResponse)
def update_change_draft(
    change_id: str,
    request: ChangeReviewDraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
):
    """Allows a compliance reviewer to edit the AI-proposed summary, dates, categories, or AST."""
    review = pipeline.save_draft_analysis(
        db=db,
        change_id=change_id,
        summary_plain_language=request.summary_plain_language,
        effective_date=request.effective_date,
        proposed_categories=request.proposed_categories,
        statutory_requirement_id=request.statutory_requirement_id,
        applicability_ast=request.approved_applicability_ast,
        user=current_user,
    )
    return get_change_detail(change_id, db=db, current_user=current_user)


@regulatory_router.post("/changes/{change_id}/review", response_model=ChangeReviewDetailResponse)
def review_decision_endpoint(
    change_id: str,
    request: ChangeReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
):
    """
    Submits an official reviewer decision (APPROVE or REJECT).
    Upon approval:
    - Generates an immutable rule version
    - Runs impact evaluation against company profiles
    - Queues proposed requirement changes for plant managers
    """
    review, _ = pipeline.submit_review_decision(
        db=db,
        change_id=change_id,
        decision=request.decision,
        review_notes=request.review_notes,
        user=current_user,
        effective_date=request.effective_date,
        applicability_ast=request.applicability_ast,
        target_requirement_code=request.target_requirement_code,
    )
    return get_change_detail(change_id, db=db, current_user=current_user)


# ------------------------------------------------------------------------------
# 4. Impact Analysis & Version History Endpoints
# ------------------------------------------------------------------------------

@regulatory_router.get("/changes/{change_id}/impacts", response_model=List[ChangeImpactResponse])
def get_change_impacts_endpoint(
    change_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists company facilities impacted by this regulatory change with matched/missing facts."""
    review = db.get(RegulatoryChangeReview, change_id)
    if not review:
        raise EntityNotFoundError("RegulatoryChangeReview", change_id)

    stmt = select(RegulatoryChangeImpact).where(RegulatoryChangeImpact.change_review_id == review.id)
    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(RegulatoryChangeImpact.tenant_id == current_user.tenant_id)
    impacts = list(db.scalars(stmt).all())

    return [
        ChangeImpactResponse(
            id=i.id,
            change_review_id=i.change_review_id,
            plant_id=i.plant_id,
            plant_name=i.plant.name if i.plant else "Unknown Plant",
            plant_code=i.plant.code if i.plant else "UNKNOWN",
            tenant_name=i.tenant.name if i.tenant else "Unknown Tenant",
            impact_status=i.impact_status,
            matched_facts=i.matched_facts,
            missing_facts=i.missing_facts,
            explanation=i.explanation,
        )
        for i in impacts
    ]


@regulatory_router.get("/changes/{change_id}/history", response_model=List[AuditLogResponse])
def get_change_history(
    change_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full immutable audit trail for a regulatory change review item."""
    stmt = (
        select(RegulatorySourceAuditLog)
        .where(RegulatorySourceAuditLog.change_review_id == change_id)
        .order_by(RegulatorySourceAuditLog.created_at.desc())
    )
    logs = list(db.scalars(stmt).all())
    return [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            performed_by=log.performed_by,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]
