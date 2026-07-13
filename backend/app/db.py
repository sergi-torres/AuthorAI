"""Supabase client factory.

A thin wrapper so routes import `get_client` and tests can monkeypatch it
without coupling to supabase-py internals.

Usage:
    from app.db import get_client
    sb = get_client()
    sb.table("documents").insert({...}).execute()
"""

from __future__ import annotations

from supabase import Client, create_client

from app.config import settings


def get_client() -> Client:
    """Return a supabase-py client wired to SUPABASE_URL + SUPABASE_KEY.

    Called once per request; supabase-py is stateless over HTTP so there is no
    connection-pooling concern at MVP scale.

    Raises RuntimeError if the required env vars are absent (caught early by
    the /health diagnostics endpoint, so this path only fires in misconfigured
    deploys).
    """
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set. "
            "Check .env.example and docs/DEPLOYMENT.md."
        )
    return create_client(settings.supabase_url, settings.supabase_key)
