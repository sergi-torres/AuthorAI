"""Tests for GET /api/authors/{author_id}/style-profile (getAuthorStyleProfile).

All Supabase I/O is mocked via unittest.mock.patch so no real DB is needed.
The mock is patched at `app.routes.authors.get_client` — the name as imported
by the route module, not the definition site (standard Python mock hygiene).

Contract being tested: docs/api_contract.yaml §getAuthorStyleProfile
  200  happy path         → stored json_data returned verbatim
  404  unknown author     → {error: "not_found", message: "Author '...' not found"}
  404  no profile yet     → {error: "not_found", message: "StyleProfile not yet computed ..."}
  200  latest-wins        → when multiple rows exist, the newest json_data is returned
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FAKE_AUTHOR_UUID = str(uuid.uuid4())

_SAMPLE_PROFILE: dict = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "corpus_stats": {"n_documents": 4, "n_tokens": 120000},
}

_OLDER_PROFILE: dict = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "corpus_stats": {"n_documents": 2, "n_tokens": 60000},
}

_NEWER_PROFILE: dict = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "corpus_stats": {"n_documents": 4, "n_tokens": 120000},
}


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_sb_mock(
    *,
    author_found: bool = True,
    profile_rows: list[dict] | None = None,
) -> MagicMock:
    """Build a Supabase client mock for the style-profile route.

    The route calls:
      sb.table("authors").select("id").eq("slug", ...).maybe_single().execute()
      sb.table("style_profiles").select("json_data").eq("author_id", ...)
          .order("computed_at", desc=True).limit(1).execute()

    ``profile_rows`` is the list returned in ``execute().data``; pass ``[]``
    to simulate a missing profile, or a list with one element for a hit.
    The mock always returns only ``profile_rows[0]`` to reflect the
    ``.limit(1)`` semantics — the caller controls which row is "newest".
    """
    if profile_rows is None:
        profile_rows = [{"json_data": _SAMPLE_PROFILE}]

    sb = MagicMock()

    # ---- authors table ----
    authors_chain = MagicMock()
    author_execute = MagicMock()
    author_execute.data = {"id": _FAKE_AUTHOR_UUID} if author_found else None
    authors_chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        author_execute
    )

    # ---- style_profiles table ----
    profiles_chain = MagicMock()
    profile_execute = MagicMock()
    profile_execute.data = profile_rows
    profiles_chain.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
        profile_execute
    )

    def _table_router(name: str) -> MagicMock:
        if name == "authors":
            return authors_chain
        if name == "style_profiles":
            return profiles_chain
        return MagicMock()

    sb.table.side_effect = _table_router
    return sb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("app.routes.authors.get_client")
def test_get_style_profile_200(mock_get_client: MagicMock) -> None:
    """Known author with a profile returns 200 and the json_data verbatim."""
    mock_get_client.return_value = _make_sb_mock(
        author_found=True,
        profile_rows=[{"json_data": _SAMPLE_PROFILE}],
    )

    resp = client.get("/api/authors/dickens/style-profile")

    assert resp.status_code == 200
    assert resp.json() == _SAMPLE_PROFILE


@patch("app.routes.authors.get_client")
def test_get_style_profile_404_unknown_author(mock_get_client: MagicMock) -> None:
    """Slug not in the authors table → 404 with error: not_found."""
    mock_get_client.return_value = _make_sb_mock(author_found=False)

    resp = client.get("/api/authors/ghost_writer/style-profile")

    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["error"] == "not_found"
    assert "ghost_writer" in detail["message"]


@patch("app.routes.authors.get_client")
def test_get_style_profile_404_no_profile(mock_get_client: MagicMock) -> None:
    """Author exists but has no style_profiles rows → 404 with error: not_found."""
    mock_get_client.return_value = _make_sb_mock(
        author_found=True,
        profile_rows=[],
    )

    resp = client.get("/api/authors/poe/style-profile")

    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["error"] == "not_found"
    assert "poe" in detail["message"]


@patch("app.routes.authors.get_client")
def test_get_style_profile_latest_wins(mock_get_client: MagicMock) -> None:
    """When multiple profiles exist the route returns only the newest one.

    The mock returns only _NEWER_PROFILE (simulating the DB honouring
    ORDER BY computed_at DESC LIMIT 1), and the test asserts the response
    body matches _NEWER_PROFILE, not _OLDER_PROFILE.
    """
    mock_get_client.return_value = _make_sb_mock(
        author_found=True,
        profile_rows=[{"json_data": _NEWER_PROFILE}],
    )

    resp = client.get("/api/authors/dickens/style-profile")

    assert resp.status_code == 200
    body = resp.json()
    assert body == _NEWER_PROFILE
    assert body != _OLDER_PROFILE
