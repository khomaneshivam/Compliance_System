"""
Integration Tests for Plant and Operational Profile Endpoints (/api/v1/plants)
"""

from fastapi.testclient import TestClient


def get_auth_token(client: TestClient, email: str = "rohit.sharma@acme-mfg.in") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "DemoPass123!"}
    )
    return response.json()["access_token"]


def test_list_and_get_plants(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. List plants
    response = client.get("/api/v1/plants", headers=headers)
    assert response.status_code == 200
    plants = response.json()
    assert len(plants) > 0
    plant = next((p for p in plants if p["code"] == "MH-PUN-01"), plants[0])
    assert plant["name"] == "Acme Manufacturing Pvt. Ltd."
    assert plant["jurisdiction"] == "Maharashtra"
    assert plant["code"] == "MH-PUN-01"

    # 2. Get single plant details
    plant_id = plant["id"]
    detail_resp = client.get(f"/api/v1/plants/{plant_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == plant_id


def test_get_and_update_plant_profile(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    plants_resp = client.get("/api/v1/plants", headers=headers)
    pune_plant = next((p for p in plants_resp.json() if p["code"] == "MH-PUN-01"), plants_resp.json()[0])
    plant_id = pune_plant["id"]

    # 1. Fetch profile
    profile_resp = client.get(f"/api/v1/plants/{plant_id}/profile", headers=headers)
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    assert profile["boiler_count"] >= 1
    assert profile["steam_capacity_tph"] > 0

    # 2. Update profile (e.g. increase employee count)
    new_employee_count = 175
    update_resp = client.put(
        f"/api/v1/plants/{plant_id}/profile",
        headers=headers,
        json={"employee_count": new_employee_count}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["employee_count"] == new_employee_count


def test_list_plant_equipment(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    plants_resp = client.get("/api/v1/plants", headers=headers)
    pune_plant = next((p for p in plants_resp.json() if p["code"] == "MH-PUN-01"), plants_resp.json()[0])
    plant_id = pune_plant["id"]

    equipment_resp = client.get(f"/api/v1/plants/{plant_id}/equipment", headers=headers)
    assert equipment_resp.status_code == 200
    equipment = equipment_resp.json()
    assert len(equipment) > 0
    tags = [e["tag_number"] for e in equipment]
    assert "BLR-01" in tags
