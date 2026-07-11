-- =============================================================================
-- Migration : 0001_init.sql
-- Project   : AutorIA
-- Purpose   : Create the full initial schema for AutorIA on PostgreSQL 16 +
--             pgvector (Supabase).  Five tables: authors, documents, chunks,
--             style_profiles, passports, plus all supporting indexes.
--
-- Source of truth: docs/erd.md  ·  docs/MVP.md §6
--
-- Apply manually:
--   psql "$DATABASE_URL" -f infra/supabase/migrations/0001_init.sql
--
-- Or via Supabase CLI:
--   supabase db push
--
-- Notes:
--   • Pure DDL — no seed data.  Seed data lives in scripts/seed/.
--   • Every statement is idempotent (IF NOT EXISTS / OR REPLACE).
--   • UUID primary keys use gen_random_uuid() from pgcrypto.
--   • HNSW index uses vector_cosine_ops (operator <=>) to match the
--     cosine-similarity component of fit_score (MVP §4.2).
--   • RLS is NOT enabled in v1 — backend connects with a privileged role.
--     A future migration (000X_rls_policies.sql) will add it if the tables
--     are ever exposed directly via Supabase PostgREST.
-- =============================================================================

begin;

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------

create extension if not exists vector;    -- pgvector: vector type + HNSW/IVFFlat
create extension if not exists pgcrypto;  -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Table: authors
-- ---------------------------------------------------------------------------

create table if not exists public.authors (
    id         uuid        primary key default gen_random_uuid(),
    name       text        not null,
    slug       text        not null unique,   -- URL/JSON-facing id, e.g. 'dickens'
    bio        text,
    created_at timestamptz not null default now()
);

comment on table  public.authors            is 'Author "voices". Three preloaded (Austen, Dickens, Poe); more can be added live.';
comment on column public.authors.slug       is 'Stable, URL/JSON-facing identifier used by the API and inside StyleProfile/Passport JSON (e.g. ''dickens''). The UNIQUE constraint doubles as the index.';
comment on column public.authors.bio        is 'Optional short description. Stored for future use / seed metadata; NOT exposed by the current API (AuthorSummary is id, name, slug, has_style_profile, n_documents).';

-- ---------------------------------------------------------------------------
-- Table: documents
-- ---------------------------------------------------------------------------

create table if not exists public.documents (
    id         uuid        primary key default gen_random_uuid(),
    author_id  uuid        not null references public.authors(id) on delete cascade,
    title      text        not null,
    source_url text,
    raw_text   text        not null,
    n_tokens   integer,
    created_at timestamptz not null default now()
);

comment on table  public.documents           is 'Cleaned source texts that make up an author corpus (one row per work, e.g. a novel). Gutenberg headers/footers are stripped before storage.';
comment on column public.documents.n_tokens  is 'Approximate token count using tiktoken cl100k_base.';
comment on column public.documents.raw_text  is 'Full cleaned text — Gutenberg headers/footers stripped, quotes and whitespace normalised.';

create index if not exists documents_author_id_idx
    on public.documents (author_id);

-- ---------------------------------------------------------------------------
-- Table: chunks
-- ---------------------------------------------------------------------------

create table if not exists public.chunks (
    id             uuid        primary key default gen_random_uuid(),
    document_id    uuid        not null references public.documents(id) on delete cascade,
    chunk_index    integer     not null,
    text           text        not null,
    embedding      vector(768),            -- nullable; filled asynchronously after insert
    token_start    integer     not null,
    token_end      integer     not null,
    created_at     timestamptz not null default now(),
    unique (document_id, chunk_index)
);

comment on table  public.chunks              is '~500-token slices of a document (overlap 50). This is the table RAG searches. Embeddings are 768-dim from sentence-transformers all-mpnet-base-v2.';
comment on column public.chunks.chunk_index  is 'Ordinal within the document. Referenced by the Authorship Passport as rag_sources[].chunk_id.';
comment on column public.chunks.embedding    is 'vector(768), nullable — chunks can be inserted first and embedded asynchronously. Model: sentence-transformers/all-mpnet-base-v2.';
comment on column public.chunks.token_start  is 'Start token offset of this chunk within the parent document (tiktoken cl100k_base).';
comment on column public.chunks.token_end    is 'End token offset of this chunk within the parent document (tiktoken cl100k_base).';

-- Btree index for document-level fetches
create index if not exists chunks_document_id_idx
    on public.chunks (document_id);

-- HNSW index for approximate nearest-neighbour search over embeddings.
-- vector_cosine_ops → cosine distance (operator <=>).
-- This matches the cosine_sim component of fit_score (MVP §4.2):
--   fit_score += cosine_sim(emb_gen, semantic_centroid) × 0.35
-- Build params: m=16, ef_construction=64 (sensible defaults for this corpus size).
-- Query-time recall can be tuned with: SET hnsw.ef_search = <n>;
create index if not exists chunks_embedding_hnsw_idx
    on public.chunks
    using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- Table: style_profiles
-- ---------------------------------------------------------------------------

create table if not exists public.style_profiles (
    id          uuid        primary key default gen_random_uuid(),
    author_id   uuid        not null references public.authors(id) on delete cascade,
    version     text        not null,       -- schema_version, e.g. '1.0'
    json_data   jsonb       not null,       -- full StyleProfile JSON (MVP §4.2)
    hash        text        not null,       -- sha256 of canonical json_data; mirrored in Passport
    computed_at timestamptz not null default now()
);

comment on table  public.style_profiles           is 'Versioned "stylistic DNA" per author (StyleProfile JSON v1.0, MVP §4.2). Recomputes append a new row; the current profile is the one with the latest computed_at.';
comment on column public.style_profiles.version   is 'schema_version string, e.g. ''1.0''. Allows the JSON shape to evolve independently of the DB columns.';
comment on column public.style_profiles.json_data is 'Full StyleProfile JSON stored as jsonb so individual fields (ttr, avg_sentence_length, etc.) are queryable.';
comment on column public.style_profiles.hash      is 'sha256 of the canonical json_data. Mirrored in the Passport as author_voice.style_profile_hash for tamper-evidence.';

create index if not exists style_profiles_author_id_computed_at_idx
    on public.style_profiles (author_id, computed_at desc);

-- ---------------------------------------------------------------------------
-- Table: passports
-- ---------------------------------------------------------------------------

create table if not exists public.passports (
    id          uuid        primary key default gen_random_uuid(),
    author_id   uuid        not null references public.authors(id) on delete cascade,
    json_data   jsonb       not null,   -- Passport payload (MVP §4.4)
    jws_token   text        not null,   -- compact JWS, ES256 (ECDSA P-256 + SHA-256)
    created_at  timestamptz not null default now()
);

comment on table  public.passports             is 'One row per issued Authorship Passport (MVP §4.4). Stores both the JSON payload and its compact JWS token so verification is fully reproducible offline.';
comment on column public.passports.json_data   is 'Passport payload JSON. Stores hashes of prompt/output/snippets (not raw text) for privacy.';
comment on column public.passports.jws_token   is 'Compact JWS signed with ES256 (ECDSA P-256 + SHA-256). Verifiable against /.well-known/jwks.json.';

create index if not exists passports_author_id_idx
    on public.passports (author_id);

commit;
