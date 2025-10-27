from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_search_employees_requires_organization():
    """Should require organization_id in headers"""
    response = client.get("/api/v1/employees/search")
    assert response.status_code == 400
    assert "organization_id" in response.json()["detail"].lower()

def test_search_employees_basic_filter():
    """Should filter employees by basic fields"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": "test-org-id"},
        params={"location": "New York"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    for employee in data["items"]:
        assert employee["location"] == "New York"

def test_search_employees_text_search():
    """Should support full-text search across fields"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": "test-org-id"},
        params={"q": "engineer"}
    )
    assert response.status_code == 200
    data = response.json()
    for employee in data["items"]:
        # Should match either position or skills
        assert ("engineer" in employee["position"].lower() or 
                "engineer" in str(employee["data"]).lower())

def test_search_employees_pagination():
    """Should support pagination"""
    page_size = 5
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": "test-org-id"},
        params={"page": 1, "page_size": page_size}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= page_size
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1
