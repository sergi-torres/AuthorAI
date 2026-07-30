"""Global UMAP 2-D projection for Style DNA scatter centroids.

Public API
----------
recompute_umap(database_url=None, chunk_table=None) -> bool
    Fetch embedded chunks, fit UMAP, rewrite ``umap_coords``, and patch
    ``embedding_umap_2d`` on each author's latest StyleProfile.  Returns
    ``True`` on success, ``False`` when there are too few embedded chunks
    (or on a soft failure the caller should treat as non-fatal).

This is the same pipeline formerly owned only by ``scripts/precompute_umap.py``.
The script remains as a thin CLI; the backend calls ``recompute_umap`` after
author add/remove so the scatter stays consistent without a manual re-run.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import numpy as np
import psycopg2
import psycopg2.extras
import umap  # umap-learn

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

UMAP_N_NEIGHBORS: int = 15
UMAP_MIN_DIST: float = 0.1
UMAP_METRIC: str = "cosine"
UMAP_N_COMPONENTS: int = 2

DEFAULT_CHUNK_TABLE: str = "public.chunks"


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
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url)


def _as_vector(value: Any) -> list[float]:
    """Return a pgvector column value as a list of floats.

    psycopg2 hands back ``"[0.013,-0.011,…]"`` (a string) for a ``vector``
    column unless the pgvector adapter is registered on the connection; other
    drivers return a real sequence. Both are accepted so this does not depend
    on how the caller built the connection.
    """
    if isinstance(value, str):
        return [float(x) for x in value.strip().lstrip("[").rstrip("]").split(",") if x]
    return list(value)


def fetch_embeddings(
    conn: psycopg2.extensions.connection,
    chunk_table: str = DEFAULT_CHUNK_TABLE,
) -> tuple[list[str], np.ndarray]:
    """Fetch author UUIDs and their chunk embeddings from the database.

    The join path is:
        <chunk_table>  →  public.documents  →  public.authors

    Only rows where ``embedding IS NOT NULL`` are returned.

    Raises
    ------
    RuntimeError
        If no embedded chunks are found.
    """
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
    """

    log.info("Querying embeddings from %s.%s …", schema, table)
    with conn.cursor() as cur:
        cur.execute(sql)
        rows: list[Any] = cur.fetchall()

    if not rows:
        raise RuntimeError(
            f"No embedded chunks found in {chunk_table}. Run backfill_embeddings() first."
        )

    author_ids: list[str] = [row[0] for row in rows]
    embeddings = np.array([_as_vector(row[1]) for row in rows], dtype=np.float32)

    log.info("Fetched %d embedded chunks across %d authors.", len(rows), len(set(author_ids)))
    return author_ids, embeddings


# ---------------------------------------------------------------------------
# UMAP reduction
# ---------------------------------------------------------------------------


def reduce_to_2d(embeddings: np.ndarray) -> np.ndarray:
    """Fit UMAP on *embeddings* and return 2-D coordinates."""
    reducer = umap.UMAP(
        n_neighbors=UMAP_N_NEIGHBORS,
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        n_components=UMAP_N_COMPONENTS,
        random_state=42,
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
    return coords


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def save_coords(
    conn: psycopg2.extensions.connection,
    author_ids: list[str],
    coords: np.ndarray,
) -> None:
    """Truncate umap_coords and bulk-insert new (author_id, x, y) rows."""
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


def update_style_profiles(
    conn: psycopg2.extensions.connection,
    author_ids: list[str],
    coords: np.ndarray,
) -> int:
    """Write each author's 2-D centroid and spread into their latest StyleProfile.

    Only the most recent profile row per author is updated; older rows are
    history and stay as they were.

    Returns the number of profile rows updated.
    """
    by_author: dict[str, list[tuple[float, float]]] = {}
    for i, aid in enumerate(author_ids):
        by_author.setdefault(aid, []).append((float(coords[i, 0]), float(coords[i, 1])))

    updated = 0
    with conn.cursor() as cur:
        for author_id, points in by_author.items():
            arr = np.asarray(points, dtype=np.float64)
            centroid = arr.mean(axis=0)
            spread = float(np.linalg.norm(arr - centroid, axis=1).mean())
            payload = json.dumps(
                {"centroid": [float(centroid[0]), float(centroid[1])], "spread": spread}
            )

            cur.execute(
                """
                UPDATE public.style_profiles AS sp
                   SET json_data = jsonb_set(
                           sp.json_data, '{embedding_umap_2d}', %s::jsonb, true)
                 WHERE sp.id = (
                       SELECT id FROM public.style_profiles
                        WHERE author_id = %s
                        ORDER BY computed_at DESC
                        LIMIT 1)
                """,
                (payload, author_id),
            )
            updated += cur.rowcount
            log.info(
                "author %s: centroid=(%.3f, %.3f) spread=%.3f over %d chunks",
                author_id,
                centroid[0],
                centroid[1],
                spread,
                len(points),
            )

    conn.commit()
    log.info("Updated embedding_umap_2d on %d style_profiles row(s).", updated)
    return updated


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def recompute_umap(
    database_url: str | None = None,
    chunk_table: str | None = None,
) -> bool:
    """Full pipeline: fetch → reduce → store.

    Returns
    -------
    bool
        ``True`` if UMAP was fitted and persisted; ``False`` if there were
        fewer than ``n_neighbors + 1`` embedded chunks (soft skip — callers
        such as the upload path must not treat this as a hard failure).
    """
    table = chunk_table or os.environ.get("CHUNK_TABLE", DEFAULT_CHUNK_TABLE)

    conn = get_connection(database_url)
    try:
        author_ids, embeddings = fetch_embeddings(conn, chunk_table=table)

        min_required = UMAP_N_NEIGHBORS + 1
        if len(author_ids) < min_required:
            log.warning(
                "UMAP requires at least %d rows but only %d embedded chunks were found; skipping.",
                min_required,
                len(author_ids),
            )
            return False

        coords = reduce_to_2d(embeddings)
        save_coords(conn, author_ids, coords)
        update_style_profiles(conn, author_ids, coords)
        return True
    finally:
        conn.close()
