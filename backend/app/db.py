"""Supabase client factory.

A thin wrapper so routes import `get_client` and tests can monkeypatch it
without coupling to supabase-py internals.

Usage:
    from app.db import get_client
    sb = get_client()
    sb.table("documents").insert({...}).execute()
"""

from __future__ import annotations

from typing import Any

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


def get_current_style_profile(sb: Client, author_uuid: str) -> dict[str, Any] | None:
    """Return the *current* StyleProfile ``json_data`` for `author_uuid`.

    ``style_profiles`` recomputes deliberately **append** a new row instead of
    overwriting (see ``docs/erd.md`` §"style_profiles" and the table comment
    in ``infra/supabase/migrations/0001_init.sql``): past profiles stay
    queryable as history, and "the current profile" is defined as the one
    with the latest ``computed_at``.

    A bare ``.select(...).eq("author_id", X)`` without an explicit order and
    limit would return an *arbitrary* row once an author has more than one —
    which happens on every re-seed or recompute (#108). Routes must call this
    helper instead of querying ``style_profiles`` directly, so that
    invariant lives in exactly one place rather than being copy-pasted (and
    potentially dropped) at every call site.

    Returns ``None`` if the author has no StyleProfile yet.
    """
    result = (
        sb.table("style_profiles")
        .select("json_data")
        .eq("author_id", author_uuid)
        .order("computed_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]["json_data"]
