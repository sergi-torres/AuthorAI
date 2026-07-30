"""Tests for DELETE /api/authors/{author_id} (deleteAuthor)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_FAKE_AUTHOR_UUID = str(uuid.uuid4())


def _make_sb_mock(*, author_found: bool = True) -> MagicMock:
    sb = MagicMock()

    authors_chain = MagicMock()
    author_execute = MagicMock()
    author_execute.data = {"id": _FAKE_AUTHOR_UUID} if author_found else None
    authors_chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        author_execute
    )
    authors_chain.delete.return_value.eq.return_value.execute.return_value = MagicMock()

    umap_chain = MagicMock()
    umap_chain.delete.return_value.eq.return_value.execute.return_value = MagicMock()

    def _table_router(name: str) -> MagicMock:
        if name == "authors":
            return authors_chain
        if name == "umap_coords":
            return umap_chain
        return MagicMock()

    sb.table.side_effect = _table_router
    sb._authors_chain = authors_chain
    sb._umap_chain = umap_chain
    return sb


@patch("app.routes.authors._recompute_umap_safe")
@patch("app.routes.authors.get_client")
def test_delete_author_204_and_enqueues_umap(
    mock_get_client: MagicMock,
    mock_umap: MagicMock,
) -> None:
    sb = _make_sb_mock(author_found=True)
    mock_get_client.return_value = sb

    resp = client.delete("/api/authors/grunon")

    assert resp.status_code == 204
    sb._umap_chain.delete.assert_called_once()
    sb._authors_chain.delete.assert_called_once()
    mock_umap.assert_called_once()


@patch("app.routes.authors.get_client")
def test_delete_unknown_author_404(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = _make_sb_mock(author_found=False)

    resp = client.delete("/api/authors/unknown_ghost")

    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["error"] == "not_found"


@patch("app.routes.authors.get_client")
def test_delete_preloaded_author_403(mock_get_client: MagicMock) -> None:
    """Austen / Dickens / Poe are demo seeds — API refuses delete."""
    for slug in ("austen", "dickens", "poe"):
        resp = client.delete(f"/api/authors/{slug}")
        assert resp.status_code == 403, slug
        assert resp.json()["detail"]["error"] == "forbidden"
    mock_get_client.assert_not_called()
