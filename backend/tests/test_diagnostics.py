"""Tests for GET /internal/env-check (deploy verification helper)."""

from fastapi.testclient import TestClient

from app.config import REQUIRED_ENV_VARS
from app.main import app

client = TestClient(app)


def test_env_check_returns_200_with_report_shape():
    resp = client.get("/internal/env-check")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"all_present", "required", "present", "missing"}
    assert body["required"] == list(REQUIRED_ENV_VARS)
    assert set(body["present"]) == set(REQUIRED_ENV_VARS)


def test_env_check_reports_missing_when_unset(monkeypatch):
    for name in REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    body = client.get("/internal/env-check").json()

    assert body["all_present"] is False
    assert set(body["missing"]) == set(REQUIRED_ENV_VARS)
    assert all(present is False for present in body["present"].values())


def test_env_check_all_present_when_set(monkeypatch):
    for name in REQUIRED_ENV_VARS:
        monkeypatch.setenv(name, "test-value")

    body = client.get("/internal/env-check").json()

    assert body["all_present"] is True
    assert body["missing"] == []
    assert all(present is True for present in body["present"].values())


def test_env_check_never_leaks_secret_values(monkeypatch):
    monkeypatch.setenv("WATSONX_API_KEY", "super-secret-token")

    raw = client.get("/internal/env-check").text

    assert "super-secret-token" not in raw
