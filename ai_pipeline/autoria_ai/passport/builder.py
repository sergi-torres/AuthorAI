"""Build an Authorship Passport JSON payload (schema_version 1.0).

This module is the *only* place that hashes raw content (prompt, output,
snippets, StyleProfile).  The returned dict contains **hashes only** — no raw
text ever escapes this module.

Canonical JSON for the StyleProfile hash (docs/passport_schema.md §5):
    json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
# CANONICAL — the style-profile extractor that stores ``style_profiles.hash``
# in the DB MUST use the identical call, or the hashes will not match.

Public API
----------
build_passport(...)  → dict                    payload only (no signing)
issue_passport(...)  → {jws_token, json_payload}  build + sign (PassportEnvelope)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from autoria_ai.passport.signer import sign_passport

# Fix #1: pattern used to validate pre-computed style_profile_hash values.
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    """Return ``sha256:<lowercase-hex>`` of *text* (UTF-8 encoded).

    Accepts only ``str``.  Raises ``TypeError`` on any other type so that a
    bytes/str confusion is caught at call time rather than producing a silent
    hash mismatch.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _canonical_hash(obj: dict[str, Any]) -> str:
    """Return ``sha256:<hex>`` of the canonical JSON serialisation of *obj*.

    Canonical form: UTF-8, keys sorted lexicographically, no insignificant
    whitespace.  Mirrors the call in the style-profile extractor exactly.
    # CANONICAL — see docs/passport_schema.md §5.

    Fix #4: a JSON round-trip normalises numpy/Decimal scalars to JSON-native
    Python types before canonicalisation, preventing hash drift when the
    StyleProfile is retrieved from Postgres/PostgREST (which may serialise
    floats differently than the extractor).  The round-trip is a no-op for
    dicts that are already JSON-safe.
    """
    # Normalise to JSON-native types; raises TypeError for non-serialisable
    # objects (e.g. bare numpy arrays), surfacing the problem at issuance time.
    try:
        normalised = json.loads(json.dumps(obj, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "style_profile contains a value that cannot be serialised to JSON "
            f"({type(exc).__name__}); ensure all values are JSON-native types"
        ) from None
    canonical = json.dumps(normalised, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256(canonical)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_passport(
    *,
    # Author / voice
    author_id: str,
    style_profile: dict[str, Any] | None = None,
    style_profile_hash: str | None = None,
    style_profile_version: str = "1.0",
    # Generation
    model_id: str,
    model_provider: str = "ibm/watsonx",
    user_prompt: str,
    output_text: str,
    output_length_tokens: int,
    # RAG
    rag_sources: list[dict[str, Any]] | None = None,
    # Scoring
    fit_score: int,
    # Optional contribution note
    contribution_note: str | None = None,
    # Optional overrides (mostly for tests / idempotent re-issuance)
    passport_id: str | None = None,
    generated_at: str | None = None,
    # Verifier URL (falls back to env)
    verifier_url: str | None = None,
) -> dict[str, Any]:
    """Return a schema v1.0 Passport payload dict.

    Raw strings (``user_prompt``, ``output_text``, snippet texts inside
    ``rag_sources``) are hashed here and **never stored** in the returned dict.

    Parameters
    ----------
    author_id:
        Author slug (e.g. ``"dickens"``).
    style_profile:
        The raw StyleProfile dict.  Exactly one of *style_profile* or
        *style_profile_hash* must be supplied.
    style_profile_hash:
        Pre-computed hash in ``sha256:<hex>`` form.  Use when the caller
        already holds the stored DB hash and the full profile is unavailable.
    style_profile_version:
        ``schema_version`` of the StyleProfile (default ``"1.0"``).
    model_id:
        Watsonx model identifier, e.g. ``"meta-llama/llama-3-3-70b-instruct"``.
    model_provider:
        Fixed ``"ibm/watsonx"`` for July; overridable for tests.
    user_prompt:
        The raw user prompt string — hashed here, not stored.
    output_text:
        The generated text — hashed here, not stored.
    output_length_tokens:
        Token count of the generated output (non-negative integer).
    rag_sources:
        List of dicts with keys ``doc_id`` (str), ``chunk_id`` (int), and
        ``snippet_text`` (str, raw — hashed here, not stored).  May be empty
        or ``None`` (treated as empty list).
    fit_score:
        Style-fit score in ``[0, 100]``.
    contribution_note:
        Optional free-text clarification for the ``contribution`` block.
    passport_id:
        UUID v4 string.  Generated fresh if omitted.
    generated_at:
        ISO-8601 UTC timestamp ending in ``Z``.  Set to ``now()`` if omitted.
    verifier_url:
        URL placed in ``payload.verifier_url``.  Falls back to the
        ``PASSPORT_VERIFIER_URL`` environment variable.  Omitted from the
        payload when neither is set (field is optional in the schema).
    """
    # --- Input validation ---------------------------------------------------
    if not isinstance(fit_score, int) or not (0 <= fit_score <= 100):
        raise ValueError("fit_score must be an integer in [0, 100]")

    if output_length_tokens < 0:
        raise ValueError("output_length_tokens must be non-negative")

    if (style_profile is None) == (style_profile_hash is None):
        raise ValueError(
            "Provide exactly one of style_profile (raw dict) or "
            "style_profile_hash (pre-computed sha256:<hex>)"
        )

    # Fix #1: validate pre-computed hash format before it reaches the payload.
    if style_profile_hash is not None and not _HASH_RE.match(style_profile_hash):
        raise ValueError("style_profile_hash must be in the form sha256:<64 lowercase hex chars>")

    # Fix #2: validate caller-supplied overrides before they reach the payload.
    if passport_id is not None:
        try:
            parsed = uuid.UUID(passport_id)
            if parsed.version != 4:
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError("passport_id must be a valid UUID v4 string") from None
    if generated_at is not None:
        if not generated_at.endswith("Z"):
            raise ValueError("generated_at must be an ISO-8601 UTC timestamp ending in 'Z'")
        try:
            datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("generated_at is not a valid ISO-8601 timestamp") from None

    # --- Hashing ------------------------------------------------------------
    computed_style_hash: str = (
        _canonical_hash(style_profile)
        if style_profile is not None
        else style_profile_hash  # type: ignore[assignment]
    )

    computed_prompt_hash: str = _sha256(user_prompt)
    computed_output_hash: str = _sha256(output_text)

    hashed_rag: list[dict[str, Any]] = []
    for src in rag_sources or []:
        hashed_rag.append(
            {
                "doc_id": src["doc_id"],
                "chunk_id": src["chunk_id"],
                "snippet_hash": _sha256(src["snippet_text"]),
            }
        )

    # --- Metadata -----------------------------------------------------------
    pid = passport_id or str(uuid.uuid4())
    ts = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    resolved_verifier_url: str | None = verifier_url or os.getenv("PASSPORT_VERIFIER_URL")

    # --- Assemble payload ---------------------------------------------------
    contribution: dict[str, Any] = {"human_pct": 0, "ai_pct": 100}
    if contribution_note is not None:
        contribution["note"] = contribution_note

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "passport_id": pid,
        "generated_at": ts,
        "author_voice": {
            "id": author_id,
            "style_profile_hash": computed_style_hash,
            "style_profile_version": style_profile_version,
        },
        "generation": {
            "model_provider": model_provider,
            "model_id": model_id,
            "user_prompt_hash": computed_prompt_hash,
            "output_hash": computed_output_hash,
            "output_length_tokens": output_length_tokens,
        },
        "rag_sources": hashed_rag,
        "contribution": contribution,
        "fit_score": fit_score,
    }

    if resolved_verifier_url is not None:
        payload["verifier_url"] = resolved_verifier_url

    return payload


def issue_passport(
    *,
    # Forwarded verbatim to build_passport — see its docstring for full details.
    author_id: str,
    style_profile: dict[str, Any] | None = None,
    style_profile_hash: str | None = None,
    style_profile_version: str = "1.0",
    model_id: str,
    model_provider: str = "ibm/watsonx",
    user_prompt: str,
    output_text: str,
    output_length_tokens: int,
    rag_sources: list[dict[str, Any]] | None = None,
    fit_score: int,
    contribution_note: str | None = None,
    passport_id: str | None = None,
    generated_at: str | None = None,
    verifier_url: str | None = None,
    # Signing — forwarded to sign_passport; resolved from env when omitted.
    private_key_path: str | None = None,
    kid: str | None = None,
) -> dict[str, Any]:
    """Build and sign an Authorship Passport.

    Returns a ``PassportEnvelope`` dict matching ``api_contract.yaml``::

        {
            "jws_token":   "<compact JWS>",   # ES256, alg/typ/kid in header
            "json_payload": { … }             # decoded passport payload v1.0
        }

    The private key is loaded from *private_key_path* or the
    ``PASSPORT_PRIVATE_KEY_PATH`` environment variable.  The key is **never**
    returned, logged, or included in any exception message raised here.
    """
    json_payload = build_passport(
        author_id=author_id,
        style_profile=style_profile,
        style_profile_hash=style_profile_hash,
        style_profile_version=style_profile_version,
        model_id=model_id,
        model_provider=model_provider,
        user_prompt=user_prompt,
        output_text=output_text,
        output_length_tokens=output_length_tokens,
        rag_sources=rag_sources,
        fit_score=fit_score,
        contribution_note=contribution_note,
        passport_id=passport_id,
        generated_at=generated_at,
        verifier_url=verifier_url,
    )
    jws_token = sign_passport(
        json_payload,
        private_key_path=private_key_path,
        kid=kid,
    )
    return {"jws_token": jws_token, "json_payload": json_payload}
