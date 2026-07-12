"""AutorIA FastAPI application entrypoint.

Run locally with:  cd backend && uvicorn app.main:app --reload --port 8000
Interactive docs at http://localhost:8000/docs

Implements docs/api_contract.yaml. Sprint 1 scope: `/health` and
`/api/authors`. Remaining endpoints (generation, passports, jwks) land in
later sprints.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.routes import authors, diagnostics, health

# Allowed frontend origins come from AUTORIA_CORS_ORIGINS (see app.config).
# Defaults to the local Next.js dev server; set the Vercel URL in prod.
ALLOWED_ORIGINS = list(settings.cors_origins)

app = FastAPI(
    title="AutorIA API",
    version=__version__,
    description=(
        "REST API for AutorIA — style-conditioned generation and Authorship "
        "Passport verification (EU AI Act Art. 50)."
    ),
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
app.include_router(diagnostics.router)
