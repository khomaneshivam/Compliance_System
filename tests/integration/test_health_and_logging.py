"""
Integration Tests for Health Probes, Correlation ID, and Structured Error Responses
"""

from fastapi.testclient import TestClient


def test_health_overview(client: TestClient):
    """Verifies health overview returns operational components without exposing secrets."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in ("healthy", "degraded")
    assert "service" in payload
    assert "version" in payload
    assert "components" in payload
    assert "database" in payload["components"]
    assert "vault_storage" in payload["components"]
    assert "correlation_id" in payload
    
    # Assert zero database credentials or secrets leaked
    raw_text = response.text
    assert "password" not in raw_text.lower()
    assert "secret" not in raw_text.lower()
    assert "sqlite" not in raw_text.lower()


def test_liveness_probe(client: TestClient):
    """Verifies liveness probe."""
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_probe(client: TestClient):
    """Verifies readiness probe returns 200 when database is responsive."""
    response = client.get("/api/v1/health/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_correlation_id_header_propagation(client: TestClient):
    """Verifies that correlation ID is generated and returned in HTTP headers."""
    # 1. System auto-generates correlation ID
    response = client.get("/api/v1/health/liveness")
    assert "X-Correlation-ID" in response.headers
    cid = response.headers["X-Correlation-ID"]
    assert len(cid) > 10

    # 2. Client passes custom correlation ID
    custom_cid = "client-trace-id-987654321"
    resp2 = client.get(
        "/api/v1/health/liveness",
        headers={"X-Correlation-ID": custom_cid}
    )
    assert resp2.headers.get("X-Correlation-ID") == custom_cid


def test_validation_error_envelope(client: TestClient):
    """Verifies that 422 validation errors are mapped into the clean error envelope."""
    # Invalid login body (missing password)
    response = client.post("/api/v1/auth/login", json={"email": "invalid-email-format"})
    assert response.status_code == 422
    payload = response.json()
    assert "error" in payload
    error = payload["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "details" in error
    assert "remediation" in error
    assert "correlation_id" in error
