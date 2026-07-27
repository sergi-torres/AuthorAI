"""Tests for GET /api/authors (listAuthors).

Supabase I/O is mocked at ``app.routes.authors.get_client``.
Contract: docs/api_contract.yaml §AuthorSummary.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_REQUIRED_FIELDS = {"id", "name", "slug", "has_style_profile", "n_documents"}

_AUSTEN_UUID = str(uuid.uuid4())
_DICKENS_UUID = str(uuid.uuid4())
_POE_UUID = str(uuid.uuid4())

_FAKE_AUTHORS = [
    {"id": _AUSTEN_UUID, "name": "Jane Austen", "slug": "austen"},
    {"id": _DICKENS_UUID, "name": "Charles Dickens", "slug": "dickens"},
    {"id": _POE_UUID, "name": "Edgar Allan Poe", "slug": "poe"},
]


@pytest.fixture(autouse=True)
def _stub_supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_KEY", "test-supabase-key")
    monkeypatch.setenv("AUTORIA_SKIP_MODEL_WARMUP", "1")


def _make_sb_mock(
    *,
    authors: list[dict] | None = None,
    documents: list[dict] | None = None,
    style_profiles: list[dict] | None = None,
) -> MagicMock:
    if authors is None:
        authors = _FAKE_AUTHORS
    if documents is None:
        documents = [
            {"author_id": _AUSTEN_UUID},
            {"author_id": _AUSTEN_UUID},
            {"author_id": _DICKENS_UUID},
            {"author_id": _DICKENS_UUID},
            {"author_id": _DICKENS_UUID},
            {"author_id": _DICKENS_UUID},
            {"author_id": _POE_UUID},
            {"author_id": _POE_UUID},
        ]
    if style_profiles is None:
        style_profiles = [{"author_id": _DICKENS_UUID}]

    sb = MagicMock()

    authors_chain = MagicMock()
    authors_exec = MagicMock()
    authors_exec.data = authors
    authors_chain.select.return_value.order.return_value.execute.return_value = authors_exec

    docs_chain = MagicMock()
    docs_exec = MagicMock()
    docs_exec.data = documents
    docs_chain.select.return_value.execute.return_value = docs_exec

    profiles_chain = MagicMock()
    profiles_exec = MagicMock()
    profiles_exec.data = style_profiles
    profiles_chain.select.return_value.execute.return_value = profiles_exec

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


@patch("app.routes.authors.get_client")
def test_list_authors_returns_three_seeded(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = _make_sb_mock()

    resp = client.get("/api/authors")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert {a["id"] for a in data} == {"austen", "dickens", "poe"}


@patch("app.routes.authors.get_client")
def test_list_authors_matches_contract_shape(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = _make_sb_mock()

    data = client.get("/api/authors").json()
    for author in data:
        assert _REQUIRED_FIELDS.issubset(author.keys())
        assert author["slug"] == author["id"]
        assert isinstance(author["has_style_profile"], bool)
        assert isinstance(author["n_documents"], int)
        assert author["n_documents"] >= 0


@patch("app.routes.authors.get_client")
def test_list_authors_names(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = _make_sb_mock()

    by_id = {a["id"]: a["name"] for a in client.get("/api/authors").json()}
    assert by_id == {
        "austen": "Jane Austen",
        "dickens": "Charles Dickens",
        "poe": "Edgar Allan Poe",
    }


@patch("app.routes.authors.get_client")
def test_list_authors_has_style_profile_and_n_documents(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = _make_sb_mock()

    by_id = {a["id"]: a for a in client.get("/api/authors").json()}
    assert by_id["dickens"]["has_style_profile"] is True
    assert by_id["austen"]["has_style_profile"] is False
    assert by_id["poe"]["has_style_profile"] is False
    assert by_id["austen"]["n_documents"] == 2
    assert by_id["dickens"]["n_documents"] == 4
    assert by_id["poe"]["n_documents"] == 2


@patch("app.routes.authors.get_client")
def test_list_authors_empty_db(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = _make_sb_mock(authors=[], documents=[], style_profiles=[])

    resp = client.get("/api/authors")
    assert resp.status_code == 200
    assert resp.json() == []
