"""JWKS endpoint — GET /.well-known/jwks.json.

Serves the EC P-256 public key as a standard JWK Set (RFC 7517) so that any
verifier can check Authorship Passport signatures **offline**, without calling
back to our servers.

Security invariants enforced here:
- Only the public key is ever read (PASSPORT_PUBLIC_KEY_PATH).
- The private key is never touched by this module.
- If the key file is absent or PASSPORT_PUBLIC_KEY_PATH is unset → 500; we
  never silently serve an empty key set (that would make all signatures
  unverifiable without error).
- The `d` (private scalar) field is never present in the response; ensured by
  using `cryptography`'s `public_key().public_bytes()` path rather than
  serializing a private key.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import APIRouter
from fastapi.responses import JSONResponse

import app.config as _cfg
from app.schemas import JsonWebKey, JwksDocument

logger = logging.getLogger(__name__)

router = APIRouter(tags=["crypto"])

# Cache-Control TTL matches the spec (§7) and api_contract.yaml example.
_CACHE_CONTROL = "public, max-age=3600"


def _b64url(n: int, byte_length: int) -> str:
    """Encode an integer as a big-endian base64url string of `byte_length` bytes."""
    return base64.urlsafe_b64encode(n.to_bytes(byte_length, "big")).rstrip(b"=").decode()


def _load_public_jwk() -> JsonWebKey:
    """Load the EC P-256 public key from PASSPORT_PUBLIC_KEY_PATH and return a JWK.

    Raises RuntimeError (→ 500) if the env var is unset or the file is missing.
    Never logs key material.
    """
    path = _cfg.settings.passport_public_key_path
    kid = _cfg.settings.passport_kid or "autoria"

    if not path:
        raise RuntimeError("PASSPORT_PUBLIC_KEY_PATH is not configured")

    if not os.path.isfile(path):
        # Log the path (not the content) to assist ops debugging.
        logger.error("Public key file not found: %s", path)
        raise RuntimeError("Public key file not found")

    try:
        key = load_pem_public_key(Path(path).read_bytes())
    except Exception as exc:
        # exc message may include path details but never key material.
        logger.error("Failed to load public key from %s: %s", path, type(exc).__name__)
        raise RuntimeError("Failed to parse public key") from exc

    if not isinstance(key, EllipticCurvePublicKey):
        raise RuntimeError("Key at PASSPORT_PUBLIC_KEY_PATH is not an EC public key")

    pub_numbers = key.public_numbers()
    # P-256 coordinates are 32 bytes each.
    return JsonWebKey(
        kty="EC",
        crv="P-256",
        x=_b64url(pub_numbers.x, 32),
        y=_b64url(pub_numbers.y, 32),
        use="sig",
        alg="ES256",
        kid=kid,
    )


@router.get(
    "/.well-known/jwks.json",
    response_model=JwksDocument,
    summary="JSON Web Key Set (public signing keys)",
    operation_id="getJwks",
)
async def get_jwks() -> JSONResponse:
    """Return the EC P-256 public key as a JWKS (RFC 7517).

    ``Cache-Control: public, max-age=3600`` is set unconditionally so CDNs and
    verifier clients cache the key for one hour — matching §7 of the spec.
    """
    jwk = _load_public_jwk()
    body = JwksDocument(keys=[jwk])
    return JSONResponse(
        content=body.model_dump(),
        headers={"Cache-Control": _CACHE_CONTROL},
    )
