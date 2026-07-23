"""Passport verification route — POST /api/passports/verify.

Delegates crypto to ``autoria_ai.passport.verifier`` (offline ES256).
All crypto outcomes are HTTP 200 with VerifyResponse; missing body → 422.

Import of ``autoria_ai`` is deferred so a misconfigured Railway Root Directory
(``backend/`` only, without sibling ``ai_pipeline/``) does not crash uvicorn
at startup — ``/health`` can still pass. Verify then returns a structured
``jwks_unavailable`` error until Root Directory is the monorepo root.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter

import app.config as _cfg
from app.schemas import VerifyError, VerifyRequest, VerifyResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/passports", tags=["passports"])

_verify_passport: Callable[..., Any] | None = None
_import_error: str | None = None


def _ensure_ai_pipeline_on_path() -> None:
    """Make monorepo ``ai_pipeline`` importable without an editable install."""
    # backend/app/routes/passport.py → parents[3] == repo root (sibling of backend/)
    here = Path(__file__).resolve()
    root = here.parents[3] / "ai_pipeline"
    if root.is_dir() and str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _load_verifier() -> Callable[..., Any] | None:
    global _verify_passport, _import_error
    if _verify_passport is not None:
        return _verify_passport
    if _import_error is not None:
        return None
    try:
        _ensure_ai_pipeline_on_path()
        from autoria_ai.passport.verifier import verify_passport as _fn  # noqa: E402

        _verify_passport = _fn
        return _verify_passport
    except ImportError as exc:
        _import_error = str(exc)
        logger.error(
            "autoria_ai not importable (%s). Set Railway Root Directory to the "
            "repo root (empty), not backend/, so ai_pipeline/ is in the image.",
            exc,
        )
        return None


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify an Authorship Passport JWS",
    operation_id="verifyPassport",
    responses={
        400: {"description": "Missing or malformed jws_token"},
        422: {"description": "Request body validation error"},
        500: {"description": "Unexpected server error"},
    },
)
async def verify_passport_route(body: VerifyRequest) -> VerifyResponse:
    """Verify a compact JWS Authorship Passport token offline."""
    verify_fn = _load_verifier()
    if verify_fn is None:
        return VerifyResponse(
            valid=False,
            payload=None,
            errors=[
                VerifyError(
                    code="jwks_unavailable",
                    message=(
                        "Passport verifier package (autoria_ai) is not installed in "
                        "this deploy. Set Railway Root Directory to empty (repo root) "
                        "so ai_pipeline/ is included, then redeploy."
                    ),
                )
            ],
        )

    result = verify_fn(
        body.jws_token,
        public_key_path=_cfg.settings.passport_public_key_path,
        expected_kid=_cfg.settings.passport_kid or "autoria",
    )
    return VerifyResponse(
        valid=result.valid,
        payload=result.payload,
        errors=[VerifyError(code=e.code, message=e.message) for e in result.errors],  # type: ignore[arg-type]
    )
