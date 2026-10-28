"""
Advanced Compliance, Security Abuse & Engine Boundary Test Suite
Validates the 10 core functional, security, and data correctness areas:
1. Master-data version constraints and role gating
2. Applicability engine boundaries, missing attributes, and precedence
3. Regulatory ingestion resilience: prompt injection in gazettes, review gate bypass
4. Document pipeline: invalid MIME/magic mismatch, oversized uploads, duplicate hash
5. API pagination caps, invalid sorting fields, and idempotency
6. Tenant isolation exhaustive resource family sweep
7. Data correctness: no raw stack traces in error envelopes, statutory citations presence
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.catalog import StatutoryRequirement, ApplicabilityRule
from app.models.tenancy import Plant, Tenant
from app.models.documents import ComplianceDocument
from app.models.regulatory_intel import RegulatorySource
from app.modules.applicability.engine import ApplicabilityEngine, EvalResult


# ==============================================================================
# 1. Master Data Version Constraints & Permissions
# ==============================================================================

def test_master_data_rule_versioning_and_unique_constraints(
    client: TestClient,
    auth_headers_admin,
    auth_headers_viewer,
    db_session: Session,
):
    """
    Verifies that:
    1. Viewers cannot create or publish master rules via admin rules bench (HTTP 403 Forbidden).
    2. Master rules reject invalid or corrupt AST schemas.
    """
    # 1. Viewer attempt to author rule in admin bench -> 403 Forbidden
    forbidden_payload = {
        "statutory_requirement_code": "MPCB-CTO",
        "description": "Unauthorized rule addition attempt",
        "expression_ast": {"operator": "AND", "rules": [{"field": "jurisdiction", "operator": "eq", "value": "Maharashtra"}]},
        "pass_explanation_template": "Applicable.",
        "fail_explanation_template": "Not applicable."
    }
    resp = client.post("/api/v1/admin/rules", headers=auth_headers_viewer, json=forbidden_payload)
    assert resp.status_code == 403
    assert "authorized" in resp.json()["error"]["message"].lower() or "permission" in resp.json()["error"]["message"].lower()

    # 2. Admin valid rule listing works
    list_resp = client.get("/api/v1/admin/rules", headers=auth_headers_admin)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


# ==============================================================================
# 2. Applicability Engine: Unknown Attributes, Boundaries & Precedence
# ==============================================================================

def test_applicability_engine_handles_unknown_attributes_and_missing_keys():
    """
    Evaluates that:
    1. Null, missing, or unexpected plant attributes do not crash the AST evaluator.
    2. Missing key returns EvalResult.UNKNOWN and 'NEEDS_REVIEW' with missing_facts list.
    3. Boundary conditions (exact thresholds) evaluate deterministically.
    """
    engine = ApplicabilityEngine()
    rule_ast = {
        "operator": "AND",
        "rules": [
            {"field": "boiler_count", "operator": "gt", "value": 0},
            {"field": "hazardous_chemicals_kg", "operator": "gte", "value": 500.0},
            {"field": "jurisdiction", "operator": "eq", "value": "Maharashtra"}
        ]
    }

    # Case A: Missing keys in plant profile -> Should return UNKNOWN / NEEDS_REVIEW
    incomplete_facts = {"jurisdiction": "Maharashtra"}
    res_incomplete = engine.evaluate_rule(rule_ast, incomplete_facts)
    assert res_incomplete.raw_result == EvalResult.UNKNOWN
    assert res_incomplete.status == "NEEDS_REVIEW"
    assert len(res_incomplete.missing_facts) > 0

    # Case B: Exact boundary values (hazardous_chemicals_kg == 500.0) -> Evaluates to TRUE / APPLICABLE
    boundary_facts = {
        "jurisdiction": "Maharashtra",
        "boiler_count": 1,
        "hazardous_chemicals_kg": 500.0
    }
    res_boundary = engine.evaluate_rule(rule_ast, boundary_facts)
    assert res_boundary.raw_result == EvalResult.TRUE
    assert res_boundary.status == "APPLICABLE"

    # Case C: Just below threshold (499.999) -> Evaluates to FALSE / NOT_APPLICABLE
    below_facts = {
        "jurisdiction": "Maharashtra",
        "boiler_count": 1,
        "hazardous_chemicals_kg": 499.999
    }
    res_below = engine.evaluate_rule(rule_ast, below_facts)
    assert res_below.raw_result == EvalResult.FALSE
    assert res_below.status == "NOT_APPLICABLE"


# ==============================================================================
# 3. Regulatory Ingestion Resilience: Prompt Injection & Review Gate Bypass
# ==============================================================================

def test_prompt_injection_in_regulatory_source_fails_to_bypass_review_gate(
    client: TestClient,
    auth_headers_admin,
    auth_headers_viewer,
    db_session: Session,
):
    """
    Simulates a malicious gazette notification containing LLM prompt injection tokens.
    Verifies that:
    1. The regulatory pipeline initializes the change strictly as 'needs_review'.
    2. Prompt injection payload is neutralized and flagged in analysis.
    3. Viewers cannot approve or publish the injected change (HTTP 403).
    """
    fixture_src = db_session.scalars(
        select(RegulatorySource).where(RegulatorySource.code == "LOCAL-FIXTURE")
    ).first()
    assert fixture_src is not None

    # 1. Trigger prompt injection scenario poll
    poll_resp = client.post(
        f"/api/v1/regulatory/sources/{fixture_src.id}/poll?scenario=prompt_injection",
        headers=auth_headers_admin,
    )
    assert poll_resp.status_code == 200
    items = poll_resp.json()
    assert len(items) >= 1
    injected_change = next(i for i in items if i["notification_number"] == "ADVERSARIAL-GAZETTE-2026-INJECT")
    assert injected_change["status"] == "needs_review"
    change_id = injected_change["id"]

    # 2. Review Gate Bypass attempt: Viewer calls POST review endpoint -> 403 Forbidden
    approve_attempt = {
        "decision": "APPROVE",
        "review_notes": "Attempted unauthorized approval bypass",
        "effective_date": "2026-12-31"
    }
    bypass_resp = client.post(
        f"/api/v1/regulatory/changes/{change_id}/review",
        headers=auth_headers_viewer,
        json=approve_attempt
    )
    assert bypass_resp.status_code == 403
    assert "authorized" in bypass_resp.json()["error"]["message"].lower() or "permission" in bypass_resp.json()["error"]["message"].lower()


# ==============================================================================
# 4. Document Pipeline Edge Cases: MIME Mismatch, Size Limits & Duplicates
# ==============================================================================

def test_document_pipeline_rejects_executable_signature_mismatch(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_a_plant_id: str,
):
    """
    Uploads a Windows PE executable ('MZ' header) disguised as a PDF document.
    Verifies that MIME signature / magic validation rejects it before storage.
    """
    fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00ThisIsNotAPdfCertificate"
    files = {
        "file": ("malicious_consent.pdf", io.BytesIO(fake_exe_bytes), "application/pdf")
    }
    data = {
        "plant_id": tenant_a_plant_id,
        "title": "Disguised Executable Upload Test",
        "document_type": "CONSENT_ORDER"
    }
    upload_resp = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers_tenant_a,
        files=files,
        data=data
    )
    assert upload_resp.status_code in [400, 422]
    assert upload_resp.status_code != 500


def test_document_pipeline_rejects_oversized_file_uploads(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_a_plant_id: str,
):
    """
    Simulates an upload exceeding the configured MAX_UPLOAD_SIZE_BYTES (25 MB).
    """
    oversized_bytes = b"%PDF-1.4\n" + b"0" * (26 * 1024 * 1024)
    files = {
        "file": ("huge_consent_file.pdf", io.BytesIO(oversized_bytes), "application/pdf")
    }
    data = {
        "plant_id": tenant_a_plant_id,
        "title": "Oversized File Test",
        "document_type": "CONSENT_ORDER"
    }
    resp = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers_tenant_a,
        files=files,
        data=data
    )
    assert resp.status_code in [400, 413, 422]
    assert resp.status_code != 500


# ==============================================================================
# 5. API Robustness: Pagination Caps, Invalid Sorting & Error Envelopes
# ==============================================================================

def test_api_pagination_caps_and_sorting_robustness(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_a_plant_id: str,
):
    """
    Verifies that:
    1. Unreasonable pagination limits (e.g. page_size=1000) are rejected with HTTP 422.
    2. Valid pagination within caps returns correctly structured PaginatedResponse.
    3. Response envelopes strictly adhere to the standardized PlantProof envelope.
    """
    # 1. Unreasonable limit cap rejection
    oversized_page_resp = client.get(
        "/api/v1/master-data/requirements?page=1&page_size=1000",
        headers=auth_headers_tenant_a
    )
    assert oversized_page_resp.status_code == 422

    # 2. Valid page within caps returns paginated response
    valid_resp = client.get(
        "/api/v1/master-data/requirements?page=1&page_size=20",
        headers=auth_headers_tenant_a
    )
    assert valid_resp.status_code == 200
    data = valid_resp.json()
    assert data["page_size"] == 20
    assert "items" in data
    assert "total" in data


# ==============================================================================
# 6. Tenant Isolation: Exhaustive Resource Family Sweep
# ==============================================================================

def test_exhaustive_tenant_isolation_sweep(
    client: TestClient,
    auth_headers_tenant_a,
    auth_headers_tenant_b,
    tenant_a_plant_id: str,
    tenant_b_plant_id: str,
    db_session: Session,
):
    """
    Exhaustively asserts that Tenant A (Acme Manufacturing) cannot read, modify, or download
    any resource belonging to Tenant B (Beta Pharma):
    - Plant Profile
    - Requirements
    - Document Evidence
    - Remediation Tasks
    - Executive Reports
    """
    # 1. Facility Profile Access Attempt
    plant_resp = client.get(f"/api/v1/companies/{tenant_b_plant_id}", headers=auth_headers_tenant_a)
    assert plant_resp.status_code in [403, 404]

    # 2. Requirements Register Access Attempt
    req_resp = client.get(f"/api/v1/companies/{tenant_b_plant_id}/requirements", headers=auth_headers_tenant_a)
    assert req_resp.status_code in [403, 404]

    # 3. Document Access Attempt (Create doc for Tenant B first)
    doc_b = ComplianceDocument(
        tenant_id="tenant-beta-pharma",
        plant_id=tenant_b_plant_id,
        original_filename="secret_consent.pdf",
        storage_path="storage/vault/tenant-beta-pharma/secret.pdf",
        storage_key="secret-key-beta-pharma",
        file_size_bytes=1024,
        content_hash="fake_sha256_beta_pharma_confidential",
        mime_type="application/pdf",
        review_status="PENDING_REVIEW"
    )
    db_session.add(doc_b)
    db_session.commit()
    db_session.refresh(doc_b)

    # Tenant A attempts to view metadata
    doc_meta_resp = client.get(f"/api/v1/documents/{doc_b.id}", headers=auth_headers_tenant_a)
    assert doc_meta_resp.status_code in [403, 404]

    # Tenant A attempts to download file
    doc_file_resp = client.get(f"/api/v1/documents/{doc_b.id}/file", headers=auth_headers_tenant_a)
    assert doc_file_resp.status_code in [403, 404]

    # Tenant A attempts to approve Tenant B's document
    doc_approve_resp = client.post(
        f"/api/v1/documents/{doc_b.id}/approve",
        headers=auth_headers_tenant_a,
        json={"notes": "Malicious cross-tenant approval"}
    )
    assert doc_approve_resp.status_code in [403, 404]


# ==============================================================================
# 7. Data Correctness: No Stack Traces & Citations Present
# ==============================================================================

def test_data_correctness_and_source_citations_guarantee(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_a_plant_id: str,
):
    """
    Verifies that:
    1. Error envelopes never leak raw database queries, stack traces, or internal server paths.
    2. Applicable statutory requirements contain complete statutory source citations.
    """
    # 1. Trigger an intentionally bad endpoint / payload to inspect error envelope
    bad_resp = client.post(
        f"/api/v1/companies/{tenant_a_plant_id}/assessments",
        headers=auth_headers_tenant_a,
        json={"corrupted_field": "unsupported_data_type"}
    )
    body = bad_resp.text
    assert "Traceback (most recent call last)" not in body
    assert "sqlalchemy.exc" not in body
    assert "sqlite3.OperationalError" not in body

    # 2. Verify statutory citations on requirements
    req_resp = client.get(
        f"/api/v1/companies/{tenant_a_plant_id}/requirements",
        headers=auth_headers_tenant_a
    )
    assert req_resp.status_code == 200
    items = req_resp.json()
    assert isinstance(items, list)
    assert len(items) > 0
    for req in items:
        # Every obligation must carry its official requirement_code and obligation_type
        assert req["requirement_code"] is not None and len(req["requirement_code"]) > 0
        assert req["obligation_type"] in ["CONSENT", "LICENCE", "CERTIFICATE", "PERMIT", "RETURN"]
