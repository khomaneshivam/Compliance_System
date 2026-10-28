"""
Requirements Register Endpoints (/api/v1/requirements)
Provides server-side pagination, sorting, filters, saved views, and full provenance detail.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.tenancy import User
from app.modules.requirements.schemas import (
    PaginatedRequirementsResponse,
    RequirementDetailResponse,
    SavedViewPreset,
)
from app.modules.requirements.services import requirements_service

requirements_router = APIRouter(prefix="/requirements", tags=["Requirements Register & Provenance"])


@requirements_router.get("", response_model=PaginatedRequirementsResponse, summary="List Paginated Requirements")
def list_requirements_endpoint(
    plant_id: Optional[str] = Query(None, description="Filter by plant facility ID"),
    applicability_status: Optional[str] = Query("ALL", description="ALL, APPLICABLE, CONDITIONALLY_APPLICABLE, EXEMPTED, NOT_APPLICABLE"),
    evidence_status: Optional[str] = Query("ALL", description="ALL, VALID, EXPIRING_SOON, MISSING, EXPIRED, UNDER_REVIEW, NOT_REQUIRED"),
    jurisdiction: Optional[str] = Query("ALL", description="Filter by jurisdiction name"),
    authority_code: Optional[str] = Query("ALL", description="Filter by authority code (MPCB, DISH, CPCB, etc.)"),
    obligation_type: Optional[str] = Query("ALL", description="Filter by obligation type (CONSENT, CERTIFICATE, RETURN, PERMIT)"),
    search: Optional[str] = Query(None, description="Search keyword in title, code, description, or authority"),
    sort_by: str = Query("current_due_date", description="current_due_date, title, code, created_at, evidence_status"),
    sort_order: str = Query("asc", description="asc, desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns server-side filtered, paginated requirements register for the authenticated tenant.
    Never loads all records into the browser at once.
    """
    return requirements_service.list_requirements(
        db=db,
        user=current_user,
        plant_id=plant_id,
        applicability_status=applicability_status,
        evidence_status=evidence_status,
        jurisdiction=jurisdiction,
        authority_code=authority_code,
        obligation_type=obligation_type,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@requirements_router.get("/saved-views", response_model=List[SavedViewPreset], summary="Saved Views Presets")
def get_saved_views_endpoint(
    plant_id: Optional[str] = Query(None, description="Optional facility filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns pre-configured saved view presets with live counts for quick compliance triage."""
    return requirements_service.get_saved_views(db=db, user=current_user, plant_id=plant_id)


@requirements_router.get("/{requirement_id}", response_model=RequirementDetailResponse, summary="Requirement Detail & Provenance")
def get_requirement_detail_endpoint(
    requirement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves complete requirement provenance, deterministic applicability explanation,
    linked evidence documents, and version history.
    """
    return requirements_service.get_requirement_detail(db=db, user=current_user, requirement_id=requirement_id)
