-- =============================================================================
-- Migration : 0004_umap_coords.sql
-- Project   : AutorIA
-- Purpose   : Create the public.umap_coords table and its author_id index.
--             This table holds one row per chunk after scripts/precompute_umap.py
--             runs UMAP on all chunk embeddings.  It is the intermediate store
--             that precompute_umap.py aggregates into
--             style_profiles.json_data.embedding_umap_2d (WO-07).
--
-- Background
-- ----------
-- Prior to this migration the table was created at runtime by
-- scripts/precompute_umap.py using CREATE TABLE IF NOT EXISTS.  Moving DDL
-- into a proper migration gives it:
--   * a canonical location in the migration sequence,
--   * consistent comments and index naming, and
--   * an idempotent path that is safe to replay on any environment.
-- The runtime DDL has been removed from precompute_umap.py in the same commit.
--
-- Table design
-- ------------
-- * One row per embedded chunk, not per author.  After UMAP fits on all chunks
--   combined, each chunk gets a 2-D (x, y) coordinate in the shared space.
--   precompute_umap.py then aggregates those per-author into centroid + spread
--   and writes the result back to style_profiles.json_data.embedding_umap_2d.
-- * SERIAL primary key (not UUID) because these rows have no external identity
--   and are truncated + repopulated on every precompute run.
-- * author_id is NOT NULL and indexed for fast per-author aggregation in the
--   precompute script.  There is intentionally no FK to public.authors: the
--   table is a volatile cache and the FK would add latency to the TRUNCATE +
--   re-insert without providing referential-integrity value (the data is always
--   regenerated from scratch on every run).
--
-- Source of truth: docs/erd.md · scripts/precompute_umap.py
--
-- Apply manually:
--   psql "$DATABASE_URL" -f infra/supabase/migrations/0004_umap_coords.sql
--
-- Or via Supabase CLI:
--   supabase db push
--
-- Idempotent: both statements use IF NOT EXISTS, so re-running against an
-- already-migrated database is a safe no-op.
-- =============================================================================

begin;

-- ---------------------------------------------------------------------------
-- Table: umap_coords
-- ---------------------------------------------------------------------------

create table if not exists public.umap_coords (
    id        serial           primary key,
    author_id uuid             not null,
    x         double precision not null,
    y         double precision not null
);

comment on table  public.umap_coords           is 'Per-chunk 2-D UMAP coordinates, produced by scripts/precompute_umap.py. One row per embedded chunk. Truncated and repopulated on every precompute run. Aggregated into style_profiles.json_data.embedding_umap_2d (centroid + spread) to power the Style DNA scatter plot.';
comment on column public.umap_coords.author_id is 'UUID of the author who owns the chunk. Denormalised here (the canonical author_id lives on documents via chunks → documents → authors) for fast per-author aggregation without a join. No FK constraint: this table is a volatile cache.';
comment on column public.umap_coords.x         is '1st UMAP dimension. Produced by umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, metric=''cosine'', random_state=42).';
comment on column public.umap_coords.y         is '2nd UMAP dimension. Same reducer as x.';

-- ---------------------------------------------------------------------------
-- Index: fast per-author lookup / aggregation
-- ---------------------------------------------------------------------------

create index if not exists umap_coords_author_id_idx
    on public.umap_coords (author_id);

commit;
