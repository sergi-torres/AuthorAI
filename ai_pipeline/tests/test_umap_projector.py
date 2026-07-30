"""Tests for ai_pipeline/autoria_ai/umap_projector.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

pytest.importorskip("psycopg2")
pytest.importorskip("umap")

from autoria_ai.umap_projector import UMAP_N_NEIGHBORS, recompute_umap


def test_recompute_umap_returns_false_when_too_few_chunks() -> None:
    """Fewer than n_neighbors+1 embedded chunks is a soft skip, not a crash."""
    n = UMAP_N_NEIGHBORS  # one short of the minimum
    author_ids = ["aaaaaaaa-0000-0000-0000-000000000001"] * n
    embeddings = np.zeros((n, 8), dtype=np.float32)

    mock_conn = MagicMock()
    with (
        patch("autoria_ai.umap_projector.get_connection", return_value=mock_conn),
        patch(
            "autoria_ai.umap_projector.fetch_embeddings",
            return_value=(author_ids, embeddings),
        ),
        patch("autoria_ai.umap_projector.reduce_to_2d") as mock_reduce,
    ):
        ok = recompute_umap(database_url="postgresql://unused")

    assert ok is False
    mock_reduce.assert_not_called()
    mock_conn.close.assert_called_once()


def test_recompute_umap_returns_true_on_happy_path() -> None:
    n = UMAP_N_NEIGHBORS + 1
    author_ids = ["aaaaaaaa-0000-0000-0000-000000000001"] * n
    embeddings = np.random.randn(n, 8).astype(np.float32)
    coords = np.random.randn(n, 2)

    mock_conn = MagicMock()
    with (
        patch("autoria_ai.umap_projector.get_connection", return_value=mock_conn),
        patch(
            "autoria_ai.umap_projector.fetch_embeddings",
            return_value=(author_ids, embeddings),
        ),
        patch("autoria_ai.umap_projector.reduce_to_2d", return_value=coords) as mock_reduce,
        patch("autoria_ai.umap_projector.save_coords") as mock_save,
        patch("autoria_ai.umap_projector.update_style_profiles", return_value=1) as mock_upd,
    ):
        ok = recompute_umap(database_url="postgresql://unused")

    assert ok is True
    mock_reduce.assert_called_once()
    mock_save.assert_called_once()
    mock_upd.assert_called_once()
    mock_conn.close.assert_called_once()
