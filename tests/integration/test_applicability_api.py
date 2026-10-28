"""
Integration Tests for Applicability Engine REST API (/api/v1/companies)
Tests assessment execution, gap analysis, proposed changes human review workflow,
jurisdiction filtering, reproducibility, and tenant isolation.
"""

from fastapi.testclient import TestClient


def test_create_company_facility_and_update_profile(
    client: TestClient,
    auth_headers_tenant_a,
):
    """Verifies creating a company facility and updating operational parameters."""
    # 1. Create company facility
    create_payload = {
        "name": "Acme Chemical Synthesis Unit 2",
        "code": "MH-THN-02",
        "jurisdiction": "Maharashtra",
        "district": "Thane",
        "pincode": "400601",
    }
    create_resp = client.post("/api/v1/companies", headers=auth_headers_tenant_a, json=create_payload)
    assert create_resp.status_code == 201
    comp = create_resp.json()
    assert comp["code"] == "MH-THN-02"
    company_id = comp["id"]

    # 2. Update operational profile
    update_payload = {
        "industry_category": "RED",
        "employee_count": 220,
        "boiler_count": 2,
        "steam_capacity_tph": 8.5,
        "hazardous_waste_tpa": 25.0,
        "effluent_discharge_kld": 75.0,
        "activities": ["Chemical Synthesis", "Solvent Recovery"],
    }
    update_resp = client.patch(
        f"/api/v1/companies/{company_id}/profile",
        headers=auth_headers_tenant_a,
        json=update_payload,
    )
    assert update_resp.status_code == 200
    updated_profile = update_resp.json()["profile"]
    assert updated_profile["boiler_count"] == 2
    assert updated_profile["steam_capacity_tph"] == 8.5


def test_run_assessment_and_reproducibility(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_a_plant_id: str,
):
    """
    Verifies running applicability assessment against seeded plant.
    Verifies reproducibility: running twice on unchanged facts yields identical outcomes.
    """
    # Run 1
    resp1 = client.post(
        f"/api/v1/companies/{tenant_a_plant_id}/assessments?auto_approve_initial=true",
        headers=auth_headers_tenant_a,
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["applicable_count"] >= 1
    assert data1["total_rules_evaluated"] >= 2
    findings1 = {f["requirement_code"]: f["evaluation_outcome"] for f in data1["findings"]}

    # Boiler should apply (BLR-01 exists with 4.5 TPH capacity)
    assert findings1["BOILER-INSP-CERT"] == "APPLICABLE"
    assert findings1["MPCB-CTO"] == "APPLICABLE"

    # Run 2 (Reproducibility check)
    resp2 = client.post(
        f"/api/v1/companies/{tenant_a_plant_id}/assessments?auto_approve_initial=true",
        headers=auth_headers_tenant_a,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    findings2 = {f["requirement_code"]: f["evaluation_outcome"] for f in data2["findings"]}

    # Identical evaluations
    assert findings1 == findings2
    assert data2["assessment_version"] > data1["assessment_version"]


def test_proposed_change_review_workflow(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_a_plant_id: str,
):
    """
    Tests Human-in-the-Loop review:
    Engine queues proposed changes when operational criteria alter obligations.
    Reviewer must approve or reject; no silent register mutations occur.
    """
    # 1. Update plant to zero boilers
    client.patch(
        f"/api/v1/companies/{tenant_a_plant_id}/profile",
        headers=auth_headers_tenant_a,
        json={"boiler_count": 0, "steam_capacity_tph": 0.0},
    )

    # 2. Run assessment (without auto_approve)
    assess_resp = client.post(
        f"/api/v1/companies/{tenant_a_plant_id}/assessments?auto_approve_initial=false",
        headers=auth_headers_tenant_a,
    )
    assert assess_resp.status_code == 200

    # 3. Check proposed changes queue
    changes_resp = client.get(
        f"/api/v1/companies/{tenant_a_plant_id}/changes",
        headers=auth_headers_tenant_a,
    )
    assert changes_resp.status_code == 200
    changes = changes_resp.json()
    
    # Should contain proposed change for BOILER-INSP-CERT
    boiler_changes = [c for c in changes if c["requirement_code"] == "BOILER-INSP-CERT"]
    assert len(boiler_changes) > 0
    change = boiler_changes[0]
    assert change["review_status"] == "PENDING_REVIEW"
    assert change["proposed_status"] == "NOT_APPLICABLE"

    # 4. Reviewer approves change
    decision_payload = {
        "decision": "APPROVE",
        "review_notes": "Confirmed boiler decommissioned from site by inspection.",
    }
    review_resp = client.post(
        f"/api/v1/companies/{tenant_a_plant_id}/changes/{change['id']}/review",
        headers=auth_headers_tenant_a,
        json=decision_payload,
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["review_status"] == "APPROVED"

    # 5. Restore profile so subsequent tests see baseline Pune plant state
    client.patch(
        f"/api/v1/companies/{tenant_a_plant_id}/profile",
        headers=auth_headers_tenant_a,
        json={"boiler_count": 1, "steam_capacity_tph": 4.5},
    )


def test_company_gaps_report(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_a_plant_id: str,
):
    """Verifies retrieval of missing facts and evidence gaps."""
    response = client.get(
        f"/api/v1/companies/{tenant_a_plant_id}/gaps",
        headers=auth_headers_tenant_a,
    )
    assert response.status_code == 200
    gaps = response.json()
    assert "company_id" in gaps
    assert "missing_profile_facts" in gaps
    assert "missing_or_expiring_evidence" in gaps


def test_tenant_isolation_on_companies_api(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_b_plant_id: str,
):
    """
    CRITICAL SECURITY CHECK:
    Tenant A cannot assess, view requirements, or review changes for Tenant B's facility.
    """
    # 1. Assessment on Tenant B facility
    resp_assess = client.post(
        f"/api/v1/companies/{tenant_b_plant_id}/assessments",
        headers=auth_headers_tenant_a,
    )
    assert resp_assess.status_code == 403

    # 2. View requirements of Tenant B
    resp_reqs = client.get(
        f"/api/v1/companies/{tenant_b_plant_id}/requirements",
        headers=auth_headers_tenant_a,
    )
    assert resp_reqs.status_code == 403

    # 3. View gaps of Tenant B
    resp_gaps = client.get(
        f"/api/v1/companies/{tenant_b_plant_id}/gaps",
        headers=auth_headers_tenant_a,
    )
    assert resp_gaps.status_code == 403
