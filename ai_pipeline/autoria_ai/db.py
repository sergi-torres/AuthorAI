"""SQLAlchemy 2.0 async DB layer for the AutorIA AI pipeline.

This module owns:
* The async SQLAlchemy engine / session factory (connection via DATABASE_URL).
* The ``Chunk`` ORM model mirroring ``public.chunks`` (vector(768) column).
* ``embed_and_persist_chunks()`` — ingest path (architecture.md §4.1).
* ``backfill_embeddings()``      — async fill-in for NULL embeddings.
* ``retrieve_top_k()``           — RAG retrieval (erd.md §5 "Vector search").

Usage
-----
All three public functions are ``async def`` and require an async context
(``asyncio.run`` or an existing event loop, e.g. inside FastAPI).

Environment
-----------
``DATABASE_URL`` must be a valid asyncpg DSN, e.g.:
    postgresql+asyncpg://user:pass@host:5432/dbname

The engine is **not** created at import time to keep the module testable
without a live DB.  Call ``get_engine()`` or ``get_session()`` once the env
is ready, or pass a ``session`` directly to the public functions.
"""

from __future__ import annotations

import os
import typing
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, Text, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from autoria_ai.embedder import EMBEDDING_DIM, embed_chunks

# ---------------------------------------------------------------------------
# ORM base + Chunk model
# ---------------------------------------------------------------------------


class _Base(DeclarativeBase):
    pass


class Chunk(_Base):
    """ORM mapping for ``public.chunks`` (read/write for embedding column).

    Only the columns relevant to the embedder and RAG retrieval are mapped
    here.  The authoritative schema lives in ``0001_init.sql``.
    """

    __tablename__ = "chunks"
    __table_args__: typing.ClassVar[dict] = {"schema": "public"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID] = mapped_column(nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # vector(768) nullable — None until embedded.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)


# ---------------------------------------------------------------------------
# Engine / session factory
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _make_engine(database_url: str | None = None) -> AsyncEngine:
    url = database_url or os.environ["DATABASE_URL"]
    return create_async_engine(url, pool_pre_ping=True)


def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Return (and lazily create) the module-level async engine.

    Pass *database_url* explicitly in tests to avoid touching ``os.environ``.
    """
    global _engine
    if _engine is None:
        _engine = _make_engine(database_url)
    return _engine


def get_session_factory(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    """Return (and lazily create) the module-level async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(database_url),
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def _session(
    database_url: str | None = None,
    existing: AsyncSession | None = None,
) -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession``, using *existing* if provided."""
    if existing is not None:
        yield existing
        return
    factory = get_session_factory(database_url)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# Public API — ingest path
# ---------------------------------------------------------------------------


async def embed_and_persist_chunks(
    rows: list[dict[str, Any]],
    *,
    database_url: str | None = None,
    session: AsyncSession | None = None,
) -> None:
    """Embed *rows* and ``UPDATE`` their ``embedding`` column in one batch.

    Parameters
    ----------
    rows:
        List of dicts, each with at minimum ``"id"`` (UUID str/UUID) and
        ``"text"`` (str).  The rows must already exist in ``public.chunks``
        (inserted with ``embedding = NULL``).
    database_url:
        Override for the DB URL (for tests).  Ignored when *session* is given.
    session:
        Existing ``AsyncSession`` to reuse (avoids opening a new connection).

    Notes
    -----
    Embeddings are committed in a single transaction.  If any UPDATE fails
    the whole batch is rolled back, leaving the rows with ``embedding = NULL``
    so the backfiller can retry them.
    """
    if not rows:
        return

    texts = [r["text"] for r in rows]
    embeddings: np.ndarray = embed_chunks(texts)  # (N, 768)

    async with _session(database_url, session) as sess, sess.begin():
        for row, emb in zip(rows, embeddings, strict=False):
            chunk_id = row["id"]
            await sess.execute(
                text("UPDATE public.chunks SET embedding = :emb WHERE id = :id"),
                {"emb": emb.tolist(), "id": str(chunk_id)},
            )


# ---------------------------------------------------------------------------
# Public API — async backfill
# ---------------------------------------------------------------------------


async def backfill_embeddings(
    *,
    batch_size: int = 256,
    database_url: str | None = None,
    session: AsyncSession | None = None,
) -> int:
    """Find chunks where ``embedding IS NULL`` and embed them in batches.

    Parameters
    ----------
    batch_size:
        Number of chunks to embed per DB round-trip.  256 is a good default
        for the all-mpnet-base-v2 model on typical hardware.
    database_url:
        Override for the DB URL (for tests).
    session:
        Existing ``AsyncSession`` to reuse.

    Returns
    -------
    int
        Total number of chunks that were backfilled.

    Notes
    -----
    Each loop iteration is two independent transactions on the same session:
    1. A read-only SELECT to fetch the next unembedded batch.
    2. A write transaction (inside ``embed_and_persist_chunks``) that UPDATEs
       the embedding column.
    Keeping them separate means a failed UPDATE leaves the rows with
    ``embedding = NULL`` so this function can be safely retried.
    """
    total_filled = 0

    async with _session(database_url, session) as sess:
        while True:
            # ── 1. Read the next batch of unembedded chunk ids + texts ──────
            async with sess.begin():
                result = await sess.execute(
                    select(Chunk.id, Chunk.text).where(Chunk.embedding.is_(None)).limit(batch_size)
                )
                batch = result.all()
            # Transaction committed; rows are now visible outside.

            if not batch:
                break

            # ── 2. Embed and write (separate transaction per batch) ─────────
            rows = [{"id": str(row.id), "text": row.text} for row in batch]
            # Pass the bare session — embed_and_persist_chunks opens its own
            # sess.begin() block, which is legal on a post-commit session.
            await embed_and_persist_chunks(rows, session=sess)
            total_filled += len(batch)

    return total_filled


# ---------------------------------------------------------------------------
# Public API — RAG retrieval
# ---------------------------------------------------------------------------

#: Default ``ef_search`` value for HNSW recall/latency tuning.
#: At 64 (matching ef_construction) recall is ~97% for this corpus size
#: while p95 query latency stays well under 200ms.
#: Raise to 128 if recall needs to improve post-demo; lower to 32 on cold starts.
HNSW_EF_SEARCH: int = 64


async def retrieve_top_k(
    query_embedding: list[float] | np.ndarray,
    *,
    k: int = 5,
    ef_search: int = HNSW_EF_SEARCH,
    database_url: str | None = None,
    session: AsyncSession | None = None,
) -> list[dict[str, Any]]:
    """Return the top-*k* chunks nearest to *query_embedding* via HNSW ANN.

    Implements the canonical RAG query from docs/erd.md §5 "Vector search":

    .. code-block:: sql

        SELECT id, document_id, chunk_index, text
        FROM public.chunks
        ORDER BY embedding <=> $1
        LIMIT 5;

    Parameters
    ----------
    query_embedding:
        768-dim vector (list or numpy array).  Must match the dimensionality
        of the stored embeddings.
    k:
        Number of nearest neighbours to retrieve.  Default 5 per spec.
    ef_search:
        HNSW ``ef_search`` parameter set at query time via ``SET``.  Higher
        values improve recall at the cost of latency.  Default ``64``
        (matches ``ef_construction``); tuning notes in ``HNSW_EF_SEARCH``.
    database_url:
        Override for the DB URL (for tests).
    session:
        Existing ``AsyncSession`` to reuse.

    Returns
    -------
    list[dict]
        Each dict has keys: ``id`` (UUID), ``document_id`` (UUID),
        ``chunk_index`` (int), ``text`` (str).
    """
    if isinstance(query_embedding, np.ndarray):
        query_embedding = query_embedding.tolist()

    # SET LOCAL scopes the GUC to the current transaction only.
    # When the transaction ends (commit or rollback) the setting reverts
    # to its session default, so it never leaks to the next caller that
    # borrows this connection from the pool.
    async with _session(database_url, session) as sess, sess.begin():
        await sess.execute(text(f"SET LOCAL hnsw.ef_search = {int(ef_search)}"))

        rows = await sess.execute(
            text(
                """
                SELECT id, document_id, chunk_index, text
                FROM public.chunks
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT :k
                """
            ),
            {"emb": str(query_embedding), "k": k},
        )
        return [
            {
                "id": row.id,
                "document_id": row.document_id,
                "chunk_index": row.chunk_index,
                "text": row.text,
            }
            for row in rows
        ]
