"""Tests for app.config env-var wiring."""

from pathlib import Path

import app.config as config
from app.config import (
    REQUIRED_ENV_VARS,
    env_report,
    load_settings,
    missing_required,
    to_asyncpg_dsn,
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


# ---------------------------------------------------------------------------
# DATABASE_URL — asyncpg DSN normalisation (issue #87 / WO-06)
#
# `.env.example` documents the plain `postgresql://` scheme (what Supabase
# hands out and what the psycopg2 seeding scripts consume), but the RAG path
# ends in SQLAlchemy's create_async_engine, which rejects a driver-less URL.
# config.py translates at the boundary, exactly like
# scripts/seed_corpus.py:to_asyncpg_url.
# ---------------------------------------------------------------------------

_PLAIN_DSN = "postgresql://postgres.abc:pw@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
_ASYNC_DSN = (
    "postgresql+asyncpg://postgres.abc:pw@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
)


def test_to_asyncpg_dsn_rewrites_plain_postgresql_scheme():
    assert to_asyncpg_dsn(_PLAIN_DSN) == _ASYNC_DSN


def test_to_asyncpg_dsn_rewrites_short_postgres_scheme():
    assert to_asyncpg_dsn("postgres://u:p@h:5432/db") == "postgresql+asyncpg://u:p@h:5432/db"


def test_to_asyncpg_dsn_is_idempotent():
    assert to_asyncpg_dsn(_ASYNC_DSN) == _ASYNC_DSN


def test_to_asyncpg_dsn_preserves_credentials_and_query_string():
    raw = "postgresql://u:p%40ss@h:5432/db?sslmode=require"
    assert to_asyncpg_dsn(raw) == "postgresql+asyncpg://u:p%40ss@h:5432/db?sslmode=require"


def test_to_asyncpg_dsn_leaves_other_drivers_untouched():
    """Normalisation is a convenience, not a validator — don't mangle inputs."""
    raw = "postgresql+psycopg://u:p@h:5432/db"
    assert to_asyncpg_dsn(raw) == raw


def test_settings_database_url_is_async_form(monkeypatch):
    """load_settings() exposes the DSN create_async_engine can actually open."""
    monkeypatch.setenv("DATABASE_URL", _PLAIN_DSN)
    assert load_settings().database_url == _ASYNC_DSN


def test_settings_database_url_none_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert load_settings().database_url is None


def test_settings_database_url_none_when_empty(monkeypatch):
    """An empty value is a missing value — never hand '' to create_async_engine."""
    monkeypatch.setenv("DATABASE_URL", "")
    assert load_settings().database_url is None


# ---------------------------------------------------------------------------
# .env overlay — the platform environment must always win
# ---------------------------------------------------------------------------


def test_dotenv_path_is_repo_root():
    """The overlay is the repo-root `.env` documented in DEPLOYMENT.md."""
    assert Path(config._REPO_ROOT, ".env") == config._DOTENV_PATH
    assert (config._REPO_ROOT / ".env.example").is_file()


def test_dotenv_does_not_override_platform_variables(monkeypatch, tmp_path):
    """A stale `.env` must never clobber a Railway/Vercel-injected variable.

    The regression this guards: loading with override=True would let a `.env`
    baked into the deploy image replace the dashboard's value.
    """
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text('AUTORIA_WO06_PROBE="from-dotenv"\n', encoding="utf-8")
    monkeypatch.setattr(config, "_DOTENV_PATH", dotenv_file)

    # Simulates the platform injecting the variable into the process env.
    monkeypatch.setenv("AUTORIA_WO06_PROBE", "from-platform")
    assert config._load_dotenv_once() is True

    import os

    assert os.environ["AUTORIA_WO06_PROBE"] == "from-platform"


def test_dotenv_fills_in_variables_absent_from_the_environment(monkeypatch, tmp_path):
    """With nothing injected, the `.env` value is what local dev gets."""
    import os

    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text('AUTORIA_WO06_PROBE="from-dotenv"\n', encoding="utf-8")
    monkeypatch.setattr(config, "_DOTENV_PATH", dotenv_file)
    os.environ.pop("AUTORIA_WO06_PROBE", None)

    try:
        assert config._load_dotenv_once() is True
        assert os.environ["AUTORIA_WO06_PROBE"] == "from-dotenv"
    finally:
        # load_dotenv writes straight to os.environ, outside monkeypatch's
        # undo log — clean up so the name cannot leak into another test.
        os.environ.pop("AUTORIA_WO06_PROBE", None)


def test_dotenv_load_is_a_noop_when_file_absent(monkeypatch, tmp_path):
    """No `.env` (the normal production case) is not an error."""
    monkeypatch.setattr(config, "_DOTENV_PATH", tmp_path / "does-not-exist.env")
    assert config._load_dotenv_once() is False
