"""
FastAPI REST API Router for Secure Document & Evidence Management
Provides upload, streaming preview, extracted field review, validation checks,
and immutable audit history endpoints.
"""

import io
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.rate_limit import rate_limit
from app.core.exceptions import EntityNotFoundError, InsufficientPermissionsError, ConflictError, TenantAccessDeniedError
from app.models.tenancy import User, Plant
from app.models.documents import ComplianceDocument, ComplianceDocumentAudit
from app.modules.documents.schemas import (
    DocumentUploadResponse,
    DocumentDetailResponse,
    ExtractedFieldResponse,
    ValidationCheckResponse,
    LinkedRequirementSummary,
    FieldUpdateRequest,
    DocumentReviewDecisionRequest,
    DocumentAuditLogResponse,
)
from app.modules.documents.storage import vault_storage
from app.modules.documents.safeguards import DocumentSecurityError
from app.modules.documents.pipeline import pipeline

documents_router = APIRouter(prefix="/documents", tags=["Document & Evidence Vault"])


@documents_router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Compliance Document to Secure Vault",
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60, key_prefix="doc_upload"))],
)
async def upload_document_endpoint(
    plant_id: str = Form(...),
    document_type_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
):
    """
    Safely validates file signature, checks content hash for duplicates,
    persists in private tenant vault under random storage key, and triggers extraction.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    try:
        doc = pipeline.ingest_document(
            db=db,
            plant_id=plant_id,
            file_bytes=file_bytes,
            original_filename=file.filename or "unnamed_document.pdf",
            declared_mime=file.content_type or "application/octet-stream",
            user=current_user,
            document_type_id=document_type_id,
            auto_extract=True,
        )
        return doc
    except DocumentSecurityError as dse:
        raise HTTPException(status_code=400, detail=dse.message)
    except InsufficientPermissionsError as ipe:
        raise HTTPException(status_code=403, detail=ipe.message)


@documents_router.get("", response_model=List[DocumentUploadResponse], summary="List Documents for Tenant / Plant")
def list_documents_endpoint(
    plant_id: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    extraction_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists compliance documents with tenant isolation enforcement."""
    stmt = select(ComplianceDocument).where(ComplianceDocument.is_archived == False)

    # Scoping
    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(ComplianceDocument.tenant_id == current_user.tenant_id)

    if plant_id:
        stmt = stmt.where(ComplianceDocument.plant_id == plant_id)
    if review_status:
        stmt = stmt.where(ComplianceDocument.review_status == review_status)
    if extraction_status:
        stmt = stmt.where(ComplianceDocument.extraction_status == extraction_status)

    stmt = stmt.order_by(desc(ComplianceDocument.created_at))
    return list(db.scalars(stmt).all())


@documents_router.get("/{document_id}", response_model=DocumentDetailResponse, summary="Get Document Review Details")
def get_document_detail_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves document metadata, extracted fields with grounding, and validation checks."""
    doc = db.get(ComplianceDocument, document_id)
    if not doc:
        raise EntityNotFoundError("ComplianceDocument", document_id)

    if current_user.role != "SUPER_ADMIN" and doc.tenant_id != current_user.tenant_id:
        raise TenantAccessDeniedError("Cross-tenant document access denied.")

    # Format linked requirements
    linked = []
    for link in doc.evidence_links:
        pr = link.plant_requirement
        if pr and pr.statutory_requirement:
            linked.append(
                LinkedRequirementSummary(
                    evidence_link_id=link.id,
                    plant_requirement_id=pr.id,
                    statutory_code=pr.statutory_requirement.code,
                    statutory_title=pr.statutory_requirement.title,
                    evidence_status=pr.evidence_status,
                )
            )

    return DocumentDetailResponse(
        id=doc.id,
        plant_id=doc.plant_id,
        plant_name=doc.plant.name if doc.plant else "Unknown Plant",
        tenant_id=doc.tenant_id,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        content_hash=doc.content_hash,
        page_count=doc.page_count,
        storage_key=doc.storage_key,
        document_type_detected=doc.document_type_detected,
        extraction_status=doc.extraction_status,
        extraction_error=doc.extraction_error,
        extracted_metadata=doc.extracted_metadata,
        review_status=doc.review_status,
        detected_issue_date=doc.detected_issue_date,
        detected_expiry_date=doc.detected_expiry_date,
        is_duplicate=doc.is_duplicate,
        duplicate_of_id=doc.duplicate_of_id,
        expiry_reminder_days=doc.expiry_reminder_days,
        uploaded_by=doc.uploaded_by.email if doc.uploaded_by else None,
        reviewed_by=doc.reviewed_by.email if doc.reviewed_by else None,
        reviewed_at=doc.reviewed_at,
        rejection_reason=doc.rejection_reason,
        extracted_fields=[ExtractedFieldResponse.model_validate(f) for f in doc.extracted_fields],
        validation_checks=[ValidationCheckResponse.model_validate(c) for c in doc.validation_checks],
        linked_requirements=linked,
        created_at=doc.created_at,
    )


@documents_router.get("/{document_id}/file", summary="Stream Original Document from Private Vault")
def stream_document_file_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Securely streams original document file bytes with inline preview headers.
    Enforces strict tenant isolation.
    """
    doc = db.get(ComplianceDocument, document_id)
    if not doc:
        raise EntityNotFoundError("ComplianceDocument", document_id)

    if current_user.role != "SUPER_ADMIN" and doc.tenant_id != current_user.tenant_id:
        raise TenantAccessDeniedError("Cross-tenant document access denied.")

    file_bytes = vault_storage.get_file(doc.storage_path, tenant_id=doc.tenant_id)
    stream = io.BytesIO(file_bytes)

    safe_filename = re.sub(r'[\r\n"\\;]', '_', doc.original_filename or "document.pdf")
    headers = {
        "Content-Disposition": f'inline; filename="{safe_filename}"',
        "Content-Length": str(len(file_bytes)),
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(stream, media_type=doc.mime_type, headers=headers)


@documents_router.patch("/{document_id}/fields", response_model=DocumentDetailResponse, summary="Reviewer Field Override")
def update_document_fields_endpoint(
    document_id: str,
    request: FieldUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
):
    """Allows authorized reviewers to edit and confirm extracted fields."""
    doc = db.get(ComplianceDocument, document_id)
    if not doc:
        raise EntityNotFoundError("ComplianceDocument", document_id)

    if current_user.role != "SUPER_ADMIN" and doc.tenant_id != current_user.tenant_id:
        raise TenantAccessDeniedError("Cross-tenant document modification prohibited.")

    pipeline.update_field_values(
        db=db,
        document_id=doc.id,
        field_updates=request.fields,
        user=current_user,
    )
    return get_document_detail_endpoint(document_id, db=db, current_user=current_user)


@documents_router.post("/{document_id}/review", response_model=DocumentDetailResponse, summary="Submit Review Decision")
def submit_review_decision_endpoint(
    document_id: str,
    request: DocumentReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
):
    """
    Human review gate. Approves/rejects document and links approved document as evidence.
    """
    doc = db.get(ComplianceDocument, document_id)
    if not doc:
        raise EntityNotFoundError("ComplianceDocument", document_id)

    if current_user.role != "SUPER_ADMIN" and doc.tenant_id != current_user.tenant_id:
        raise TenantAccessDeniedError("Cross-tenant review decision prohibited.")

    pipeline.submit_review_decision(
        db=db,
        document_id=doc.id,
        decision=request.decision,
        user=current_user,
        review_notes=request.review_notes,
        rejection_reason=request.rejection_reason,
        link_to_statutory_requirement_id=request.link_to_statutory_requirement_id,
        expiry_reminder_days=request.expiry_reminder_days,
        field_overrides=request.field_overrides,
    )
    return get_document_detail_endpoint(document_id, db=db, current_user=current_user)


@documents_router.post("/{document_id}/re-extract", response_model=DocumentDetailResponse, summary="Retry Extraction")
def re_extract_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN", "PLANT_MANAGER", "EHS_MANAGER"])),
):
    """Retries extraction on a failed or queued document."""
    doc = db.get(ComplianceDocument, document_id)
    if not doc:
        raise EntityNotFoundError("ComplianceDocument", document_id)

    if current_user.role != "SUPER_ADMIN" and doc.tenant_id != current_user.tenant_id:
        raise TenantAccessDeniedError("Cross-tenant re-extraction prohibited.")

    pipeline.execute_extraction(db=db, document_id=doc.id, user_email=current_user.email)
    return get_document_detail_endpoint(document_id, db=db, current_user=current_user)


@documents_router.get("/{document_id}/history", response_model=List[DocumentAuditLogResponse], summary="Document Audit Trail")
def get_document_history_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves immutable provenance and review audit trail."""
    doc = db.get(ComplianceDocument, document_id)
    if not doc:
        raise EntityNotFoundError("ComplianceDocument", document_id)

    if current_user.role != "SUPER_ADMIN" and doc.tenant_id != current_user.tenant_id:
        raise TenantAccessDeniedError("Cross-tenant audit access denied.")

    stmt = select(ComplianceDocumentAudit).where(
        ComplianceDocumentAudit.document_id == document_id
    ).order_by(desc(ComplianceDocumentAudit.created_at))

    return list(db.scalars(stmt).all())


@documents_router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Archive Document")
def archive_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN"])),
):
    """Soft-deletes / archives document according to retention policies."""
    doc = db.get(ComplianceDocument, document_id)
    if not doc:
        raise EntityNotFoundError("ComplianceDocument", document_id)

    if current_user.role != "SUPER_ADMIN" and doc.tenant_id != current_user.tenant_id:
        raise TenantAccessDeniedError("Cross-tenant document archiving prohibited.")

    doc.is_archived = True
    pipeline._record_audit(
        db=db,
        document_id=doc.id,
        action="DOCUMENT_ARCHIVED",
        performed_by=current_user.email,
        details={"original_filename": doc.original_filename},
    )
    db.commit()
    return None
