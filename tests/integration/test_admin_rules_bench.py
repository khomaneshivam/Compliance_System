"""
Integration Tests for Admin Regulatory Rules Bench (/api/v1/admin/rules)
Tests rule versioning, RBAC authorization, approval lifecycle, immutability locking,
superseding workflows, and version history.
"""

from fastapi.testclient import TestClient


def test_non_admin_forbidden_from_rules_bench(
    client: TestClient,
    auth_headers_tenant_a,
):
    """
    CRITICAL SECURITY CHECK:
    Only ADMIN and SUPER_ADMIN roles can author, approve, or modify regulatory rules.
    Plant managers or regular users receive HTTP 403 Forbidden.
    """
    resp = client.get("/api/v1/admin/rules", headers=auth_headers_tenant_a)
    assert resp.status_code == 403
    error_data = resp.json()["error"]
    assert "not authorized" in error_data["message"].lower() or "permission" in error_data["message"].lower()


def test_admin_list_and_filter_rules(
    client: TestClient,
    auth_headers_admin,
):
    """Verifies that an admin user can list and filter regulatory rule versions."""
    # 1. List all rules
    resp = client.get("/api/v1/admin/rules", headers=auth_headers_admin)
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) >= 2
    codes = [r["statutory_requirement_code"] for r in rules]
    assert "MPCB-CTO" in codes
    assert "BOILER-INSP-CERT" in codes

    # 2. Filter by status=ACTIVE
    resp_active = client.get("/api/v1/admin/rules?status=ACTIVE", headers=auth_headers_admin)
    assert resp_active.status_code == 200
    active_rules = resp_active.json()
    assert all(r["status"] == "ACTIVE" for r in active_rules)

    # 3. Filter by requirement_code
    resp_filtered = client.get("/api/v1/admin/rules?requirement_code=MPCB-CTO", headers=auth_headers_admin)
    assert resp_filtered.status_code == 200
    mpcb_rules = resp_filtered.json()
    assert len(mpcb_rules) >= 1
    assert all(r["statutory_requirement_code"] == "MPCB-CTO" for r in mpcb_rules)


def test_rule_authoring_approval_and_immutability_lifecycle(
    client: TestClient,
    auth_headers_admin,
):
    """
    Full rule lifecycle test:
    1. Author new proposed rule version.
    2. Verify status=PROPOSED and is_immutable=False.
    3. Approve rule -> status=ACTIVE, is_immutable=True.
    4. Verify attempting to re-approve an immutable active rule fails with 409 Conflict.
    5. Retrieve version history and verify ordering.
    """
    # 1. Author new proposed version for MPCB-CTO
    new_rule_payload = {
        "statutory_requirement_code": "MPCB-CTO",
        "expression_ast": {
            "operator": "AND",
            "rules": [
                {"field": "jurisdiction", "operator": "eq", "value": "Maharashtra"},
                {"field": "industry_category", "operator": "in", "value": ["RED", "ORANGE"]},
                {"field": "effluent_discharge_kld", "operator": "gte", "value": 10.0},
            ]
        },
        "pass_explanation_template": "Facility operates in {jurisdiction} as {industry_category} discharging {effluent_discharge_kld} KLD.",
        "fail_explanation_template": "Discharge does not meet the 10 KLD threshold for MPCB consent.",
        "change_rationale": "Amended discharge threshold for small red category units per gazette 2026/04.",
    }

    create_resp = client.post("/api/v1/admin/rules", headers=auth_headers_admin, json=new_rule_payload)
    assert create_resp.status_code == 201
    created_rule = create_resp.json()
    rule_id = created_rule["id"]

    assert created_rule["status"] == "PROPOSED"
    assert created_rule["is_immutable"] is False
    assert created_rule["rule_version"] >= 2
    assert created_rule["statutory_requirement_code"] == "MPCB-CTO"

    # 2. Approve the proposed rule
    approve_resp = client.post(f"/api/v1/admin/rules/{rule_id}/approve", headers=auth_headers_admin)
    assert approve_resp.status_code == 200
    approved_rule = approve_resp.json()
    assert approved_rule["status"] == "ACTIVE"
    assert approved_rule["is_immutable"] is True
    assert approved_rule["approved_at"] is not None

    # 3. Attempt to re-approve locked immutable rule -> 400 Bad Request (IMMUTABLE_RECORD_MODIFICATION)
    re_approve_resp = client.post(f"/api/v1/admin/rules/{rule_id}/approve", headers=auth_headers_admin)
    assert re_approve_resp.status_code == 400
    assert re_approve_resp.json()["error"]["code"] == "IMMUTABLE_RECORD_MODIFICATION"

    # 4. Verify version history
    versions_resp = client.get(f"/api/v1/admin/rules/{rule_id}/versions", headers=auth_headers_admin)
    assert versions_resp.status_code == 200
    versions = versions_resp.json()
    assert len(versions) >= 2
    # Verify versions are sorted descending by rule_version
    assert versions[0]["rule_version"] > versions[1]["rule_version"]


def test_supersede_active_rule_workflow(
    client: TestClient,
    auth_headers_admin,
):
    """
    Tests superseding an active rule:
    1. Finds active rule.
    2. Calls /supersede endpoint with new AST, rationale, and effective date.
    3. Verifies original rule transitions to SUPERSEDED.
    4. Verifies newly created rule is version N + 1 and ACTIVE.
    """
    # 1. Get active rule for BOILER-INSP-CERT
    list_resp = client.get("/api/v1/admin/rules?requirement_code=BOILER-INSP-CERT&status=ACTIVE", headers=auth_headers_admin)
    assert list_resp.status_code == 200
    active_rules = list_resp.json()
    assert len(active_rules) > 0
    current_rule = active_rules[0]
    current_rule_id = current_rule["id"]
    current_version = current_rule["rule_version"]

    # 2. Supersede the rule
    supersede_payload = {
        "new_expression_ast": {
            "operator": "OR",
            "rules": [
                {"field": "boiler_count", "operator": "gte", "value": 1},
                {"field": "steam_capacity_tph", "operator": "gte", "value": 0.5},
            ]
        },
        "pass_explanation_template": "Steam boiler capacity threshold met ({steam_capacity_tph} TPH).",
        "fail_explanation_template": "Steam capacity below 0.5 TPH exemption threshold.",
        "change_rationale": "Updated DISH exemption threshold for micro-boilers under 0.5 TPH.",
    }

    supersede_resp = client.post(
        f"/api/v1/admin/rules/{current_rule_id}/supersede",
        headers=auth_headers_admin,
        json=supersede_payload,
    )
    assert supersede_resp.status_code == 200
    new_rule = supersede_resp.json()
    assert new_rule["rule_version"] == current_version + 1
    assert new_rule["status"] == "ACTIVE"
    assert new_rule["is_immutable"] is True
    assert new_rule["change_rationale"] == supersede_payload["change_rationale"]

    # 3. Check version history: previous rule is now SUPERSEDED
    versions_resp = client.get(f"/api/v1/admin/rules/{new_rule['id']}/versions", headers=auth_headers_admin)
    assert versions_resp.status_code == 200
    all_versions = versions_resp.json()
    old_version_record = next((v for v in all_versions if v["id"] == current_rule_id), None)
    assert old_version_record is not None
    assert old_version_record["status"] == "SUPERSEDED"
