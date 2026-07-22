"""Passport verification route — POST /api/passports/verify.

Delegates crypto to ``autoria_ai.passport.verifier`` (offline ES256).
All crypto outcomes are HTTP 200 with VerifyResponse; missing body → 422.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter

import app.config as _cfg
from app.schemas import VerifyError, VerifyRequest, VerifyResponse

# Make monorepo ai_pipeline importable when backend is run without an editable
# install of autoria-ai (local uvicorn / pytest).
_AI_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "ai_pipeline"
if _AI_PIPELINE_ROOT.is_dir() and str(_AI_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_PIPELINE_ROOT))

from autoria_ai.passport.verifier import verify_passport  # noqa: E402

router = APIRouter(prefix="/api/passports", tags=["passports"])


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
    result = verify_passport(
        body.jws_token,
        public_key_path=_cfg.settings.passport_public_key_path,
        expected_kid=_cfg.settings.passport_kid or "autoria",
    )
    return VerifyResponse(
        valid=result.valid,
        payload=result.payload,
        errors=[VerifyError(code=e.code, message=e.message) for e in result.errors],  # type: ignore[arg-type]
    )
