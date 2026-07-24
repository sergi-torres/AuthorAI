"""AutorIA FastAPI application entrypoint.

Run locally with:  cd backend && uvicorn app.main:app --reload --port 8000
Interactive docs at http://localhost:8000/docs

Implements docs/api_contract.yaml.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.routes import authors, diagnostics, generate, health, jwks, passport

logger = logging.getLogger(__name__)

# Allowed frontend origins come from AUTORIA_CORS_ORIGINS (see app.config).
# Defaults to the local Next.js dev server; set the Vercel URL in prod.
ALLOWED_ORIGINS = list(settings.cors_origins)


def _warmup_generation_stack() -> None:
    """Eager-load ai_pipeline generator models so the first /api/generate is warm.

    Failures are logged but do not abort startup — /health must stay up even
    when spaCy / sentence-transformers are missing in a slim deploy image.

    Set ``AUTORIA_SKIP_MODEL_WARMUP=1`` to skip (unit tests / slim CI images).
    """
    import os

    if os.getenv("AUTORIA_SKIP_MODEL_WARMUP", "").strip() in {"1", "true", "yes"}:
        logger.info("Skipping generation model warmup (AUTORIA_SKIP_MODEL_WARMUP).")
        return

    orchestrate = generate._load_orchestrator()
    if orchestrate is None:
        logger.warning("Skipping generation warmup: autoria_ai.generator not importable.")
        return
    try:
        from autoria_ai.generator import warmup_models

        logger.info("Warming up generation NLP models ...")
        warmup_models()
        logger.info("Generation NLP models ready.")
    except Exception:
        logger.exception("Generation model warmup failed; first /api/generate may be slow or 503.")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _warmup_generation_stack()
    yield


app = FastAPI(
    title="AutorIA API",
    version=__version__,
    description=(
        "REST API for AutorIA — style-conditioned generation and Authorship "
        "Passport verification (EU AI Act Art. 50)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(authors.router)
app.include_router(generate.router)
app.include_router(diagnostics.router)
app.include_router(jwks.router)
app.include_router(passport.router)
