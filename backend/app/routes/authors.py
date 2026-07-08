"""Authors route — `GET /api/authors`.

Sprint 1 stub: returns the three preloaded authors (Austen, Dickens, Poe) as
static mock data. Once the DB layer lands this will read from the `authors`
table; the response shape (AuthorSummary) stays identical.

`has_style_profile` is False for all three because StyleProfiles are not
computed yet at this stage (matches the "style profile not ready" state).
`n_documents` reflects the corpus files currently shipped under corpus/.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import AuthorSummary

router = APIRouter(prefix="/api", tags=["authors"])

# Preloaded authors — see docs/decision_log.md and docs/MVP.md §6.
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


@router.get(
    "/authors",
    response_model=list[AuthorSummary],
    summary="List authors",
)
async def list_authors() -> list[AuthorSummary]:
    """Return all authors (3 preloaded + any added via document upload)."""
    return _PRELOADED_AUTHORS
