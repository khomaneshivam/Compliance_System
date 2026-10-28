"""
Readiness and Evidence Report Generation Service
Supports background compilation, formatted HTML/JSON export, storage vault persistence,
and strict tenant isolation checks.
"""

import os
import json
import math
import html
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, asc, func

from app.core.exceptions import EntityNotFoundError, TenantAccessDeniedError, AppException
from app.models.tenancy import User, Plant, Tenant
from app.models.requirements import PlantRequirement, EvidenceLink
from app.models.catalog import StatutoryRequirement
from app.models.documents import ComplianceDocument
from app.models.tasks import ComplianceTask
from app.models.reports import ReadinessReportJob
from app.modules.reports.schemas import (
    ReportCreateRequest,
    ReportJobResponse,
    PaginatedReportJobsResponse,
    ReadinessReportContent,
    ReadinessReportRequirementDetail,
    EvidenceSummaryItem,
    MissingEvidenceItem,
    LEGAL_DISCLAIMER,
)

VAULT_BASE_DIR = Path("vault")


class ReportService:
    def list_jobs(
        self,
        db: Session,
        user: User,
        plant_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedReportJobsResponse:
        """Returns paginated report generation jobs for the tenant."""
        page = max(1, page)
        page_size = min(max(1, page_size), 50)

        stmt = select(ReadinessReportJob).where(ReadinessReportJob.tenant_id == user.tenant_id)
        if plant_id:
            stmt = stmt.where(ReadinessReportJob.plant_id == plant_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(desc(ReadinessReportJob.created_at))
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        jobs = list(db.scalars(stmt).all())
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        items = [
            ReportJobResponse(
                id=j.id,
                plant_id=j.plant_id,
                plant_name=j.plant.name if j.plant else None,
                report_title=j.report_title,
                status=j.status,
                error_message=j.error_message,
                prepared_at=j.prepared_at,
                data_as_of=j.data_as_of,
                file_format=j.file_format,
                file_size_bytes=j.file_size_bytes,
                summary_metrics=j.summary_metrics or {},
                download_url=f"/api/v1/reports/{j.id}/download" if j.status == "COMPLETED" else None,
                created_at=j.created_at,
            )
            for j in jobs
        ]

        return PaginatedReportJobsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_job(self, db: Session, user: User, job_id: str) -> ReportJobResponse:
        """Retrieves single report job status."""
        job = db.get(ReadinessReportJob, job_id)
        if not job or job.tenant_id != user.tenant_id:
            raise EntityNotFoundError("ReadinessReportJob", job_id)

        return ReportJobResponse(
            id=job.id,
            plant_id=job.plant_id,
            plant_name=job.plant.name if job.plant else None,
            report_title=job.report_title,
            status=job.status,
            error_message=job.error_message,
            prepared_at=job.prepared_at,
            data_as_of=job.data_as_of,
            file_format=job.file_format,
            file_size_bytes=job.file_size_bytes,
            summary_metrics=job.summary_metrics or {},
            download_url=f"/api/v1/reports/{job.id}/download" if job.status == "COMPLETED" else None,
            created_at=job.created_at,
        )

    def create_report_job(
        self, db: Session, user: User, payload: ReportCreateRequest, run_immediate: bool = True
    ) -> ReportJobResponse:
        """Creates a report job record and optionally generates it immediately."""
        plant = db.get(Plant, payload.plant_id)
        if not plant or plant.tenant_id != user.tenant_id:
            raise EntityNotFoundError("Plant", payload.plant_id)

        job = ReadinessReportJob(
            tenant_id=user.tenant_id,
            plant_id=plant.id,
            requested_by_user_id=user.id,
            report_title=payload.report_title,
            status="QUEUED",
            date_range_start=payload.date_range_start,
            date_range_end=payload.date_range_end,
            file_format=payload.file_format.upper(),
            data_as_of=date.today(),
            summary_metrics={},
            report_payload={},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if run_immediate:
            self.execute_report_generation(db, job.id)
            db.refresh(job)

        return ReportJobResponse(
            id=job.id,
            plant_id=job.plant_id,
            plant_name=plant.name,
            report_title=job.report_title,
            status=job.status,
            error_message=job.error_message,
            prepared_at=job.prepared_at,
            data_as_of=job.data_as_of,
            file_format=job.file_format,
            file_size_bytes=job.file_size_bytes,
            summary_metrics=job.summary_metrics or {},
            download_url=f"/api/v1/reports/{job.id}/download" if job.status == "COMPLETED" else None,
            created_at=job.created_at,
        )

    def execute_report_generation(self, db: Session, job_id: str) -> None:
        """
        Gathers evidence, builds missing items, aggregates tasks, creates report payload,
        renders the artifact to vault disk, and updates the job status to COMPLETED.
        """
        job = db.get(ReadinessReportJob, job_id)
        if not job:
            return

        job.status = "GENERATING"
        db.commit()

        try:
            plant = db.get(Plant, job.plant_id)
            tenant = db.get(Tenant, job.tenant_id)
            user = db.get(User, job.requested_by_user_id) if job.requested_by_user_id else None

            # Fetch all applicable plant requirements
            req_stmt = (
                select(PlantRequirement)
                .where(
                    PlantRequirement.plant_id == plant.id,
                    PlantRequirement.applicability_status == "APPLICABLE",
                )
                .join(PlantRequirement.statutory_requirement)
            )
            plant_reqs = list(db.scalars(req_stmt).all())

            # Fetch open tasks
            task_stmt = select(ComplianceTask).where(
                ComplianceTask.plant_id == plant.id,
                ComplianceTask.status != "COMPLETED",
            )
            open_tasks = list(db.scalars(task_stmt).all())

            today = date.today()
            expiring_cutoff = today + timedelta(days=30)

            total_applicable = len(plant_reqs)
            verified_count = 0
            missing_count = 0
            expiring_soon_count = 0

            req_details: List[ReadinessReportRequirementDetail] = []
            missing_items: List[MissingEvidenceItem] = []

            for pr in plant_reqs:
                req = pr.statutory_requirement
                act = req.act if req else None
                auth = act.authority if act else None
                auth_name = auth.name if auth else "Regulatory Authority"
                auth_code = auth.code if auth else "REG"

                evidence_list: List[EvidenceSummaryItem] = []
                has_verified = False

                for link in pr.evidence_links:
                    doc = link.document
                    if doc:
                        evidence_list.append(
                            EvidenceSummaryItem(
                                document_id=doc.id,
                                original_filename=doc.original_filename,
                                authority_name=doc.extracted_data.get("issuing_authority") if doc.extracted_data else auth_code,
                                document_type=doc.extracted_data.get("document_type") if doc.extracted_data else req.obligation_type,
                                verification_status=doc.verification_status,
                                valid_until=doc.valid_until,
                            )
                        )
                        if doc.verification_status == "VERIFIED":
                            has_verified = True

                # Determine evidence status
                ev_status = "MISSING"
                if has_verified:
                    if pr.current_due_date and pr.current_due_date < today:
                        ev_status = "EXPIRED"
                    elif pr.current_due_date and pr.current_due_date <= expiring_cutoff:
                        ev_status = "EXPIRING_SOON"
                        expiring_soon_count += 1
                        verified_count += 1
                    else:
                        ev_status = "VALID"
                        verified_count += 1
                else:
                    missing_count += 1
                    missing_items.append(
                        MissingEvidenceItem(
                            requirement_code=req.code,
                            requirement_title=req.title,
                            authority=auth_code,
                            obligation_type=req.obligation_type,
                            severity="HIGH" if req.obligation_type in ["CONSENT", "PERMIT", "LICENCE"] else "MEDIUM",
                            remediation_guidance=f"Upload and verify {req.obligation_type} from {auth_name} to satisfy condition {req.code}.",
                        )
                    )

                sources = [act.title] if act else ["Statutory Regulation"]

                req_details.append(
                    ReadinessReportRequirementDetail(
                        requirement_code=req.code,
                        title=req.title,
                        authority=auth_code,
                        jurisdiction=plant.jurisdiction or "State",
                        obligation_type=req.obligation_type,
                        applicability_status="APPLICABLE",
                        evidence_status=ev_status,
                        valid_until=pr.current_due_date,
                        review_state="ACCEPTED",
                        sources=sources,
                        evidence=evidence_list,
                    )
                )

            readiness_pct = (
                round((verified_count / total_applicable) * 100, 1) if total_applicable > 0 else 100.0
            )

            metrics = {
                "total_applicable_requirements": total_applicable,
                "verified_evidence_count": verified_count,
                "missing_evidence_count": missing_count,
                "expiring_soon_count": expiring_soon_count,
                "open_tasks_count": len(open_tasks),
                "readiness_percentage": readiness_pct,
            }

            tasks_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "status": t.status,
                    "due_date": t.due_date.isoformat(),
                    "assigned_to": t.assignee.email if t.assignee else "Unassigned",
                }
                for t in open_tasks
            ]

            report_obj = ReadinessReportContent(
                report_title=job.report_title,
                disclaimer=LEGAL_DISCLAIMER,
                prepared_on=datetime.now(timezone.utc),
                data_as_of=job.data_as_of,
                generated_by_email=user.email if user else "system",
                tenant_name=tenant.name if tenant else "PlantProof Enterprise",
                plant_id=plant.id,
                plant_name=plant.name,
                jurisdiction=plant.jurisdiction or "Maharashtra (MPCB)",
                industry_type=(plant.profile.industry_category if plant.profile else None) or "Chemical Manufacturing",
                summary_metrics=metrics,
                requirements=req_details,
                missing_items=missing_items,
                open_tasks=tasks_data,
                regulatory_sources=[
                    {"authority": "MPCB", "scope": "Water & Air Acts", "state": "Maharashtra"},
                    {"authority": "DISH", "scope": "Factories Act, 1948", "state": "Maharashtra"},
                    {"authority": "CPCB / MoEFCC", "scope": "Environment Protection Act, 1986", "jurisdiction": "Central"},
                ],
            )

            report_dict = report_obj.model_dump(mode="json")

            # Write file to disk vault
            vault_dir = VAULT_BASE_DIR / job.tenant_id / "reports"
            vault_dir.mkdir(parents=True, exist_ok=True)

            ext = "json" if job.file_format == "JSON" else "html"
            filename = f"readiness_report_{job.id}.{ext}"
            file_path = vault_dir / filename

            if job.file_format == "HTML":
                html_content = self._render_report_html(report_dict)
                file_path.write_text(html_content, encoding="utf-8")
                size = file_path.stat().st_size
            else:
                json_str = json.dumps(report_dict, indent=2)
                file_path.write_text(json_str, encoding="utf-8")
                size = file_path.stat().st_size

            job.status = "COMPLETED"
            job.storage_key = str(file_path.as_posix())
            job.file_size_bytes = size
            job.summary_metrics = metrics
            job.report_payload = report_dict
            job.prepared_at = datetime.now(timezone.utc)
            db.commit()

        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            db.commit()

    def get_report_download(self, db: Session, user: User, job_id: str) -> Tuple[str, str, str]:
        """
        Returns (filepath, filename, media_type) for downloading the completed report.
        Strictly checks tenant boundaries.
        """
        job = db.get(ReadinessReportJob, job_id)
        if not job or job.tenant_id != user.tenant_id:
            raise EntityNotFoundError("ReadinessReportJob", job_id)

        if job.status != "COMPLETED" or not job.storage_key:
            raise AppException(
                code="REPORT_NOT_READY",
                message=f"Report job '{job_id}' is currently {job.status}. Download unavailable until COMPLETED.",
                status_code=400,
                remediation="Poll report status or wait for generation to complete.",
            )

        file_path = Path(job.storage_key)
        resolved_path = file_path.resolve()
        expected_vault = (VAULT_BASE_DIR / job.tenant_id).resolve()
        if not str(resolved_path).startswith(str(expected_vault)):
            raise AppException(
                code="STORAGE_SECURITY_VIOLATION",
                message="Directory traversal detected in report artifact path.",
                status_code=403,
            )

        if not resolved_path.exists() or not resolved_path.is_file():
            raise AppException(
                code="REPORT_FILE_NOT_FOUND",
                message="Report artifact file not found on disk storage.",
                status_code=500,
            )

        ext = "html" if job.file_format == "HTML" else "json"
        media_type = "text/html" if ext == "html" else "application/json"
        safe_title = "".join(c for c in job.report_title if c.isalnum() or c in ("-", "_")).rstrip()
        filename = f"{safe_title}_{job.data_as_of.isoformat()}.{ext}"

        return str(resolved_path), filename, media_type

    def _render_report_html(self, data: Dict[str, Any]) -> str:
        """Renders an executive-grade HTML readiness & evidence dossier with full HTML escaping."""
        metrics = data.get("summary_metrics", {})
        reqs = data.get("requirements", [])
        gaps = data.get("missing_items", [])
        tasks = data.get("open_tasks", [])

        plant_name = html.escape(str(data.get("plant_name") or ""))
        tenant_name = html.escape(str(data.get("tenant_name") or "PlantProof Enterprise"))
        jurisdiction = html.escape(str(data.get("jurisdiction") or ""))
        industry_type = html.escape(str(data.get("industry_type") or ""))
        generated_by = html.escape(str(data.get("generated_by_email") or "system"))
        report_title = html.escape(str(data.get("report_title") or "Facility Regulatory Readiness & Evidence Dossier"))
        disclaimer = html.escape(str(data.get("disclaimer") or LEGAL_DISCLAIMER))

        req_rows = ""
        for r in reqs:
            code = html.escape(str(r.get("requirement_code") or ""))
            title = html.escape(str(r.get("title") or ""))
            auth = html.escape(str(r.get("authority") or ""))
            ob_type = html.escape(str(r.get("obligation_type") or ""))
            ev_status = html.escape(str(r.get("evidence_status") or ""))
            valid_until = html.escape(str(r.get("valid_until") or "N/A"))

            badge_class = "badge-green" if r.get("evidence_status") == "VALID" else ("badge-amber" if r.get("evidence_status") == "EXPIRING_SOON" else "badge-red")
            req_rows += f"""
            <tr>
                <td><strong>{code}</strong></td>
                <td>{title}</td>
                <td>{auth}</td>
                <td>{ob_type}</td>
                <td><span class="badge {badge_class}">{ev_status}</span></td>
                <td>{valid_until}</td>
            </tr>
            """

        gap_rows = ""
        for g in gaps:
            sev = html.escape(str(g.get("severity") or ""))
            g_code = html.escape(str(g.get("requirement_code") or ""))
            g_title = html.escape(str(g.get("requirement_title") or ""))
            g_auth = html.escape(str(g.get("authority") or ""))
            g_type = html.escape(str(g.get("obligation_type") or ""))
            g_rem = html.escape(str(g.get("remediation_guidance") or ""))

            gap_rows += f"""
            <tr>
                <td><span class="badge badge-red">{sev}</span></td>
                <td><strong>{g_code}</strong>: {g_title}</td>
                <td>{g_auth} ({g_type})</td>
                <td>{g_rem}</td>
            </tr>
            """

        task_rows = ""
        for t in tasks:
            t_title = html.escape(str(t.get("title") or ""))
            t_prio = html.escape(str(t.get("priority") or ""))
            t_stat = html.escape(str(t.get("status") or ""))
            t_due = html.escape(str(t.get("due_date") or ""))
            t_assign = html.escape(str(t.get("assigned_to") or "Unassigned"))

            task_rows += f"""
            <tr>
                <td>{t_title}</td>
                <td><span class="badge badge-amber">{t_prio}</span></td>
                <td>{t_stat}</td>
                <td>{t_due}</td>
                <td>{t_assign}</td>
            </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{plant_name} - {report_title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 32px; }}
        .container {{ max-width: 1080px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 40px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #06281e; padding-bottom: 24px; margin-bottom: 24px; }}
        .title-block h1 {{ margin: 0 0 8px 0; color: #06281e; font-size: 26px; }}
        .title-block p {{ margin: 0; color: #64748b; font-size: 14px; }}
        .disclaimer-box {{ background: #fffbeb; border: 1px solid #fef3c7; border-left: 4px solid #f59e0b; padding: 14px 18px; border-radius: 6px; margin-bottom: 32px; font-size: 13px; color: #92400e; line-height: 1.5; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 36px; }}
        .metric-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; text-align: center; }}
        .metric-val {{ font-size: 28px; font-weight: 700; color: #06281e; margin-bottom: 4px; }}
        .metric-lbl {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; }}
        h2 {{ font-size: 18px; color: #1e293b; margin: 32px 0 16px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 28px; font-size: 13px; }}
        th {{ background: #f1f5f9; text-align: left; padding: 10px 14px; font-weight: 600; color: #334155; border-bottom: 1px solid #cbd5e1; }}
        td {{ padding: 12px 14px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
        .badge-green {{ background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }}
        .badge-amber {{ background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }}
        .badge-red {{ background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }}
        .footer {{ margin-top: 48px; border-top: 1px solid #e2e8f0; padding-top: 16px; color: #94a3b8; font-size: 12px; display: flex; justify-content: space-between; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title-block">
                <h1>{report_title}</h1>
                <p>Plant: <strong>{plant_name}</strong> | Jurisdiction: {jurisdiction} | Prepared for: {tenant_name}</p>
            </div>
            <div style="text-align: right; font-size: 12px; color: #64748b;">
                <div>Data as of: <strong>{data.get('data_as_of')}</strong></div>
                <div>Generated: {data.get('prepared_on')}</div>
            </div>
        </div>

        <div class="disclaimer-box">
            <strong>Operational Readiness Document:</strong> {disclaimer}
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-val" style="color: #059669;">{metrics.get('readiness_percentage', 0)}%</div>
                <div class="metric-lbl">Readiness Score</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{metrics.get('total_applicable_requirements', 0)}</div>
                <div class="metric-lbl">Applicable Obligations</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color: #059669;">{metrics.get('verified_evidence_count', 0)}</div>
                <div class="metric-lbl">Verified Evidence</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color: #dc2626;">{metrics.get('missing_evidence_count', 0)}</div>
                <div class="metric-lbl">Missing Evidence Gaps</div>
            </div>
        </div>

        <h2>Applicable Regulatory Requirements & Evidence Status</h2>
        <table>
            <thead>
                <tr>
                    <th>Requirement Code</th>
                    <th>Obligation Title</th>
                    <th>Authority</th>
                    <th>Type</th>
                    <th>Evidence State</th>
                    <th>Valid Until</th>
                </tr>
            </thead>
            <tbody>
                {req_rows or '<tr><td colspan="6" style="text-align: center; color: #94a3b8;">No applicable requirements found.</td></tr>'}
            </tbody>
        </table>

        <h2>Missing or Unverified Evidence Items</h2>
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Obligation Reference</th>
                    <th>Authority & Type</th>
                    <th>Remediation Action</th>
                </tr>
            </thead>
            <tbody>
                {gap_rows or '<tr><td colspan="4" style="text-align: center; color: #059669;">No missing evidence items identified.</td></tr>'}
            </tbody>
        </table>

        <h2>Open Remediation Tasks</h2>
        <table>
            <thead>
                <tr>
                    <th>Task Description</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Due Date</th>
                    <th>Assignee</th>
                </tr>
            </thead>
            <tbody>
                {task_rows or '<tr><td colspan="5" style="text-align: center; color: #059669;">All remediation tasks completed.</td></tr>'}
            </tbody>
        </table>

        <div class="footer">
            <div>PlantProof Enterprise Regulatory Intelligence Engine</div>
            <div>Generated by: {data.get('generated_by_email', 'System')}</div>
        </div>
    </div>
</body>
</html>"""


report_service = ReportService()
