"""Resolve Passport signing/verification keys from the environment or disk.

Why this exists
---------------
The signing keys live in `keys/` as PEM files, and `.gitignore` excludes
`keys/**` and `*.pem` — correctly, since the private key must never be
committed. But Railway and Vercel deploy from the repository: the PEM files
simply are not there, so a path-only lookup resolves to nothing in production.
The visible symptom is `/.well-known/jwks.json` answering 500 and
`POST /api/generate` failing to sign, which is the demo's centrepiece.

Platform dashboards inject *values*, not files, so this module accepts the PEM
content directly through `PASSPORT_PRIVATE_KEY_PEM` / `PASSPORT_PUBLIC_KEY_PEM`
and keeps the existing `*_PATH` variables working unchanged for local
development.

Precedence is explicit-argument → `*_PEM` → `*_PATH`. The PEM variable wins
over the path because it is the production signal: an image that happens to
ship a stale key file must not silently outrank the key the operator set in the
dashboard.

Never log the return value of anything here.
"""

from __future__ import annotations

import os
from pathlib import Path

# A PEM pasted into a dashboard field often arrives with literal backslash-n
# instead of real newlines (shells, .env files and some CI UIs escape them).
# `load_pem_*` rejects that with a parse error that says nothing useful, so we
# normalise before handing the bytes over.
_ESCAPED_NEWLINE = "\\n"


def _normalise_pem(raw: str) -> bytes:
    text = raw.strip()
    if _ESCAPED_NEWLINE in text and "\n" not in text:
        text = text.replace(_ESCAPED_NEWLINE, "\n")
    return text.encode("utf-8")


def resolve_pem(
    *,
    pem_env: str,
    path_env: str,
    explicit_path: str | Path | None = None,
) -> bytes:
    """Return PEM bytes for a key, or raise RuntimeError naming what is missing.

    Args:
        pem_env: Name of the env var holding the PEM content (production).
        path_env: Name of the env var holding a filesystem path (local dev).
        explicit_path: Caller-supplied path; wins over both env vars.

    Raises:
        RuntimeError: Neither source is configured, or the file is absent.
            The message names the variables to set and never includes key
            material.
    """
    if explicit_path:
        path = Path(explicit_path)
        if not path.is_file():
            raise RuntimeError(f"Key file not found: {path}")
        return path.read_bytes()

    inline = os.getenv(pem_env)
    if inline and inline.strip():
        return _normalise_pem(inline)

    env_path = os.getenv(path_env)
    if env_path:
        path = Path(env_path)
        if not path.is_file():
            raise RuntimeError(f"Key file not found at {path_env}: {path}")
        return path.read_bytes()

    raise RuntimeError(
        f"No key configured: set {pem_env} (PEM content, for deploys) "
        f"or {path_env} (file path, for local development)"
    )
