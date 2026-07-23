"""Sign an Authorship Passport payload as a compact JWS (ES256)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from jose import jws as jose_jws

_TYP = "passport+jws"
_ALG = "ES256"


def _load_private_key(path: str | Path | None = None):
    key_path = path or os.getenv("PASSPORT_PRIVATE_KEY_PATH")
    if not key_path:
        raise RuntimeError("PASSPORT_PRIVATE_KEY_PATH is not configured")
    pem = Path(key_path).read_bytes()
    # Fix #3: wrap cryptography errors with `from None` so the raw PEM bytes
    # never appear in __cause__/__context__ or in log traces.
    try:
        return load_pem_private_key(pem, password=None)
    except Exception:
        raise RuntimeError("Failed to load private key (check key file format)") from None


def sign_passport(
    payload: dict[str, Any],
    *,
    private_key_path: str | Path | None = None,
    kid: str | None = None,
    private_key=None,
) -> str:
    """Return a compact JWS over *payload*.

    Header: ``{alg: ES256, typ: passport+jws, kid}``.
    Payload bytes are canonical compact JSON (no JWT claims wrapping).
    """
    # Fix #5: kid is security-critical; a silent fallback to a generic string
    # produces tokens that pass local verify but are rejected by any external
    # JWKS consumer whose key was generated with a real kid.
    resolved_kid = kid or os.getenv("PASSPORT_KID")
    if not resolved_kid:
        raise RuntimeError(
            "PASSPORT_KID is not configured; refusing to sign without a key id"
        )
    key = private_key if private_key is not None else _load_private_key(private_key_path)
    payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return jose_jws.sign(
        payload_bytes,
        key,
        headers={"kid": resolved_kid, "typ": _TYP},
        algorithm=_ALG,
    )
