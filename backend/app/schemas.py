"""Pydantic response models mirroring docs/api_contract.yaml.

These are the wire contract shared with the frontend client (lib/types.ts).
Field names and types MUST stay in sync with the OpenAPI schemas of the same
name. The contract is locked (see docs/api_contract.yaml header) — changing it
requires a 2/3 vote + Decision Log entry.
"""

from __future__ import annotations

from typing import Any, Literal

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


# ---------------------------------------------------------------------------
# Passport / JWKS — mirrors VerifyRequest, VerifyError, VerifyResponse,
# JwksDocument, JsonWebKey in docs/api_contract.yaml.
# ---------------------------------------------------------------------------


class VerifyRequest(BaseModel):
    """Mirrors `VerifyRequest` — compact JWS token to be verified."""

    jws_token: str = Field(
        min_length=1, description="Compact serialized JWS from passport.jws_token"
    )


class VerifyError(BaseModel):
    """Mirrors `VerifyError` — one structured error entry inside VerifyResponse."""

    code: Literal[
        "invalid_token",
        "invalid_signature",
        "unknown_kid",
        "unsupported_algorithm",
        "schema_mismatch",
        "jwks_unavailable",
    ]
    message: str


class VerifyResponse(BaseModel):
    """Mirrors `VerifyResponse` — always HTTP 200 for crypto outcomes."""

    valid: bool
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Decoded passport payload when valid; null otherwise",
    )
    errors: list[VerifyError] = Field(default_factory=list)


class JsonWebKey(BaseModel):
    """Mirrors `JsonWebKey` — one EC P-256 public key in a JWKS."""

    kty: Literal["EC"] = "EC"
    crv: Literal["P-256"] = "P-256"
    x: str = Field(description="Base64url-encoded x coordinate")
    y: str = Field(description="Base64url-encoded y coordinate")
    use: Literal["sig"] = "sig"
    alg: Literal["ES256"] = "ES256"
    kid: str


class JwksDocument(BaseModel):
    """Mirrors `JwksDocument` — RFC 7517 key set served at /.well-known/jwks.json."""

    keys: list[JsonWebKey] = Field(min_length=1)
