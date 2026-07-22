"""Runtime configuration and environment-variable wiring.

Centralizes access to deployment secrets so routes/services never call
``os.getenv`` directly. On Railway/Vercel these values are injected by the
platform; locally they come from ``.env`` (see ``.env.example``).

Secrets are NEVER logged or serialized. ``env_report()`` and
``missing_required()`` expose only booleans / names — never the values — so
they are safe to surface over the deploy-verification endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

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


def _split_origins(raw: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    """Snapshot of process configuration, read once at import time."""

    watsonx_api_key: str | None
    watsonx_url: str | None
    watsonx_project_id: str | None
    supabase_url: str | None
    supabase_key: str | None
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
        database_url=os.getenv("DATABASE_URL"),
        cors_origins=_split_origins(os.getenv("AUTORIA_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)),
        passport_private_key_path=os.getenv("PASSPORT_PRIVATE_KEY_PATH"),
        passport_public_key_path=os.getenv("PASSPORT_PUBLIC_KEY_PATH"),
        passport_kid=os.getenv("PASSPORT_KID"),
        passport_verifier_url=os.getenv("PASSPORT_VERIFIER_URL"),
    )


settings = load_settings()


def env_report() -> dict[str, bool]:
    """Presence map for the required secrets — booleans only, never values.

    Read live from ``os.environ`` (not the cached ``settings``) so the deploy
    check reflects the real process env even if it changed after import.
    """
    return {name: bool(os.getenv(name)) for name in REQUIRED_ENV_VARS}


def missing_required() -> list[str]:
    """Names of required secrets that are unset or empty."""
    return [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
