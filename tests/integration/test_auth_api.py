"""
Integration Tests for Authentication Endpoints (/api/v1/auth)
"""

from fastapi.testclient import TestClient


def test_login_success_and_me_profile(client: TestClient):
    # 1. Login with seeded credentials
    login_payload = {
        "email": "rohit.sharma@acme-mfg.in",
        "password": "DemoPass123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "rohit.sharma@acme-mfg.in"
    assert data["user"]["full_name"] == "Rohit Sharma"
    assert data["user"]["role"] == "PLANT_MANAGER"
    assert len(data["user"]["plant_ids"]) > 0

    token = data["access_token"]

    # 2. Query /api/v1/auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["id"] == data["user"]["id"]
    assert me_data["email"] == "rohit.sharma@acme-mfg.in"


def test_login_invalid_password(client: TestClient):
    login_payload = {
        "email": "rohit.sharma@acme-mfg.in",
        "password": "IncorrectPassword!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    payload = response.json()
    error_msg = payload.get("error", {}).get("message", payload.get("detail", ""))
    assert "Incorrect email or password" in error_msg


def test_unauthenticated_request_rejected(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
