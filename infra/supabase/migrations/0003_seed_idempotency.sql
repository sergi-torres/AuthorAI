-- =============================================================================
-- Migration : 0003_seed_idempotency.sql
-- Project   : AutorIA
-- Purpose   : Make scripts/seed_corpus.py safely re-runnable by adding a
--             content_hash column to public.documents, with a UNIQUE
--             constraint so re-seeding the same corpus file is a no-op
--             (ON CONFLICT (content_hash) DO NOTHING) instead of a
--             duplicate row.
--
-- Background
-- ----------
-- documents has no natural unique key today (title is not unique — the
-- same novel could legitimately be uploaded under different titles, and
-- two different authors could have identically-titled works). The seed
-- script needs a stable fingerprint to detect "this exact text is already
-- seeded" across repeated `make seed` runs without truncating the table.
--
-- Why content_hash is NULLABLE (not NOT NULL)
-- --------------------------------------------
-- documents is written from two different paths:
--   1. scripts/seed_corpus.py  — computes content_hash = sha256(cleaned
--      text), falling back to sha256(title) if the cleaned text is
--      somehow empty. Always populates the column.
--   2. POST /api/authors/{id}/documents (backend/app/routes/authors.py,
--      upload_author_document) — the live user-upload path. It has no
--      idempotency requirement (every upload is intentionally a new row,
--      even re-uploading the same file twice is a legitimate user action)
--      and does not compute a hash today.
-- Making the column NOT NULL would require touching and coordinating a
-- backend deploy in lockstep with this migration just to backfill a value
-- the upload path does not need. Nullable + a PARTIAL unique index keeps
-- the two write paths fully decoupled: uploads keep working unmodified
-- (content_hash stays NULL, uniqueness is simply not enforced for them),
-- while seeded rows get real de-duplication.
--
-- Why a PARTIAL unique index instead of a plain UNIQUE constraint
-- -----------------------------------------------------------------
-- A plain UNIQUE constraint on a nullable column already allows multiple
-- NULLs in standard SQL (NULL <> NULL), so in principle a bare UNIQUE
-- would "work" here too — but we use an explicit partial index
-- (`WHERE content_hash IS NOT NULL`) to:
--   * document the intent unambiguously (uniqueness only applies to rows
--     that opted into hashing),
--   * keep the index smaller (only seeded rows are indexed), and
--   * give ON CONFLICT (content_hash) WHERE content_hash IS NOT NULL a
--     concrete, self-describing conflict target in seed_corpus.py.
--
-- Source of truth: infra/supabase/migrations/0001_init.sql (documents
-- table) · scripts/seed_corpus.py
--
-- Apply manually:
--   psql "$DATABASE_URL" -f infra/supabase/migrations/0003_seed_idempotency.sql
--
-- Or via Supabase CLI:
--   supabase db push
--
-- Idempotent: every statement uses IF NOT EXISTS, so re-running this
-- migration against an already-migrated database is a safe no-op.
-- =============================================================================

begin;

-- ---------------------------------------------------------------------------
-- Column: documents.content_hash
--
-- NULLABLE — see "Why content_hash is NULLABLE" above. Populated by
-- scripts/seed_corpus.py; left NULL by the POST /documents upload path.
-- ---------------------------------------------------------------------------

alter table public.documents
    add column if not exists content_hash text;

comment on column public.documents.content_hash is
    'sha256 hex digest of the cleaned document text, used only by '
    'scripts/seed_corpus.py to make re-seeding idempotent '
    '(ON CONFLICT (content_hash) DO NOTHING). NULL for documents created '
    'via POST /api/authors/{id}/documents (the live upload path), which '
    'has no de-duplication requirement and does not compute a hash. '
    'Falls back to sha256(title) if the cleaned text is empty, so the '
    'column is still populated (never blank-string) whenever the seed '
    'script writes a row.';

-- ---------------------------------------------------------------------------
-- Partial unique index — uniqueness enforced only where a hash exists.
--
-- IF NOT EXISTS makes this safe to re-run. Rows with content_hash IS NULL
-- (every row inserted via the upload path) are excluded from the index
-- entirely, so they never collide with each other or with seeded rows.
-- ---------------------------------------------------------------------------

create unique index if not exists documents_content_hash_uniq
    on public.documents (content_hash)
    where content_hash is not null;

commit;
