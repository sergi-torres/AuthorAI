"""Tests for POST /api/authors/{author_id}/style-profile/recompute
(recomputeAuthorStyleProfile).

All Supabase I/O is mocked via unittest.mock.patch so no real DB is needed.
The mock is patched at `app.routes.authors.get_client` — the name as imported
by the route module, not the definition site (standard Python mock hygiene).

Contract being tested: docs/api_contract.yaml §recomputeAuthorStyleProfile
  202  happy path  → {status: "computing", estimated_seconds: <int >= 0>}
  404  unknown author
  background task  → style_profiles.insert was called with a schema-valid row
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_AUTHOR_UUID = str(uuid.uuid4())

# Simulate two documents with known token counts so estimated_seconds is
# deterministic: 4000 + 2000 = 6000 tokens → max(30, 6000 // 2000) = max(30, 3) = 30
_FAKE_DOCS = [{"n_tokens": 4000}, {"n_tokens": 2000}]

# A larger corpus that pushes estimated_seconds above the floor:
# 120_000 tokens → max(30, 120_000 // 2000) = max(30, 60) = 60
_LARGE_DOCS = [{"n_tokens": 120_000}]


def _make_sb_mock(
    *,
    author_found: bool = True,
    doc_rows: list[dict] | None = None,
) -> MagicMock:
    """Build a Supabase client mock for the recompute route.

    The route calls:
      sb.table("authors").select("id").eq("slug", ...).maybe_single().execute()
      sb.table("documents").select("n_tokens").eq("author_id", ...).execute()
    and in the background task:
      sb.table("style_profiles").insert({...}).execute()

    We model each table("x") call returning a dedicated chained mock so that
    table("authors"), table("documents"), and table("style_profiles") can each
    return different data.
    """
    if doc_rows is None:
        doc_rows = _FAKE_DOCS

    sb = MagicMock()

    # ---- authors table ----
    authors_chain = MagicMock()
    author_execute = MagicMock()
    author_execute.data = {"id": _FAKE_AUTHOR_UUID} if author_found else None
    authors_chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        author_execute
    )

    # ---- documents table ----
    docs_chain = MagicMock()
    docs_execute = MagicMock()
    docs_execute.data = doc_rows
    docs_chain.select.return_value.eq.return_value.execute.return_value = docs_execute

    # ---- style_profiles table ----
    profiles_chain = MagicMock()
    profiles_chain.insert.return_value.execute.return_value = MagicMock()

    def _table_router(name: str) -> MagicMock:
        if name == "authors":
            return authors_chain
        if name == "documents":
            return docs_chain
        if name == "style_profiles":
            return profiles_chain
        return MagicMock()

    sb.table.side_effect = _table_router
    return sb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("app.routes.authors.get_client")
def test_recompute_202_happy_path(mock_get_client: MagicMock) -> None:
    """Known author returns 202 with status='computing' and estimated_seconds >= 0."""
    mock_get_client.return_value = _make_sb_mock(author_found=True)

    resp = client.post("/api/authors/dickens/style-profile/recompute")

    assert resp.status_code == 202
    body = resp.json()
    assert set(body.keys()) == {"status", "estimated_seconds"}
    assert body["status"] == "computing"
    assert isinstance(body["estimated_seconds"], int)
    assert body["estimated_seconds"] >= 0


@patch("app.routes.authors.get_client")
def test_recompute_estimated_seconds_floor(mock_get_client: MagicMock) -> None:
    """estimated_seconds is at least 30 even for a small corpus (floor heuristic)."""
    # 6 000 tokens → 6000 // 2000 = 3; max(30, 3) = 30
    mock_get_client.return_value = _make_sb_mock(author_found=True, doc_rows=_FAKE_DOCS)

    resp = client.post("/api/authors/austen/style-profile/recompute")

    assert resp.status_code == 202
    assert resp.json()["estimated_seconds"] == 30


@patch("app.routes.authors.get_client")
def test_recompute_estimated_seconds_above_floor(mock_get_client: MagicMock) -> None:
    """estimated_seconds exceeds 30 when the corpus is large enough."""
    # 120 000 tokens → 120 000 // 2000 = 60; max(30, 60) = 60
    mock_get_client.return_value = _make_sb_mock(author_found=True, doc_rows=_LARGE_DOCS)

    resp = client.post("/api/authors/dickens/style-profile/recompute")

    assert resp.status_code == 202
    assert resp.json()["estimated_seconds"] == 60


@patch("app.routes.authors.get_client")
def test_recompute_404_unknown_author(mock_get_client: MagicMock) -> None:
    """An author_id not present in the DB returns 404 with error: not_found."""
    mock_get_client.return_value = _make_sb_mock(author_found=False)

    resp = client.post("/api/authors/ghost_writer/style-profile/recompute")

    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["error"] == "not_found"
    assert "ghost_writer" in detail["message"]


@patch("app.routes.authors.get_client")
def test_recompute_background_task_insert_called(mock_get_client: MagicMock) -> None:
    """The background task runs and calls style_profiles.insert exactly once.

    FastAPI's TestClient executes BackgroundTasks synchronously before
    returning, so we can assert on the mock immediately after the response.
    """
    sb = _make_sb_mock(author_found=True)
    mock_get_client.return_value = sb

    resp = client.post("/api/authors/poe/style-profile/recompute")

    assert resp.status_code == 202

    # style_profiles table was accessed
    profiles_chain = sb.table("style_profiles")
    profiles_chain.insert.assert_called_once()

    # The inserted payload must contain the required keys
    inserted_payload: dict = profiles_chain.insert.call_args[0][0]
    assert inserted_payload["author_id"] == _FAKE_AUTHOR_UUID
    assert inserted_payload["version"] == "1.0"
    assert "json_data" in inserted_payload
    assert "hash" in inserted_payload
    assert inserted_payload["hash"].startswith("sha256:")

    # Stub stylistic distributions must include all schema-required keys
    stylistic = inserted_payload["json_data"]["stylistic"]
    assert set(stylistic["punct_distribution"]) == {",", ".", ";", ":", "—", "?", "!", '"'}
    assert set(stylistic["pos_distribution"]) == {
        "NOUN",
        "VERB",
        "ADJ",
        "ADV",
        "DET",
        "ADP",
        "PRON",
        "CONJ",
        "SCONJ",
        "OTHER",
    }
