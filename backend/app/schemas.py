"""Pydantic response models mirroring docs/api_contract.yaml.

These are the wire contract shared with the frontend client (lib/types.ts).
Field names and types MUST stay in sync with the OpenAPI schemas of the same
name. The contract is locked (see docs/api_contract.yaml header) — changing it
requires a 2/3 vote + Decision Log entry.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Mirrors `HealthResponse` — liveness/readiness probe payload."""

    status: Literal["ok", "degraded"] = "ok"
    version: str | None = Field(default=None, description="API semver")
    database: Literal["connected", "disconnected"] | None = Field(
        default=None, description="Optional dependency check"
    )


class AuthorSummary(BaseModel):
    """Mirrors `AuthorSummary` — one entry of the author catalog."""

    id: str = Field(description="Stable author identifier (same as slug for preloaded authors)")
    name: str
    slug: str
    has_style_profile: bool = Field(
        description="True when a StyleProfile v1.0 exists and is served by GET style-profile"
    )
    n_documents: int = Field(ge=0, description="Number of ingested documents in the corpus")


class DocumentUploadAccepted(BaseModel):
    """Mirrors `DocumentUploadAccepted` — 202 response for uploadAuthorDocument.

    Fields MUST match docs/api_contract.yaml §DocumentUploadAccepted exactly.
    """

    document_id: str = Field(description="UUID of the newly created document row")
    status: Literal["processing"] = "processing"
