"""
Admin Audit Log Router (/api/v1/admin/audit-logs)
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.tenancy import User
from app.modules.audit.schemas import PaginatedAuditLogsResponse
from app.modules.audit.services import audit_service

audit_router = APIRouter(prefix="/admin/audit-logs", tags=["Admin Audit & Governance Logs"])


@audit_router.get("", response_model=PaginatedAuditLogsResponse, summary="Query Admin Audit Logs")
def get_audit_logs_endpoint(
    action: Optional[str] = Query("ALL", description="Filter by audit action type"),
    entity_type: Optional[str] = Query("ALL", description="Filter by entity type (TASK, REQUIREMENT, PROFILE, etc.)"),
    user_id: Optional[str] = Query(None, description="Filter by initiating user ID"),
    search: Optional[str] = Query(None, description="Search keyword in action, entity, or ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "AUDITOR"])),
):
    """
    Returns paginated audit logs with readable descriptions, without displaying raw machine JSON dumps.
    """
    return audit_service.list_logs(
        db=db,
        user=current_user,
        action=action,
        entity_type=entity_type,
        user_id=user_id,
        search=search,
        page=page,
        page_size=page_size,
    )
