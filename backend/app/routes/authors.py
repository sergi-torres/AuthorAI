"""Authors routes.

Implements:
  GET  /api/authors                                        — list all authors
  GET  /api/authors/{author_id}/style-profile              — getAuthorStyleProfile
  POST /api/authors/{author_id}/documents                  — uploadAuthorDocument
  POST /api/authors/{author_id}/style-profile/recompute    — recomputeAuthorStyleProfile

GET /authors reads ``public.authors`` and derives ``has_style_profile`` /
``n_documents`` from ``style_profiles`` and ``documents``.

The POST /documents handler persists to Supabase synchronously (documents row)
and schedules async chunking (+ embedding backfill) via BackgroundTask.
Contract: 202 {document_id, status:"processing"} — docs/api_contract.yaml
§DocumentUploadAccepted and Decision Log 2026-07-13.

The POST /recompute handler resolves the slug → UUID, estimates wall-clock
seconds from corpus n_tokens, schedules a BackgroundTask, and returns 202
{status:"computing", estimated_seconds:N} — docs/api_contract.yaml
§StyleProfileRecomputeAccepted and Decision Log 2026-07-20.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

import tiktoken
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from supabase import Client

from app.db import get_client, get_current_style_profile
from app.schemas import AuthorSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["authors"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md"})
# 10 MiB — match Railway's default request body limit.
_MAX_FILE_BYTES: int = 10 * 1024 * 1024
_CHUNK_SIZE: int = 500
_CHUNK_OVERLAP: int = 50


# ---------------------------------------------------------------------------
# ai_pipeline import helper (mirrors passport.py / generate.py)
# ---------------------------------------------------------------------------


def _ensure_ai_pipeline_on_path() -> None:
    """Make monorepo ``ai_pipeline`` importable without an editable install."""
    here = Path(__file__).resolve()
    root = here.parents[3] / "ai_pipeline"
    if root.is_dir() and str(root) not in sys.path:
        sys.path.insert(0, str(root))


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------


def _build_style_profile(author_slug: str, documents: list[str], sb: Client) -> dict[str, Any]:
    """Load spaCy + compute StyleProfile for *author_slug* from document texts.

    Fetches other authors' texts for log-odds comparison when available.
    Separated so tests can patch this without loading ML models.

    NOTE: comparison corpora MUST be built with lemmatize_corpus() — the same
    spaCy-based pipeline used for this author's own lemmas (NOUN/ADJ/ADV,
    alpha-only, len>=3, lowercased lemmas). Using raw .lower() text collapses
    discrimination and produces near-identical distinctive_vocab across authors.
    """
    _ensure_ai_pipeline_on_path()
    import spacy  # type: ignore[import-untyped]

    from autoria_ai.extractor.style_profile import compute_style_profile, lemmatize_corpus

    # Load the model once — reused for both comparison lemmatization below
    # and for compute_style_profile's own spaCy pass.
    nlp = spacy.load("en_core_web_lg")

    comparison: dict[str, str] = {}
    try:
        others = sb.table("authors").select("id,slug").neq("slug", author_slug).execute()
        for row in others.data or []:
            docs = sb.table("documents").select("raw_text").eq("author_id", row["id"]).execute()
            texts = [d["raw_text"] for d in (docs.data or []) if d.get("raw_text")]
            if texts:
                # lemmatize_corpus applies the same rules as the author's own
                # log-odds bag: spaCy lemmas, NOUN/ADJ/ADV, alpha-only, len>=3.
                comparison[row["slug"]] = lemmatize_corpus(documents=texts, nlp=nlp)
    except Exception:
        logger.exception(
            "comparison corpora fetch failed; continuing with single-author log-odds"
        )

    return compute_style_profile(
        author_slug=author_slug,
        documents=documents,
        nlp=nlp,
        comparison_lemmas=comparison or None,
    )


def _recompute_style_profile(author_uuid: str, author_slug: str, sb: Client) -> None:
    """Compute a real StyleProfile and INSERT into style_profiles.

    Errors are logged but not re-raised: the 202 has already been sent.
    """
    try:
        docs_result = (
            sb.table("documents").select("raw_text").eq("author_id", author_uuid).execute()
        )
        documents = [row["raw_text"] for row in (docs_result.data or []) if row.get("raw_text")]
        if not documents:
            logger.warning(
                "recompute skipped for %s (%s): no documents in corpus",
                author_slug,
                author_uuid,
            )
            return

        profile = _build_style_profile(author_slug, documents, sb)

        canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        row_hash = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

        sb.table("style_profiles").insert(
            {
                "author_id": author_uuid,
                "version": "1.0",
                "json_data": profile,
                "hash": row_hash,
            }
        ).execute()
        logger.info("style_profiles row inserted for author %s (%s)", author_slug, author_uuid)
    except Exception:
        logger.exception("recompute failed for author %s (%s)", author_slug, author_uuid)


def _chunk_and_insert(document_id: str, author_uuid: str, author_id: str, raw_text: str, sb: Client) -> None:
    """Chunk raw_text with tiktoken cl100k_base and insert into chunks table.

    Window: size=500 tokens, overlap=50 tokens.
    embedding is left NULL here; ``_embed_document_chunks`` fills it afterwards.
    """
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(raw_text)

    rows: list[dict] = []
    chunk_index = 0
    step = _CHUNK_SIZE - _CHUNK_OVERLAP
    pos = 0

    while pos < len(tokens):
        end = min(pos + _CHUNK_SIZE, len(tokens))
        chunk_tokens = tokens[pos:end]
        rows.append(
            {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "text": enc.decode(chunk_tokens),
                "token_start": pos,
                "token_end": end,
            }
        )
        chunk_index += 1
        if end == len(tokens):
            break
        pos += step

    if not rows:
        logger.warning("document %s produced zero chunks — raw_text may be empty", document_id)
        return

    try:
        sb.table("chunks").insert(rows).execute()
        logger.info("document %s: inserted %d chunks", document_id, len(rows))
    except Exception:
        logger.exception("chunk insert failed for document %s", document_id)
        return

    _embed_document_chunks(document_id, sb)
    
    # After embedding, automatically trigger the style profile computation
    # so the frontend polling loop eventually detects the author as ready!
    _recompute_style_profile(author_uuid, author_id, sb)


def _embed_document_chunks(document_id: str, sb: Client) -> None:
    """Embed NULL-embedding chunks for *document_id* via sentence-transformers."""
    try:
        result = (
            sb.table("chunks")
            .select("id, text")
            .eq("document_id", document_id)
            .is_("embedding", "null")
            .execute()
        )
        rows = result.data or []
        if not rows:
            return

        _ensure_ai_pipeline_on_path()
        from autoria_ai.embedder import embed_chunks

        embeddings = embed_chunks([r["text"] for r in rows])
        for row, emb in zip(rows, embeddings, strict=False):
            sb.table("chunks").update({"embedding": emb.tolist()}).eq("id", row["id"]).execute()
        logger.info("document %s: embedded %d chunks", document_id, len(rows))
    except Exception:
        logger.exception("embedding backfill failed for document %s", document_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/authors",
    response_model=list[AuthorSummary],
    summary="List authors",
)
async def list_authors() -> list[AuthorSummary]:
    """Return authors from ``public.authors`` with live profile/doc counts."""
    sb = get_client()

    authors_result = sb.table("authors").select("id, name, slug").order("slug").execute()
    authors = authors_result.data or []
    if not authors:
        return []

    docs_result = sb.table("documents").select("author_id").execute()
    doc_counts: dict[str, int] = {}
    for row in docs_result.data or []:
        aid = row["author_id"]
        doc_counts[aid] = doc_counts.get(aid, 0) + 1

    profiles_result = sb.table("style_profiles").select("author_id").execute()
    with_profile = {row["author_id"] for row in (profiles_result.data or [])}

    return [
        AuthorSummary(
            id=row["slug"],
            name=row["name"],
            slug=row["slug"],
            has_style_profile=row["id"] in with_profile,
            n_documents=doc_counts.get(row["id"], 0),
        )
        for row in authors
    ]


@router.get(
    "/authors/{author_id}/style-profile",
    response_model=None,
    summary="Get StyleProfile (Style DNA)",
    operation_id="getAuthorStyleProfile",
    responses={
        404: {"description": "Author unknown or StyleProfile not yet computed"},
    },
)
async def get_author_style_profile(author_id: str) -> JSONResponse:
    """Return the latest StyleProfile v1.0 JSON for *author_id* (slug)."""
    sb = get_client()

    author_result = sb.table("authors").select("id").eq("slug", author_id).maybe_single().execute()
    if author_result.data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Author '{author_id}' not found"},
        )

    author_uuid: str = author_result.data["id"]

    style_profile = get_current_style_profile(sb, author_uuid)
    if style_profile is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"StyleProfile not yet computed for '{author_id}'",
            },
        )

    return JSONResponse(status_code=200, content=style_profile)


@router.post(
    "/authors/{author_id}/documents",
    status_code=202,
    summary="Upload a document to an author's corpus",
    operation_id="uploadAuthorDocument",
    responses={
        400: {"description": "Invalid file type, empty content, or malformed body"},
        404: {"description": "Unknown author_id"},
        413: {"description": "Payload too large"},
    },
)
async def upload_author_document(
    author_id: str,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="Plain-text or Markdown file (.txt, .md)")],
    title: Annotated[str | None, Form(max_length=500)] = None,
) -> JSONResponse:
    """Accept a .txt or .md file, persist a documents row, and enqueue chunking."""
    sb = get_client()

    author_result = sb.table("authors").select("id").eq("slug", author_id).maybe_single().execute()
    
    if author_result is None or getattr(author_result, "data", None) is None:
        # Auto-create the author since they don't exist yet!
        insert_res = sb.table("authors").insert({"name": title or author_id, "slug": author_id}).execute()
        author_uuid = insert_res.data[0]["id"]
    else:
        author_uuid = author_result.data["id"]

    filename: str = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "message": f"Unsupported file type '{ext}'. Only .txt and .md are accepted.",
            },
        )

    raw_bytes = await file.read(_MAX_FILE_BYTES + 1)

    if len(raw_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "payload_too_large",
                "message": f"File exceeds the {_MAX_FILE_BYTES // (1024 * 1024)} MiB limit.",
            },
        )

    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "File is empty."},
        )

    raw_text = raw_bytes.decode("utf-8", errors="replace")

    doc_title = title or (filename.rsplit(".", 1)[0] if "." in filename else filename) or filename

    enc = tiktoken.get_encoding("cl100k_base")
    n_tokens = len(enc.encode(raw_text))

    insert_result = (
        sb.table("documents")
        .insert(
            {
                "author_id": author_uuid,
                "title": doc_title,
                "raw_text": raw_text,
                "n_tokens": n_tokens,
            }
        )
        .execute()
    )
    document_id: str = insert_result.data[0]["id"]

    background_tasks.add_task(_chunk_and_insert, document_id, author_uuid, author_id, raw_text, sb)

    return JSONResponse(
        status_code=202,
        content={"document_id": document_id, "status": "processing"},
    )


@router.post(
    "/authors/{author_id}/style-profile/recompute",
    status_code=202,
    summary="Trigger manual StyleProfile recompute",
    operation_id="recomputeAuthorStyleProfile",
    responses={
        404: {"description": "Unknown author_id"},
        500: {"description": "Unexpected server error"},
    },
)
async def recompute_author_style_profile(
    author_id: str,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """Enqueue an async StyleProfile recompute for *author_id* (slug).

    Returns 202 {status:"computing", estimated_seconds:N} immediately.
    The background task loads the author's documents and calls
    ``compute_style_profile`` before inserting a new ``style_profiles`` row.
    """
    sb = get_client()

    author_result = sb.table("authors").select("id").eq("slug", author_id).maybe_single().execute()
    if author_result.data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Author '{author_id}' not found"},
        )

    author_uuid: str = author_result.data["id"]

    try:
        docs_result = (
            sb.table("documents").select("n_tokens").eq("author_id", author_uuid).execute()
        )
        total_tokens: int = sum(row["n_tokens"] for row in (docs_result.data or []))
    except Exception:
        logger.warning("could not fetch n_tokens for author %s; defaulting to 0", author_id)
        total_tokens = 0

    estimated_seconds: int = max(30, total_tokens // 2000)

    background_tasks.add_task(_recompute_style_profile, author_uuid, author_id, sb)

    return JSONResponse(
        status_code=202,
        content={"status": "computing", "estimated_seconds": estimated_seconds},
    )
