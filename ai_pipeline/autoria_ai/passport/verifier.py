"""Offline Authorship Passport verification (normative §8 algorithm).

Error *codes* follow docs/api_contract.yaml VerifyError enums (not the
divergent names in passport_schema.md §8.2).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from jose import JWTError
from jose import jws as jose_jws
from jose.exceptions import JOSEError

_ALLOWED_ALGS = frozenset({"ES256"})
_SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0"})
# Hard cap against oversized-token DoS (compact JWS string length).
MAX_TOKEN_CHARS = 64 * 1024

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "passport.json"


@dataclass(frozen=True)
class VerifyError:
    code: str
    message: str


@dataclass(frozen=True)
class VerifyResult:
    valid: bool
    payload: dict[str, Any] | None = None
    errors: list[VerifyError] = field(default_factory=list)


def _err(code: str, message: str) -> VerifyResult:
    return VerifyResult(valid=False, payload=None, errors=[VerifyError(code=code, message=message)])


def _load_schema() -> dict[str, Any]:
    if not _SCHEMA_PATH.is_file():
        raise RuntimeError(f"passport.json schema not found at {_SCHEMA_PATH}")
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_public_key(
    *,
    public_key_path: str | Path | None = None,
    public_key: EllipticCurvePublicKey | None = None,
) -> EllipticCurvePublicKey:
    if public_key is not None:
        return public_key
    path = public_key_path or os.getenv("PASSPORT_PUBLIC_KEY_PATH")
    if not path:
        raise RuntimeError("PASSPORT_PUBLIC_KEY_PATH is not configured")
    if not Path(path).is_file():
        raise RuntimeError("Public key file not found")
    key = load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, EllipticCurvePublicKey):
        raise RuntimeError("Configured public key is not an EC key")
    return key


def verify_passport(
    token: str,
    *,
    public_key_path: str | Path | None = None,
    public_key: EllipticCurvePublicKey | None = None,
    expected_kid: str | None = None,
    schema: dict[str, Any] | None = None,
) -> VerifyResult:
    """Verify a compact JWS Authorship Passport offline.

    Resolves ``kid`` against the locally configured public key only — never
    trusts ``jku`` / ``jwk`` / ``x5u`` / ``x5c`` from the token header.
    """
    if len(token) > MAX_TOKEN_CHARS:
        return _err("invalid_token", f"Token exceeds {MAX_TOKEN_CHARS} character limit")

    parts = token.split(".")
    if len(parts) != 3:
        return _err(
            "invalid_token",
            "Token is not a compact JWS (expected 3 base64url segments)",
        )

    try:
        header: dict[str, Any] = jose_jws.get_unverified_header(token)
    except (JOSEError, Exception):
        return _err("invalid_token", "Could not decode JWS protected header")

    alg = header.get("alg", "")
    if alg not in _ALLOWED_ALGS:
        return _err(
            "unsupported_algorithm",
            f"Algorithm {alg!r} is not accepted; only ES256 is allowed",
        )

    kid = header.get("kid", "")
    # Fix #5: if neither expected_kid nor PASSPORT_KID is set, fail closed —
    # never accept a token by falling back to a hardcoded kid string.
    configured_kid = expected_kid or os.getenv("PASSPORT_KID")
    if not configured_kid:
        return _err("unknown_kid", "No PASSPORT_KID configured; cannot resolve key")
    if kid != configured_kid:
        return _err("unknown_kid", f"kid {kid!r} is not in the key set")

    try:
        key = _load_public_key(public_key_path=public_key_path, public_key=public_key)
    except RuntimeError:
        return _err("jwks_unavailable", "Could not load the public key for verification")

    try:
        payload_bytes: bytes = jose_jws.verify(token, key, algorithms=["ES256"])
    except (JWTError, JOSEError, Exception):
        return _err("invalid_signature", "ES256 signature verification failed")

    try:
        payload: dict[str, Any] = json.loads(payload_bytes)
    except Exception:
        return _err("invalid_token", "Payload is not valid JSON")

    try:
        passport_schema = schema if schema is not None else _load_schema()
    except RuntimeError:
        return _err("schema_mismatch", "Server-side schema unavailable")

    # Fix #2: pass FormatChecker so format:uuid and format:date-time constraints
    # are enforced as errors, not silently ignored (Draft 2020-12 default).
    validator = jsonschema.Draft202012Validator(
        passport_schema,
        format_checker=jsonschema.FormatChecker(),
    )
    schema_errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if schema_errors:
        offending = "; ".join(
            f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
            for e in schema_errors[:5]
        )
        return _err("schema_mismatch", f"Payload does not match schema: {offending}")

    sv = payload.get("schema_version", "")
    if sv not in _SUPPORTED_SCHEMA_VERSIONS:
        return _err(
            "schema_mismatch",
            f"schema_version {sv!r} is not supported; "
            f"supported: {sorted(_SUPPORTED_SCHEMA_VERSIONS)}",
        )

    return VerifyResult(valid=True, payload=payload, errors=[])
