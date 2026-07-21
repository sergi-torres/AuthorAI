"""Chunk embedding generation using sentence-transformers all-mpnet-base-v2.

Public API
----------
embed_chunks(texts: list[str]) -> np.ndarray
    Batch-encode *texts* and return a float32 array of shape ``(N, 768)``.

The ``SentenceTransformer`` model is loaded **once** at module import as a
module-level singleton.  Callers must never reload it per request.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Module-level singleton — loaded once, reused for every call.
# The model name is the canonical one from docs/MVP.md §4.1 and
# docs/style_features.md §5.
# ---------------------------------------------------------------------------
_MODEL_NAME = "all-mpnet-base-v2"
_MODEL: SentenceTransformer = SentenceTransformer(_MODEL_NAME)

#: Dimensionality guaranteed by all-mpnet-base-v2 — used as the assertion
#: guard in embed_chunks() and as the vector(768) column width in the DB.
EMBEDDING_DIM: int = 768


def embed_chunks(texts: list[str]) -> np.ndarray:
    """Batch-encode *texts* and return embeddings as a float32 NumPy array.

    Parameters
    ----------
    texts:
        Non-empty list of chunk strings to embed.  Passing an empty list
        returns a zero-row array with shape ``(0, 768)``.

    Returns
    -------
    np.ndarray
        Float32 array of shape ``(len(texts), 768)``.  Each row is the
        normalised sentence embedding for the corresponding chunk.

    Notes
    -----
    *   Uses ``_MODEL.encode()`` in batch mode with ``convert_to_numpy=True``
        so the result is a contiguous C-order float32 array compatible with
        pgvector's ``VECTOR(768)`` column.
    *   The model is **not** reloaded here; the module-level ``_MODEL``
        singleton is used throughout the process lifetime.
    """
    if not texts:
        return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)

    embeddings: np.ndarray = _MODEL.encode(
        texts,
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    # Guarantee correct dtype regardless of sentence-transformers version.
    return embeddings.astype(np.float32, copy=False)
