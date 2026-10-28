"""
Regulatory Ingestion Pipeline & Change Review Workflow Engine
Implements the 11-stage auditable regulatory ingestion lifecycle with
provenance tracking, diffing, AI drafting, human review gates, and impact evaluation.
"""

from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.core.exceptions import EntityNotFoundError, InsufficientPermissionsError, ConflictError
from app.models.tenancy import User, Plant
from app.models.profile import PlantProfile
from app.models.catalog import RegulatoryAuthority, StatutoryRequirement, ApplicabilityRule
from app.models.assessments import ProposedRequirementChange
from app.models.regulatory_intel import (
    RegulatorySource,
    RegulatoryDocument,
    RegulatoryChangeReview,
    RegulatoryChangeImpact,
    RegulatorySourceAuditLog,
)
from app.modules.regulatory_intel.adapters.base import FetchedRegulatoryPayload
from app.modules.regulatory_intel.adapters.fixture_adapter import LocalFixtureAdapter
from app.modules.regulatory_intel.adapters.http_adapter import SafeHttpDocumentAdapter
from app.modules.regulatory_intel.extractors.text_extractor import (
    RegulatoryTextExtractor,
    ExtractionFailedError,
    ExtractionResult,
)
from app.modules.regulatory_intel.diffing.differ import RegulatoryDiffer, DiffResult
from app.modules.regulatory_intel.ai_provider.provider import (
    DeterministicRegulatoryLLMProvider,
    AIDraftAnalysisResult,
)
from app.modules.applicability.engine import engine as applicability_engine
from app.modules.regulatory_intel.safeguards import (
    FileSizeExceededError,
    MalformedFileError,
    IngestionSecurityError,
    SourceUnavailableError,
    validate_file_content_safety,
    sanitize_source_error,
)
from decimal import Decimal


def compute_source_adapter_mode(source: RegulatorySource) -> str:
    """
    Computes customer-facing adapter mode: FIXTURE, LIVE_HTTP, DISABLED, or FAILED.
    Discloses honest operational origin to compliance reviewers.
    """
    if not source.is_active:
        return "DISABLED"
    if source.health_status == "UNAVAILABLE" or source.consecutive_failures >= 3:
        return "FAILED"
    if source.adapter_type == "LOCAL_FIXTURE" or (source.url and source.url.startswith("fixture://")):
        return "FIXTURE"
    return "LIVE_HTTP"



def _make_json_safe(data: Any) -> Any:
    """Recursively converts Decimals and date objects to JSON-serializable primitives."""
    if isinstance(data, dict):
        return {str(k): _make_json_safe(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [_make_json_safe(v) for v in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, (date, datetime)):
        return data.isoformat()
    return data


class RegulatoryIngestionPipeline:
    """
    Orchestrates the 11 pipeline stages from source fetch through human review and publication.
    """

    def __init__(self):
        self.extractor = RegulatoryTextExtractor()
        self.differ = RegulatoryDiffer()
        self.ai_provider = DeterministicRegulatoryLLMProvider()

    def get_adapter(self, source: RegulatorySource, scenario: str = "default"):
        """Returns the appropriate safe source adapter."""
        if source.adapter_type == "LOCAL_FIXTURE" or source.url.startswith("fixture://"):
            return LocalFixtureAdapter(source_code=source.code, base_url=source.url, scenario=scenario)
        return SafeHttpDocumentAdapter(
            source_code=source.code,
            base_url=source.url,
            rate_limit_per_minute=source.rate_limit_per_minute,
        )

    def trigger_source_poll(
        self,
        db: Session,
        source_id: str,
        scenario: str = "default",
        user: Optional[User] = None,
    ) -> List[RegulatoryChangeReview]:
        """
        Executes Pipeline Stages 1 to 8:
        1. Source check / rate limit
        2. Fetch metadata/content with timeout and size limits
        3. Stable identifier and SHA-256 hash deduplication
        4. Store original document & provenance
        5. Extract text safely with section/page tracking
        6. Compare with prior version (Diffing)
        7. AI-drafted structured summary, affected categories, snippets
        8. Create Change Review item in needs_review or extraction_failed
        """
        source = db.get(RegulatorySource, source_id)
        if not source:
            raise EntityNotFoundError("RegulatorySource", source_id)

        now = datetime.now(timezone.utc)
        source.last_checked_at = now
        performed_by_name = user.email if user else "SYSTEM_SCHEDULER"

        # Log Stage 1: Poll Attempt
        self._record_audit(
            db,
            source_id=source.id,
            action="POLL_ATTEMPT",
            performed_by=performed_by_name,
            details={"scenario": scenario, "source_code": source.code, "url": source.url},
        )

        created_reviews: List[RegulatoryChangeReview] = []
        adapter = self.get_adapter(source, scenario=scenario)

        try:
            # Stage 2: Fetch documents from adapter
            payloads = adapter.poll()

            for payload in payloads:
                # Stage 2b: Validate content limits and sanity
                validate_file_content_safety(payload.raw_bytes, payload.mime_type)

                # Stage 3: Hash deduplication check
                existing_doc = db.scalars(
                    select(RegulatoryDocument).where(RegulatoryDocument.content_hash == payload.content_hash)
                ).first()

                if existing_doc:
                    # Idempotent skip: Identical content hash already ingested
                    self._record_audit(
                        db,
                        source_id=source.id,
                        change_review_id=existing_doc.change_review.id if existing_doc.change_review else None,
                        action="DUPLICATE_SKIPPED",
                        performed_by=performed_by_name,
                        details={
                            "external_id": payload.external_id,
                            "content_hash": payload.content_hash,
                            "message": "Document identical to previously ingested revision; skipped creation.",
                        },
                    )
                    # Return existing change review if available
                    if existing_doc.change_review:
                        created_reviews.append(existing_doc.change_review)
                    continue

                # Stage 4: Store original document record
                doc = RegulatoryDocument(
                    source_id=source.id,
                    external_id=payload.external_id,
                    title=payload.title,
                    document_url=payload.document_url,
                    published_date=payload.published_date,
                    effective_date=payload.effective_date,
                    content_hash=payload.content_hash,
                    file_size_bytes=len(payload.raw_bytes),
                    mime_type=payload.mime_type,
                    ingestion_status="FETCHED",
                )
                db.add(doc)
                db.flush()

                fetch_log = self._record_audit(
                    db,
                    source_id=source.id,
                    action="DOCUMENT_FETCHED",
                    performed_by=performed_by_name,
                    details={
                        "document_id": doc.id,
                        "external_id": doc.external_id,
                        "content_hash": doc.content_hash,
                        "file_size_bytes": doc.file_size_bytes,
                    },
                )

                # Stage 5: Extract text safely
                try:
                    extraction: ExtractionResult = self.extractor.extract(payload.raw_bytes, payload.mime_type)
                    doc.raw_text = extraction.raw_text
                    doc.page_count = extraction.page_count
                    doc.sections = [s.model_dump() for s in extraction.sections]
                    doc.ingestion_status = "EXTRACTED"
                    db.flush()

                except ExtractionFailedError as ef:
                    # Handle extraction failure gracefully without crashing pipeline
                    doc.ingestion_status = "EXTRACTION_FAILED"
                    doc.failure_reason = ef.message
                    db.flush()

                    change_review = RegulatoryChangeReview(
                        source_id=source.id,
                        document_id=doc.id,
                        notification_number=payload.external_id,
                        title=payload.title,
                        published_date=payload.published_date,
                        effective_date=payload.effective_date,
                        summary_plain_language=f"Text extraction failed: {ef.message}",
                        key_changes_summary=["Document unreadable or corrupted"],
                        who_may_be_affected=["Manual plain-text upload required"],
                        evidence_snippets=[],
                        proposed_categories=["Uncategorized"],
                        confidence_score=0.0,
                        confidence_band="LOW",
                        detected_change_type="EXTRACTION_FAILED",
                        status="extraction_failed",
                    )
                    db.add(change_review)
                    db.flush()
                    fetch_log.change_review_id = change_review.id

                    self._record_audit(
                        db,
                        source_id=source.id,
                        change_review_id=change_review.id,
                        action="EXTRACTION_FAILED",
                        performed_by=performed_by_name,
                        details={"document_id": doc.id, "error": ef.message},
                    )
                    created_reviews.append(change_review)
                    continue

                # Stage 6: Locate prior baseline & compare (Diffing)
                target_req = None
                target_code = payload.metadata.get("target_requirement_code")
                if target_code:
                    target_req = db.scalars(
                        select(StatutoryRequirement).where(StatutoryRequirement.code == target_code)
                    ).first()

                old_text = None
                if target_req:
                    # Get latest active rule pass explanation or description as baseline text
                    active_rule = db.scalars(
                        select(ApplicabilityRule)
                        .where(
                            and_(
                                ApplicabilityRule.statutory_requirement_id == target_req.id,
                                ApplicabilityRule.status == "ACTIVE",
                            )
                        )
                    ).first()
                    if active_rule:
                        old_text = active_rule.pass_explanation_template or target_req.description

                diff_result: DiffResult = self.differ.compare(old_text, doc.raw_text)

                # Stage 7: AI draft structured summary & affected candidates
                ai_analysis: AIDraftAnalysisResult = self.ai_provider.draft_change_analysis(
                    extracted_text=doc.raw_text,
                    external_id=doc.external_id,
                    diff_summary=diff_result.diff_summary,
                    sections=doc.sections,
                )

                # Stage 8: Create Change Review item in 'needs_review'
                eff_date = payload.effective_date or ai_analysis.detected_effective_date or date.today()
                pub_date = payload.published_date or ai_analysis.detected_published_date or date.today()

                change_review = RegulatoryChangeReview(
                    source_id=source.id,
                    document_id=doc.id,
                    statutory_requirement_id=target_req.id if target_req else None,
                    notification_number=payload.external_id,
                    title=payload.title,
                    published_date=pub_date,
                    effective_date=eff_date,
                    summary_plain_language=ai_analysis.summary_plain_language,
                    key_changes_summary=ai_analysis.key_changes,
                    who_may_be_affected=ai_analysis.who_may_be_affected,
                    evidence_snippets=[s.model_dump() for s in ai_analysis.evidence_snippets],
                    proposed_categories=ai_analysis.proposed_categories,
                    confidence_score=ai_analysis.confidence_score,
                    confidence_band=ai_analysis.confidence_band,
                    detected_change_type=diff_result.detected_change_type,
                    old_text=old_text,
                    new_text=doc.raw_text[:2000],
                    diff_summary=diff_result.diff_summary,
                    status="needs_review",
                )
                db.add(change_review)
                db.flush()
                fetch_log.change_review_id = change_review.id

                self._record_audit(
                    db,
                    source_id=source.id,
                    change_review_id=change_review.id,
                    action="AI_DRAFT_ANALYSIS",
                    performed_by=performed_by_name,
                    details={
                        "change_review_id": change_review.id,
                        "confidence": ai_analysis.confidence_score,
                        "confidence_band": ai_analysis.confidence_band,
                        "detected_change_type": diff_result.detected_change_type,
                        "categories": ai_analysis.proposed_categories,
                    },
                )
                created_reviews.append(change_review)

            # Update Source status to HEALTHY upon success
            source.health_status = "HEALTHY"
            source.last_successful_check_at = now
            source.consecutive_failures = 0
            source.error_message = None
            db.commit()

            return created_reviews

        except Exception as e:
            # Handle source unavailable, network timeout, or size boundary errors with sanitized messages
            category, clean_error = sanitize_source_error(e)
            source.consecutive_failures += 1
            source.error_message = clean_error
            if source.consecutive_failures >= 3:
                source.health_status = "UNAVAILABLE"
            else:
                source.health_status = "DEGRADED"

            self._record_audit(
                db,
                source_id=source.id,
                action="SOURCE_CHECK_FAILED",
                performed_by=performed_by_name,
                details={
                    "consecutive_failures": source.consecutive_failures,
                    "error_category": category,
                    "error": clean_error,
                },
            )
            db.commit()

            if isinstance(e, (ConnectionError, TimeoutError)):
                raise SourceUnavailableError(clean_error)
            raise e


    def save_draft_analysis(
        self,
        db: Session,
        change_id: str,
        summary_plain_language: Optional[str] = None,
        effective_date: Optional[date] = None,
        proposed_categories: Optional[List[str]] = None,
        statutory_requirement_id: Optional[str] = None,
        applicability_ast: Optional[Dict[str, Any]] = None,
        user: Optional[User] = None,
    ) -> RegulatoryChangeReview:
        """Stage 9: Reviewer edits proposed summary, dates, categories, or AST."""
        review = db.get(RegulatoryChangeReview, change_id)
        if not review:
            raise EntityNotFoundError("RegulatoryChangeReview", change_id)

        if review.status in ("approved", "published", "superseded"):
            raise ConflictError(f"Cannot edit change review in finalized state '{review.status}'.")

        if summary_plain_language is not None:
            review.summary_plain_language = summary_plain_language
        if effective_date is not None:
            review.effective_date = effective_date
        if proposed_categories is not None:
            review.proposed_categories = proposed_categories
        if statutory_requirement_id is not None:
            review.statutory_requirement_id = statutory_requirement_id
        if applicability_ast is not None:
            review.approved_applicability_ast = applicability_ast

        review.status = "draft_analysis"

        self._record_audit(
            db,
            source_id=review.source_id,
            change_review_id=review.id,
            action="REVIEW_DRAFT_SAVED",
            performed_by=user.email if user else "SYSTEM",
            details={"status": review.status, "updated_fields": ["summary", "dates", "categories"]},
        )
        db.commit()
        db.refresh(review)
        return review

    def submit_review_decision(
        self,
        db: Session,
        change_id: str,
        decision: str,
        review_notes: str,
        user: User,
        effective_date: Optional[date] = None,
        applicability_ast: Optional[Dict[str, Any]] = None,
        target_requirement_code: Optional[str] = None,
    ) -> Tuple[RegulatoryChangeReview, List[RegulatoryChangeImpact]]:
        """
        Executes Pipeline Stages 9, 10, and 11:
        9. Reviewer approves/rejects with audit justification.
        10. On approval:
            - Creates immutable version N+1.
            - Supersedes prior active rule.
            - Evaluates impact against all company profiles.
            - Creates ProposedRequirementChange items for human review in tenant queues.
        11. Complete immutable audit trail.
        """
        review = db.get(RegulatoryChangeReview, change_id)
        if not review:
            raise EntityNotFoundError("RegulatoryChangeReview", change_id)

        now = datetime.now(timezone.utc)
        clean_decision = decision.strip().upper()
        impacts: List[RegulatoryChangeImpact] = []

        if clean_decision == "REJECT":
            review.status = "rejected"
            review.review_decision = "REJECT"
            review.review_notes = review_notes
            review.reviewed_by_user_id = user.id
            review.reviewed_at = now

            self._record_audit(
                db,
                source_id=review.source_id,
                change_review_id=review.id,
                action="REVIEW_REJECTED",
                performed_by=user.email,
                details={"rejection_notes": review_notes},
            )
            db.commit()
            db.refresh(review)
            return review, impacts

        if clean_decision != "APPROVE":
            raise IngestionSecurityError(f"Decision must be 'APPROVE' or 'REJECT', got '{decision}'.")

        # ----------------------------------------------------------------------
        # STAGE 10: Approval & Immutable Rule Creation
        # ----------------------------------------------------------------------
        review.review_decision = "APPROVE"
        review.review_notes = review_notes
        review.reviewed_by_user_id = user.id
        review.reviewed_at = now
        review.approved_effective_date = effective_date or review.effective_date or date.today()

        # Identify target statutory requirement
        stat_req = None
        if target_requirement_code:
            stat_req = db.scalars(
                select(StatutoryRequirement).where(StatutoryRequirement.code == target_requirement_code)
            ).first()
        elif review.statutory_requirement_id:
            stat_req = db.get(StatutoryRequirement, review.statutory_requirement_id)
        else:
            # Default to first statutory requirement if unspecified
            stat_req = db.scalars(select(StatutoryRequirement)).first()

        if not stat_req:
            raise EntityNotFoundError("StatutoryRequirement", target_requirement_code or "DEFAULT")

        review.statutory_requirement_id = stat_req.id

        # Supersede prior active rule
        active_rule = db.scalars(
            select(ApplicabilityRule).where(
                and_(
                    ApplicabilityRule.statutory_requirement_id == stat_req.id,
                    ApplicabilityRule.status == "ACTIVE",
                )
            )
        ).first()

        old_version = active_rule.rule_version if active_rule else 0
        new_version = old_version + 1

        if active_rule:
            active_rule.status = "SUPERSEDED"
            active_rule.effective_to = review.approved_effective_date
            review.superseded_rule_id = active_rule.id

        # Determine AST condition tree
        final_ast = applicability_ast or review.approved_applicability_ast
        if not final_ast:
            if active_rule:
                final_ast = active_rule.expression_ast
            else:
                final_ast = {"field": "industry_category", "operator": "in", "value": ["RED", "ORANGE"]}

        # Create new immutable rule version
        new_rule = ApplicabilityRule(
            statutory_requirement_id=stat_req.id,
            rule_version=new_version,
            expression_ast=final_ast,
            pass_explanation_template=review.summary_plain_language,
            fail_explanation_template="Plant parameters do not trigger this amended statutory obligation.",
            status="ACTIVE",
            effective_from=review.approved_effective_date,
            change_rationale=f"Approved per regulatory update {review.notification_number}: {review_notes}",
            is_immutable=True,
            approved_by_user_id=user.id,
            approved_at=now,
        )
        db.add(new_rule)
        db.flush()

        review.published_rule_id = new_rule.id
        review.status = "published"

        # ----------------------------------------------------------------------
        # STAGE 10 (cont): Impact Evaluation Against Company Profiles
        # ----------------------------------------------------------------------
        all_plants = db.scalars(select(Plant)).all()

        for plant in all_plants:
            profile = db.scalars(select(PlantProfile).where(PlantProfile.plant_id == plant.id)).first()
            # Assemble facts
            facts: Dict[str, Any] = {
                "jurisdiction": plant.jurisdiction,
                "district": plant.district,
                "plant_name": plant.name,
                "industry_category": profile.industry_category if profile else None,
                "employee_count": profile.employee_count if profile else None,
                "hazardous_waste_tpa": profile.hazardous_waste_tpa if profile else None,
                "effluent_discharge_kld": profile.effluent_discharge_kld if profile else None,
                "boiler_count": profile.boiler_count if profile else 0,
                "steam_capacity_tph": profile.steam_capacity_tph if profile else 0.0,
            }
            if profile and isinstance(profile.raw_attributes, dict):
                facts.update(profile.raw_attributes)

            outcome = applicability_engine.evaluate_rule(final_ast, facts, pass_template=review.summary_plain_language)

            if outcome.status == "APPLICABLE":
                impact_status = "POTENTIALLY_APPLICABLE"
            elif outcome.status == "NEEDS_REVIEW":
                impact_status = "REQUIRES_REVIEW"
            else:
                impact_status = "NOT_APPLICABLE"

            # Record facility impact
            impact = RegulatoryChangeImpact(
                change_review_id=review.id,
                plant_id=plant.id,
                tenant_id=plant.tenant_id,
                impact_status=impact_status,
                matched_facts=_make_json_safe(outcome.matched_facts),
                missing_facts=_make_json_safe(outcome.missing_facts),
                explanation=outcome.explanation,
            )
            db.add(impact)
            impacts.append(impact)

            # Safeguard: Queue ProposedRequirementChange in human review queue
            # Never silently alter customer obligations without permitted plant reviewer confirmation
            if impact_status in ("POTENTIALLY_APPLICABLE", "REQUIRES_REVIEW"):
                prop_status = "APPLICABLE" if impact_status == "POTENTIALLY_APPLICABLE" else "NEEDS_REVIEW"
                prop_change = ProposedRequirementChange(
                    plant_id=plant.id,
                    statutory_requirement_id=stat_req.id,
                    rule_version_id=new_rule.id,
                    change_type="STATUS_MODIFIED" if review.detected_change_type == "AMENDMENT" else "NEW_REQUIREMENT",
                    previous_status="ACTIVE",
                    proposed_status=prop_status,
                    rationale=f"Regulatory update {review.notification_number} published: {review.summary_plain_language[:200]}",
                    review_status="PENDING_REVIEW",
                )
                db.add(prop_change)

        # Stage 11: Complete Audit Trail Logging
        self._record_audit(
            db,
            source_id=review.source_id,
            change_review_id=review.id,
            action="REVIEW_APPROVED",
            performed_by=user.email,
            details={
                "decision": "APPROVE",
                "published_rule_version": new_version,
                "superseded_rule_id": review.superseded_rule_id,
                "impacted_plants_count": len(impacts),
                "review_notes": review_notes,
            },
        )

        db.commit()
        db.refresh(review)
        return review, impacts

    def _record_audit(
        self,
        db: Session,
        action: str,
        performed_by: str,
        details: Dict[str, Any],
        source_id: Optional[str] = None,
        change_review_id: Optional[str] = None,
    ) -> RegulatorySourceAuditLog:
        """Records an immutable audit event."""
        log = RegulatorySourceAuditLog(
            source_id=source_id,
            change_review_id=change_review_id,
            action=action,
            performed_by=performed_by,
            details=_make_json_safe(details),
        )
        db.add(log)
        db.flush()
        return log


pipeline = RegulatoryIngestionPipeline()
