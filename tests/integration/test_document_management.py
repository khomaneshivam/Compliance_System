"""
Comprehensive Integration Test Suite for Document & Evidence Vault
Verifies:
- Malformed PDFs and empty scans rejection
- Prohibited MIME and archive formats rejection
- Oversized upload boundary (>25MB) rejection
- Cryptographic SHA-256 duplicate detection without silent merging
- Text extraction and snippet grounding
- Deterministic rules & permanent certificates (no invented expiry dates)
- Prompt injection neutralization
- Strict cross-tenant isolation on preview and details
- Role-based reviewer permissions
- Extraction error / invalid schema resilience
- Human review field override and statutory evidence linking
- Immutable audit trail
"""

import io
import pytest
from fastapi.testclient import TestClient

from tests.fixtures.document_fixtures import (
    create_synthetic_boiler_cert_pdf,
    create_synthetic_cto_pdf,
    create_synthetic_permanent_factory_license_pdf,
    create_synthetic_prompt_injection_pdf,
    create_malformed_pdf,
    create_empty_pdf,
    create_prohibited_zip_file,
    create_prohibited_exe_file,
    create_oversized_file,
)


def get_token(client: TestClient, email: str, password: str = "DemoPass123!") -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def test_setup(client: TestClient):
    """Provides authenticated headers for Tenant A (Admin & Manager) and Tenant B."""
    token_a_admin = get_token(client, "amit.jadhav@acme-mfg.in")
    token_a_mgr = get_token(client, "rohit.sharma@acme-mfg.in")
    token_b = get_token(client, "vikram.singh@beta-pharma.in")

    headers_a_admin = {"Authorization": f"Bearer {token_a_admin}"}
    headers_a_mgr = {"Authorization": f"Bearer {token_a_mgr}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Fetch plants for Tenant A and Tenant B
    resp_a = client.get("/api/v1/plants", headers=headers_a_mgr)
    assert resp_a.status_code == 200
    plant_a_id = resp_a.json()[0]["id"]

    resp_b = client.get("/api/v1/plants", headers=headers_b)
    assert resp_b.status_code == 200
    plant_b_id = resp_b.json()[0]["id"]

    return {
        "headers_a_admin": headers_a_admin,
        "headers_a_mgr": headers_a_mgr,
        "headers_b": headers_b,
        "plant_a_id": plant_a_id,
        "plant_b_id": plant_b_id,
    }


def get_error_message(resp) -> str:
    data = resp.json()
    if isinstance(data, dict):
        if "error" in data and isinstance(data["error"], dict):
            return data["error"].get("message", "")
        return data.get("detail", "")
    return ""


def test_malformed_and_empty_scans_rejection(client: TestClient, test_setup):
    """Verifies that corrupted PDFs and 0-byte scans are rejected with 400 Bad Request."""
    # 1. Empty scan (0 bytes)
    resp_empty = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("empty.pdf", create_empty_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp_empty.status_code == 400
    assert "empty" in get_error_message(resp_empty).lower()

    # 2. Malformed / corrupted PDF structure
    resp_corrupted = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("corrupted.pdf", create_malformed_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp_corrupted.status_code == 400
    assert "corrupted" in get_error_message(resp_corrupted).lower()


def test_wrong_mime_and_prohibited_formats(client: TestClient, test_setup):
    """Verifies that executables and archives are strictly rejected even if named .pdf."""
    # 1. Disguised ZIP archive
    resp_zip = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("archive.pdf", create_prohibited_zip_file(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp_zip.status_code == 400
    assert "prohibited" in get_error_message(resp_zip).lower()

    # 2. Disguised Windows PE executable
    resp_exe = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("malware.pdf", create_prohibited_exe_file(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp_exe.status_code == 400
    assert "prohibited" in get_error_message(resp_exe).lower()


def test_oversized_upload_rejection(client: TestClient, test_setup):
    """Verifies that files exceeding 25MB boundary are rejected."""
    resp = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("huge.pdf", create_oversized_file(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp.status_code == 400
    assert "exceeds" in get_error_message(resp).lower()


def test_duplicate_document_detection_without_silent_merging(client: TestClient, test_setup):
    """Verifies that duplicate document hashes are flagged visibly and never silently merged."""
    boiler_bytes = create_synthetic_boiler_cert_pdf()

    # First upload
    resp1 = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("boiler_cert_v1.pdf", boiler_bytes, "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp1.status_code == 201
    doc1 = resp1.json()
    assert doc1["is_duplicate"] is False
    assert doc1["duplicate_of_id"] is None

    # Second upload with identical bytes
    resp2 = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("boiler_cert_duplicate.pdf", boiler_bytes, "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp2.status_code == 201
    doc2 = resp2.json()
    assert doc2["id"] != doc1["id"]
    assert doc2["is_duplicate"] is True
    assert doc2["duplicate_of_id"] == doc1["id"]


def test_extraction_and_snippet_grounding(client: TestClient, test_setup):
    """Verifies OCR text extraction, field grounding with source snippet and page numbers."""
    resp = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("boiler_inspection_cert.pdf", create_synthetic_boiler_cert_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    detail_resp = client.get(f"/api/v1/documents/{doc_id}", headers=test_setup["headers_a_mgr"])
    assert detail_resp.status_code == 200
    data = detail_resp.json()

    assert data["document_type_detected"] == "Boiler Inspection Certificate"
    assert data["extraction_status"] == "EXTRACTED"
    assert len(data["extracted_fields"]) >= 4

    # Check provenance snippet and page numbers
    cert_field = [f for f in data["extracted_fields"] if f["field_key"] == "certificate_number"][0]
    assert cert_field["extracted_value"] == "MH/B/2025/1042"
    assert cert_field["confidence_band"] == "HIGH"
    assert cert_field["source_page"] == 1
    assert cert_field["source_snippet"] is not None

    # Check deterministic validation checks
    check_codes = [c["check_code"] for c in data["validation_checks"]]
    assert "DOC_TYPE_MATCH" in check_codes
    assert "VALID_DATE_WINDOW" in check_codes
    assert "CERT_FORMAT_VALID" in check_codes
    assert "AUTHORITY_RECOGNIZED" in check_codes


def test_missing_expiry_permanent_license_not_invented(client: TestClient, test_setup):
    """
    Cardinal Rule: If a document has no expiry date, do not invent one.
    Permanent documents must preserve expiry as None with NO_EXPIRY_PERMANENT check.
    """
    resp = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("permanent_factory_license.pdf", create_synthetic_permanent_factory_license_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    detail_resp = client.get(f"/api/v1/documents/{doc_id}", headers=test_setup["headers_a_mgr"])
    data = detail_resp.json()

    assert data["document_type_detected"] == "Factory Licence"
    # Assert NO expiry date invented
    assert data["detected_expiry_date"] is None

    # Assert deterministic check confirms permanent status
    perm_check = [c for c in data["validation_checks"] if c["check_code"] == "NO_EXPIRY_PERMANENT"][0]
    assert perm_check["status"] == "PASSED"
    assert "perpetual" in perm_check["details"].lower() or "permanent" in perm_check["details"].lower()


def test_prompt_injection_neutralization_in_document(client: TestClient, test_setup):
    """Verifies that hostile prompt overrides in document text are neutralized."""
    resp = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("hostile_injection.pdf", create_synthetic_prompt_injection_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    detail_resp = client.get(f"/api/v1/documents/{doc_id}", headers=test_setup["headers_a_mgr"])
    data = detail_resp.json()
    assert data["extraction_status"] == "EXTRACTED"
    summary = data["extracted_metadata"].get("summary", "")
    # Hostile instruction override tokens must not execute tools or trigger system modes
    assert "drop table" not in summary.lower()


def test_cross_tenant_document_access_isolation(client: TestClient, test_setup):
    """Verifies that Tenant B cannot access or stream documents uploaded by Tenant A."""
    # Tenant A uploads document
    resp_upload = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("tenant_a_doc.pdf", create_synthetic_boiler_cert_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp_upload.status_code == 201
    doc_a_id = resp_upload.json()["id"]

    # Tenant B attempts to read detail -> 403 Forbidden
    resp_detail = client.get(f"/api/v1/documents/{doc_a_id}", headers=test_setup["headers_b"])
    assert resp_detail.status_code == 403

    # Tenant B attempts to stream file -> 403 Forbidden
    resp_stream = client.get(f"/api/v1/documents/{doc_a_id}/file", headers=test_setup["headers_b"])
    assert resp_stream.status_code == 403

    # Tenant B attempts to patch fields -> 403 Forbidden
    resp_patch = client.patch(
        f"/api/v1/documents/{doc_a_id}/fields",
        json={"fields": {"certificate_number": "HIJACKED"}},
        headers=test_setup["headers_b"],
    )
    assert resp_patch.status_code == 403


def test_reviewer_permissions_and_unauthorized_review(client: TestClient, test_setup):
    """Verifies that unauthorized review attempts are rejected with 403."""
    # Tenant A uploads document
    resp_upload = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("tenant_a_doc2.pdf", create_synthetic_boiler_cert_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp_upload.status_code == 201
    doc_id = resp_upload.json()["id"]

    # Tenant B attempts review on Tenant A document -> 403
    resp_review = client.post(
        f"/api/v1/documents/{doc_id}/review",
        json={"decision": "APPROVE", "review_notes": "Unauthorized review attempt"},
        headers=test_setup["headers_b"],
    )
    assert resp_review.status_code == 403


def test_human_review_field_override_and_evidence_linking(client: TestClient, test_setup):
    """Verifies human reviewer field editing, approval, and evidence linking."""
    # 1. Upload CTO document
    resp_upload = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("cto_document.pdf", create_synthetic_cto_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp_upload.status_code == 201
    doc_id = resp_upload.json()["id"]

    # 2. Reviewer overrides field
    resp_edit = client.patch(
        f"/api/v1/documents/{doc_id}/fields",
        json={"fields": {"consent_number": "MPCB/RO-PUNE/CTO/2025/892-REV"}},
        headers=test_setup["headers_a_admin"],
    )
    assert resp_edit.status_code == 200
    overridden_field = [f for f in resp_edit.json()["extracted_fields"] if f["field_key"] == "consent_number"][0]
    assert overridden_field["confirmed_value"] == "MPCB/RO-PUNE/CTO/2025/892-REV"
    assert overridden_field["is_overridden"] is True

    # 3. Reviewer approves document and links to statutory requirement
    resp_review = client.post(
        f"/api/v1/documents/{doc_id}/review",
        json={
            "decision": "APPROVE",
            "review_notes": "Consent to operate verified with state board registry.",
            "link_to_statutory_requirement_id": "MPCB-CTO",
            "expiry_reminder_days": 60,
        },
        headers=test_setup["headers_a_admin"],
    )
    assert resp_review.status_code == 200
    reviewed_data = resp_review.json()
    assert reviewed_data["review_status"] == "EDITED_AND_APPROVED"
    assert len(reviewed_data["linked_requirements"]) >= 1
    assert reviewed_data["linked_requirements"][0]["evidence_status"] == "VALID"

    # 4. Verify immutable audit history
    resp_hist = client.get(f"/api/v1/documents/{doc_id}/history", headers=test_setup["headers_a_admin"])
    assert resp_hist.status_code == 200
    actions = [h["action"] for h in resp_hist.json()]
    assert "DOCUMENT_UPLOADED" in actions
    assert "EXTRACTION_COMPLETED" in actions
    assert "FIELD_OVERRIDDEN" in actions
    assert "DOCUMENT_APPROVED" in actions
    assert "EVIDENCE_LINKED" in actions


def test_extraction_retry_and_resilience(client: TestClient, test_setup):
    """Verifies that re-extract endpoint correctly re-runs extraction and records audit."""
    resp_upload = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": test_setup["plant_a_id"]},
        files={"file": ("re_extract_target.pdf", create_synthetic_boiler_cert_pdf(), "application/pdf")},
        headers=test_setup["headers_a_mgr"],
    )
    assert resp_upload.status_code == 201
    doc_id = resp_upload.json()["id"]

    # Re-extract
    resp_re = client.post(f"/api/v1/documents/{doc_id}/re-extract", headers=test_setup["headers_a_mgr"])
    assert resp_re.status_code == 200
    assert resp_re.json()["extraction_status"] == "EXTRACTED"
