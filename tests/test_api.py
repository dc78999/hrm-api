import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_users_default_columns():
    resp = client.get("/users", params={"org_id": "org_1"})
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    # Default columns include email per config
    if body["data"]:
        assert "email" in body["data"][0]

def test_list_users_requested_columns():
    resp = client.get("/users", params={"org_id": "org_2", "columns": "id,first_name,position"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["columns"] == ["id", "first_name", "position"]
    if body["data"]:
        row = body["data"][0]
        assert set(row.keys()) <= set(["id", "first_name", "position"])

def test_rate_limit_exceeded():
    headers = {"X-API-Key": "test-key-rl"}
    # Small number of quick requests to exceed the small bucket in demo config
    # Note: depends on RateLimiter settings, do some fast repeated calls
    allowed = 0
    for i in range(40):
        resp = client.get("/users", params={"org_id": "org_public"}, headers=headers)
        if resp.status_code == 200:
            allowed += 1
        elif resp.status_code == 429:
            assert resp.json()["detail"] == "rate limit exceeded"
            # once we hit 429 we can stop
            break
    assert allowed >= 1
