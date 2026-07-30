"""scripts/precompute_umap.py
=============================================================================
CLI wrapper around ``autoria_ai.umap_projector.recompute_umap``.

Usage
-----
    # from the repo root, with the virtualenv active:
    python scripts/precompute_umap.py

    # override chunk source table (default: public.chunks):
    CHUNK_TABLE=public.my_chunks python scripts/precompute_umap.py

Environment variables
---------------------
    DATABASE_URL  — PostgreSQL DSN, e.g.
                    postgresql://user:pass@host:5432/dbname
    CHUNK_TABLE   — optional; defaults to "public.chunks"

The implementation lives in ``ai_pipeline/autoria_ai/umap_projector.py`` so the
backend can call the same pipeline after author add/remove without shelling out.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Make ai_pipeline importable when invoked as a script from the repo root.
_ROOT = Path(__file__).resolve().parents[1]
_AI = _ROOT / "ai_pipeline"
if _AI.is_dir() and str(_AI) not in sys.path:
    sys.path.insert(0, str(_AI))

from autoria_ai.umap_projector import (  # noqa: E402
    DEFAULT_CHUNK_TABLE,
    UMAP_METRIC,
    UMAP_MIN_DIST,
    UMAP_N_COMPONENTS,
    UMAP_N_NEIGHBORS,
    fetch_embeddings,
    get_connection,
    recompute_umap,
    reduce_to_2d,
    save_coords,
    update_style_profiles,
)

# Re-export for tests / callers that still import from this module.
__all__ = [
    "DEFAULT_CHUNK_TABLE",
    "UMAP_METRIC",
    "UMAP_MIN_DIST",
    "UMAP_N_COMPONENTS",
    "UMAP_N_NEIGHBORS",
    "fetch_embeddings",
    "get_connection",
    "recompute_umap",
    "reduce_to_2d",
    "run",
    "save_coords",
    "update_style_profiles",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)


def run(
    database_url: str | None = None,
    chunk_table: str | None = None,
) -> None:
    """CLI entry: exit 1 when UMAP cannot run (too few chunks)."""
    ok = recompute_umap(database_url=database_url, chunk_table=chunk_table)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    run()
