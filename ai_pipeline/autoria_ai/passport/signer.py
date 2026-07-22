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
    return load_pem_private_key(pem, password=None)


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
    resolved_kid = kid or os.getenv("PASSPORT_KID") or "autoria"
    key = private_key if private_key is not None else _load_private_key(private_key_path)
    payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return jose_jws.sign(
        payload_bytes,
        key,
        headers={"kid": resolved_kid, "typ": _TYP},
        algorithm=_ALG,
    )
