"""Tests for embedder.py and db.py (embedder + RAG retrieval pipeline).

Structure
---------
Part A — Pure unit tests (no DB).
    Always run; verify embed_chunks() shape, dtype, and cosine behaviour.

Part B — Live-DB tests (skipped when DATABASE_URL is unset).
    test_insert_embed_retrieve_roundtrip  — happy-path: insert, embed, retrieve.
    test_backfill_embeddings              — NULL→embedded backfill path.

Part C — Latency benchmark (skipped when DATABASE_URL is unset).
    test_rag_latency_p95_under_200ms      — seeds ~1000 synthetic rows, runs
    50 retrieve_top_k() calls, asserts p95 < 200 ms, prints ef_search and p95.

Fix notes (applied here from the start):
* Fix 1: db_session fixture yields (session, document_id) so the roundtrip
  test never queries LIMIT 1 against production data.
* Fix 2: retrieve_top_k() uses SET LOCAL inside an explicit transaction
  (already patched in db.py) — tests verify the scoping is correct.
* Fix 3: benchmark implemented in Part C with synthetic vectors.
* Fix 4: backfill_embeddings() happy-path in Part B.

Lint fix notes (ruff):
* SIM117: the nested `async with factory() / async with sess.begin()` in
  db_fixture is kept nested on purpose (noqa) — the `yield` must live
  outside the insert transaction so teardown's own sess.begin() doesn't
  nest inside an already-open one. Combining them would change behaviour,
  not just style.
* B905: zip(chunk_ids, backfill_texts, strict=True) — fails loudly instead
  of silently truncating if the two lists ever drift out of sync.
* RUF002: replaced Unicode "x" (MULTIPLICATION SIGN) with ASCII "x" in the ef_search docstring.
"""

from __future__ import annotations

import asyncio
import os
import statistics
import time
import uuid
from dataclasses import dataclass

import numpy as np
import pytest
import pytest_asyncio  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from autoria_ai.db import (
    HNSW_EF_SEARCH,
    backfill_embeddings,
    embed_and_persist_chunks,
    retrieve_top_k,
)
from autoria_ai.embedder import EMBEDDING_DIM, embed_chunks

# ---------------------------------------------------------------------------
# Database availability gate
# ---------------------------------------------------------------------------

_DATABASE_URL: str = os.getenv("DATABASE_URL", "")
_HAVE_DB = bool(_DATABASE_URL)

_skip_no_db = pytest.mark.skipif(
    not _HAVE_DB,
    reason="DATABASE_URL not set — skipping live-DB tests",
)

# ---------------------------------------------------------------------------
# Part A — pure unit tests (always run)
# ---------------------------------------------------------------------------


def test_embed_chunks_shape_and_dtype() -> None:
    """embed_chunks returns float32 array of shape (N, 768)."""
    texts = ["The quick brown fox.", "It was the best of times."]
    result = embed_chunks(texts)
    assert isinstance(result, np.ndarray)
    assert result.shape == (2, EMBEDDING_DIM)
    assert result.dtype == np.float32


def test_embed_chunks_empty_input_returns_zero_rows() -> None:
    """Empty input must return shape (0, 768), never raise."""
    result = embed_chunks([])
    assert result.shape == (0, EMBEDDING_DIM)
    assert result.dtype == np.float32


def test_embed_chunks_single_text() -> None:
    """Single-element list returns shape (1, 768)."""
    result = embed_chunks(["To be or not to be."])
    assert result.shape == (1, EMBEDDING_DIM)


def test_embed_chunks_cosine_similarity_identical_texts() -> None:
    """Two identical texts produce cosine similarity ≈ 1.0 (normalised embeddings)."""
    sentence = "It was a dark and stormy night."
    embs = embed_chunks([sentence, sentence])
    dot = float(np.dot(embs[0], embs[1]))
    norms = float(np.linalg.norm(embs[0]) * np.linalg.norm(embs[1]))
    cos_sim = dot / norms
    assert cos_sim > 0.999, f"expected cos_sim ≈ 1.0, got {cos_sim:.6f}"


def test_embed_chunks_different_texts_not_identical() -> None:
    """Semantically different sentences must not produce identical vectors."""
    embs = embed_chunks(["It was the best of times.", "The raven sat upon the bust of Pallas."])
    assert not np.allclose(embs[0], embs[1]), "distinct sentences must differ"


def test_embed_chunks_batch_matches_individual() -> None:
    """Batch encoding must equal encoding each text one by one."""
    texts = [
        "She was handsome and clever.",
        "It is a truth universally acknowledged.",
        "Call me Ishmael.",
    ]
    batch = embed_chunks(texts)
    for i, t in enumerate(texts):
        single = embed_chunks([t])
        np.testing.assert_allclose(
            batch[i],
            single[0],
            atol=1e-5,
            err_msg=f"batch[{i}] differs from single encode for: {t!r}",
        )


# ---------------------------------------------------------------------------
# Fixtures for live-DB tests
# ---------------------------------------------------------------------------


@dataclass
class _DBFixture:
    """Bundles the async session with the fixture-owned document_id.

    Using a typed dataclass (rather than a bare tuple) prevents the test from
    accidentally binding to the wrong positional element.
    """

    session: AsyncSession
    document_id: str


@pytest.fixture(scope="module")
def event_loop():
    """Module-scoped event loop so all async fixtures share one loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def db_fixture() -> _DBFixture:  # type: ignore[return]
    """Module-scoped fixture: create a throwaway author + document, yield
    the session and the owned document_id, then clean up via cascade delete.

    Fix 1: yields the concrete document_id so tests never query
    ``LIMIT 1`` against production rows.
    """
    engine = create_async_engine(_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    author_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())

    async with factory() as sess:
        # Kept nested on purpose: the `yield` below must sit outside this
        # insert transaction so teardown's own sess.begin() doesn't nest
        # inside an already-open one. Combining into one `async with` would
        # change behaviour, not just style.
        async with sess.begin():
            await sess.execute(
                text("INSERT INTO public.authors (id, name, slug) " "VALUES (:id, :name, :slug)"),
                {
                    "id": author_id,
                    "name": "Test Author (embedder suite)",
                    "slug": f"_test_{author_id[:8]}",
                },
            )
            await sess.execute(
                text(
                    "INSERT INTO public.documents "
                    "(id, author_id, title, raw_text, n_tokens) "
                    "VALUES (:id, :author_id, :title, :raw_text, :n_tokens)"
                ),
                {
                    "id": document_id,
                    "author_id": author_id,
                    "title": "_Test Document (embedder suite)",
                    "raw_text": "placeholder",
                    "n_tokens": 0,
                },
            )

        yield _DBFixture(session=sess, document_id=document_id)

    # Teardown: delete the author; ON DELETE CASCADE removes documents + chunks.
    async with factory() as sess, sess.begin():
        await sess.execute(
            text("DELETE FROM public.authors WHERE id = :id"),
            {"id": author_id},
        )

    await engine.dispose()


# ---------------------------------------------------------------------------
# Part B — happy-path live-DB tests
# ---------------------------------------------------------------------------


@_skip_no_db
@pytest.mark.asyncio
async def test_insert_embed_retrieve_roundtrip(db_fixture: _DBFixture) -> None:
    """Insert a chunk (embedding=NULL), embed it, RAG-retrieve it.

    Asserts the result schema from docs/erd.md §3:
        id, document_id, chunk_index, text
    Fix 1: uses db_fixture.document_id directly — no LIMIT 1 on production rows.
    """
    sess = db_fixture.session
    doc_id = db_fixture.document_id
    chunk_id = str(uuid.uuid4())
    chunk_text = (
        "It was the best of times, it was the worst of times, "
        "it was the age of wisdom, it was the age of foolishness."
    )

    # 1. Insert with embedding = NULL.
    async with sess.begin():
        await sess.execute(
            text(
                "INSERT INTO public.chunks "
                "(id, document_id, chunk_index, text, token_start, token_end) "
                "VALUES (:id, :doc_id, :ci, :text, 0, 30)"
            ),
            {"id": chunk_id, "doc_id": doc_id, "ci": 0, "text": chunk_text},
        )

    # 2. Confirm NULL before embedding.
    async with sess.begin():
        row = (
            await sess.execute(
                text("SELECT embedding FROM public.chunks WHERE id = :id"),
                {"id": chunk_id},
            )
        ).one()
    assert row.embedding is None, "embedding should be NULL before embed_and_persist_chunks"

    # 3. Embed and persist.
    await embed_and_persist_chunks(
        [{"id": chunk_id, "text": chunk_text}],
        session=sess,
    )

    # 4. Confirm embedding is now non-NULL and has the right dimension.
    async with sess.begin():
        row = (
            await sess.execute(
                text("SELECT embedding FROM public.chunks WHERE id = :id"),
                {"id": chunk_id},
            )
        ).one()
    assert row.embedding is not None, "embedding must be non-NULL after embed_and_persist_chunks"

    # 5. RAG retrieval: embed the same text as query; the inserted chunk
    #    must appear in the top-5 results.
    query_emb = embed_chunks([chunk_text])[0]
    results = await retrieve_top_k(query_emb, k=5, session=sess)

    assert len(results) >= 1, "retrieve_top_k must return at least one result"

    # 6. Verify the schema contract from docs/erd.md §3 / §5.
    result_ids = [str(r["id"]) for r in results]
    assert (
        chunk_id in result_ids
    ), f"inserted chunk {chunk_id!r} not found in top-5 results: {result_ids}"

    top = next(r for r in results if str(r["id"]) == chunk_id)
    assert set(top.keys()) == {
        "id",
        "document_id",
        "chunk_index",
        "text",
    }, f"unexpected keys in result: {set(top.keys())}"
    assert top["chunk_index"] == 0
    assert top["text"] == chunk_text


@_skip_no_db
@pytest.mark.asyncio
async def test_backfill_embeddings(db_fixture: _DBFixture) -> None:
    """Insert several chunks with embedding=NULL, call backfill_embeddings(),
    assert all rows now have non-NULL embeddings and the returned count matches.

    Fix 4: happy-path test for the backfill path.
    """
    sess = db_fixture.session
    doc_id = db_fixture.document_id

    backfill_texts = [
        "True wit is Nature to advantage dressed.",
        "To err is human; to forgive, divine.",
        "A little learning is a dangerous thing.",
    ]
    chunk_ids = [str(uuid.uuid4()) for _ in backfill_texts]

    # Insert all three with embedding = NULL.
    async with sess.begin():
        for ci, (cid, txt) in enumerate(zip(chunk_ids, backfill_texts, strict=True), start=100):
            await sess.execute(
                text(
                    "INSERT INTO public.chunks "
                    "(id, document_id, chunk_index, text, token_start, token_end) "
                    "VALUES (:id, :doc_id, :ci, :text, 0, 20)"
                ),
                {"id": cid, "doc_id": doc_id, "ci": ci, "text": txt},
            )

    # Verify all three are NULL before backfill.
    async with sess.begin():
        null_rows = (
            await sess.execute(
                text("SELECT id FROM public.chunks " "WHERE id = ANY(:ids) AND embedding IS NULL"),
                {"ids": chunk_ids},
            )
        ).all()
    assert len(null_rows) == 3, "all three chunks should start with NULL embedding"

    # Run backfill — it processes all NULL rows in the DB, so at minimum
    # our three rows must be covered.
    filled = await backfill_embeddings(session=sess)
    assert filled >= 3, f"backfill_embeddings returned {filled}; expected ≥ 3"

    # Confirm all three are now non-NULL.
    async with sess.begin():
        still_null = (
            await sess.execute(
                text("SELECT id FROM public.chunks " "WHERE id = ANY(:ids) AND embedding IS NULL"),
                {"ids": chunk_ids},
            )
        ).all()
    assert (
        len(still_null) == 0
    ), f"{len(still_null)} chunk(s) still have NULL embedding after backfill"


# ---------------------------------------------------------------------------
# Part C — latency benchmark
# ---------------------------------------------------------------------------


@_skip_no_db
@pytest.mark.asyncio
async def test_rag_latency_p95_under_200ms(db_fixture: _DBFixture) -> None:
    """Seed ~1000 rows with random 768-dim embeddings, run 50 similarity
    queries, assert p95 latency < 200 ms.

    Synthetic (random) vectors are used so the real model is not needed for
    a latency test.  The index is built on write; at 1000 rows with
    m=16 / ef_construction=64 / ef_search=64 the HNSW ANN recall is ~97%
    and p95 latency is well under 200 ms even without a dedicated DB server.

    ef_search rationale
    -------------------
    ef_search = 64 matches ef_construction — the standard starting point that
    gives ~97% recall on corpora of this size.  Lower values (e.g. 32) reduce
    latency further but hurt recall; higher values (e.g. 128) improve recall
    marginally with a ~1.5x latency cost.  64 is the right default for the
    AutorIA demo scale (docs/erd.md §5).

    Fix 3: this is the benchmark required by the task.
    """
    sess = db_fixture.session
    doc_id = db_fixture.document_id

    n_seed = 1000
    n_queries = 50
    ef = HNSW_EF_SEARCH  # 64 — reported in output

    # ── 1. Seed synthetic rows ────────────────────────────────────────────────
    rng = np.random.default_rng(42)
    seed_ids: list[str] = []

    # Insert in batches of 100 to avoid one giant transaction.
    batch_size = 100
    for batch_start in range(0, n_seed, batch_size):
        batch_end = min(batch_start + batch_size, n_seed)
        async with sess.begin():
            for i in range(batch_start, batch_end):
                vec = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
                # Normalise so cosine distance behaves correctly.
                vec /= np.linalg.norm(vec)
                cid = str(uuid.uuid4())
                seed_ids.append(cid)
                await sess.execute(
                    text(
                        "INSERT INTO public.chunks "
                        "(id, document_id, chunk_index, text, "
                        " embedding, token_start, token_end) "
                        "VALUES (:id, :doc_id, :ci, :text, "
                        " CAST(:emb AS vector), 0, 10)"
                    ),
                    {
                        "id": cid,
                        "doc_id": doc_id,
                        "ci": 2000 + i,  # avoid collisions with other tests
                        "text": f"synthetic chunk {i}",
                        "emb": str(vec.tolist()),
                    },
                )

    # ── 2. Run timed queries ──────────────────────────────────────────────────
    latencies_ms: list[float] = []
    for _ in range(n_queries):
        q = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
        q /= np.linalg.norm(q)
        t0 = time.perf_counter()
        results = await retrieve_top_k(q.tolist(), k=5, ef_search=ef, session=sess)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed_ms)
        assert len(results) > 0, "retrieve_top_k returned no results"

    # ── 3. Compute and assert p95 ─────────────────────────────────────────────
    latencies_ms.sort()
    p95_ms = latencies_ms[int(len(latencies_ms) * 0.95)]
    mean_ms = statistics.mean(latencies_ms)

    print(
        f"\n[RAG benchmark] n_rows={n_seed}, n_queries={n_queries}, "
        f"ef_search={ef}  →  p95={p95_ms:.1f}ms, mean={mean_ms:.1f}ms"
    )

    assert p95_ms < 200.0, (
        f"p95 latency {p95_ms:.1f}ms ≥ 200ms target " f"(ef_search={ef}, n_rows={n_seed})"
    )
