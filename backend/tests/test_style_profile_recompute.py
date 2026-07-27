"""Tests for POST /api/authors/{author_id}/style-profile/recompute
(recomputeAuthorStyleProfile).

All Supabase I/O is mocked via unittest.mock.patch so no real DB is needed.
ML is patched via ``_build_style_profile`` so spaCy is never loaded in CI.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_FAKE_AUTHOR_UUID = str(uuid.uuid4())

_FAKE_DOCS = [
    {"n_tokens": 4000, "raw_text": "It was the best of times. " * 50},
    {"n_tokens": 2000, "raw_text": "It was the worst of times. " * 30},
]

_LARGE_DOCS = [{"n_tokens": 120_000, "raw_text": "Fog everywhere. " * 100}]

_FAKE_PROFILE = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "computed_at": "2026-07-27T00:00:00+00:00",
    "corpus_stats": {"n_documents": 1, "n_tokens": 1000, "n_sentences": 10},
    "lexical": {"mattr_500": 0.5, "avg_word_length": 4.0, "hapax_ratio": 0.3},
    "syntactic": {
        "avg_sentence_length_tokens": 12.0,
        "std_sentence_length_tokens": 3.0,
        "subordination_ratio": 0.2,
        "passive_voice_ratio": 0.1,
        "noun_to_verb_ratio": 1.5,
    },
    "stylistic": {
        "punct_distribution": {
            ",": 0.2,
            ".": 0.2,
            ";": 0.1,
            ":": 0.1,
            "—": 0.1,
            "?": 0.1,
            "!": 0.1,
            '"': 0.1,
        },
        "pos_distribution": {
            "NOUN": 0.2,
            "VERB": 0.2,
            "ADJ": 0.1,
            "ADV": 0.1,
            "DET": 0.1,
            "ADP": 0.1,
            "PRON": 0.05,
            "CONJ": 0.05,
            "SCONJ": 0.05,
            "OTHER": 0.05,
        },
        "dialogue_ratio": 0.1,
        "first_person_ratio": 5.0,
    },
    "distinctive_vocab": [],
    "semantic_centroid": [0.0] * 768,
    "embedding_umap_2d": {"centroid": [0.0, 0.0], "spread": 0.0},
}


@pytest.fixture(autouse=True)
def _patch_build_style_profile():
    with patch("app.routes.authors._build_style_profile", return_value=_FAKE_PROFILE):
        yield


def _make_sb_mock(
    *,
    author_found: bool = True,
    doc_rows: list[dict] | None = None,
) -> MagicMock:
    if doc_rows is None:
        doc_rows = _FAKE_DOCS

    sb = MagicMock()

    authors_chain = MagicMock()
    author_execute = MagicMock()
    author_execute.data = {"id": _FAKE_AUTHOR_UUID} if author_found else None
    authors_chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        author_execute
    )

    docs_chain = MagicMock()
    docs_execute = MagicMock()
    docs_execute.data = doc_rows
    docs_chain.select.return_value.eq.return_value.execute.return_value = docs_execute

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


@patch("app.routes.authors.get_client")
def test_recompute_202_happy_path(mock_get_client: MagicMock) -> None:
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
    mock_get_client.return_value = _make_sb_mock(author_found=True, doc_rows=_FAKE_DOCS)

    resp = client.post("/api/authors/austen/style-profile/recompute")

    assert resp.status_code == 202
    assert resp.json()["estimated_seconds"] == 30


@patch("app.routes.authors.get_client")
def test_recompute_estimated_seconds_above_floor(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = _make_sb_mock(author_found=True, doc_rows=_LARGE_DOCS)

    resp = client.post("/api/authors/dickens/style-profile/recompute")

    assert resp.status_code == 202
    assert resp.json()["estimated_seconds"] == 60


@patch("app.routes.authors.get_client")
def test_recompute_404_unknown_author(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = _make_sb_mock(author_found=False)

    resp = client.post("/api/authors/ghost_writer/style-profile/recompute")

    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["error"] == "not_found"
    assert "ghost_writer" in detail["message"]


@patch("app.routes.authors.get_client")
@patch("app.routes.authors._build_style_profile")
def test_recompute_background_task_insert_called(
    mock_build: MagicMock,
    mock_get_client: MagicMock,
) -> None:
    mock_build.return_value = {**_FAKE_PROFILE, "author_id": "poe"}

    sb = _make_sb_mock(author_found=True)
    mock_get_client.return_value = sb

    resp = client.post("/api/authors/poe/style-profile/recompute")

    assert resp.status_code == 202
    mock_build.assert_called_once()

    profiles_chain = sb.table("style_profiles")
    profiles_chain.insert.assert_called_once()

    inserted_payload: dict = profiles_chain.insert.call_args[0][0]
    assert inserted_payload["author_id"] == _FAKE_AUTHOR_UUID
    assert inserted_payload["version"] == "1.0"
    assert "json_data" in inserted_payload
    assert "hash" in inserted_payload
    assert inserted_payload["hash"].startswith("sha256:")

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
