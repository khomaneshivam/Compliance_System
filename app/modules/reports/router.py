"""
Readiness and Evidence Report Job Router (/api/v1/reports)
"""

from typing import Optional
import re
from fastapi import APIRouter, Depends, Query, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import rate_limit
from app.models.tenancy import User
from app.modules.reports.schemas import (
    ReportCreateRequest,
    ReportJobResponse,
    PaginatedReportJobsResponse,
)
from app.modules.reports.services import report_service

reports_router = APIRouter(prefix="/reports", tags=["Readiness & Evidence Reports"])


@reports_router.get("", response_model=PaginatedReportJobsResponse, summary="List Report Jobs")
def list_reports_endpoint(
    plant_id: Optional[str] = Query(None, description="Filter by facility ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns paginated report generation jobs for the tenant.
    """
    return report_service.list_jobs(
        db=db, user=current_user, plant_id=plant_id, page=page, page_size=page_size
    )


@reports_router.post(
    "",
    response_model=ReportJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Report Job",
    dependencies=[Depends(rate_limit(max_requests=15, window_seconds=60, key_prefix="reports"))],
)
def create_report_endpoint(
    payload: ReportCreateRequest,
    background_tasks: BackgroundTasks,
    run_async: bool = Query(False, description="Whether to generate report in background worker"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Queues or synchronously executes a readiness and evidence dossier generation job.
    """
    if run_async:
        job = report_service.create_report_job(db=db, user=current_user, payload=payload, run_immediate=False)
        # Background task generation
        background_tasks.add_task(report_service.execute_report_generation, db, job.id)
        return job
    else:
        return report_service.create_report_job(db=db, user=current_user, payload=payload, run_immediate=True)


@reports_router.get("/{job_id}", response_model=ReportJobResponse, summary="Get Report Job Status")
def get_report_job_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns status, metrics, and download metadata for a specific report job.
    """
    return report_service.get_job(db=db, user=current_user, job_id=job_id)


@reports_router.get("/{job_id}/download", summary="Download Report Artifact")
def download_report_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Secured endpoint to download the generated readiness report dossier (JSON or HTML).
    Enforces tenant access controls.
    """
    file_path, filename, media_type = report_service.get_report_download(
        db=db, user=current_user, job_id=job_id
    )
    safe_filename = re.sub(r'[\r\n"\\;]', '_', filename or "readiness_report")
    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )
