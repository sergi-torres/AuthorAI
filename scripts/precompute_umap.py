"""scripts/precompute_umap.py
=============================================================================
Pre-compute per-chunk 2-D UMAP coordinates from pgvector embeddings and
persist them to the ``public.umap_coords`` table.

Pipeline
--------
1. Connect to PostgreSQL via DATABASE_URL (psycopg2, synchronous).
2. Fetch (author_id, embedding) from ``public.chunks`` joined through
   ``public.documents`` (chunks carry no direct author_id column — the
   canonical join path is chunks → documents → authors).
3. Reduce the N x 768 embedding matrix to N x 2 with UMAP
   (n_neighbors=15, min_dist=0.1, metric='cosine', n_components=2).
4. Truncate and repopulate ``public.umap_coords``.

Usage
-----
    # from the repo root, with the virtualenv active:
    python scripts/precompute_umap.py

    # override chunk source table (default: public.chunks):
    CHUNK_TABLE=public.my_chunks python scripts/precompute_umap.py

Dependencies (beyond ai_pipeline/pyproject.toml)
-------------------------------------------------
    pip install psycopg2-binary          # sync PG driver for this script
    # umap-learn and numpy are already in ai_pipeline/pyproject.toml

Environment variables
---------------------
    DATABASE_URL  — PostgreSQL DSN, e.g.
                    postgresql://user:pass@host:5432/dbname
    CHUNK_TABLE   — optional; defaults to "public.chunks"

Notes
-----
* UMAP requires ≥ (n_neighbors + 1) rows.  The script exits early with a
  clear message if the table has fewer embedded chunks.
* Embeddings are read as plain Python lists (pgvector returns them that way
  from psycopg2); they are cast to a float32 NumPy array for UMAP.
* The insert uses psycopg2's execute_values for a single round-trip.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import numpy as np
import psycopg2
import psycopg2.extras
import umap  # umap-learn

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: UMAP parameters — fixed per spec.
UMAP_N_NEIGHBORS: int = 15
UMAP_MIN_DIST: float = 0.1
UMAP_METRIC: str = "cosine"
UMAP_N_COMPONENTS: int = 2

#: Source table for embeddings.  Override with env var CHUNK_TABLE.
DEFAULT_CHUNK_TABLE: str = "public.chunks"

#: DDL for the output table.
_CREATE_UMAP_COORDS_DDL = """
CREATE TABLE IF NOT EXISTS public.umap_coords (
    id        SERIAL      PRIMARY KEY,
    author_id UUID        NOT NULL,
    x         DOUBLE PRECISION NOT NULL,
    y         DOUBLE PRECISION NOT NULL
);
"""

#: Index for fast lookups by author — created alongside the table.
_CREATE_UMAP_COORDS_IDX = """
CREATE INDEX IF NOT EXISTS umap_coords_author_id_idx
    ON public.umap_coords (author_id);
"""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def get_connection(database_url: str | None = None) -> psycopg2.extensions.connection:
    """Return a psycopg2 connection.

    Parameters
    ----------
    database_url:
        Full PostgreSQL DSN.  If *None*, reads ``DATABASE_URL`` from the
        environment.  The DSN must be compatible with psycopg2 (plain
        ``postgresql://`` scheme, not ``postgresql+asyncpg://``).

    Raises
    ------
    KeyError
        If ``DATABASE_URL`` is not set and *database_url* was not provided.
    """
    url = database_url or os.environ["DATABASE_URL"]
    # Strip the "+asyncpg" driver suffix if the DSN was copied from db.py.
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url)


def fetch_embeddings(
    conn: psycopg2.extensions.connection,
    chunk_table: str = DEFAULT_CHUNK_TABLE,
) -> tuple[list[str], np.ndarray]:
    """Fetch author UUIDs and their chunk embeddings from the database.

    The join path is:
        <chunk_table>  →  public.documents  →  public.authors

    Only rows where ``embedding IS NOT NULL`` are returned.

    Parameters
    ----------
    conn:
        Open psycopg2 connection.
    chunk_table:
        Fully-qualified table name that holds the embedding column
        (default: ``public.chunks``).

    Returns
    -------
    author_ids : list[str]
        One UUID string per chunk row (may repeat for the same author).
    embeddings : np.ndarray
        Float32 array of shape ``(N, 768)``.

    Raises
    ------
    RuntimeError
        If no embedded chunks are found.
    """
    # Split schema.table so we can reference them separately in the query.
    # If the caller omits the schema, default to "public".
    if "." in chunk_table:
        schema, table = chunk_table.split(".", 1)
    else:
        schema, table = "public", chunk_table

    sql = f"""
        SELECT d.author_id::text, c.embedding
        FROM   {schema}.{table} c
        JOIN   public.documents d ON d.id = c.document_id
        WHERE  c.embedding IS NOT NULL
        ORDER BY d.author_id
    """  # ORDER BY keeps same-author rows together (cosmetic, not required)

    log.info("Querying embeddings from %s.%s …", schema, table)
    with conn.cursor() as cur:
        cur.execute(sql)
        rows: list[Any] = cur.fetchall()

    if not rows:
        raise RuntimeError(
            f"No embedded chunks found in {chunk_table}. " "Run backfill_embeddings() first."
        )

    author_ids: list[str] = [row[0] for row in rows]
    # pgvector returns embeddings as Python lists of floats.
    embeddings = np.array([row[1] for row in rows], dtype=np.float32)

    log.info("Fetched %d embedded chunks across %d authors.", len(rows), len(set(author_ids)))
    return author_ids, embeddings


# ---------------------------------------------------------------------------
# UMAP reduction
# ---------------------------------------------------------------------------


def reduce_to_2d(embeddings: np.ndarray) -> np.ndarray:
    """Fit UMAP on *embeddings* and return 2-D coordinates.

    Parameters
    ----------
    embeddings:
        Float32 array of shape ``(N, D)``.  D is typically 768.

    Returns
    -------
    np.ndarray
        Float64 array of shape ``(N, 2)``.

    Notes
    -----
    UMAP requires at least ``n_neighbors + 1 = 16`` rows to fit.  The check
    is done by the caller (``run``).
    """
    reducer = umap.UMAP(
        n_neighbors=UMAP_N_NEIGHBORS,
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        n_components=UMAP_N_COMPONENTS,
        random_state=42,  # reproducible layouts across runs
    )
    log.info(
        "Fitting UMAP (n_neighbors=%d, min_dist=%.2f, metric=%s) on %d vectors …",
        UMAP_N_NEIGHBORS,
        UMAP_MIN_DIST,
        UMAP_METRIC,
        embeddings.shape[0],
    )
    coords: np.ndarray = reducer.fit_transform(embeddings)
    log.info("UMAP fit complete. Output shape: %s", coords.shape)
    return coords  # (N, 2), float64


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def ensure_umap_coords_table(conn: psycopg2.extensions.connection) -> None:
    """Create ``public.umap_coords`` and its index if they do not exist."""
    with conn.cursor() as cur:
        cur.execute(_CREATE_UMAP_COORDS_DDL)
        cur.execute(_CREATE_UMAP_COORDS_IDX)
    conn.commit()
    log.info("Table public.umap_coords is ready.")


def save_coords(
    conn: psycopg2.extensions.connection,
    author_ids: list[str],
    coords: np.ndarray,
) -> None:
    """Truncate umap_coords and bulk-insert new (author_id, x, y) rows.

    Parameters
    ----------
    conn:
        Open psycopg2 connection.
    author_ids:
        List of UUID strings, one per row; must be same length as *coords*.
    coords:
        Float64 array of shape ``(N, 2)``; coords[:, 0] = x, coords[:, 1] = y.
    """
    rows = [(aid, float(coords[i, 0]), float(coords[i, 1])) for i, aid in enumerate(author_ids)]

    with conn.cursor() as cur:
        log.info("Truncating public.umap_coords …")
        cur.execute("TRUNCATE TABLE public.umap_coords RESTART IDENTITY")

        log.info("Inserting %d rows into public.umap_coords …", len(rows))
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO public.umap_coords (author_id, x, y) VALUES %s",
            rows,
            page_size=1000,
        )

    conn.commit()
    log.info("Done — %d umap_coords rows committed.", len(rows))


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run(
    database_url: str | None = None,
    chunk_table: str | None = None,
) -> None:
    """Full pipeline: fetch → reduce → store.

    Parameters
    ----------
    database_url:
        PostgreSQL DSN.  Falls back to ``DATABASE_URL`` env var.
    chunk_table:
        Source table for embeddings.  Falls back to ``CHUNK_TABLE`` env var,
        then to ``DEFAULT_CHUNK_TABLE`` (``public.chunks``).
    """
    table = chunk_table or os.environ.get("CHUNK_TABLE", DEFAULT_CHUNK_TABLE)

    conn = get_connection(database_url)
    try:
        author_ids, embeddings = fetch_embeddings(conn, chunk_table=table)

        min_required = UMAP_N_NEIGHBORS + 1
        if len(author_ids) < min_required:
            log.error(
                "UMAP requires at least %d rows but only %d embedded chunks were found. "
                "Embed more chunks and re-run.",
                min_required,
                len(author_ids),
            )
            sys.exit(1)

        coords = reduce_to_2d(embeddings)
        ensure_umap_coords_table(conn)
        save_coords(conn, author_ids, coords)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
