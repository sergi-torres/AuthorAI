"""Chunk embedding generation using sentence-transformers all-mpnet-base-v2.

Public API
----------
embed_chunks(texts: list[str]) -> np.ndarray
    Batch-encode *texts* and return a float32 array of shape ``(N, 768)``.
ensure_model_loaded() -> SentenceTransformer
    Force the model to load now (used by ``autoria_ai.generator.warmup_models``
    to pre-warm at process startup) and return the singleton.

Model loading
-------------
The ``SentenceTransformer`` is a **lazily-constructed** process-level
singleton: it loads on first call to ``embed_chunks`` or
``ensure_model_loaded``, not at import time (#104). Constructing it used to
happen as a bare module-level statement, so *any* import of this module —
including ``autoria_ai.db`` and ``autoria_ai.extractor.style_profile``, which
import it just for ``EMBEDDING_DIM`` / ``embed_chunks`` and may not need to
actually embed anything — paid the full ~418 MB HuggingFace download/load
unconditionally. Lazy construction means importing this module is cheap; the
cost is paid exactly once, by whichever caller first needs embeddings.

This does **not** by itself remove the cost from a cold Railway boot: prod
still calls ``ensure_model_loaded()`` during FastAPI's lifespan (via
``autoria_ai.generator.warmup_models``) so the first real request isn't the
one paying for it. What it removes is the download turning into *network*
time at all when it can be avoided: ``railway.toml``'s ``buildCommand`` now
pre-fetches this model into the HuggingFace cache at **build** time (the same
technique already used there for the spaCy model), so a cold boot loads it
from local disk instead of downloading it fresh, deploy or restart.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Module-level singleton — constructed lazily on first use (see module
# docstring), reused for every call afterwards. The model name is the
# canonical one from docs/MVP.md §4.1 and docs/style_features.md §5.
# ---------------------------------------------------------------------------
_MODEL_NAME = "all-mpnet-base-v2"
_MODEL: SentenceTransformer | None = None

#: Dimensionality guaranteed by all-mpnet-base-v2 — used as the assertion
#: guard in embed_chunks() and as the vector(768) column width in the DB.
EMBEDDING_DIM: int = 768


def ensure_model_loaded() -> SentenceTransformer:
    """Return the process-level SentenceTransformer singleton, loading it
    on the first call. Safe to call more than once or from more than one
    caller (e.g. an explicit warmup *and* the first real ``embed_chunks``
    call racing on it) — the model is constructed at most once per process.
    """
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(_MODEL_NAME)
    return _MODEL


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
    *   Uses ``.encode()`` in batch mode with ``convert_to_numpy=True`` so
        the result is a contiguous C-order float32 array compatible with
        pgvector's ``VECTOR(768)`` column.
    *   The model singleton is loaded on first call (see
        ``ensure_model_loaded``) and never reloaded per request.
    """
    if not texts:
        return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)

    model = ensure_model_loaded()
    embeddings: np.ndarray = model.encode(
        texts,
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    # Guarantee correct dtype regardless of sentence-transformers version.
    return embeddings.astype(np.float32, copy=False)
