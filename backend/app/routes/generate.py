"""Generation route — POST /api/generate.

Implements docs/api_contract.yaml §generateText (issue #25).

HTTP concerns only:
  1. Parse + validate GenerateRequest (Pydantic; 422 on bad input).
  2. Resolve author slug → UUID + latest StyleProfile from Supabase.
  3. Delegate to ai_pipeline orchestrator (generator.orchestrate).
  4. Persist the issued passport to public.passports.
  5. Map WatsonxError → 503; not_found → 404.

The orchestrator (autoria_ai.generator) is imported via the same deferred
sys.path helper used by passport.py so a misconfigured Railway deploy
(backend-only Root Directory) can still serve /health without crashing.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db import get_client
from app.schemas import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generation"])

# ---------------------------------------------------------------------------
# ai_pipeline path helper — mirrors passport.py exactly
# ---------------------------------------------------------------------------

_ORCHESTRATE_FN: Any = None
_IMPORT_ERROR: str | None = None

# Model identifier — overridable via environment variable.
_MODEL_ID: str = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")


def _ensure_ai_pipeline_on_path() -> None:
    """Prepend the monorepo ``ai_pipeline`` directory to ``sys.path``.

    backend/app/routes/generate.py → parents[3] == repo root.
    """
    here = Path(__file__).resolve()
    root = here.parents[3] / "ai_pipeline"
    if root.is_dir() and str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _load_orchestrator() -> Any | None:
    """Return the ``orchestrate`` callable, importing it on first call."""
    global _ORCHESTRATE_FN, _IMPORT_ERROR
    if _ORCHESTRATE_FN is not None:
        return _ORCHESTRATE_FN
    if _IMPORT_ERROR is not None:
        return None
    try:
        _ensure_ai_pipeline_on_path()
        from autoria_ai.generator import orchestrate  # type: ignore[import-untyped]

        _ORCHESTRATE_FN = orchestrate
        return _ORCHESTRATE_FN
    except ImportError as exc:
        _IMPORT_ERROR = str(exc)
        logger.error(
            "autoria_ai not importable (%s). "
            "Set Railway Root Directory to the repo root so ai_pipeline/ is in the image.",
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate vanilla and AutorIA outputs",
    operation_id="generateText",
    responses={
        404: {"description": "Author not found or StyleProfile missing"},
        503: {"description": "LLM provider unavailable or timeout"},
    },
)
async def generate_text(body: GenerateRequest) -> GenerateResponse:
    """Run two parallel Watsonx calls, score both, mint Authorship Passport.

    Target P95 latency < 8 s (docs/MVP.md §4.3).

    Steps:
    1. Resolve author slug → UUID.
    2. Load latest StyleProfile from style_profiles.
    3. Delegate to autoria_ai.generator.orchestrate (RAG + generation + scoring
       + passport issuance).
    4. Persist the issued passport to public.passports.
    5. Return GenerateResponse.
    """
    # ------------------------------------------------------------------
    # 1. Resolve slug → UUID  (same pattern as authors.py get_style_profile)
    # ------------------------------------------------------------------
    sb = get_client()

    author_result = (
        sb.table("authors").select("id").eq("slug", body.author_id).maybe_single().execute()
    )
    if author_result.data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Author '{body.author_id}' not found"},
        )

    author_uuid: str = author_result.data["id"]

    # ------------------------------------------------------------------
    # 2. Fetch latest StyleProfile  (same ORDER+LIMIT pattern as authors.py)
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
                "message": f"StyleProfile not yet computed for '{body.author_id}'",
            },
        )

    style_profile: dict[str, Any] = profile_result.data[0]["json_data"]

    # ------------------------------------------------------------------
    # 3. Delegate to the orchestrator
    # ------------------------------------------------------------------
    orchestrate = _load_orchestrator()
    if orchestrate is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "service_unavailable",
                "message": (
                    "AI pipeline package is not installed in this deploy. "
                    "Set Railway Root Directory to empty (repo root) and redeploy."
                ),
            },
        )

    try:
        # Import here so the name is available for the except clause below;
        # the module is already cached by _load_orchestrator's sys.path setup.
        from app.services.watsonx_client import WatsonxError

        from app.config import settings

        result: dict[str, Any] = await orchestrate(
            prompt=body.prompt,
            style_profile=style_profile,
            author_id=body.author_id,
            author_uuid=author_uuid,
            model_id=_MODEL_ID,
            verifier_url=settings.passport_verifier_url,
        )
    except WatsonxError as exc:
        logger.warning("Watsonx generation failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "service_unavailable",
                "message": "Generation timed out or LLM provider is unavailable; retry later.",
            },
        ) from exc

    # ------------------------------------------------------------------
    # 4. Persist passport to public.passports
    # ------------------------------------------------------------------
    passport_envelope: dict[str, Any] = result["passport"]
    try:
        sb.table("passports").insert(
            {
                "author_id": author_uuid,
                "json_data": passport_envelope["json_payload"],
                "jws_token": passport_envelope["jws_token"],
            }
        ).execute()
    except Exception:
        # Persistence failure must not abort the response — the passport was
        # already issued and the client receives it regardless.
        logger.exception(
            "Failed to persist passport to DB for author '%s'; "
            "passport was still issued and returned to caller.",
            body.author_id,
        )

    # ------------------------------------------------------------------
    # 5. Return GenerateResponse
    # ------------------------------------------------------------------
    return GenerateResponse(**result)
