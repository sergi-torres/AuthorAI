"""Tests for POST /api/authors/{author_id}/documents (uploadAuthorDocument).

All Supabase I/O is mocked via unittest.mock.patch so no real DB is needed.
The mock is patched at `app.routes.authors.get_client` — the name as imported
by the route module, not the definition site (standard Python mock hygiene).

Contract being tested: docs/api_contract.yaml §uploadAuthorDocument
  202  happy path  → {document_id: <uuid>, status: "processing"}
  400  bad extension
  400  empty file
  404  unknown author
"""

from __future__ import annotations

import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_AUTHOR_UUID = str(uuid.uuid4())
_FAKE_DOCUMENT_UUID = str(uuid.uuid4())

# A minimal valid text that produces at least one token.
_SAMPLE_TEXT = b"Call me Ishmael. Some years ago, never mind how long precisely."


def _make_sb_mock(author_found: bool = True) -> MagicMock:
    """Build a Supabase client mock that satisfies the call chain used in the route.

    The route calls:
      sb.table("authors").select("id").eq("slug", ...).maybe_single().execute()
      sb.table("documents").insert({...}).execute()
    and in the background task:
      sb.table("chunks").insert([...]).execute()

    We model each table("x") call returning a dedicated chained mock so that
    table("authors") and table("documents") can return different data.
    """
    sb = MagicMock()

    # ---- authors table ----
    authors_chain = MagicMock()
    author_execute = MagicMock()
    if author_found:
        author_execute.data = {"id": _FAKE_AUTHOR_UUID}
    else:
        author_execute.data = None
    authors_chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        author_execute
    )

    # ---- documents table ----
    docs_chain = MagicMock()
    doc_execute = MagicMock()
    doc_execute.data = [{"id": _FAKE_DOCUMENT_UUID}]
    docs_chain.insert.return_value.execute.return_value = doc_execute

    # ---- chunks table ----
    chunks_chain = MagicMock()
    chunks_chain.insert.return_value.execute.return_value = MagicMock()

    def _table_router(name: str) -> MagicMock:
        if name == "authors":
            return authors_chain
        if name == "documents":
            return docs_chain
        if name == "chunks":
            return chunks_chain
        return MagicMock()

    sb.table.side_effect = _table_router
    return sb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("app.routes.authors.get_client")
def test_upload_202_happy_path(mock_get_client: MagicMock) -> None:
    """A valid .txt file for a known author returns 202 with correct schema."""
    mock_get_client.return_value = _make_sb_mock(author_found=True)

    resp = client.post(
        "/api/authors/dickens/documents",
        files={"file": ("great_expectations.txt", BytesIO(_SAMPLE_TEXT), "text/plain")},
    )

    assert resp.status_code == 202
    body = resp.json()
    assert set(body.keys()) == {"document_id", "status"}
    assert body["status"] == "processing"
    # document_id must be the UUID echoed from the DB mock
    assert body["document_id"] == _FAKE_DOCUMENT_UUID


@patch("app.routes.authors.get_client")
def test_upload_202_md_file(mock_get_client: MagicMock) -> None:
    """A valid .md file is also accepted (202)."""
    mock_get_client.return_value = _make_sb_mock(author_found=True)

    resp = client.post(
        "/api/authors/austen/documents",
        files={"file": ("notes.md", BytesIO(_SAMPLE_TEXT), "text/markdown")},
    )

    assert resp.status_code == 202
    assert resp.json()["status"] == "processing"


@patch("app.routes.authors.get_client")
def test_upload_bad_extension(mock_get_client: MagicMock) -> None:
    """A file with an unsupported extension returns 400 before any DB call."""
    mock_get_client.return_value = _make_sb_mock(author_found=True)

    resp = client.post(
        "/api/authors/dickens/documents",
        files={"file": ("document.pdf", BytesIO(_SAMPLE_TEXT), "application/pdf")},
    )

    assert resp.status_code == 400
    body = resp.json()
    # FastAPI wraps HTTPException detail in {"detail": ...}
    assert body["detail"]["error"] == "bad_request"


@patch("app.routes.authors.get_client")
def test_upload_empty_file(mock_get_client: MagicMock) -> None:
    """A zero-byte .txt file returns 400."""
    mock_get_client.return_value = _make_sb_mock(author_found=True)

    resp = client.post(
        "/api/authors/dickens/documents",
        files={"file": ("empty.txt", BytesIO(b""), "text/plain")},
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["error"] == "bad_request"
    assert "empty" in body["detail"]["message"].lower()


@patch("app.routes.authors.get_client")
def test_upload_unknown_author(mock_get_client: MagicMock) -> None:
    """An author_id not present in the DB returns 404."""
    mock_get_client.return_value = _make_sb_mock(author_found=False)

    resp = client.post(
        "/api/authors/unknown_ghost/documents",
        files={"file": ("text.txt", BytesIO(_SAMPLE_TEXT), "text/plain")},
    )

    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["error"] == "not_found"
