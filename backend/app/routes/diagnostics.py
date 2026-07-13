"""Deploy-verification route — `GET /internal/env-check`.

Reports whether the required deployment secrets (WATSONX_API_KEY,
SUPABASE_URL, SUPABASE_KEY) are injected on the current platform. Returns
booleans only — never secret values — so it is safe to hit against a live
Railway/Vercel deployment to confirm the environment is wired correctly.

This is an internal ops helper and is intentionally NOT part of the locked
public API contract (docs/api_contract.yaml).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import REQUIRED_ENV_VARS, env_report, missing_required

router = APIRouter(prefix="/internal", tags=["diagnostics"])


class EnvCheckResponse(BaseModel):
    """Presence report for required deployment secrets (no values)."""

    all_present: bool = Field(description="True when every required secret is set")
    required: list[str] = Field(description="Names of the secrets that must be injected")
    present: dict[str, bool] = Field(description="Per-secret presence map (name -> is set)")
    missing: list[str] = Field(description="Required secrets that are currently unset")


@router.get(
    "/env-check",
    response_model=EnvCheckResponse,
    summary="Verify required env vars are injected",
)
async def env_check() -> EnvCheckResponse:
    """Confirm the platform injected the secrets the app needs to run."""
    missing = missing_required()
    return EnvCheckResponse(
        all_present=not missing,
        required=list(REQUIRED_ENV_VARS),
        present=env_report(),
        missing=missing,
    )
