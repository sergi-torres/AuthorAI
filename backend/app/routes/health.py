"""Health check route — `GET /health`.

Used by Railway/Vercel deploy probes and local smoke tests
(see docs/api_contract.yaml → operationId getHealth).
"""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    responses={503: {"description": "Service degraded (e.g. database unreachable)"}},
)
async def get_health() -> HealthResponse:
    """Return `200 {"status": "ok"}` while the service is up.

    No dependency checks yet (no DB wired in Sprint 1); `database` is omitted
    until the Postgres/pgvector layer lands.
    """
    return HealthResponse(status="ok", version=__version__)
