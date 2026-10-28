"""
Integration Tests for Master Data Endpoints (/api/v1/master-data)
"""

from fastapi.testclient import TestClient


def test_list_jurisdictions(client: TestClient):
    """Verifies listing of global jurisdictions and hierarchy."""
    response = client.get("/api/v1/master-data/jurisdictions")
    assert response.status_code == 200
    jurisdictions = response.json()
    assert len(jurisdictions) >= 3
    codes = [j["code"] for j in jurisdictions]
    assert "IN-CENTRAL" in codes
    assert "IN-MH" in codes
    assert "IN-GJ" in codes


def test_list_industry_categories(client: TestClient):
    """Verifies CPCB Red/Orange/Green/White pollution categories."""
    response = client.get("/api/v1/master-data/industry-categories")
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) == 4
    codes = [c["code"] for c in categories]
    assert codes == ["RED", "ORANGE", "GREEN", "WHITE"]


def test_list_regulatory_authorities(client: TestClient):
    """Verifies regulatory authorities endpoint."""
    response = client.get("/api/v1/master-data/authorities")
    assert response.status_code == 200
    authorities = response.json()
    codes = [a["code"] for a in authorities]
    assert "MPCB" in codes
    assert "DISH" in codes
    assert "CPCB" in codes


def test_list_document_types(client: TestClient):
    """Verifies standard document/evidence types."""
    response = client.get("/api/v1/master-data/document-types")
    assert response.status_code == 200
    doc_types = response.json()
    codes = [d["code"] for d in doc_types]
    assert "MPCB_CTO" in codes
    assert "BOILER_INSP_CERT" in codes


def test_list_statutory_requirements_paginated(client: TestClient):
    """Verifies paginated statutory requirements with metadata envelope."""
    response = client.get("/api/v1/master-data/requirements?page=1&page_size=10")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "total" in payload
    assert "page" in payload
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total"] >= 2
    
    codes = [r["code"] for r in payload["items"]]
    assert "MPCB-CTO" in codes
    assert "BOILER-INSP-CERT" in codes


def test_get_statutory_requirement_detail_with_rule_ast(client: TestClient):
    """Verifies fetching requirement detail with structured AST rules and immutability flags."""
    response = client.get("/api/v1/master-data/requirements/MPCB-CTO")
    assert response.status_code == 200
    req = response.json()
    assert req["code"] == "MPCB-CTO"
    assert req["obligation_type"] == "CONSENT"
    assert len(req["rules"]) > 0
    rule = req["rules"][0]
    assert rule["rule_version"] == 1
    assert rule["is_immutable"] is True
    assert "operator" in rule["expression_ast"]
    assert "pass_explanation_template" in rule
