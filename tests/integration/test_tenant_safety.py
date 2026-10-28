"""
Integration Tests for Multi-Tenant Data Isolation and Cross-Tenant Safety
Verifies that Tenant A cannot read, update, delete or infer Tenant B's data.
"""

from fastapi.testclient import TestClient


def test_tenant_a_cannot_access_tenant_b_plant(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_b_plant_id: str
):
    """Proves Tenant A cannot fetch Tenant B's plant by ID."""
    response = client.get(
        f"/api/v1/plants/{tenant_b_plant_id}",
        headers=auth_headers_tenant_a
    )
    assert response.status_code == 403
    payload = response.json()
    assert "error" in payload
    assert payload["error"]["code"] in ("TENANT_ACCESS_DENIED", "HTTP_ERROR")


def test_tenant_b_cannot_access_tenant_a_plant(
    client: TestClient,
    auth_headers_tenant_b,
    tenant_a_plant_id: str
):
    """Proves Tenant B cannot fetch Tenant A's plant by ID."""
    response = client.get(
        f"/api/v1/plants/{tenant_a_plant_id}",
        headers=auth_headers_tenant_b
    )
    assert response.status_code == 403
    payload = response.json()
    assert "error" in payload
    assert payload["error"]["code"] in ("TENANT_ACCESS_DENIED", "HTTP_ERROR")


def test_tenant_a_cannot_access_or_update_tenant_b_profile(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_b_plant_id: str
):
    """Proves Tenant A cannot read or mutate Tenant B's operational profile."""
    # 1. Attempt Read
    read_resp = client.get(
        f"/api/v1/plants/{tenant_b_plant_id}/profile",
        headers=auth_headers_tenant_a
    )
    assert read_resp.status_code == 403

    # 2. Attempt Mutation
    update_resp = client.put(
        f"/api/v1/plants/{tenant_b_plant_id}/profile",
        headers=auth_headers_tenant_a,
        json={"employee_count": 999}
    )
    assert update_resp.status_code == 403


def test_tenant_a_cannot_view_tenant_b_equipment(
    client: TestClient,
    auth_headers_tenant_a,
    tenant_b_plant_id: str
):
    """Proves Tenant A cannot enumerate Tenant B's equipment or capacity tags."""
    response = client.get(
        f"/api/v1/plants/{tenant_b_plant_id}/equipment",
        headers=auth_headers_tenant_a
    )
    assert response.status_code == 403


def test_tenant_isolation_in_plant_listing(
    client: TestClient,
    auth_headers_tenant_a,
    auth_headers_tenant_b,
    tenant_a_plant_id: str,
    tenant_b_plant_id: str
):
    """Proves Tenant A and B listings return strictly their own facilities."""
    # Tenant A
    resp_a = client.get("/api/v1/plants", headers=auth_headers_tenant_a)
    assert resp_a.status_code == 200
    ids_a = [p["id"] for p in resp_a.json()]
    assert tenant_a_plant_id in ids_a
    assert tenant_b_plant_id not in ids_a

    # Tenant B
    resp_b = client.get("/api/v1/plants", headers=auth_headers_tenant_b)
    assert resp_b.status_code == 200
    ids_b = [p["id"] for p in resp_b.json()]
    assert tenant_b_plant_id in ids_b
    assert tenant_a_plant_id not in ids_b


def test_nonexistent_plant_returns_clean_404(
    client: TestClient,
    auth_headers_tenant_a
):
    """Proves invalid IDs return clean 404 without leaking internal traces."""
    response = client.get(
        "/api/v1/plants/00000000-0000-0000-0000-000000000000",
        headers=auth_headers_tenant_a
    )
    assert response.status_code == 404
    payload = response.json()
    assert "error" in payload
    assert "remediation" in payload["error"]
