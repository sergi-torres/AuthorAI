"""Runtime configuration and environment-variable wiring.

Centralizes access to deployment secrets so routes/services never call
``os.getenv`` directly. On Railway/Vercel these values are injected by the
platform; locally they come from ``.env`` (see ``.env.example``).

Importing this module loads the repo-root ``.env`` into ``os.environ`` with
``override=False`` — see ``_load_dotenv_once()``. Every backend entry point
reaches configuration through here (``app.main``, ``app.db``,
``app.services.watsonx_client``, ``app.routes.diagnostics``), so that single
import is enough to give ``uvicorn app.main:app`` the same environment the
platform dashboards inject in production.

Secrets are NEVER logged or serialized. ``env_report()`` and
``missing_required()`` expose only booleans / names — never the values — so
they are safe to surface over the deploy-verification endpoint.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Secrets that MUST be injected on BOTH platforms for the app to be healthy.
# Keep in sync with .env.example and docs/DEPLOYMENT.md.
REQUIRED_ENV_VARS: tuple[str, ...] = ("WATSONX_API_KEY", "SUPABASE_URL", "SUPABASE_KEY")

# Passport key env var names — exposed only as presence booleans in env_report().
PASSPORT_ENV_VARS: tuple[str, ...] = (
    "PASSPORT_PRIVATE_KEY_PATH",
    "PASSPORT_PUBLIC_KEY_PATH",
    "PASSPORT_KID",
    "PASSPORT_VERIFIER_URL",
)

_DEFAULT_CORS_ORIGINS = "http://localhost:3000"

# backend/app/config.py -> parents[2] == repo root (where `.env` lives per
# README.md, CONTRIBUTING.md and docs/DEPLOYMENT.md §"Local parity").
_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_DOTENV_PATH: Path = _REPO_ROOT / ".env"


def _split_origins(raw: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------


def _load_dotenv_once() -> bool:
    """Load the repo-root ``.env`` into ``os.environ``; return True if read.

    ``override=False`` is load-bearing, not a stylistic default: on Railway and
    Vercel the real secrets are injected into the process environment by the
    platform, and a stale ``.env`` that happened to ship in the image must
    never win over them. Only names that are *absent* from the environment are
    filled in, so the platform always has the last word and this call is a
    no-op in production (where no ``.env`` exists at all).

    ``python-dotenv`` is a declared runtime dependency (``pyproject.toml`` /
    ``requirements.txt``), but its absence is degraded rather than fatal: a
    deploy that injects every variable through the dashboard does not need it,
    and ``/health`` must keep answering either way.
    """
    if not _DOTENV_PATH.is_file():
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependency is declared
        logger.warning(
            "python-dotenv is not installed; %s will NOT be read. "
            "Configuration must come from the process environment.",
            _DOTENV_PATH,
        )
        return False
    load_dotenv(_DOTENV_PATH, override=False)
    logger.info("Loaded local environment overlay from %s (override=False).", _DOTENV_PATH)
    return True


_DOTENV_LOADED: bool = _load_dotenv_once()


# ---------------------------------------------------------------------------
# DATABASE_URL normalisation
# ---------------------------------------------------------------------------


def to_asyncpg_dsn(database_url: str) -> str:
    """Return *database_url* in the ``postgresql+asyncpg://`` form.

    ``.env.example`` — the canonical list of variable names and shapes — spells
    ``DATABASE_URL`` with the plain ``postgresql://`` scheme, because that is
    the DSN Supabase's dashboard hands out and the one psycopg2 consumers
    (``scripts/seed_corpus.py``, ``scripts/precompute_umap.py``) expect. The
    RAG path is the opposite: ``autoria_ai.db._make_engine`` feeds the value to
    SQLAlchemy's ``create_async_engine``, which rejects a driver-less
    ``postgresql://`` URL outright.

    Rather than change the documented ``.env`` shape (which would break the
    seeding scripts) or ``autoria_ai.db``'s contract (explicitly out of scope
    for WO-06), the backend translates at the boundary — the same rule, in the
    same direction, as ``scripts/seed_corpus.py:to_asyncpg_url``. Both plain
    schemes are accepted; ``postgres://`` is the short form some hosts emit.

    A DSN that already names a driver (``postgresql+asyncpg``,
    ``postgresql+psycopg``, ...) is returned untouched, as is any unrecognised
    scheme — normalising is a convenience, not a validator, and swallowing an
    unknown DSN here would replace one silent failure with another.
    """
    if database_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + database_url[len("postgresql://") :]
    if database_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + database_url[len("postgres://") :]
    return database_url


def _resolve_database_url() -> str | None:
    """Read ``DATABASE_URL`` and return it as an async-engine-ready DSN."""
    raw = os.getenv("DATABASE_URL")
    if not raw:
        return None
    return to_asyncpg_dsn(raw)


@dataclass(frozen=True)
class Settings:
    """Snapshot of process configuration, read once at import time."""

    watsonx_api_key: str | None
    watsonx_url: str | None
    watsonx_project_id: str | None
    supabase_url: str | None
    supabase_key: str | None
    #: Async DSN for the pgvector RAG lookup — always in the
    #: ``postgresql+asyncpg://`` form (see ``to_asyncpg_dsn``), never the plain
    #: ``postgresql://`` scheme written in ``.env``. ``None`` when unset.
    database_url: str | None
    cors_origins: tuple[str, ...]
    # Passport — paths/ids only; never log the values of *_PATH vars.
    passport_private_key_path: str | None
    passport_public_key_path: str | None
    passport_kid: str | None
    passport_verifier_url: str | None


def load_settings() -> Settings:
    """Read the current environment into an immutable ``Settings``."""
    return Settings(
        watsonx_api_key=os.getenv("WATSONX_API_KEY"),
        watsonx_url=os.getenv("WATSONX_URL"),
        watsonx_project_id=os.getenv("WATSONX_PROJECT_ID"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        database_url=_resolve_database_url(),
        cors_origins=_split_origins(os.getenv("AUTORIA_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)),
        passport_private_key_path=os.getenv("PASSPORT_PRIVATE_KEY_PATH"),
        passport_public_key_path=os.getenv("PASSPORT_PUBLIC_KEY_PATH"),
        passport_kid=os.getenv("PASSPORT_KID"),
        passport_verifier_url=os.getenv("PASSPORT_VERIFIER_URL"),
    )


settings = load_settings()


def _log_database_url_status() -> None:
    """State once, at import, whether RAG retrieval can work at all.

    Without this the only symptom of an unset ``DATABASE_URL`` is a generic
    ``RAG retrieval failed`` warning emitted by
    ``autoria_ai.generator.orchestrate`` on *every* generation, while the
    request still returns 200 with ``rag_sources: []`` — a configuration error
    disguised as a per-request hiccup (issue #87).
    """
    if settings.database_url:
        return
    logger.error(
        "DATABASE_URL is not set: RAG retrieval is disabled for this process. "
        "Every /api/generate will fall back to an unconditioned prompt "
        "('(no example passages provided)') and issue a passport with "
        "rag_sources: []. Set DATABASE_URL in %s (local) or in the Railway "
        "service Variables (deploy). See .env.example.",
        _DOTENV_PATH,
    )


_log_database_url_status()


def env_report() -> dict[str, bool]:
    """Presence map for the required secrets — booleans only, never values.

    Read live from ``os.environ`` (not the cached ``settings``) so the deploy
    check reflects the real process env even if it changed after import.
    """
    return {name: bool(os.getenv(name)) for name in REQUIRED_ENV_VARS}


def missing_required() -> list[str]:
    """Names of required secrets that are unset or empty."""
    return [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
