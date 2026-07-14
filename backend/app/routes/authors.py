"""Authors routes.

Implements:
  GET  /api/authors                          — list all authors
  GET  /api/authors/{author_id}/style-profile — getAuthorStyleProfile (operationId)
  POST /api/authors/{author_id}/documents    — uploadAuthorDocument (operationId)

The GET handler returns the three preloaded authors as static mocks; once the
DB seed is applied those mocks will be replaced by a live DB query.

The POST handler persists to Supabase synchronously (documents row) and
schedules async chunking (chunks rows) via a FastAPI BackgroundTask.
Contract: 202 {document_id, status:"processing"} — see docs/api_contract.yaml
§DocumentUploadAccepted and Decision Log 2026-07-13.
"""

from __future__ import annotations

import logging
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
    author_result = (
        sb.table("authors").select("id").eq("slug", author_id).maybe_single().execute()
    )
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
