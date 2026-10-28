"""
Security and Reliability Hardening Test Suite (PlantProof)
Negative and Boundary Control Verifications:
- IDOR/BOLA cross-tenant access isolation across documents, files, reports, and tasks
- Server-side RBAC enforcement and privilege escalation guards (invite, company creation, audit logs)
- Regulatory change impact query tenant scoping (no leakage of Tenant B facility metadata to Tenant A)
- Rate limiting protection with sliding window 429 response and Retry-After headers
- Path traversal rejection on vault artifact retrieval
- Safe header construction against CRLF / splitting attacks
- Stored XSS defense via HTML escaping in generated readiness dossiers
- PII and credential automated redaction in structured telemetry
- Strict security headers injection and correlation ID sanitization
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.core.logging import redact_sensitive_data
from tests.fixtures.document_fixtures import create_synthetic_cto_pdf


# ==============================================================================
# 1. IDOR & BOLA Multi-Tenant Isolation
# ==============================================================================

def test_tenant_a_cannot_access_tenant_b_document_or_stream(
    client: TestClient,
    auth_headers_tenant_a: dict,
    auth_headers_tenant_b: dict,
    tenant_b_plant_id: str,
):
    """
    IDOR/BOLA Defense: Tenant B uploads a sensitive consent order.
    Tenant A must be rejected with 403 Forbidden when requesting metadata or binary download.
    """
    # 1. Tenant B uploads consent order
    upload_resp = client.post(
        "/api/v1/documents/upload",
        data={"plant_id": tenant_b_plant_id},
        files={"file": ("tenant_b_confidential_cto.pdf", create_synthetic_cto_pdf(), "application/pdf")},
        headers=auth_headers_tenant_b,
    )
    assert upload_resp.status_code == 201
    doc_b_id = upload_resp.json()["id"]

    # 2. Tenant A attempts to fetch Tenant B's document metadata by ID
    leak_meta = client.get(f"/api/v1/documents/{doc_b_id}", headers=auth_headers_tenant_a)
    assert leak_meta.status_code == 403
    assert "TENANT_ACCESS_DENIED" in leak_meta.text or "Cross-tenant" in leak_meta.text

    # 3. Tenant A attempts to download/stream Tenant B's document file
    leak_stream = client.get(f"/api/v1/documents/{doc_b_id}/file", headers=auth_headers_tenant_a)
    assert leak_stream.status_code == 403


def test_tenant_a_cannot_access_or_mutate_tenant_b_tasks(
    client: TestClient,
    auth_headers_tenant_a: dict,
    auth_headers_tenant_b: dict,
    tenant_b_plant_id: str,
):
    """
    IDOR Defense on Tasks: Tenant B creates a compliance task.
    Tenant A cannot read details, transition task status, or post comments.
    """
    # 1. Tenant B creates task
    create_resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers_tenant_b,
        json={
            "plant_id": tenant_b_plant_id,
            "title": "Upgrade ETP Aeration Tank Impeller",
            "description": "Internal engineering task for Tenant B facility.",
            "due_date": "2026-12-31",
            "priority": "HIGH",
        },
    )
    assert create_resp.status_code == 201
    task_b_id = create_resp.json()["id"]

    # 2. Tenant A attempts to read Tenant B's task details
    read_resp = client.get(f"/api/v1/tasks/{task_b_id}", headers=auth_headers_tenant_a)
    assert read_resp.status_code == 403

    # 3. Tenant A attempts to transition Tenant B's task status
    transition_resp = client.post(
        f"/api/v1/tasks/{task_b_id}/status",
        headers=auth_headers_tenant_a,
        json={"new_status": "COMPLETED"},
    )
    assert transition_resp.status_code == 403

    # 4. Tenant A attempts to post comments on Tenant B's task
    comment_resp = client.post(
        f"/api/v1/tasks/{task_b_id}/comments",
        headers=auth_headers_tenant_a,
        json={"comment_text": "Unauthorized cross-tenant comment attempt"},
    )
    assert comment_resp.status_code == 403


def test_tenant_a_cannot_access_or_download_tenant_b_report(
    client: TestClient,
    auth_headers_tenant_a: dict,
    auth_headers_tenant_b: dict,
    tenant_b_plant_id: str,
):
    """
    IDOR Defense on Reports: Tenant B generates an executive readiness dossier.
    Tenant A cannot fetch report job status or download the generated HTML/JSON artifact.
    """
    # 1. Tenant B generates report
    create_resp = client.post(
        "/api/v1/reports?run_async=false",
        headers=auth_headers_tenant_b,
        json={
            "plant_id": tenant_b_plant_id,
            "report_title": "Tenant B Executive Compliance Audit",
            "file_format": "HTML",
            "include_evidence_items": True,
            "include_missing_items": True,
        },
    )
    assert create_resp.status_code == 201
    report_b_id = create_resp.json()["id"]

    # 2. Tenant A attempts to fetch report job metadata
    read_resp = client.get(f"/api/v1/reports/{report_b_id}", headers=auth_headers_tenant_a)
    assert read_resp.status_code in (403, 404)

    # 3. Tenant A attempts to download report artifact
    download_resp = client.get(f"/api/v1/reports/{report_b_id}/download", headers=auth_headers_tenant_a)
    assert download_resp.status_code in (403, 404)


def test_regulatory_change_impacts_scoping_prevents_tenant_leak(
    client: TestClient,
    auth_headers_tenant_a: dict,
    tenant_b_plant_id: str,
):
    """
    Tenant Isolation in Global Intelligence:
    A regulatory change may impact facilities across multiple tenants.
    When Tenant A queries impacts, only Tenant A's plants must be returned.
    Tenant B's facility names and plant IDs must NEVER appear.
    """
    # Fetch regulatory changes
    changes_resp = client.get("/api/v1/regulatory/changes?page=1&page_size=10", headers=auth_headers_tenant_a)
    assert changes_resp.status_code == 200
    res = changes_resp.json()
    items = res["items"] if isinstance(res, dict) and "items" in res else res
    assert len(items) > 0
    change_id = items[0]["id"]

    # Query impacts as Tenant A
    impacts_resp = client.get(f"/api/v1/regulatory/changes/{change_id}/impacts", headers=auth_headers_tenant_a)
    assert impacts_resp.status_code == 200
    impacts = impacts_resp.json()

    # Assert no impact in the list belongs to Tenant B
    for imp in impacts:
        assert imp.get("plant_id") != tenant_b_plant_id
        assert "Beta Pharma" not in imp.get("plant_name", "")


# ==============================================================================
# 2. Server-Side RBAC & Privilege Escalation Protection
# ==============================================================================

def test_rbac_viewer_denied_user_invitations(
    client: TestClient,
    auth_headers_viewer: dict,
):
    """
    RBAC: Read-Only VIEWER role must not be able to invite new users.
    Server must reject with 403 Forbidden regardless of UI presentation.
    """
    resp = client.post(
        "/api/v1/auth/users/invite",
        headers=auth_headers_viewer,
        json={
            "email": "malicious.invitee@acme-mfg.in",
            "full_name": "Hostile Account",
            "role": "ADMIN",
        },
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.text.lower() or "permission denied" in resp.text.lower()


def test_rbac_viewer_denied_facility_creation_and_profile_edits(
    client: TestClient,
    auth_headers_viewer: dict,
    tenant_a_plant_id: str,
):
    """
    RBAC: Read-Only VIEWER role cannot create facilities, edit profiles, or trigger assessments.
    """
    # 1. Attempt facility creation
    create_facility = client.post(
        "/api/v1/companies",
        headers=auth_headers_viewer,
        json={
            "name": "Unauthorized Plant Branch",
            "code": "MH-ILLEGAL-01",
            "state_jurisdiction": "Maharashtra",
            "primary_authority": "MPCB",
        },
    )
    assert create_facility.status_code == 403

    # 2. Attempt profile update
    update_profile = client.patch(
        f"/api/v1/companies/{tenant_a_plant_id}/profile",
        headers=auth_headers_viewer,
        json={"hazardous_waste_tpa": 999.0},
    )
    assert update_profile.status_code == 403

    # 3. Attempt triggering assessment
    trigger_assess = client.post(
        f"/api/v1/companies/{tenant_a_plant_id}/assessments",
        headers=auth_headers_viewer,
    )
    assert trigger_assess.status_code == 403


def test_rbac_audit_logs_restricted_to_admin_and_auditor(
    client: TestClient,
    auth_headers_viewer: dict,
    auth_headers_auditor: dict,
    auth_headers_admin: dict,
):
    """
    RBAC: Audit log endpoint (/api/v1/admin/audit-logs) must reject VIEWER (403)
    while granting access to AUDITOR and ADMIN.
    """
    # VIEWER -> 403 Forbidden
    resp_viewer = client.get("/api/v1/admin/audit-logs", headers=auth_headers_viewer)
    assert resp_viewer.status_code == 403

    # AUDITOR -> 200 OK
    resp_auditor = client.get("/api/v1/admin/audit-logs", headers=auth_headers_auditor)
    assert resp_auditor.status_code == 200
    assert "items" in resp_auditor.json()

    # ADMIN -> 200 OK
    resp_admin = client.get("/api/v1/admin/audit-logs", headers=auth_headers_admin)
    assert resp_admin.status_code == 200


def test_privilege_escalation_tenant_admin_cannot_invite_superadmin(
    client: TestClient,
    auth_headers_admin: dict,
):
    """
    Privilege Escalation Guard: A tenant ADMIN cannot invite a SUPER_ADMIN.
    Only an existing SUPER_ADMIN can grant the platform superadmin role.
    """
    resp = client.post(
        "/api/v1/auth/users/invite",
        headers=auth_headers_admin,
        json={
            "email": "escalated.user@acme-mfg.in",
            "full_name": "Privilege Escalation Attempt",
            "role": "SUPER_ADMIN",
        },
    )
    assert resp.status_code == 403
    assert "privilege escalation prohibited" in resp.text.lower() or "super administrator" in resp.text.lower()


def test_cross_tenant_email_invitation_collision_conflict(
    client: TestClient,
    auth_headers_admin: dict,
):
    """
    Tenant Collision Guard: Attempting to invite an email address that already belongs
    to another tenant or active user must return 409 Conflict.
    """
    resp = client.post(
        "/api/v1/auth/users/invite",
        headers=auth_headers_admin,
        json={
            "email": "rohit.sharma@acme-mfg.in",  # Existing active user
            "full_name": "Duplicate Rohit",
            "role": "PLANT_MANAGER",
        },
    )
    assert resp.status_code == 409
    assert "already registered" in resp.text


# ==============================================================================
# 3. Rate Limiting Protection (Brute Force Defense)
# ==============================================================================

def test_login_endpoint_rate_limiting_enforcement(client: TestClient):
    """
    Rate Limiting: Exceeding 15 login requests within 60 seconds returns HTTP 429
    with a valid Retry-After header.
    """
    # Issue 15 rapid invalid login attempts
    for _ in range(15):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "WrongPassword123!"},
        )
        assert resp.status_code in (401, 404, 422)

    # 16th attempt must trigger HTTP 429 Too Many Requests
    blocked_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "WrongPassword123!"},
    )
    assert blocked_resp.status_code == 429
    assert "Rate limit exceeded" in blocked_resp.text
    assert "Retry-After" in blocked_resp.headers
    assert int(blocked_resp.headers["Retry-After"]) >= 1


# ==============================================================================
# 4. Path Traversal & Header Injection Protections
# ==============================================================================

def test_report_path_traversal_rejection(
    client: TestClient,
    auth_headers_tenant_a: dict,
    db_session,
):
    """
    Path Traversal Defense: If an attacker modifies report storage_key to include
    relative traversal '../', the service must reject access and refuse to escape the vault.
    """
    from app.models.tenancy import Plant
    from app.models.reports import ReadinessReportJob
    plant = db_session.query(Plant).filter(Plant.code == "MH-PUN-01").first()

    # Create dummy report job with path traversal storage key
    malicious_job = ReadinessReportJob(
        tenant_id=plant.tenant_id,
        plant_id=plant.id,
        requested_by_user_id=None,
        report_title="Malicious Traversal Report",
        file_format="HTML",
        status="COMPLETED",
        storage_key="../../etc/passwd",
    )
    db_session.add(malicious_job)
    db_session.commit()
    db_session.refresh(malicious_job)

    # Attempt download
    resp = client.get(f"/api/v1/reports/{malicious_job.id}/download", headers=auth_headers_tenant_a)
    assert resp.status_code in (403, 404)
    assert "traversal" in resp.text.lower() or "not found" in resp.text.lower() or "denied" in resp.text.lower()


# ==============================================================================
# 5. Stored XSS Mitigation in Reports
# ==============================================================================

def test_stored_xss_in_report_html_is_escaped(
    client: TestClient,
    auth_headers_tenant_a: dict,
    tenant_a_plant_id: str,
):
    """
    Stored XSS Defense: If hostile HTML or Javascript tags (<script>alert(1)</script>)
    are provided in report titles or descriptions, the report HTML generator must
    strictly escape them to HTML entities (&lt;script&gt;).
    """
    resp = client.post(
        "/api/v1/reports?run_async=false",
        headers=auth_headers_tenant_a,
        json={
            "plant_id": tenant_a_plant_id,
            "report_title": "<script>alert('XSS-Audit-Attack')</script>",
            "file_format": "HTML",
            "include_evidence_items": False,
            "include_missing_items": False,
        },
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    dl_resp = client.get(f"/api/v1/reports/{job_id}/download", headers=auth_headers_tenant_a)
    assert dl_resp.status_code == 200
    html = dl_resp.text

    # Raw script tags must NEVER be present unescaped
    assert "<script>alert('XSS-Audit-Attack')</script>" not in html
    # Must be rendered as safely escaped HTML entities
    assert "&lt;script&gt;alert(" in html or "&lt;script&gt;" in html


# ==============================================================================
# 6. Structured Logging Secret & PII Redaction
# ==============================================================================

def test_structured_log_secret_and_pii_redaction():
    """
    Telemetry Hardening: Sensitive fields (passwords, JWT tokens, Bearer strings,
    Aadhaar numbers, API keys) must be automatically redacted in log structures.
    """
    raw_payload = {
        "user_email": "operator@acme-mfg.in",
        "password": "SuperSecretPassword123!",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.fake_signature_part",
        "authorization_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_token_data",
        "aadhaar_proof": "Resident Aadhaar: 4123 4567 8901 for gate pass",
        "nested_details": {
            "api_key": "live_sk_98327498172938749823",
            "safe_metric": 42.5,
        },
    }

    sanitized = redact_sensitive_data(raw_payload)

    # Passwords and direct tokens must be masked
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["authorization_header"] == "[REDACTED]"
    assert sanitized["nested_details"]["api_key"] == "[REDACTED]"

    # Safe metrics must remain untouched
    assert sanitized["nested_details"]["safe_metric"] == 42.5

    # Aadhaar pattern in strings must be masked
    assert "4123 4567 8901" not in sanitized["aadhaar_proof"]
    assert "[REDACTED_AADHAAR]" in sanitized["aadhaar_proof"]


# ==============================================================================
# 7. Security Headers & Telemetry Ingress Sanitization
# ==============================================================================

def test_security_headers_and_correlation_id_sanitization(client: TestClient):
    """
    HTTP Protocol & Header Hardening:
    - Inspect required defensive headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
    - Hostile X-Correlation-ID containing CRLF or invalid characters must be rejected or sanitized
    """
    # 1. Clean request verifying security headers
    resp = client.get("/api/v1/health/liveness")
    assert resp.status_code == 200
    headers = resp.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin-when-cross-origin" in headers.get("Referrer-Policy", "")

    # 2. Hostile correlation ID with header injection attempt (\r\nInjected-Header: evil)
    malicious_cid = "valid-prefix\r\nInjected-Header: hostile\r\n"
    resp_injection = client.get("/api/v1/health/liveness", headers={"X-Correlation-ID": malicious_cid})
    assert resp_injection.status_code == 200
    returned_cid = resp_injection.headers.get("X-Correlation-ID")

    # Returned correlation ID must NOT contain CRLF or the injected header text
    assert "\r" not in returned_cid
    assert "\n" not in returned_cid
    assert "hostile" not in returned_cid
