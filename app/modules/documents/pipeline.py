"""
Document Ingestion, Extraction Job Orchestrator & Human Review Workflow Pipeline
Coordinates upload validation, private vault storage, asynchronous extraction with retry,
deterministic rules, and evidence linking.
"""

from datetime import datetime, date, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.core.exceptions import EntityNotFoundError, InsufficientPermissionsError, ConflictError
from app.models.tenancy import User, Plant
from app.models.catalog import StatutoryRequirement
from app.models.requirements import PlantRequirement, EvidenceLink
from app.models.documents import (
    ComplianceDocument,
    ExtractedField,
    ValidationCheck,
    ComplianceDocumentAudit,
)
from app.modules.documents.safeguards import (
    validate_upload_safety,
    compute_sha256,
    sanitize_filename,
    DocumentSecurityError,
    sanitize_document_error,
)

from app.modules.documents.storage import vault_storage
from app.modules.documents.extractors import DocumentTextExtractor
from app.modules.documents.ai_service import ai_extractor_provider, DocumentAIExtractionOutput


class DocumentProcessingPipeline:
    """
    Orchestrates the complete document evidence lifecycle.
    """

    def __init__(self):
        self.text_extractor = DocumentTextExtractor()
        self.ai_provider = ai_extractor_provider

    def ingest_document(
        self,
        db: Session,
        plant_id: str,
        file_bytes: bytes,
        original_filename: str,
        declared_mime: str,
        user: User,
        document_type_id: Optional[str] = None,
        auto_extract: bool = True,
    ) -> ComplianceDocument:
        """
        Stage 1 to 4:
        Validates safety, computes content hash, detects duplicates,
        saves to private vault under random key, and stages extraction job.
        """
        plant = db.get(Plant, plant_id)
        if not plant:
            raise EntityNotFoundError("Plant", plant_id)

        # Enforce tenant scoping: User must belong to the plant's tenant
        if user.role != "SUPER_ADMIN" and plant.tenant_id != user.tenant_id:
            raise InsufficientPermissionsError("Cross-tenant document upload prohibited.")

        # 1. Multi-layered binary & format validation
        safe_filename = sanitize_filename(original_filename)
        canonical_mime, page_count = validate_upload_safety(
            file_bytes=file_bytes,
            original_filename=safe_filename,
            declared_mime=declared_mime,
        )

        # 2. Cryptographic content hash
        content_hash = compute_sha256(file_bytes)

        # 3. Duplicate document detection
        existing_doc = db.scalars(
            select(ComplianceDocument).where(
                and_(
                    ComplianceDocument.plant_id == plant.id,
                    ComplianceDocument.content_hash == content_hash,
                    ComplianceDocument.is_archived == False,
                )
            )
        ).first()

        is_duplicate = False
        duplicate_of_id = None
        if existing_doc:
            # Cardinal Rule: Never silently merge records!
            is_duplicate = True
            duplicate_of_id = existing_doc.id

        # 4. Save to private vault under random storage key
        storage_key, relative_storage_path = vault_storage.save_file(
            content=file_bytes,
            tenant_id=plant.tenant_id,
        )

        doc = ComplianceDocument(
            tenant_id=plant.tenant_id,
            plant_id=plant.id,
            original_filename=safe_filename,
            storage_path=relative_storage_path,
            storage_key=storage_key,
            mime_type=canonical_mime,
            file_size_bytes=len(file_bytes),
            content_hash=content_hash,
            page_count=page_count,
            document_type_id=document_type_id,
            extraction_status="QUEUED",
            review_status="PENDING_REVIEW",
            uploaded_by_user_id=user.id,
            is_duplicate=is_duplicate,
            duplicate_of_id=duplicate_of_id,
            expiry_reminder_days=30,
        )
        db.add(doc)
        db.flush()

        # Audit: Document Uploaded
        self._record_audit(
            db=db,
            document_id=doc.id,
            action="DOCUMENT_UPLOADED",
            performed_by=user.email,
            details={
                "original_filename": safe_filename,
                "file_size_bytes": doc.file_size_bytes,
                "mime_type": canonical_mime,
                "page_count": page_count,
                "content_hash": content_hash,
                "is_duplicate": is_duplicate,
                "duplicate_of_id": duplicate_of_id,
                "storage_key": storage_key,
            },
        )

        db.commit()
        db.refresh(doc)

        # Execute extraction immediately (synchronous fallback for zero-dependency tests)
        if auto_extract:
            self.execute_extraction(db=db, document_id=doc.id, user_email=user.email)
            db.refresh(doc)

        return doc

    def execute_extraction(
        self,
        db: Session,
        document_id: str,
        user_email: str = "SYSTEM_WORKER",
    ) -> ComplianceDocument:
        """
        Stage 5 to 7:
        OCR / text extraction, PII minimization, schema-constrained AI extraction,
        and deterministic compliance rule validation.
        """
        doc = db.get(ComplianceDocument, document_id)
        if not doc:
            raise EntityNotFoundError("ComplianceDocument", document_id)

        now = datetime.now(timezone.utc)
        doc.extraction_status = "PROCESSING"
        db.flush()

        try:
            # 1. Fetch file bytes from private vault
            file_bytes = vault_storage.get_file(doc.storage_path, tenant_id=doc.tenant_id)

            # 2. Safe text & page extraction
            pages = self.text_extractor.extract_pages(file_bytes=file_bytes, mime_type=doc.mime_type)

            # 3. AI schema extraction with PII minimization and confidence scoring
            extraction_output: DocumentAIExtractionOutput = self.ai_provider.extract_document(
                pages=pages,
                original_filename=doc.original_filename,
            )

            # 4. Clear any previous fields / checks for clean idempotency
            for old_field in list(doc.extracted_fields):
                db.delete(old_field)
            for old_check in list(doc.validation_checks):
                db.delete(old_check)
            db.flush()

            # 5. Persist extracted fields
            for f in extraction_output.fields:
                ef = ExtractedField(
                    document_id=doc.id,
                    field_key=f.key,
                    extracted_value=f.value,
                    confirmed_value=f.value,
                    confidence_score=f.confidence_score,
                    confidence_band=f.confidence_band,
                    source_page=f.source_page,
                    source_snippet=f.source_snippet,
                    field_type=f.field_type,
                    is_mandatory=f.is_mandatory,
                    is_overridden=False,
                )
                db.add(ef)

            # 6. Persist deterministic validation checks
            for c in extraction_output.validation_checks:
                vc = ValidationCheck(
                    document_id=doc.id,
                    check_code=c.check_code,
                    check_name=c.check_name,
                    status=c.status,
                    details=c.details,
                )
                db.add(vc)

            # 7. Update document state
            doc.document_type_detected = extraction_output.document_type_detected
            doc.detected_issue_date = extraction_output.detected_issue_date
            doc.detected_expiry_date = extraction_output.detected_expiry_date
            doc.extraction_status = "EXTRACTED"
            doc.extraction_error = None
            doc.extracted_metadata = {
                "provider": extraction_output.provider_name,
                "provider_mode": getattr(extraction_output, "provider_mode", "FIXTURE"),
                "model_version": extraction_output.model_version,
                "schema_version": extraction_output.schema_version,
                "has_expiry": extraction_output.has_expiry,
                "summary": extraction_output.raw_text_summary,
            }

            self._record_audit(
                db=db,
                document_id=doc.id,
                action="EXTRACTION_COMPLETED",
                performed_by=user_email,
                details={
                    "document_type": extraction_output.document_type_detected,
                    "confidence_score": extraction_output.confidence_score,
                    "provider_mode": getattr(extraction_output, "provider_mode", "FIXTURE"),
                    "fields_count": len(extraction_output.fields),
                    "checks_count": len(extraction_output.validation_checks),
                    "detected_expiry_date": extraction_output.detected_expiry_date.isoformat() if extraction_output.detected_expiry_date else None,
                },
            )

            db.commit()
            return doc

        except Exception as e:
            category, clean_error = sanitize_document_error(e)
            doc.extraction_status = "EXTRACTION_FAILED"
            doc.extraction_error = clean_error
            metadata = dict(doc.extracted_metadata or {})
            metadata["error_category"] = category
            metadata["provider_mode"] = "FAILED"
            doc.extracted_metadata = metadata
            self._record_audit(
                db=db,
                document_id=doc.id,
                action="EXTRACTION_FAILED",
                performed_by=user_email,
                details={"error_category": category, "error": clean_error},
            )
            db.commit()
            return doc


    def update_field_values(
        self,
        db: Session,
        document_id: str,
        field_updates: Dict[str, str],
        user: User,
    ) -> ComplianceDocument:
        """Allows reviewer to edit/override extracted fields."""
        doc = db.get(ComplianceDocument, document_id)
        if not doc:
            raise EntityNotFoundError("ComplianceDocument", document_id)

        overridden_keys = []
        for ef in doc.extracted_fields:
            if ef.field_key in field_updates:
                new_val = field_updates[ef.field_key]
                if new_val != ef.confirmed_value:
                    ef.confirmed_value = new_val
                    ef.is_overridden = True
                    overridden_keys.append(ef.field_key)

        self._record_audit(
            db=db,
            document_id=doc.id,
            action="FIELD_OVERRIDDEN",
            performed_by=user.email,
            details={"overridden_fields": overridden_keys},
        )
        db.commit()
        db.refresh(doc)
        return doc

    def submit_review_decision(
        self,
        db: Session,
        document_id: str,
        decision: str,
        user: User,
        review_notes: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        link_to_statutory_requirement_id: Optional[str] = None,
        expiry_reminder_days: Optional[int] = None,
        field_overrides: Optional[Dict[str, str]] = None,
    ) -> ComplianceDocument:
        """
        Stage 8 to 10:
        Human review gate. Approves or rejects document.
        Links approved document as evidence to plant requirement.
        """
        doc = db.get(ComplianceDocument, document_id)
        if not doc:
            raise EntityNotFoundError("ComplianceDocument", document_id)

        now = datetime.now(timezone.utc)
        today = date.today()

        if expiry_reminder_days:
            doc.expiry_reminder_days = expiry_reminder_days

        # Apply field overrides if provided in review payload
        if field_overrides:
            for ef in doc.extracted_fields:
                if ef.field_key in field_overrides:
                    ef.confirmed_value = field_overrides[ef.field_key]
                    ef.is_overridden = True

        if decision == "REJECT":
            doc.review_status = "REJECTED"
            doc.reviewed_by_user_id = user.id
            doc.reviewed_at = now
            doc.rejection_reason = rejection_reason or review_notes or "Rejected during human compliance verification."

            self._record_audit(
                db=db,
                document_id=doc.id,
                action="DOCUMENT_REJECTED",
                performed_by=user.email,
                details={"rejection_reason": doc.rejection_reason},
            )
            db.commit()
            db.refresh(doc)
            return doc

        # Decision: APPROVE or EDIT_AND_APPROVE
        any_overridden = any(ef.is_overridden for ef in doc.extracted_fields)
        doc.review_status = "EDITED_AND_APPROVED" if any_overridden else "APPROVED"
        doc.reviewed_by_user_id = user.id
        doc.reviewed_at = now

        # Link as Evidence to Plant Requirement if statutory requirement specified
        if link_to_statutory_requirement_id:
            stat_req = db.get(StatutoryRequirement, link_to_statutory_requirement_id)
            if not stat_req:
                # Try finding by code
                stat_req = db.scalars(
                    select(StatutoryRequirement).where(StatutoryRequirement.code == link_to_statutory_requirement_id)
                ).first()

            if stat_req:
                plant_req = db.scalars(
                    select(PlantRequirement).where(
                        and_(
                            PlantRequirement.plant_id == doc.plant_id,
                            PlantRequirement.statutory_requirement_id == stat_req.id,
                        )
                    )
                ).first()

                if not plant_req:
                    # Create requirement register item if not already in register
                    plant_req = PlantRequirement(
                        plant_id=doc.plant_id,
                        statutory_requirement_id=stat_req.id,
                        applicability_status="APPLICABLE",
                        applicability_rationale=f"Linked to verified document {doc.original_filename}",
                        evidence_status="MISSING",
                        current_due_date=doc.detected_expiry_date,
                    )
                    db.add(plant_req)
                    db.flush()

                # Calculate deterministic evidence status
                evidence_status = "VALID"
                if doc.detected_expiry_date:
                    if doc.detected_expiry_date < today:
                        evidence_status = "EXPIRED"
                    elif (doc.detected_expiry_date - today).days <= doc.expiry_reminder_days:
                        evidence_status = "EXPIRING_SOON"
                    else:
                        evidence_status = "VALID"
                else:
                    # Permanent/perpetual document without expiry
                    evidence_status = "VALID"

                plant_req.evidence_status = evidence_status
                plant_req.current_due_date = doc.detected_expiry_date

                # Check if evidence link already exists
                existing_link = db.scalars(
                    select(EvidenceLink).where(
                        and_(
                            EvidenceLink.plant_requirement_id == plant_req.id,
                            EvidenceLink.document_id == doc.id,
                        )
                    )
                ).first()

                if not existing_link:
                    ev_link = EvidenceLink(
                        plant_requirement_id=plant_req.id,
                        document_id=doc.id,
                        linked_by_user_id=user.id,
                    )
                    db.add(ev_link)
                    db.flush()

                self._record_audit(
                    db=db,
                    document_id=doc.id,
                    action="EVIDENCE_LINKED",
                    performed_by=user.email,
                    details={
                        "plant_requirement_id": plant_req.id,
                        "statutory_code": stat_req.code,
                        "evidence_status": evidence_status,
                    },
                )

        self._record_audit(
            db=db,
            document_id=doc.id,
            action="DOCUMENT_APPROVED",
            performed_by=user.email,
            details={
                "review_status": doc.review_status,
                "review_notes": review_notes,
                "linked_requirement": link_to_statutory_requirement_id,
            },
        )

        db.commit()
        db.refresh(doc)
        return doc

    def _record_audit(
        self,
        db: Session,
        document_id: str,
        action: str,
        performed_by: str,
        details: Dict[str, Any],
    ) -> ComplianceDocumentAudit:
        """Records an immutable audit log entry."""
        audit = ComplianceDocumentAudit(
            document_id=document_id,
            action=action,
            performed_by=performed_by,
            details=details,
        )
        db.add(audit)
        db.flush()
        return audit


pipeline = DocumentProcessingPipeline()
