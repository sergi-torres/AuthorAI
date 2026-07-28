"""scripts/seed_corpus.py
=============================================================================
Seed the AutorIA database with the 3 preloaded authors — Jane Austen,
Charles Dickens, Edgar Allan Poe — from the plain-text corpus checked into
``corpus/`` (see ``corpus/README.md``).

This is the script ``make seed`` (Makefile) and ``README.md`` "Getting
Started" both point at. It is also the prerequisite for issue #18
(StyleProfile must be computed from real seeded documents, not a
zeros-stub) — see ``completeness_audit.md`` items #7 and #18.

Pipeline (5 stages, run in order)
----------------------------------
1. authors    — upsert the 3 preloaded authors by ``slug``
                (``ON CONFLICT (slug) DO UPDATE``). Always runs.
2. documents  — insert one row per corpus ``.txt`` file. Idempotent via
                ``content_hash`` (migration 0003_seed_idempotency.sql):
                re-running the script skips files already seeded instead
                of duplicating rows. Always runs.
3. chunks     — token-windowed slices (500 tokens / 50 overlap, tiktoken
                ``cl100k_base``), mirroring
                ``backend/app/routes/authors.py::_chunk_and_insert`` byte
                for byte so RAG retrieval behaves identically regardless
                of whether a document arrived via seeding or upload.
                Always runs (skipped per-document if already chunked).
4. embeddings — OPT-IN via ``--with-embeddings``. Runs
                ``autoria_ai.db.backfill_embeddings()`` (async, pgvector)
                to fill every ``chunks.embedding IS NULL`` row — seeded or
                uploaded, corpus-wide.
5. profiles   — OPT-IN via ``--with-profiles``. Runs
                ``autoria_ai.extractor.style_profile.compute_style_profile``
                over each seeded author's cleaned documents and inserts a
                real (non-stub) row into ``style_profiles``. Requires the
                ``en_core_web_lg`` spaCy model (``make install-py``).
                Before the first profile, every author's corpus is
                lemmatized once (``build_comparison_lemmas``) so
                ``distinctive_vocab`` is a real three-document TF-IDF —
                docs/style_features.md 4.1. This holds even with
                ``--author``: the other two authors are still lemmatized,
                because they are the comparison documents.

Embeddings and profiles are opt-in (not run by default) because both are
slow (model downloads + CPU-bound inference) and are not required just to
get ``authors`` / ``documents`` / ``chunks`` populated for local dev.

Usage
-----
    # from the repo root, with the virtualenv active and DATABASE_URL set:
    python scripts/seed_corpus.py                     # stages 1-3, all 3 authors
    python scripts/seed_corpus.py --author dickens     # stages 1-3, one author
    python scripts/seed_corpus.py --with-embeddings    # + stage 4
    python scripts/seed_corpus.py --with-profiles      # + stage 5
    python scripts/seed_corpus.py --dry-run            # validate corpus/, no DB writes

``--author`` may be repeated to seed more than one author but not all
three, e.g. ``--author austen --author poe``.

Dependencies (beyond ai_pipeline/pyproject.toml)
-------------------------------------------------
    pip install psycopg2-binary       # sync PG driver used by this script
    # tiktoken, sqlalchemy, asyncpg, spacy are already declared in
    # ai_pipeline/pyproject.toml and installed via `make install-py`.
    # --with-profiles additionally requires the spaCy model:
    #   python -m spacy download en_core_web_lg

Environment variables
----------------------
    DATABASE_URL — PostgreSQL DSN, plain ``postgresql://`` scheme
                   (matches .env.example). Stage 4 derives an
                   ``postgresql+asyncpg://`` variant internally; you do
                   not need to set that yourself.

Exit codes
----------
    0 — success (or --dry-run found no warnings)
    1 — --dry-run found warnings, or a seeding stage failed
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
import tiktoken

# ---------------------------------------------------------------------------
# sys.path bootstrap — ai_pipeline is a separate, uninstalled package when
# this script is run directly from the repo root (it is normally installed
# editable via `pip install -e ai_pipeline[dev]`, but `make seed` / a bare
# `python scripts/seed_corpus.py` should also work on a fresh checkout
# without requiring that install step first). Prepending the package
# directory to sys.path lets `import autoria_ai...` resolve either way.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_AI_PIPELINE_SRC = _REPO_ROOT / "ai_pipeline"
if str(_AI_PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(_AI_PIPELINE_SRC))

from autoria_ai.extractor.cleaner import clean_text  # noqa: E402

# ---------------------------------------------------------------------------
# Logging — plain ASCII only. This script is exercised on Windows
# PowerShell (see Makefile "Windows note"), whose default console code
# page is not UTF-8; a stray unicode arrow/checkmark in a log record can
# raise UnicodeEncodeError and crash the run. Keep every f-string/log
# message below ASCII-only (docstrings and comments are fine — they are
# never printed).
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CORPUS_DIR: Path = _REPO_ROOT / "corpus"

#: Token-window parameters. MUST match
#: backend/app/routes/authors.py::_CHUNK_SIZE / _CHUNK_OVERLAP exactly, so
#: seeded and uploaded documents chunk identically.
CHUNK_SIZE: int = 500
CHUNK_OVERLAP: int = 50

#: Validation gate from corpus/README.md ("Each author has >= 30,000
#: cleaned tokens"). Used only by --dry-run and as a post-clean warning.
MIN_TOKENS_PER_AUTHOR: int = 30_000

#: The 3 preloaded authors and the corpus files that make up each corpus.
#: Filenames must match corpus/<slug>/ exactly (including the em dash in
#: the Poe volume titles) — see corpus/README.md.
AUTHOR_MANIFEST: dict[str, dict[str, Any]] = {
    "austen": {
        "name": "Jane Austen",
        "bio": (
            "English novelist (1775-1817) celebrated for social irony, "
            "free indirect discourse, and the comedy of manners of "
            "Regency-era England."
        ),
        "files": [
            "Pride and Prejudice by Jane Austen.txt",
            "Emma by Jane Austen.txt",
            "Sense and Sensibility by Jane Austen.txt",
            "Northanger Abbey by Jane Austen.txt",
        ],
    },
    "dickens": {
        "name": "Charles Dickens",
        "bio": (
            "English novelist (1812-1870) known for Victorian social "
            "criticism, sprawling ensemble casts, and maximalist, "
            "serialized prose."
        ),
        "files": [
            "Great Expectations by Charles Dickens.txt",
            "A Tale of Two Cities by Charles Dickens.txt",
            "Oliver Twist by Charles Dickens.txt",
            "Bleak House by Charles Dickens.txt",
        ],
    },
    "poe": {
        "name": "Edgar Allan Poe",
        "bio": (
            "American writer (1809-1849) known for Gothic first-person "
            "intensity, unreliable narrators, and the invention of the "
            "modern detective story."
        ),
        "files": [
            "The Works of Edgar Allan Poe \u2014 Volume 1 by Edgar Allan Poe.txt",
            "The Works of Edgar Allan Poe \u2014 Volume 2 by Edgar Allan Poe.txt",
        ],
    },
}

_ENCODER = tiktoken.get_encoding("cl100k_base")

# ---------------------------------------------------------------------------
# Data holder — one cleaned document, carried between stages 2, 3 and 5
# without needing to re-read it back from the DB.
# ---------------------------------------------------------------------------


@dataclass
class SeededDocument:
    """A single corpus file after cleaning, plus its DB identity once seeded."""

    author_slug: str
    title: str
    path: Path
    cleaned_text: str = ""
    content_hash: str = ""
    n_tokens: int = 0
    document_id: str | None = None
    is_new: bool = False  # False if this row already existed (ON CONFLICT hit)


@dataclass
class SeedReport:
    """Accumulated outcome of a full run, printed at the end."""

    authors_upserted: int = 0
    documents_inserted: int = 0
    documents_skipped: int = 0
    chunks_inserted: int = 0
    embeddings_backfilled: int | None = None
    profiles_inserted: int = 0
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Corpus validation (used by --dry-run, and as a pre-flight check before
# any DB write in a normal run).
# ---------------------------------------------------------------------------


def _gutenberg_sentinel_present(text: str) -> bool:
    """True if raw Project Gutenberg header/footer sentinels survived cleaning."""
    upper = text.upper()
    return "START OF THE PROJECT GUTENBERG" in upper or "END OF THE PROJECT GUTENBERG" in upper


def validate_corpus(authors: list[str]) -> list[str]:
    """Check every corpus file for *authors* and return a list of warnings.

    An empty return value means the corpus is seed-ready. Checks performed,
    per corpus/README.md "Validation":
      * every manifest file exists under CORPUS_DIR/<slug>/
      * the file decodes as UTF-8 (no latin-1/cp1252 leftovers)
      * the file is non-empty after clean_text()
      * no Gutenberg header/footer sentinel survives clean_text()
      * each author's corpus totals >= MIN_TOKENS_PER_AUTHOR cleaned tokens

    This function performs no DB I/O and is safe to call without
    DATABASE_URL set — it is the entire implementation of --dry-run.
    """
    warnings: list[str] = []

    for slug in authors:
        manifest = AUTHOR_MANIFEST[slug]
        author_dir = CORPUS_DIR / slug
        total_tokens = 0

        for filename in manifest["files"]:
            file_path = author_dir / filename

            if not file_path.is_file():
                warnings.append(f"[{slug}] missing corpus file: {file_path}")
                continue

            try:
                raw_bytes = file_path.read_bytes()
                raw_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                warnings.append(f"[{slug}] {file_path.name}: not valid UTF-8 ({exc})")
                continue

            cleaned = clean_text(raw_text)

            if not cleaned.strip():
                warnings.append(f"[{slug}] {file_path.name}: empty after clean_text()")
                continue

            if _gutenberg_sentinel_present(cleaned):
                warnings.append(
                    f"[{slug}] {file_path.name}: Gutenberg header/footer sentinel "
                    "survived clean_text()"
                )

            total_tokens += len(_ENCODER.encode(cleaned))

        if total_tokens and total_tokens < MIN_TOKENS_PER_AUTHOR:
            warnings.append(
                f"[{slug}] corpus has only {total_tokens} cleaned tokens "
                f"(< {MIN_TOKENS_PER_AUTHOR} minimum)"
            )

        log.info(
            "[%s] validated: %d cleaned tokens across %d file(s)",
            slug,
            total_tokens,
            len(manifest["files"]),
        )

    return warnings


# ---------------------------------------------------------------------------
# DB connection helpers
# ---------------------------------------------------------------------------


def get_connection(database_url: str | None = None) -> psycopg2.extensions.connection:
    """Return a synchronous psycopg2 connection.

    Parameters
    ----------
    database_url:
        Full PostgreSQL DSN. If *None*, reads ``DATABASE_URL`` from the
        environment (see .env.example — plain ``postgresql://`` scheme).

    Raises
    ------
    KeyError
        If ``DATABASE_URL`` is not set and *database_url* was not provided.
    """
    url = database_url or os.environ["DATABASE_URL"]
    # Defensive: accept an asyncpg-flavoured DSN too, in case a caller
    # copy-pasted it from ai_pipeline/autoria_ai/db.py.
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url)


def to_asyncpg_url(database_url: str) -> str:
    """Convert a plain ``postgresql://`` DSN to the ``+asyncpg`` form.

    ``autoria_ai.db`` (SQLAlchemy async engine) requires the
    ``postgresql+asyncpg://`` driver prefix, while this script and
    ``.env.example`` use the plain ``postgresql://`` scheme shared with
    psycopg2 and the Supabase dashboard. Both ``postgres://`` (short form,
    sometimes emitted by hosting providers) and ``postgresql://`` are
    normalised to ``postgresql+asyncpg://``.
    """
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + database_url[len("postgresql://") :]
    if database_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + database_url[len("postgres://") :]
    raise ValueError(f"Unrecognized DATABASE_URL scheme: {database_url.split('://', 1)[0]}")


# ---------------------------------------------------------------------------
# Stage 1 — authors
# ---------------------------------------------------------------------------


def seed_authors(conn: psycopg2.extensions.connection, authors: list[str]) -> dict[str, str]:
    """Upsert each author in *authors* by slug and return {slug: uuid}.

    Uses ``ON CONFLICT (slug) DO UPDATE`` (not DO NOTHING) so re-running
    the seed after editing a bio/name in AUTHOR_MANIFEST picks up the
    change, while the row's ``id`` (and every FK pointing at it) is left
    untouched.
    """
    ids: dict[str, str] = {}
    with conn.cursor() as cur:
        for slug in authors:
            manifest = AUTHOR_MANIFEST[slug]
            cur.execute(
                """
                INSERT INTO public.authors (name, slug, bio)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                    SET name = EXCLUDED.name,
                        bio  = EXCLUDED.bio
                RETURNING id
                """,
                (manifest["name"], slug, manifest["bio"]),
            )
            row = cur.fetchone()
            assert row is not None  # RETURNING always yields a row here
            ids[slug] = str(row[0])
    conn.commit()
    log.info("Stage 1/5 authors: upserted %d author(s): %s", len(ids), ", ".join(ids))
    return ids


# ---------------------------------------------------------------------------
# Stage 2 — documents
# ---------------------------------------------------------------------------


def _compute_content_hash(cleaned_text: str, title: str) -> str:
    """sha256 hex digest of *cleaned_text*, falling back to hashing *title*.

    The fallback exists so a document that somehow cleans down to an
    empty string (e.g. a corrupted download) still gets a stable,
    non-empty content_hash instead of colliding with every other empty
    document under the partial unique index
    (documents_content_hash_uniq, migration 0003).
    """
    basis = cleaned_text if cleaned_text.strip() else f"title:{title}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def load_documents(author_slug: str) -> list[SeededDocument]:
    """Read + clean every corpus file for *author_slug* (no DB I/O)."""
    manifest = AUTHOR_MANIFEST[author_slug]
    author_dir = CORPUS_DIR / author_slug
    docs: list[SeededDocument] = []

    for filename in manifest["files"]:
        file_path = author_dir / filename
        raw_text = file_path.read_text(encoding="utf-8")
        cleaned = clean_text(raw_text)
        title = file_path.stem  # filename without ".txt", e.g. "Emma by Jane Austen"

        doc = SeededDocument(
            author_slug=author_slug,
            title=title,
            path=file_path,
            cleaned_text=cleaned,
            content_hash=_compute_content_hash(cleaned, title),
            n_tokens=len(_ENCODER.encode(cleaned)),
        )
        docs.append(doc)

    return docs


def seed_documents(
    conn: psycopg2.extensions.connection,
    author_uuid: str,
    docs: list[SeededDocument],
) -> None:
    """Insert *docs* into public.documents, skipping ones already seeded.

    Idempotency: ``ON CONFLICT (content_hash) WHERE content_hash IS NOT
    NULL DO NOTHING`` (partial unique index from migration
    0003_seed_idempotency.sql). When a row already exists, its ``id`` is
    looked up by content_hash so stage 3 can still decide whether that
    document needs chunking (see ``doc.is_new``).

    Mutates each ``SeededDocument`` in place: sets ``document_id`` and
    ``is_new``.
    """
    with conn.cursor() as cur:
        for doc in docs:
            cur.execute(
                """
                INSERT INTO public.documents
                    (author_id, title, raw_text, n_tokens, content_hash)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) WHERE content_hash IS NOT NULL
                    DO NOTHING
                RETURNING id
                """,
                (author_uuid, doc.title, doc.cleaned_text, doc.n_tokens, doc.content_hash),
            )
            row = cur.fetchone()
            if row is not None:
                doc.document_id = str(row[0])
                doc.is_new = True
                continue

            # Conflict hit — the row already exists; fetch its id so the
            # caller can still reason about it (e.g. re-chunk check).
            cur.execute(
                "SELECT id FROM public.documents WHERE content_hash = %s",
                (doc.content_hash,),
            )
            existing = cur.fetchone()
            assert existing is not None  # the ON CONFLICT proved this row exists
            doc.document_id = str(existing[0])
            doc.is_new = False

    conn.commit()

    n_new = sum(1 for d in docs if d.is_new)
    n_skipped = len(docs) - n_new
    log.info(
        "Stage 2/5 documents [%s]: %d inserted, %d already seeded (skipped)",
        docs[0].author_slug if docs else "?",
        n_new,
        n_skipped,
    )


# ---------------------------------------------------------------------------
# Stage 3 — chunks
# ---------------------------------------------------------------------------


def _chunk_document(cleaned_text: str) -> list[tuple[int, str, int, int]]:
    """Token-window *cleaned_text* into (chunk_index, text, token_start, token_end).

    This MUST stay in lockstep with
    ``backend/app/routes/authors.py::_chunk_and_insert`` (same encoding,
    same window/overlap, same 0-based sequential chunk_index, same
    inclusive-start/exclusive-end token offsets) so a document seeded here
    is indistinguishable — for RAG retrieval and the Authorship Passport's
    ``rag_sources[].chunk_id`` — from one uploaded through the API.
    """
    tokens = _ENCODER.encode(cleaned_text)
    rows: list[tuple[int, str, int, int]] = []
    chunk_index = 0
    step = CHUNK_SIZE - CHUNK_OVERLAP
    pos = 0

    while pos < len(tokens):
        end = min(pos + CHUNK_SIZE, len(tokens))
        chunk_tokens = tokens[pos:end]
        rows.append((chunk_index, _ENCODER.decode(chunk_tokens), pos, end))
        chunk_index += 1
        if end == len(tokens):
            break
        pos += step

    return rows


def seed_chunks(conn: psycopg2.extensions.connection, docs: list[SeededDocument]) -> int:
    """Chunk + insert every document in *docs* that does not have chunks yet.

    Only documents with ``is_new = True`` are chunked — a document that
    already existed (stage 2 hit the content_hash conflict) is assumed to
    already have its chunks too, since chunk seeding always follows
    document seeding in the same run. ``ON CONFLICT (document_id,
    chunk_index) DO NOTHING`` is still applied as a defensive no-op in
    case that assumption is ever wrong (e.g. a previous run was
    interrupted between stage 2 and stage 3).

    Returns the total number of chunk rows inserted (across all *docs*).
    """
    total_inserted = 0

    with conn.cursor() as cur:
        for doc in docs:
            if not doc.is_new:
                continue
            assert doc.document_id is not None

            windows = _chunk_document(doc.cleaned_text)
            if not windows:
                log.warning(
                    "[%s] %s produced zero chunks -- cleaned text may be empty",
                    doc.author_slug,
                    doc.title,
                )
                continue

            rows = [
                (doc.document_id, chunk_index, text, token_start, token_end)
                for chunk_index, text, token_start, token_end in windows
            ]
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO public.chunks
                    (document_id, chunk_index, text, token_start, token_end)
                VALUES %s
                ON CONFLICT (document_id, chunk_index) DO NOTHING
                """,
                rows,
                page_size=500,
            )
            total_inserted += len(rows)
            log.info(
                "Stage 3/5 chunks [%s] %s: inserted %d chunk(s)",
                doc.author_slug,
                doc.title,
                len(rows),
            )

    conn.commit()
    return total_inserted


# ---------------------------------------------------------------------------
# Stage 4 — embeddings (opt-in via --with-embeddings)
# ---------------------------------------------------------------------------


async def _run_embedding_backfill(database_url: str) -> int:
    """Import + run autoria_ai.db.backfill_embeddings() with an asyncpg DSN.

    Imported lazily (inside the function, not at module top) so that
    stages 1-3 and --dry-run never pay the cost of importing
    sentence-transformers / torch when --with-embeddings is not passed.
    """
    from autoria_ai.db import backfill_embeddings

    asyncpg_url = to_asyncpg_url(database_url)
    return await backfill_embeddings(database_url=asyncpg_url)


def run_embedding_backfill(database_url: str) -> int:
    """Synchronous entrypoint for stage 4 — wraps the async backfill in asyncio.run().

    Returns the number of chunks that were backfilled (0 if every chunk
    already had an embedding).
    """
    import asyncio

    log.info("Stage 4/5 embeddings: backfilling NULL chunk embeddings (this loads a model)...")
    n_filled = asyncio.run(_run_embedding_backfill(database_url))
    log.info("Stage 4/5 embeddings: backfilled %d chunk(s)", n_filled)
    return n_filled


# ---------------------------------------------------------------------------
# Stage 5 — style profiles (opt-in via --with-profiles)
# ---------------------------------------------------------------------------


def build_comparison_lemmas(nlp: Any, authors: list[str] | None = None) -> dict[str, str]:
    """Lemmatize every author's corpus once, for the cross-author TF-IDF.

    ``docs/style_features.md`` §4.1 defines ``distinctive_vocab`` as TF-IDF
    where *each author's full corpus is one "document" and the collection is
    all three authors combined*. A single-document collection makes the IDF
    term constant, which collapses the ranking to raw frequency — that is why
    this mapping has to be built before any profile is computed.

    *authors* defaults to **every** slug in AUTHOR_MANIFEST, deliberately
    ignoring ``--author``: seeding one author still needs the other two as
    comparison documents, otherwise the TF-IDF degenerates again.

    Cost: one extra spaCy pass per author, each capped at
    ``style_profile._MAX_LEMMA_CHARS`` (800k chars). The pass streams
    ``nlp.pipe`` and stops at the cap, so it is a fraction of a full feature
    pass; peak extra memory is 3 x 800 KB of lemma text.
    """
    from autoria_ai.extractor.style_profile import lemmatize_corpus

    slugs = list(AUTHOR_MANIFEST) if authors is None else authors
    lemmas: dict[str, str] = {}
    for slug in slugs:
        docs = load_documents(slug)
        texts = [d.cleaned_text for d in docs if d.cleaned_text.strip()]
        if not texts:
            log.warning("Stage 5/5 profiles: no corpus text for %s -- excluded from TF-IDF", slug)
            continue
        log.info("Stage 5/5 profiles: lemmatizing %s corpus for cross-author TF-IDF...", slug)
        lemmas[slug] = lemmatize_corpus(documents=texts, nlp=nlp)
    log.info(
        "Stage 5/5 profiles: comparison corpora ready for %d author(s): %s",
        len(lemmas),
        ", ".join(lemmas),
    )
    return lemmas


def seed_style_profile(
    conn: psycopg2.extensions.connection,
    author_slug: str,
    author_uuid: str,
    documents: list[str],
    nlp: Any,
    comparison_lemmas: dict[str, str] | None = None,
) -> None:
    """Compute a real StyleProfile v1.0 for *author_slug* and insert it.

    Replaces, for seeded authors, the all-zeros placeholder that
    ``backend/app/routes/authors.py::_recompute_style_profile`` still
    inserts for authors created purely through the upload API (see
    completeness_audit.md #1 / issue #18). ``nlp`` is a loaded spaCy
    ``en_core_web_lg`` pipeline, shared across all authors in this run so
    the (slow) model load happens exactly once.

    ``comparison_lemmas`` is the ``{slug: lemmatized_corpus}`` mapping from
    ``build_comparison_lemmas`` — every author's corpus, so TF-IDF sees the
    three-document collection that docs/style_features.md §4.1 specifies.
    ``compute_style_profile`` overwrites this author's own entry with the
    lemmas from its own pass (same rules, same ``_MAX_LEMMA_CHARS`` cap), so
    passing the whole mapping — self included — is intentional and harmless.
    """
    from autoria_ai.extractor.style_profile import compute_style_profile, profile_hash

    log.info(
        "Stage 5/5 profiles [%s]: computing StyleProfile over %d document(s)...",
        author_slug,
        len(documents),
    )
    if not comparison_lemmas:
        log.warning(
            "Stage 5/5 profiles [%s]: no comparison corpora -- distinctive_vocab "
            "will collapse to raw frequency (see docs/style_features.md 4.1)",
            author_slug,
        )
    profile = compute_style_profile(
        author_slug=author_slug,
        documents=documents,
        nlp=nlp,
        comparison_lemmas=comparison_lemmas or None,
    )
    phash = profile_hash(profile)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.style_profiles (author_id, version, json_data, hash)
            VALUES (%s, %s, %s, %s)
            """,
            (author_uuid, profile["schema_version"], psycopg2.extras.Json(profile), phash),
        )
    conn.commit()
    log.info(
        "Stage 5/5 profiles [%s]: inserted style_profiles row (hash=%s)",
        author_slug,
        phash[:19] + "...",
    )


def _load_spacy_model() -> Any:
    """Load en_core_web_lg once, with a friendly error if it is not installed."""
    import spacy

    try:
        return spacy.load("en_core_web_lg")
    except OSError as exc:
        raise SystemExit(
            "en_core_web_lg is required for --with-profiles but is not installed.\n"
            "Run: python -m spacy download en_core_web_lg\n"
            f"(original error: {exc})"
        ) from exc


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run(
    authors: list[str],
    *,
    database_url: str | None = None,
    with_embeddings: bool = False,
    with_profiles: bool = False,
) -> SeedReport:
    """Run stages 1-3 (always) + 4/5 (opt-in) for *authors*.

    Parameters
    ----------
    authors:
        Subset of AUTHOR_MANIFEST keys to seed. Order is preserved.
    database_url:
        Override for DATABASE_URL (used by tests). Falls back to the
        environment inside ``get_connection``.
    with_embeddings:
        Run stage 4 (backfill_embeddings) after documents/chunks are seeded.
    with_profiles:
        Run stage 5 (compute_style_profile) after documents are seeded.
        Loads the en_core_web_lg spaCy model once, shared across authors.
    """
    report = SeedReport()
    conn = get_connection(database_url)
    nlp = _load_spacy_model() if with_profiles else None

    try:
        author_ids = seed_authors(conn, authors)
        report.authors_upserted = len(author_ids)

        # Built once for the whole run, after the first DB write has proven the
        # connection: every author's lemmas are needed as comparison documents
        # for every other author's TF-IDF (see build_comparison_lemmas /
        # docs/style_features.md 4.1).
        comparison_lemmas = build_comparison_lemmas(nlp) if with_profiles else None

        for slug in authors:
            docs = load_documents(slug)
            seed_documents(conn, author_ids[slug], docs)

            n_new = sum(1 for d in docs if d.is_new)
            report.documents_inserted += n_new
            report.documents_skipped += len(docs) - n_new

            n_chunks = seed_chunks(conn, docs)
            report.chunks_inserted += n_chunks

            if with_profiles:
                seed_style_profile(
                    conn,
                    slug,
                    author_ids[slug],
                    [d.cleaned_text for d in docs],
                    nlp,
                    comparison_lemmas=comparison_lemmas,
                )
                report.profiles_inserted += 1

        if with_embeddings:
            resolved_url = database_url or os.environ["DATABASE_URL"]
            report.embeddings_backfilled = run_embedding_backfill(resolved_url)

    finally:
        conn.close()

    return report


def _print_report(report: SeedReport) -> None:
    log.info("=" * 60)
    log.info("Seed complete.")
    log.info("  authors upserted     : %d", report.authors_upserted)
    log.info("  documents inserted   : %d", report.documents_inserted)
    log.info("  documents skipped    : %d (already seeded)", report.documents_skipped)
    log.info("  chunks inserted      : %d", report.chunks_inserted)
    if report.embeddings_backfilled is not None:
        log.info("  embeddings backfilled: %d", report.embeddings_backfilled)
    if report.profiles_inserted:
        log.info("  style profiles seeded: %d", report.profiles_inserted)
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed AutorIA's authors/documents/chunks (and optionally "
        "embeddings/style_profiles) from corpus/.",
    )
    parser.add_argument(
        "--author",
        action="append",
        choices=sorted(AUTHOR_MANIFEST),
        dest="authors",
        default=None,
        help="Seed only this author (repeatable). Default: all 3 preloaded authors.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate corpus/ (encoding, Gutenberg sentinels, token minimums) "
        "and exit without touching the database. Exit code 1 if any warning is found.",
    )
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="After seeding, run the async embedding backfill (stage 4). "
        "Loads sentence-transformers all-mpnet-base-v2.",
    )
    parser.add_argument(
        "--with-profiles",
        action="store_true",
        help="After seeding, compute + insert a real StyleProfile per author (stage 5). "
        "Requires the en_core_web_lg spaCy model.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    authors: list[str] = args.authors or list(AUTHOR_MANIFEST)

    if args.dry_run:
        log.info("Dry run: validating corpus/ for %s...", ", ".join(authors))
        warnings = validate_corpus(authors)
        if warnings:
            log.warning("Dry run found %d warning(s):", len(warnings))
            for w in warnings:
                log.warning("  - %s", w)
            return 1
        print("OK")
        return 0

    # Fail fast on a clearly broken corpus before opening a DB connection.
    warnings = validate_corpus(authors)
    for w in warnings:
        log.warning("%s", w)

    try:
        report = run(
            authors,
            with_embeddings=args.with_embeddings,
            with_profiles=args.with_profiles,
        )
    except KeyError as exc:
        log.error("Missing required environment variable: %s", exc)
        return 1
    except Exception:
        log.exception("Seeding failed")
        return 1

    report.warnings = warnings
    _print_report(report)
    return 0


# ---------------------------------------------------------------------------
# Back-compat surface for ai_pipeline/tests/test_seed_corpus.py (Bob Task A API)
# ---------------------------------------------------------------------------
#
# The production entrypoints above are ``main()`` / ``run()`` / ``validate_corpus``.
# Unit tests were written against an earlier helper surface (``seed``, ``_run_dry``,
# ``_compute_chunks_with_offsets``, ``_run_embeddings``, …). Keep those names as
# thin wrappers so the restored suite stays green without duplicating the pipeline.

CORPUS_ROOT: Path = CORPUS_DIR
_CHUNK_SIZE: int = CHUNK_SIZE
_CHUNK_OVERLAP: int = CHUNK_OVERLAP

_get_connection = get_connection


def _compute_chunks_with_offsets(text: str) -> list[dict[str, Any]]:
    """Dict-shaped view of ``_chunk_document`` (keys match the unit tests)."""
    return [
        {
            "chunk_index": chunk_index,
            "text": chunk_text,
            "token_start": token_start,
            "token_end": token_end,
        }
        for chunk_index, chunk_text, token_start, token_end in _chunk_document(text)
    ]


def _document_exists_by_hash(
    conn: psycopg2.extensions.connection,
    author_id: str,
    content_hash: str,
) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM public.documents WHERE author_id = %s AND content_hash = %s",
            (author_id, content_hash),
        )
        row = cur.fetchone()
    return str(row[0]) if row else None


def _document_exists_by_title(
    conn: psycopg2.extensions.connection,
    author_id: str,
    title: str,
) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM public.documents WHERE author_id = %s AND title = %s",
            (author_id, title),
        )
        row = cur.fetchone()
    return str(row[0]) if row else None


def _content_hash_column_exists(conn: psycopg2.extensions.connection) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name = 'documents'
               AND column_name = 'content_hash'
            """)
        return cur.fetchone() is not None


def _run_dry(*, author_filter: str | None = None) -> None:
    """Validate corpus under ``CORPUS_ROOT`` and ``sys.exit`` (0=ok, 1=warnings).

    Unlike ``validate_corpus`` (manifest filenames under ``CORPUS_DIR``), this
    helper globs ``*.txt`` so unit tests can point ``CORPUS_ROOT`` at ``tmp_path``.
    Prints a short per-author line to stdout for the filter test.
    """
    authors = [author_filter] if author_filter else list(AUTHOR_MANIFEST)
    warnings: list[str] = []

    for slug in authors:
        folder = CORPUS_ROOT / slug
        files = sorted(folder.glob("*.txt")) if folder.is_dir() else []
        if not files:
            warnings.append(f"[{slug}] no corpus .txt files under {folder}")
            print(f"[{slug}] MISSING")
            continue

        total_tokens = 0
        for file_path in files:
            try:
                raw_text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                warnings.append(f"[{slug}] {file_path.name}: not valid UTF-8 ({exc})")
                continue

            cleaned = clean_text(raw_text)
            if not cleaned.strip():
                warnings.append(f"[{slug}] {file_path.name}: empty after clean_text()")
                continue
            if _gutenberg_sentinel_present(cleaned):
                warnings.append(
                    f"[{slug}] {file_path.name}: Gutenberg sentinel survived clean_text()"
                )
            total_tokens += len(_ENCODER.encode(cleaned))

        if total_tokens < MIN_TOKENS_PER_AUTHOR:
            warnings.append(
                f"[{slug}] corpus has only {total_tokens} cleaned tokens "
                f"(< {MIN_TOKENS_PER_AUTHOR} minimum)"
            )
            print(f"[{slug}] LOW_TOKENS={total_tokens}")
        else:
            print(f"[{slug}] OK tokens={total_tokens}")

    sys.exit(1 if warnings else 0)


def _seed_authors(
    conn: psycopg2.extensions.connection,
    author_filter: str | None = None,
) -> dict[str, str]:
    authors = [author_filter] if author_filter else list(AUTHOR_MANIFEST)
    return seed_authors(conn, authors)


def _seed_documents(
    conn: psycopg2.extensions.connection,
    slug_to_uuid: dict[str, str],
    *,
    use_hash: bool = True,
) -> dict[str, str]:
    """Seed documents for each slug; return ``{title_stem: document_id}``."""
    del use_hash  # production path always uses content_hash when column exists
    stem_to_id: dict[str, str] = {}
    # Prefer CORPUS_ROOT so tests can redirect; keep CORPUS_DIR in sync.
    global CORPUS_DIR
    CORPUS_DIR = CORPUS_ROOT
    for slug, author_uuid in slug_to_uuid.items():
        docs = load_documents(slug)
        seed_documents(conn, author_uuid, docs)
        for doc in docs:
            if doc.document_id:
                stem_to_id[doc.title] = doc.document_id
    return stem_to_id


def _seed_chunks(
    conn: psycopg2.extensions.connection,
    slug_to_uuid: dict[str, str],
    stem_to_doc_uuid: dict[str, str],
) -> int:
    del stem_to_doc_uuid
    total = 0
    global CORPUS_DIR
    CORPUS_DIR = CORPUS_ROOT
    for slug in slug_to_uuid:
        docs = load_documents(slug)
        # Mark as new so seed_chunks inserts (idempotent ON CONFLICT protects dups).
        for doc in docs:
            doc.is_new = True
            doc.document_id = doc.document_id or "00000000-0000-0000-0000-000000000000"
        total += seed_chunks(conn, docs)
    return total


def _run_embeddings(database_url: str | None) -> None:
    """Stage 4 — backfill NULL embeddings via autoria_ai.db.backfill_embeddings."""
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise KeyError("DATABASE_URL")
    run_embedding_backfill(url)


def _run_profiles(slug_to_uuid: dict[str, str], database_url: str | None) -> None:
    """Stage 5 — compute StyleProfile for each seeded author and INSERT."""
    nlp = _load_spacy_model()
    comparison_lemmas = build_comparison_lemmas(nlp)
    conn = _get_connection(database_url)
    try:
        for slug, author_uuid in slug_to_uuid.items():
            docs = load_documents(slug)
            if not docs:
                log.warning("Stage 5: no documents for %s — skipping profile", slug)
                continue
            seed_style_profile(
                conn,
                slug,
                author_uuid,
                [d.cleaned_text for d in docs],
                nlp,
                comparison_lemmas=comparison_lemmas,
            )
    finally:
        conn.close()


def seed(
    *,
    database_url: str | None = None,
    author_filter: str | None = None,
    with_embeddings: bool = False,
    with_profiles: bool = False,
    dry_run: bool = False,
) -> None:
    """Full seed pipeline (Stages 1-3 always; 4/5 opt-in via flags)."""
    if dry_run:
        _run_dry(author_filter=author_filter)
        return

    try:
        conn = _get_connection(database_url)
    except KeyError:
        log.error(
            "DATABASE_URL is not set. "
            "Copy .env.example to .env and fill in the connection string. "
            "Use --dry-run to validate without a database."
        )
        sys.exit(1)

    try:
        use_hash = _content_hash_column_exists(conn)
        if not use_hash:
            log.warning(
                "public.documents.content_hash column not found — "
                "Apply infra/supabase/migrations/0003_seed_idempotency.sql "
                "to enable hash-based deduplication."
            )

        slug_to_uuid = _seed_authors(conn, author_filter)
        stem_to_doc_uuid = _seed_documents(conn, slug_to_uuid, use_hash=use_hash)
        _seed_chunks(conn, slug_to_uuid, stem_to_doc_uuid)
    finally:
        conn.close()

    if with_embeddings:
        _run_embeddings(database_url)
    if with_profiles:
        _run_profiles(slug_to_uuid, database_url)

    log.info("Seed complete.")


def _build_parser() -> argparse.ArgumentParser:
    """Bob-era argparse surface: singular ``--author`` (not repeatable)."""
    parser = argparse.ArgumentParser(
        description="Seed AutorIA authors/documents/chunks from corpus/.",
    )
    parser.add_argument(
        "--author",
        choices=sorted(AUTHOR_MANIFEST),
        default=None,
        help="Seed only this author. Default: all 3 preloaded authors.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--with-embeddings", action="store_true")
    parser.add_argument("--with-profiles", action="store_true")
    return parser


if __name__ == "__main__":
    sys.exit(main())
