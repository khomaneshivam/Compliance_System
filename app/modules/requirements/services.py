"""
Requirements Register Query Service with Server-Side Filtering, Pagination and Provenance Assembly
"""

import math
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_, or_, desc, asc, func

from app.core.exceptions import EntityNotFoundError, TenantAccessDeniedError
from app.models.tenancy import User, Plant
from app.models.requirements import PlantRequirement, EvidenceLink
from app.models.catalog import StatutoryRequirement, RegulatoryAct, RegulatoryAuthority, ApplicabilityRule
from app.models.master_data import Jurisdiction
from app.models.documents import ComplianceDocument
from app.models.tasks import ComplianceTask, AuditLog
from app.models.assessments import AssessmentRun, AssessmentFinding, ProposedRequirementChange
from app.modules.requirements.schemas import (
    RequirementItemResponse,
    PaginatedRequirementsResponse,
    RequirementDetailResponse,
    StatutoryProvenance,
    EvidenceSummary,
    ApplicabilityProvenance,
    RequirementHistoryItem,
    SavedViewPreset,
)


class RequirementsService:
    def list_requirements(
        self,
        db: Session,
        user: User,
        plant_id: Optional[str] = None,
        applicability_status: Optional[str] = None,
        evidence_status: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        authority_code: Optional[str] = None,
        obligation_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "current_due_date",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedRequirementsResponse:
        """
        Server-side filtered, paginated query for company statutory requirements.
        Enforces strict tenant isolation.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        # Base statement joined with Plant and StatutoryRequirement
        stmt = (
            select(PlantRequirement)
            .join(PlantRequirement.plant)
            .join(PlantRequirement.statutory_requirement)
            .outerjoin(StatutoryRequirement.act)
            .outerjoin(RegulatoryAct.authority)
        )

        # Tenant isolation
        if user.role != "SUPER_ADMIN":
            stmt = stmt.where(Plant.tenant_id == user.tenant_id)

        if plant_id:
            stmt = stmt.where(PlantRequirement.plant_id == plant_id)

        # Filters
        if applicability_status and applicability_status.upper() != "ALL":
            stmt = stmt.where(PlantRequirement.applicability_status == applicability_status.upper())

        if evidence_status and evidence_status.upper() != "ALL":
            stmt = stmt.where(PlantRequirement.evidence_status == evidence_status.upper())

        if jurisdiction and jurisdiction.upper() != "ALL":
            stmt = stmt.where(Plant.jurisdiction == jurisdiction)

        if authority_code and authority_code.upper() != "ALL":
            stmt = stmt.where(RegulatoryAuthority.code == authority_code.upper())

        if obligation_type and obligation_type.upper() != "ALL":
            stmt = stmt.where(StatutoryRequirement.obligation_type == obligation_type.upper())

        # Search
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(StatutoryRequirement.code).like(term),
                    func.lower(StatutoryRequirement.title).like(term),
                    func.lower(StatutoryRequirement.description).like(term),
                    func.lower(RegulatoryAuthority.code).like(term),
                    func.lower(RegulatoryAuthority.name).like(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Sorting
        order_col = PlantRequirement.current_due_date
        if sort_by == "title":
            order_col = StatutoryRequirement.title
        elif sort_by == "code":
            order_col = StatutoryRequirement.code
        elif sort_by == "created_at":
            order_col = PlantRequirement.created_at
        elif sort_by == "evidence_status":
            order_col = PlantRequirement.evidence_status

        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(order_col).nulls_last())
        else:
            stmt = stmt.order_by(asc(order_col).nulls_last())

        # Pagination offset
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        requirements = list(db.scalars(stmt).all())
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        items = []
        for req in requirements:
            stat = req.statutory_requirement
            act = stat.act if stat else None
            auth = act.authority if act else None

            # Get task count for this requirement
            task_count = db.scalar(
                select(func.count(ComplianceTask.id)).where(ComplianceTask.plant_requirement_id == req.id)
            ) or 0

            evidence_count = len(req.evidence_links)

            items.append(
                RequirementItemResponse(
                    id=req.id,
                    statutory_requirement_id=stat.id if stat else "",
                    code=stat.code if stat else "UNKNOWN",
                    title=stat.title if stat else "Unknown Obligation",
                    description=stat.description if stat else None,
                    obligation_type=stat.obligation_type if stat else "CERTIFICATE",
                    authority_code=auth.code if auth else None,
                    authority_name=auth.name if auth else None,
                    jurisdiction=req.plant.jurisdiction if req.plant else None,
                    applicability_status=req.applicability_status,
                    evidence_status=req.evidence_status,
                    current_due_date=req.current_due_date,
                    owner_name=req.owner.full_name if req.owner else None,
                    owner_email=req.owner.email if req.owner else None,
                    evidence_count=evidence_count,
                    tasks_count=task_count,
                    is_custom=req.is_custom,
                    last_evaluated_at=req.last_evaluated_at,
                )
            )

        return PaginatedRequirementsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_requirement_detail(self, db: Session, user: User, requirement_id: str) -> RequirementDetailResponse:
        """
        Retrieves deep requirement details with complete provenance,
        deterministic applicability rationale, linked evidence documents, and version history.
        """
        req = db.get(PlantRequirement, requirement_id)
        if not req:
            # Try searching by statutory requirement id or code scoped to current tenant
            stmt = (
                select(PlantRequirement)
                .join(PlantRequirement.statutory_requirement)
                .join(PlantRequirement.plant)
                .where(
                    (PlantRequirement.id == requirement_id)
                    | (PlantRequirement.statutory_requirement_id == requirement_id)
                    | (StatutoryRequirement.code == requirement_id)
                )
            )
            if user.role != "SUPER_ADMIN":
                stmt = stmt.where(Plant.tenant_id == user.tenant_id)
            req = db.scalars(stmt).first()

        if not req:
            raise EntityNotFoundError("PlantRequirement", requirement_id)

        # Tenant isolation
        if user.role != "SUPER_ADMIN" and req.plant.tenant_id != user.tenant_id:
            raise TenantAccessDeniedError("Cross-tenant access prohibited.")

        stat = req.statutory_requirement
        act = stat.act if stat else None
        auth = act.authority if act else None

        # 1. Statutory Provenance & Rule Association
        rule = db.get(ApplicabilityRule, req.rule_version_id) if req.rule_version_id else None
        rule_ver = rule.rule_version if rule else 1

        section_clause = (
            rule.clause_reference
            if (rule and rule.clause_reference)
            else (f"Section 25/26" if "consent" in (stat.title or "").lower() else "Section 7/8")
        )
        gazette_ref = (
            rule.instrument_identifier
            if (rule and rule.instrument_identifier)
            else (f"Gazette Notification Pending" if rule else None)
        )
        source_url = (
            rule.official_source_url
            if (rule and rule.official_source_url)
            else (f"https://{auth.code.lower() if auth else 'mpcb'}.gov.in/statutes")
        )
        pub_date = rule.publication_date if rule else None
        source_status = rule.source_verification_status if rule else "UNVERIFIED_DEMO"
        is_verified = source_status == "VERIFIED"

        provenance = StatutoryProvenance(
            authority_code=auth.code if auth else None,
            authority_name=auth.name if auth else None,
            act_title=act.title if act else None,
            act_short_name=act.short_name if act else None,
            act_year=act.year if act else None,
            jurisdiction=req.plant.jurisdiction if req.plant else None,
            jurisdiction_level=auth.jurisdiction_level if auth else "STATE",
            section_clause=section_clause,
            gazette_reference=gazette_ref,
            official_source_url=source_url,
            publication_date=pub_date,
            source_verification_status=source_status,
            source_fingerprint=rule.source_fingerprint if rule else None,
            instrument_identifier=gazette_ref,
            is_verified=is_verified,
        )

        # 2. Applicability Provenance & Finding Trace
        finding = db.scalars(
            select(AssessmentFinding)
            .join(AssessmentRun, AssessmentRun.id == AssessmentFinding.assessment_run_id)
            .where(
                and_(
                    AssessmentRun.plant_id == req.plant_id,
                    AssessmentFinding.statutory_requirement_id == req.statutory_requirement_id,
                )
            )
            .order_by(AssessmentFinding.created_at.desc())
        ).first()

        condition_trace = finding.condition_results if finding else {}
        missing_facts = finding.missing_facts if finding else []
        matched_facts = finding.matched_facts if finding else {}

        if not matched_facts and req.plant and req.plant.profile:
            profile = req.plant.profile
            matched_facts = {
                "industry_category": profile.industry_category,
                "boiler_count": profile.boiler_count,
                "effluent_discharge_kld": float(profile.effluent_discharge_kld or 0.0),
                "connected_power_kw": float(profile.connected_power_kw or 0.0),
                "steam_capacity_tph": float(profile.steam_capacity_tph or 0.0),
            }

        applicability = ApplicabilityProvenance(
            applicability_status=req.applicability_status,
            applicability_rationale=req.applicability_rationale,
            rule_version=rule_ver,
            matched_facts=matched_facts,
            missing_facts=missing_facts,
            condition_trace=condition_trace,
            last_evaluated_at=req.last_evaluated_at,
        )

        # 3. Linked Evidence Documents
        evidence_list = []
        for link in req.evidence_links:
            doc = link.document
            if doc:
                evidence_list.append(
                    EvidenceSummary(
                        evidence_link_id=link.id,
                        document_id=doc.id,
                        original_filename=doc.original_filename,
                        mime_type=doc.mime_type,
                        file_size_bytes=doc.file_size_bytes,
                        storage_key=doc.storage_key,
                        upload_date=doc.created_at,
                        detected_expiry_date=doc.detected_expiry_date,
                        evidence_status=req.evidence_status,
                        review_status=doc.review_status,
                        verified_by=doc.reviewed_by.email if doc.reviewed_by else None,
                    )
                )

        # 4. Version & Audit History
        history = []
        # Audit log changes
        audit_records = list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.entity_id == req.id)
                .order_by(AuditLog.created_at.desc())
            ).all()
        )
        for a in audit_records:
            history.append(
                RequirementHistoryItem(
                    id=a.id,
                    action=a.action,
                    performed_by=a.user.email if a.user else "SYSTEM",
                    timestamp=a.created_at,
                    details=a.new_state or {},
                    summary_text=f"{a.action} performed on {req.statutory_requirement.code}",
                )
            )

        # Proposed changes history
        prop_changes = list(
            db.scalars(
                select(ProposedRequirementChange)
                .where(
                    ProposedRequirementChange.plant_id == req.plant_id,
                    ProposedRequirementChange.statutory_requirement_id == req.statutory_requirement_id,
                )
                .order_by(ProposedRequirementChange.created_at.desc())
            ).all()
        )
        for pc in prop_changes:
            history.append(
                RequirementHistoryItem(
                    id=pc.id,
                    action=f"PROPOSED_CHANGE_{pc.review_status}",
                    performed_by=(pc.reviewed_by.email if getattr(pc, "reviewed_by", None) else "APPLICABILITY_ENGINE"),
                    timestamp=pc.reviewed_at or pc.created_at,
                    details={"proposed_status": pc.proposed_status, "rationale": pc.rationale},
                    summary_text=f"Rule reassessment evaluated status as {pc.proposed_status}: {pc.rationale}",
                )
            )

        # Fallback baseline history entry if empty
        if not history:
            history.append(
                RequirementHistoryItem(
                    id="hist-baseline",
                    action="BASELINE_ASSESSMENT",
                    performed_by="Deterministic Applicability Engine v1.0",
                    timestamp=req.created_at,
                    details={"applicability_status": req.applicability_status},
                    summary_text=f"Baseline assessment evaluated requirement as {req.applicability_status}",
                )
            )

        task_count = db.scalar(
            select(func.count(ComplianceTask.id)).where(ComplianceTask.plant_requirement_id == req.id)
        ) or 0

        return RequirementDetailResponse(
            id=req.id,
            statutory_requirement_id=stat.id if stat else "",
            code=stat.code if stat else "UNKNOWN",
            title=stat.title if stat else "Unknown Obligation",
            description=stat.description if stat else None,
            obligation_type=stat.obligation_type if stat else "CERTIFICATE",
            authority_code=auth.code if auth else None,
            authority_name=auth.name if auth else None,
            jurisdiction=req.plant.jurisdiction if req.plant else None,
            applicability_status=req.applicability_status,
            evidence_status=req.evidence_status,
            current_due_date=req.current_due_date,
            owner_name=req.owner.full_name if req.owner else None,
            owner_email=req.owner.email if req.owner else None,
            evidence_count=len(evidence_list),
            tasks_count=task_count,
            is_custom=req.is_custom,
            last_evaluated_at=req.last_evaluated_at,
            provenance=provenance,
            applicability=applicability,
            evidence_list=evidence_list,
            history=history,
        )

    def get_saved_views(self, db: Session, user: User, plant_id: Optional[str] = None) -> List[SavedViewPreset]:
        """Provides pre-computed saved view counts for fast compliance triage."""
        base_stmt = select(PlantRequirement).join(PlantRequirement.plant)
        if user.role != "SUPER_ADMIN":
            base_stmt = base_stmt.where(Plant.tenant_id == user.tenant_id)
        if plant_id:
            base_stmt = base_stmt.where(PlantRequirement.plant_id == plant_id)

        # 1. Missing Evidence
        missing_count = db.scalar(
            select(func.count()).select_from(
                base_stmt.where(
                    PlantRequirement.applicability_status == "APPLICABLE",
                    PlantRequirement.evidence_status == "MISSING",
                ).subquery()
            )
        ) or 0

        # 2. Expiring in 30 Days
        today = date.today()
        in_30_days = today + timedelta(days=30)
        expiring_count = db.scalar(
            select(func.count()).select_from(
                base_stmt.where(
                    PlantRequirement.applicability_status == "APPLICABLE",
                    or_(
                        PlantRequirement.evidence_status == "EXPIRING_SOON",
                        and_(
                            PlantRequirement.current_due_date.isnot(None),
                            PlantRequirement.current_due_date <= in_30_days,
                        ),
                    ),
                ).subquery()
            )
        ) or 0

        # 3. High Priority Consents
        high_pri_count = db.scalar(
            select(func.count()).select_from(
                base_stmt.join(PlantRequirement.statutory_requirement)
                .where(
                    PlantRequirement.applicability_status == "APPLICABLE",
                    StatutoryRequirement.obligation_type.in_(["CONSENT", "CERTIFICATE"]),
                )
                .subquery()
            )
        ) or 0

        # 4. All Applicable
        all_app_count = db.scalar(
            select(func.count()).select_from(
                base_stmt.where(PlantRequirement.applicability_status == "APPLICABLE").subquery()
            )
        ) or 0

        return [
            SavedViewPreset(
                id="missing_evidence",
                name="Missing Evidence Gaps",
                description="Applicable obligations currently lacking a valid certificate or consent document",
                filter_params={"applicability_status": "APPLICABLE", "evidence_status": "MISSING"},
                count=missing_count,
            ),
            SavedViewPreset(
                id="expiring_soon",
                name="Expiring in 30 Days",
                description="Consents or inspection certificates requiring renewal in the near term",
                filter_params={"applicability_status": "APPLICABLE", "evidence_status": "EXPIRING_SOON"},
                count=expiring_count,
            ),
            SavedViewPreset(
                id="high_priority",
                name="Statutory Consents & Licences",
                description="Core operating permits and mandatory inspection certificates",
                filter_params={"applicability_status": "APPLICABLE", "obligation_type": "CONSENT"},
                count=high_pri_count,
            ),
            SavedViewPreset(
                id="all_applicable",
                name="All Applicable Obligations",
                description="Full inventory of all evaluated operational legal obligations",
                filter_params={"applicability_status": "APPLICABLE"},
                count=all_app_count,
            ),
        ]


requirements_service = RequirementsService()
