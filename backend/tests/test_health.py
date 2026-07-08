"""Happy-path tests for GET /health."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200_status_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_reports_version():
    resp = client.get("/health")
    assert resp.json()["version"] == app.version
