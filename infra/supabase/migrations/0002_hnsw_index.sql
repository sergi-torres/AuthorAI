-- =============================================================================
-- Migration : 0002_hnsw_index.sql
-- Project   : AutorIA
-- Purpose   : Idempotent guard migration that ensures:
--               1. The pgvector and pgcrypto extensions are enabled.
--               2. The HNSW ANN index on chunks.embedding exists with the
--                  exact parameters specified in docs/erd.md §5.
--
-- Background
-- ----------
-- The HNSW index was already included in 0001_init.sql for fresh installs.
-- This migration exists so environments that ran 0001 before the index was
-- added (or that stripped it) can be brought up to spec in one idempotent step,
-- without touching the table shape.
--
-- Spec (docs/erd.md §5):
--   Index name : chunks_embedding_hnsw_idx
--   Table      : public.chunks
--   Method     : hnsw
--   Operator   : vector_cosine_ops  (distance <=>)
--   m          : 16
--   ef_construction : 64
--
-- Source of truth: docs/erd.md · infra/supabase/migrations/0001_init.sql
--
-- Apply manually:
--   psql "$DATABASE_URL" -f infra/supabase/migrations/0002_hnsw_index.sql
--
-- Or via Supabase CLI:
--   supabase db push
-- =============================================================================

begin;

-- ---------------------------------------------------------------------------
-- Extensions (already created by 0001 — these are no-ops on an up-to-date DB)
-- ---------------------------------------------------------------------------

create extension if not exists vector;    -- pgvector: vector type + HNSW/IVFFlat
create extension if not exists pgcrypto;  -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- HNSW index on chunks.embedding
--
-- IF NOT EXISTS: completely safe to re-run; does nothing when the index is
-- already present (as it will be on any DB that applied 0001_init.sql fully).
--
-- Build parameters:
--   m = 16               — number of bi-directional links per node; controls
--                          graph connectivity.  16 is the recommended default
--                          for corpora of this size (300–1000 rows per author).
--   ef_construction = 64 — size of the candidate list during index build;
--                          higher → better recall, slower build.  64 matches
--                          ef_search = 64 at query time (see db.py HNSW_EF_SEARCH).
--
-- Query-time recall can be tuned without rebuilding the index:
--   SET hnsw.ef_search = <n>;   -- session-level, before the ORDER BY <=> query
-- ---------------------------------------------------------------------------

create index if not exists chunks_embedding_hnsw_idx
    on public.chunks
    using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);

commit;
