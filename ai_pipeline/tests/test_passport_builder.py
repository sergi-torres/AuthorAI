"""Tests for passport builder.py — build_passport and issue_passport.

Covers:
  - build → sign → verify roundtrip (valid: True, errors: [])
  - raw strings never appear in the payload (prompt, output, snippets)
  - all sha256:<hex> hash fields match the pattern from passport.json
  - contribution human_pct + ai_pct == 100 always
  - JWS protected header: alg=ES256, typ=passport+jws, kid present
  - PassportEnvelope shape {jws_token, json_payload}
  - canonical JSON stability for StyleProfile hash
  - input-validation guards (fit_score range, mutual-exclusion of style args)
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key

from autoria_ai.passport.builder import _canonical_hash, build_passport, issue_passport
from autoria_ai.passport.verifier import verify_passport

# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

_RAW_PROMPT = "Write a Victorian ghost story."
_RAW_OUTPUT = "It was a dark and stormy night in London."
_RAW_SNIPPET = "Marley was dead, to begin with."

_STYLE_PROFILE: dict[str, Any] = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "lexical": {"mattr_500": 0.72, "avg_word_length": 4.8, "hapax_ratio": 0.38},
}

_RAG_SOURCES = [
    {"doc_id": "great_expectations", "chunk_id": 0, "snippet_text": _RAW_SNIPPET},
    {"doc_id": "bleak_house", "chunk_id": 3, "snippet_text": "Fog everywhere."},
]


def _build(**overrides: Any) -> dict[str, Any]:
    """Return a valid build_passport result, with optional field overrides."""
    kwargs: dict[str, Any] = {
        "author_id": "dickens",
        "style_profile": _STYLE_PROFILE,
        "model_id": "meta-llama/llama-3-3-70b-instruct",
        "user_prompt": _RAW_PROMPT,
        "output_text": _RAW_OUTPUT,
        "output_length_tokens": 42,
        "rag_sources": _RAG_SOURCES,
        "fit_score": 87,
        "verifier_url": "https://autoria.app/verify",
    }
    kwargs.update(overrides)
    return build_passport(**kwargs)


# ---------------------------------------------------------------------------
# Ephemeral keypair fixture (session-scoped: one pair for all builder tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ec_keypair(tmp_path_factory: pytest.TempPathFactory):
    """Generate a fresh P-256 keypair; yield (priv_path, pub_path, kid)."""
    key_dir = tmp_path_factory.mktemp("builder_keys")
    priv = generate_private_key(SECP256R1())
    pub = priv.public_key()

    priv_path = key_dir / "priv.pem"
    pub_path = key_dir / "pub.pem"
    priv_path.write_bytes(
        priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        pub.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return priv_path, pub_path, "builder-test-kid"


# ===========================================================================
# build_passport — payload shape
# ===========================================================================


def test_build_returns_all_required_fields():
    p = _build()
    for field in (
        "schema_version",
        "passport_id",
        "generated_at",
        "author_voice",
        "generation",
        "rag_sources",
        "contribution",
        "fit_score",
    ):
        assert field in p, f"required field missing: {field}"


def test_schema_version_is_1_0():
    assert _build()["schema_version"] == "1.0"


def test_passport_id_is_uuid4():
    pid = _build()["passport_id"]
    parsed = uuid.UUID(pid)
    assert parsed.version == 4


def test_generated_at_ends_with_z():
    ts = _build()["generated_at"]
    assert ts.endswith("Z"), f"generated_at must end with Z, got: {ts}"


# ===========================================================================
# build_passport — privacy: no raw strings in the returned dict
# ===========================================================================


def _flat_json(p: dict[str, Any]) -> str:
    return json.dumps(p)


def test_raw_user_prompt_not_in_payload():
    flat = _flat_json(_build())
    assert _RAW_PROMPT not in flat, "raw user_prompt leaked into payload"


def test_raw_output_not_in_payload():
    flat = _flat_json(_build())
    assert _RAW_OUTPUT not in flat, "raw output_text leaked into payload"


def test_raw_snippet_not_in_payload():
    flat = _flat_json(_build())
    assert _RAW_SNIPPET not in flat, "raw snippet_text leaked into payload"


# ===========================================================================
# build_passport — hash format (sha256:<64 lowercase hex chars>)
# ===========================================================================


def test_user_prompt_hash_format():
    assert _HASH_PATTERN.match(_build()["generation"]["user_prompt_hash"])


def test_output_hash_format():
    assert _HASH_PATTERN.match(_build()["generation"]["output_hash"])


def test_style_profile_hash_format():
    assert _HASH_PATTERN.match(_build()["author_voice"]["style_profile_hash"])


def test_snippet_hash_format():
    for src in _build()["rag_sources"]:
        assert _HASH_PATTERN.match(src["snippet_hash"]), f"bad snippet_hash: {src}"


# ===========================================================================
# build_passport — canonical JSON stability for StyleProfile hash
# ===========================================================================


def test_style_profile_hash_is_key_order_independent():
    """Same profile content in different insertion order → same hash."""
    profile_a = {"b": 2, "a": 1, "schema_version": "1.0", "author_id": "poe"}
    profile_b = {"schema_version": "1.0", "author_id": "poe", "a": 1, "b": 2}
    h_a = _canonical_hash(profile_a)
    h_b = _canonical_hash(profile_b)
    assert h_a == h_b


def test_style_profile_hash_matches_manual_canonical():
    """Hash produced by build_passport equals an independent manual computation."""
    import hashlib

    canonical = json.dumps(_STYLE_PROFILE, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert _build()["author_voice"]["style_profile_hash"] == expected


# ===========================================================================
# build_passport — contribution block (v1 hard-codes 0 / 100)
# ===========================================================================


def test_contribution_human_pct_is_0():
    assert _build()["contribution"]["human_pct"] == 0


def test_contribution_ai_pct_is_100():
    assert _build()["contribution"]["ai_pct"] == 100


def test_contribution_sums_to_100():
    c = _build()["contribution"]
    assert c["human_pct"] + c["ai_pct"] == 100


def test_contribution_note_included_when_provided():
    p = _build(contribution_note="v1: fully AI")
    assert p["contribution"]["note"] == "v1: fully AI"


def test_contribution_note_absent_when_not_provided():
    assert "note" not in _build()["contribution"]


# ===========================================================================
# build_passport — input-validation guards
# ===========================================================================


def test_fit_score_above_100_raises():
    with pytest.raises(ValueError, match="fit_score"):
        _build(fit_score=101)


def test_fit_score_below_0_raises():
    with pytest.raises(ValueError, match="fit_score"):
        _build(fit_score=-1)


def test_fit_score_error_message_does_not_contain_raw_value():
    """Error messages must name the field, never the caller-supplied value."""
    sentinel = "CANARY_VALUE_9a3f"
    with pytest.raises(ValueError) as exc_info:
        build_passport(
            author_id="x",
            style_profile={"v": 1},
            model_id="m",
            user_prompt=sentinel,
            output_text="o",
            output_length_tokens=1,
            fit_score=999,
        )
    assert sentinel not in str(exc_info.value)


def test_both_style_args_raises():
    with pytest.raises(ValueError, match="exactly one"):
        build_passport(
            author_id="dickens",
            style_profile=_STYLE_PROFILE,
            style_profile_hash="sha256:" + "ab" * 32,
            model_id="m",
            user_prompt="p",
            output_text="o",
            output_length_tokens=1,
            fit_score=50,
        )


def test_neither_style_arg_raises():
    with pytest.raises(ValueError, match="exactly one"):
        build_passport(
            author_id="dickens",
            model_id="m",
            user_prompt="p",
            output_text="o",
            output_length_tokens=1,
            fit_score=50,
        )


def test_precomputed_style_hash_accepted():
    pre = "sha256:" + "cd" * 32
    p = build_passport(
        author_id="poe",
        style_profile_hash=pre,
        model_id="m",
        user_prompt="p",
        output_text="o",
        output_length_tokens=0,
        fit_score=0,
    )
    assert p["author_voice"]["style_profile_hash"] == pre


# ===========================================================================
# issue_passport — PassportEnvelope shape + JWS header
# ===========================================================================


def _issue(ec_keypair, **overrides: Any) -> dict[str, Any]:
    priv_path, _pub, kid = ec_keypair
    kwargs: dict[str, Any] = {
        "author_id": "dickens",
        "style_profile": _STYLE_PROFILE,
        "model_id": "meta-llama/llama-3-3-70b-instruct",
        "user_prompt": _RAW_PROMPT,
        "output_text": _RAW_OUTPUT,
        "output_length_tokens": 42,
        "rag_sources": _RAG_SOURCES,
        "fit_score": 87,
        "verifier_url": "https://autoria.app/verify",
        "private_key_path": str(priv_path),
        "kid": kid,
    }
    kwargs.update(overrides)
    return issue_passport(**kwargs)


def test_issue_returns_jws_token_and_json_payload(ec_keypair):
    envelope = _issue(ec_keypair)
    assert "jws_token" in envelope
    assert "json_payload" in envelope


def test_issue_jws_token_is_three_part_compact_jws(ec_keypair):
    token = _issue(ec_keypair)["jws_token"]
    assert token.count(".") == 2, "compact JWS must have exactly 3 dot-separated segments"


def test_issue_header_alg_is_es256(ec_keypair):
    token = _issue(ec_keypair)["jws_token"]
    header_b64 = token.split(".")[0]
    # Re-pad and decode
    pad = (-len(header_b64)) % 4
    header = json.loads(base64.urlsafe_b64decode(header_b64 + "=" * pad))
    assert header["alg"] == "ES256"


def test_issue_header_typ_is_passport_jws(ec_keypair):
    token = _issue(ec_keypair)["jws_token"]
    header_b64 = token.split(".")[0]
    pad = (-len(header_b64)) % 4
    header = json.loads(base64.urlsafe_b64decode(header_b64 + "=" * pad))
    assert header["typ"] == "passport+jws"


def test_issue_header_kid_matches_fixture(ec_keypair):
    _priv, _pub, kid = ec_keypair
    token = _issue(ec_keypair)["jws_token"]
    header_b64 = token.split(".")[0]
    pad = (-len(header_b64)) % 4
    header = json.loads(base64.urlsafe_b64decode(header_b64 + "=" * pad))
    assert header["kid"] == kid


def test_issue_json_payload_equals_independently_built_payload(ec_keypair):
    """json_payload in the envelope is the same dict build_passport would produce
    for the same inputs (modulo passport_id/generated_at which are deterministic
    when pinned via overrides)."""
    fixed_id = str(uuid.uuid4())
    fixed_ts = "2026-07-15T10:00:00Z"
    envelope = _issue(
        ec_keypair,
        passport_id=fixed_id,
        generated_at=fixed_ts,
    )
    expected = build_passport(
        author_id="dickens",
        style_profile=_STYLE_PROFILE,
        model_id="meta-llama/llama-3-3-70b-instruct",
        user_prompt=_RAW_PROMPT,
        output_text=_RAW_OUTPUT,
        output_length_tokens=42,
        rag_sources=_RAG_SOURCES,
        fit_score=87,
        verifier_url="https://autoria.app/verify",
        passport_id=fixed_id,
        generated_at=fixed_ts,
    )
    assert envelope["json_payload"] == expected


# ===========================================================================
# issue_passport → verify_passport roundtrip
# ===========================================================================


def test_roundtrip_issue_verify_valid_true(ec_keypair):
    _priv, pub_path, kid = ec_keypair
    envelope = _issue(ec_keypair)
    result = verify_passport(envelope["jws_token"], public_key_path=pub_path, expected_kid=kid)
    assert result.valid is True


def test_roundtrip_issue_verify_errors_empty(ec_keypair):
    _priv, pub_path, kid = ec_keypair
    envelope = _issue(ec_keypair)
    result = verify_passport(envelope["jws_token"], public_key_path=pub_path, expected_kid=kid)
    assert result.errors == []


def test_roundtrip_issue_verify_payload_matches_envelope(ec_keypair):
    _priv, pub_path, kid = ec_keypair
    envelope = _issue(ec_keypair)
    result = verify_passport(envelope["jws_token"], public_key_path=pub_path, expected_kid=kid)
    assert result.payload == envelope["json_payload"]


def test_roundtrip_verified_payload_has_no_raw_strings(ec_keypair):
    _priv, pub_path, kid = ec_keypair
    envelope = _issue(ec_keypair)
    result = verify_passport(envelope["jws_token"], public_key_path=pub_path, expected_kid=kid)
    flat = json.dumps(result.payload)
    for raw in (_RAW_PROMPT, _RAW_OUTPUT, _RAW_SNIPPET):
        assert raw not in flat, f"raw string leaked into verified payload: {raw!r}"


def test_roundtrip_contribution_sums_to_100(ec_keypair):
    _priv, pub_path, kid = ec_keypair
    envelope = _issue(ec_keypair)
    result = verify_passport(envelope["jws_token"], public_key_path=pub_path, expected_kid=kid)
    assert result.payload is not None
    c = result.payload["contribution"]
    assert c["human_pct"] + c["ai_pct"] == 100


# ===========================================================================
# Adversarial fixes - regression tests
# (findings #1-#5 from the PassportAuditor review)
# ===========================================================================


# ---------------------------------------------------------------------------
# Fix #1 — pre-computed style_profile_hash format validation
# ---------------------------------------------------------------------------


def test_bad_style_profile_hash_rejected_plain_string():
    with pytest.raises(ValueError, match="sha256"):
        build_passport(
            author_id="dickens",
            style_profile_hash="not-a-hash",
            model_id="m",
            user_prompt="p",
            output_text="o",
            output_length_tokens=1,
            fit_score=50,
        )


def test_bad_style_profile_hash_rejected_uppercase_hex():
    # Schema requires lowercase hex; uppercase must be rejected.
    with pytest.raises(ValueError, match="sha256"):
        build_passport(
            author_id="dickens",
            style_profile_hash="sha256:" + "AB" * 32,
            model_id="m",
            user_prompt="p",
            output_text="o",
            output_length_tokens=1,
            fit_score=50,
        )


def test_bad_style_profile_hash_rejected_wrong_length():
    with pytest.raises(ValueError, match="sha256"):
        build_passport(
            author_id="dickens",
            style_profile_hash="sha256:" + "ab" * 10,  # only 20 hex chars, not 64
            model_id="m",
            user_prompt="p",
            output_text="o",
            output_length_tokens=1,
            fit_score=50,
        )


def test_valid_precomputed_hash_still_accepted():
    """Regression: a correctly formatted pre-computed hash must still work."""
    good = "sha256:" + "a1" * 32
    p = build_passport(
        author_id="dickens",
        style_profile_hash=good,
        model_id="m",
        user_prompt="p",
        output_text="o",
        output_length_tokens=1,
        fit_score=50,
    )
    assert p["author_voice"]["style_profile_hash"] == good


# ---------------------------------------------------------------------------
# Fix #2 — passport_id / generated_at override validation (builder)
# ---------------------------------------------------------------------------


def test_bad_passport_id_rejected():
    with pytest.raises(ValueError, match="passport_id"):
        _build(passport_id="not-a-uuid")


def test_passport_id_v1_rejected():
    # Only UUID v4 is accepted.
    v1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    with pytest.raises(ValueError, match="passport_id"):
        _build(passport_id=v1)


def test_bad_generated_at_garbage_rejected():
    with pytest.raises(ValueError, match="generated_at"):
        _build(generated_at="not-a-timestamp-at-all")


def test_generated_at_without_z_rejected():
    with pytest.raises(ValueError, match="generated_at"):
        _build(generated_at="2026-07-15T10:00:00+00:00")  # valid ISO-8601 but no trailing Z


def test_valid_passport_id_override_accepted():
    valid_id = str(uuid.uuid4())
    p = _build(passport_id=valid_id)
    assert p["passport_id"] == valid_id


def test_valid_generated_at_override_accepted():
    p = _build(generated_at="2026-07-15T10:00:00Z")
    assert p["generated_at"] == "2026-07-15T10:00:00Z"


# ---------------------------------------------------------------------------
# Fix #2 — FormatChecker in verifier: garbage timestamp/uuid in a signed
#          payload now produces schema_mismatch instead of valid:True
# ---------------------------------------------------------------------------


def test_verifier_rejects_bad_generated_at_format(ec_keypair):
    """A token whose payload has a malformed generated_at should fail schema."""
    priv_path, pub_path, kid = ec_keypair
    from autoria_ai.passport.signer import sign_passport

    bad_payload = _build()
    # Bypass builder validation by mutating after build.
    bad_payload["generated_at"] = "not-a-date"
    token = sign_passport(bad_payload, private_key_path=str(priv_path), kid=kid)
    result = verify_passport(token, public_key_path=pub_path, expected_kid=kid)
    assert result.valid is False
    assert any(e.code == "schema_mismatch" for e in result.errors)


def test_verifier_rejects_bad_passport_id_format(ec_keypair):
    """A token whose payload has a non-UUID passport_id should fail schema."""
    priv_path, pub_path, kid = ec_keypair
    from autoria_ai.passport.signer import sign_passport

    bad_payload = _build()
    bad_payload["passport_id"] = "totally-not-a-uuid"
    token = sign_passport(bad_payload, private_key_path=str(priv_path), kid=kid)
    result = verify_passport(token, public_key_path=pub_path, expected_kid=kid)
    assert result.valid is False
    assert any(e.code == "schema_mismatch" for e in result.errors)


# ---------------------------------------------------------------------------
# Fix #3 — PEM load failure: RuntimeError with no key material in the message
# ---------------------------------------------------------------------------


def test_corrupted_key_file_raises_runtime_error_without_pem_content(tmp_path):
    bad_key = tmp_path / "bad.pem"
    bad_key.write_bytes(b"-----BEGIN PRIVATE KEY-----\nNOTVALIDBASE64\n-----END PRIVATE KEY-----\n")
    from autoria_ai.passport.signer import sign_passport

    with pytest.raises(RuntimeError) as exc_info:
        sign_passport(
            _build(),
            private_key_path=str(bad_key),
            kid="test-kid",
        )
    msg = str(exc_info.value)
    # The error message must not contain PEM markers or base64 key material.
    assert "BEGIN" not in msg
    assert "PRIVATE" not in msg
    # `from None` sets __suppress_context__ = True, which is what prevents the
    # original exception (carrying PEM bytes) from appearing in tracebacks and
    # logging.exception() output.  __context__ is always set by the interpreter
    # even with `from None`; the guarantee is suppression, not nulling.
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


# ---------------------------------------------------------------------------
# Fix #4 — _canonical_hash: JSON round-trip normalises non-JSON-native scalars
#          without changing the hash for already-JSON-safe dicts
# ---------------------------------------------------------------------------


def test_canonical_hash_stable_for_json_safe_dict():
    """Verify round-trip normalisation does not change the hash for plain dicts."""
    import hashlib

    profile = {"schema_version": "1.0", "author_id": "poe", "score": 0.95}
    canonical = json.dumps(
        json.loads(json.dumps(profile, ensure_ascii=False)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    expected = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert _canonical_hash(profile) == expected


def test_canonical_hash_non_serialisable_raises_typeerror():
    class _Unserializable:
        pass

    with pytest.raises(TypeError, match="JSON"):
        _canonical_hash({"key": _Unserializable()})


# ---------------------------------------------------------------------------
# Fix #5 — missing PASSPORT_KID: signer raises, verifier fails closed
# ---------------------------------------------------------------------------


def test_sign_passport_raises_when_kid_unset(monkeypatch, tmp_path):
    """sign_passport must refuse when neither kid arg nor PASSPORT_KID env is set."""
    from cryptography.hazmat.primitives import serialization as _ser
    from cryptography.hazmat.primitives.asymmetric.ec import (
        SECP256R1,
        generate_private_key,
    )

    from autoria_ai.passport.signer import sign_passport

    monkeypatch.delenv("PASSPORT_KID", raising=False)

    priv = generate_private_key(SECP256R1())
    priv_path = tmp_path / "priv.pem"
    priv_path.write_bytes(
        priv.private_bytes(_ser.Encoding.PEM, _ser.PrivateFormat.PKCS8, _ser.NoEncryption())
    )
    with pytest.raises(RuntimeError, match="PASSPORT_KID"):
        sign_passport(_build(), private_key_path=str(priv_path))  # kid arg omitted


def test_verify_passport_fails_closed_when_kid_unset(monkeypatch, ec_keypair):
    """verify_passport must return unknown_kid when PASSPORT_KID env is absent
    and expected_kid is not passed explicitly."""
    _priv_path, pub_path, _kid = ec_keypair
    envelope = _issue(ec_keypair)  # issued with kid set

    monkeypatch.delenv("PASSPORT_KID", raising=False)
    # Call without expected_kid — verifier has no configured key id.
    result = verify_passport(envelope["jws_token"], public_key_path=pub_path)
    assert result.valid is False
    assert any(e.code == "unknown_kid" for e in result.errors)


# ---------------------------------------------------------------------------
# Regression: all five fixes applied — happy path still green
# ---------------------------------------------------------------------------


def test_happy_path_roundtrip_still_passes_after_all_fixes(ec_keypair):
    """Full build → sign → verify pipeline must remain valid after all fixes."""
    _priv_path, pub_path, kid = ec_keypair
    envelope = _issue(ec_keypair)
    result = verify_passport(envelope["jws_token"], public_key_path=pub_path, expected_kid=kid)
    assert result.valid is True
    assert result.errors == []
    assert result.payload is not None
    assert result.payload["schema_version"] == "1.0"
    c = result.payload["contribution"]
    assert c["human_pct"] + c["ai_pct"] == 100
