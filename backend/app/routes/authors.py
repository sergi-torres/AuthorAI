"""Authors routes.

Implements:
  GET  /api/authors                                        — list all authors
  GET  /api/authors/{author_id}/style-profile              — getAuthorStyleProfile
  POST /api/authors/{author_id}/documents                  — uploadAuthorDocument
  POST /api/authors/{author_id}/style-profile/recompute    — recomputeAuthorStyleProfile

The GET handler returns the three preloaded authors as static mocks; once the
DB seed is applied those mocks will be replaced by a live DB query.

The POST /documents handler persists to Supabase synchronously (documents row)
and schedules async chunking (chunks rows) via a FastAPI BackgroundTask.
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
from datetime import UTC, datetime
from typing import Annotated

import tiktoken
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from supabase import Client

from app.db import get_client
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
# Preloaded authors (static mock — replaced by DB query once seed runs)
# ---------------------------------------------------------------------------

_PRELOADED_AUTHORS: list[AuthorSummary] = [
    AuthorSummary(
        id="austen",
        name="Jane Austen",
        slug="austen",
        has_style_profile=False,
        n_documents=4,
    ),
    AuthorSummary(
        id="dickens",
        name="Charles Dickens",
        slug="dickens",
        has_style_profile=False,
        n_documents=4,
    ),
    AuthorSummary(
        id="poe",
        name="Edgar Allan Poe",
        slug="poe",
        has_style_profile=False,
        n_documents=2,
    ),
]


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


def _recompute_style_profile(author_uuid: str, author_slug: str, sb: Client) -> None:
    """Build a stub StyleProfile and INSERT into style_profiles.

    The values are schema-valid placeholders — all numeric features are 0.0,
    semantic_centroid is 768 zeros, embedding_umap_2d is {centroid:[0,0],spread:0}.
    A sha256 hash of the canonical JSON is stored alongside.

    TODO(P2): replace the placeholder dict below with a call to
        compute_style_profile(author_uuid, sb)
    from ai_pipeline once the Sprint 2 extractor is wired in.

    Errors are logged but not re-raised: the 202 has already been sent.
    """
    try:
        computed_at = datetime.now(UTC).isoformat()

        # ------------------------------------------------------------------
        # Stub StyleProfile — satisfies docs/api_contract.yaml §StyleProfile
        # ------------------------------------------------------------------
        profile: dict = {
            "schema_version": "1.0",
            "author_id": author_slug,
            "computed_at": computed_at,
            "corpus_stats": {
                "n_documents": 0,
                "n_tokens": 0,
                "n_sentences": 0,
            },
            "lexical": {
                "mattr_500": 0.0,
                "avg_word_length": 0.0,
                "hapax_ratio": 0.0,
            },
            "syntactic": {
                "avg_sentence_length_tokens": 0.0,
                "std_sentence_length_tokens": 0.0,
                "subordination_ratio": 0.0,
                "passive_voice_ratio": 0.0,
                "noun_to_verb_ratio": 0.0,
            },
            "stylistic": {
                "punct_distribution": {
                    ",": 0.0,
                    ".": 0.0,
                    ";": 0.0,
                    ":": 0.0,
                    "—": 0.0,
                    "?": 0.0,
                    "!": 0.0,
                    '"': 0.0,
                },
                "pos_distribution": {
                    "NOUN": 0.0,
                    "VERB": 0.0,
                    "ADJ": 0.0,
                    "ADV": 0.0,
                    "DET": 0.0,
                    "ADP": 0.0,
                    "PRON": 0.0,
                    "CONJ": 0.0,
                    "SCONJ": 0.0,
                    "OTHER": 0.0,
                },
                "dialogue_ratio": 0.0,
                "first_person_ratio": 0.0,
            },
            "distinctive_vocab": [],
            # 768 zeros — real centroid computed by P2 sentence-transformers
            "semantic_centroid": [0.0] * 768,
            # UMAP placeholder — real projection computed by P2 UMAP fit
            "embedding_umap_2d": {"centroid": [0.0, 0.0], "spread": 0.0},
        }

        canonical = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()
        profile_hash = "sha256:" + hashlib.sha256(canonical).hexdigest()

        sb.table("style_profiles").insert(
            {
                "author_id": author_uuid,
                "version": "1.0",
                "json_data": profile,
                "hash": profile_hash,
            }
        ).execute()
        logger.info("style_profiles stub inserted for author %s (%s)", author_slug, author_uuid)
    except Exception:
        logger.exception("recompute stub failed for author %s (%s)", author_slug, author_uuid)


def _chunk_and_insert(document_id: str, raw_text: str, sb: Client) -> None:
    """Chunk raw_text with tiktoken cl100k_base and insert into chunks table.

    Window: size=500 tokens, overlap=50 tokens.
    chunk_index is 0-based sequential — satisfies UNIQUE(document_id, chunk_index).
    embedding is left NULL (filled by a later async embedding job, out of scope).

    Errors are logged but not re-raised: the 202 has already been sent.
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
                # embedding intentionally omitted — column is nullable
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/authors",
    response_model=list[AuthorSummary],
    summary="List authors",
)
async def list_authors() -> list[AuthorSummary]:
    """Return all authors (3 preloaded + any added via document upload)."""
    return _PRELOADED_AUTHORS


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
    """Return the latest StyleProfile v1.0 JSON for *author_id* (slug).

    Resolves the slug to an authors.id UUID, then fetches the single
    style_profiles row with the greatest computed_at.  The stored json_data
    is returned verbatim — no re-serialisation through a Pydantic model.

    404 is raised for both an unknown author slug and an author that exists
    but has no computed profile yet (error: "not_found" in both cases,
    per docs/api_contract.yaml §getAuthorStyleProfile).
    """
    sb = get_client()

    # ------------------------------------------------------------------
    # 1. Resolve slug → UUID  (same pattern as upload_author_document)
    # ------------------------------------------------------------------
    author_result = sb.table("authors").select("id").eq("slug", author_id).maybe_single().execute()
    if author_result.data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Author '{author_id}' not found"},
        )

    author_uuid: str = author_result.data["id"]

    # ------------------------------------------------------------------
    # 2. Fetch latest style_profiles row  (max computed_at via ORDER+LIMIT)
    # ------------------------------------------------------------------
    profile_result = (
        sb.table("style_profiles")
        .select("json_data")
        .eq("author_id", author_uuid)
        .order("computed_at", desc=True)
        .limit(1)
        .execute()
    )
    if not profile_result.data:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"StyleProfile not yet computed for '{author_id}'",
            },
        )

    return JSONResponse(status_code=200, content=profile_result.data[0]["json_data"])


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
    """Accept a .txt or .md file, persist a documents row, and enqueue chunking.

    Returns 202 {document_id, status:"processing"} immediately.
    Chunking runs asynchronously in a BackgroundTask.
    """
    sb = get_client()

    # ------------------------------------------------------------------
    # 1. Validate author exists in DB (404 guard + resolve UUID for FK)
    # ------------------------------------------------------------------
    author_result = sb.table("authors").select("id").eq("slug", author_id).maybe_single().execute()
    if author_result.data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Author '{author_id}' not found"},
        )

    author_uuid: str = author_result.data["id"]

    # ------------------------------------------------------------------
    # 2. Validate file extension
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 3. Read and validate content
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 4. Resolve title (default = filename without extension)
    # ------------------------------------------------------------------
    doc_title = title or (filename.rsplit(".", 1)[0] if "." in filename else filename) or filename

    # ------------------------------------------------------------------
    # 5. Count tokens (synchronous — cheap enough to block on)
    # ------------------------------------------------------------------
    enc = tiktoken.get_encoding("cl100k_base")
    n_tokens = len(enc.encode(raw_text))

    # ------------------------------------------------------------------
    # 6. Insert documents row and read back generated UUID
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 7. Schedule async chunking (202 already committed after return)
    # ------------------------------------------------------------------
    background_tasks.add_task(_chunk_and_insert, document_id, raw_text, sb)

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
    The background task inserts a stub-valid StyleProfile row; it will be
    replaced by the real P2 compute_style_profile entrypoint in Sprint 2.

    estimated_seconds heuristic: sum author's documents.n_tokens, then
    max(30, n_tokens // 2000).  Fetching n_tokens is one cheap SELECT with
    client-side aggregation — no SQL aggregate needed.  Falls back to 30 if
    the documents table is empty or the query fails.
    """
    sb = get_client()

    # ------------------------------------------------------------------
    # 1. Resolve slug → UUID  (404 guard — same pattern as upload)
    # ------------------------------------------------------------------
    author_result = sb.table("authors").select("id").eq("slug", author_id).maybe_single().execute()
    if author_result.data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Author '{author_id}' not found"},
        )

    author_uuid: str = author_result.data["id"]

    # ------------------------------------------------------------------
    # 2. Estimate wall-clock seconds from corpus token count
    # ------------------------------------------------------------------
    try:
        docs_result = (
            sb.table("documents").select("n_tokens").eq("author_id", author_uuid).execute()
        )
        total_tokens: int = sum(row["n_tokens"] for row in (docs_result.data or []))
    except Exception:
        logger.warning("could not fetch n_tokens for author %s; defaulting to 0", author_id)
        total_tokens = 0

    estimated_seconds: int = max(30, total_tokens // 2000)

    # ------------------------------------------------------------------
    # 3. Schedule async recompute and return 202
    # ------------------------------------------------------------------
    background_tasks.add_task(_recompute_style_profile, author_uuid, author_id, sb)

    return JSONResponse(
        status_code=202,
        content={"status": "computing", "estimated_seconds": estimated_seconds},
    )
