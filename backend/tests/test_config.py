"""Tests for app.config env-var wiring."""

from app.config import (
    REQUIRED_ENV_VARS,
    env_report,
    load_settings,
    missing_required,
)


def test_required_env_vars_are_the_three_deploy_secrets():
    assert set(REQUIRED_ENV_VARS) == {"WATSONX_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"}


def test_env_report_and_missing_agree_when_unset(monkeypatch):
    for name in REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    report = env_report()
    assert report == dict.fromkeys(REQUIRED_ENV_VARS, False)
    assert set(missing_required()) == set(REQUIRED_ENV_VARS)


def test_empty_string_counts_as_missing(monkeypatch):
    monkeypatch.setenv("WATSONX_API_KEY", "")
    assert "WATSONX_API_KEY" in missing_required()
    assert env_report()["WATSONX_API_KEY"] is False


def test_cors_origins_parsed_from_env(monkeypatch):
    monkeypatch.setenv(
        "AUTORIA_CORS_ORIGINS",
        "http://localhost:3000, https://autoria.vercel.app ,",
    )
    settings = load_settings()
    assert settings.cors_origins == (
        "http://localhost:3000",
        "https://autoria.vercel.app",
    )


def test_cors_origins_defaults_to_localhost(monkeypatch):
    monkeypatch.delenv("AUTORIA_CORS_ORIGINS", raising=False)
    settings = load_settings()
    assert settings.cors_origins == ("http://localhost:3000",)
