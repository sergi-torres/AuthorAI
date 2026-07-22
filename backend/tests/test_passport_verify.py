"""Tests for POST /api/passports/verify.

Uses an ephemeral EC P-256 keypair; signs a minimal valid passport payload and
exercises the full §8 verification algorithm through the HTTP layer.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256R1,
    generate_private_key,
)
from fastapi.testclient import TestClient
from jose import jws as jose_jws

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ec_keypair(tmp_path_factory):
    """Generate a P-256 keypair; write PEM files; return (priv_path, pub_path, kid)."""
    key_dir = tmp_path_factory.mktemp("keys_verify")
    priv_key = generate_private_key(SECP256R1())
    pub_key = priv_key.public_key()

    priv_path = key_dir / "test.priv.pem"
    pub_path = key_dir / "test.pub.pem"

    priv_path.write_bytes(
        priv_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        pub_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return str(priv_path), str(pub_path), "test-kid-2026", priv_key


def _sha256_hex(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _valid_payload(kid: str = "test-kid-2026") -> dict:
    """Return a schema-valid passport payload."""
    return {
        "schema_version": "1.0",
        "passport_id": str(uuid.uuid4()),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "author_voice": {
            "id": "dickens",
            "style_profile_hash": _sha256_hex("style-profile-data"),
            "style_profile_version": "1.0",
        },
        "generation": {
            "model_provider": "ibm/watsonx",
            "model_id": "meta-llama/llama-3-3-70b-instruct",
            "user_prompt_hash": _sha256_hex("write me a story"),
            "output_hash": _sha256_hex("it was a dark and stormy night"),
            "output_length_tokens": 42,
        },
        "rag_sources": [
            {
                "doc_id": "great_expectations",
                "chunk_id": 0,
                "snippet_hash": _sha256_hex("snippet text"),
            }
        ],
        "contribution": {
            "human_pct": 0,
            "ai_pct": 100,
            "note": "v1: 100% AI-assisted.",
        },
        "fit_score": 87,
        "verifier_url": "https://autoria.app/verify",
    }


def _sign(payload: dict, priv_key, kid: str) -> str:
    """Sign *payload* with *priv_key* using ES256 and *kid* in the header."""
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    return jose_jws.sign(
        payload_bytes,
        priv_key,
        headers={"kid": kid, "typ": "passport+jws"},
        algorithm="ES256",
    )


@pytest.fixture()
def client_with_keys(ec_keypair, monkeypatch):
    """TestClient patched to use the ephemeral keypair."""
    _priv, pub_path, kid, _priv_key = ec_keypair
    import app.config as cfg

    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PATH", pub_path)
    monkeypatch.setenv("PASSPORT_KID", kid)
    monkeypatch.setattr(cfg, "settings", cfg.load_settings())

    from app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_verify_valid_token_returns_200(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    token = _sign(_valid_payload(kid), priv_key, kid)
    resp = client_with_keys.post("/api/passports/verify", json={"jws_token": token})
    assert resp.status_code == 200


def test_verify_valid_token_returns_valid_true(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    token = _sign(_valid_payload(kid), priv_key, kid)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": token}).json()
    assert body["valid"] is True


def test_verify_valid_token_errors_is_empty(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    token = _sign(_valid_payload(kid), priv_key, kid)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": token}).json()
    assert body["errors"] == []


def test_verify_valid_token_payload_contains_schema_version(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    token = _sign(_valid_payload(kid), priv_key, kid)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": token}).json()
    assert body["payload"]["schema_version"] == "1.0"


# ---------------------------------------------------------------------------
# Tampered payload → invalid_signature
# ---------------------------------------------------------------------------


def test_verify_tampered_payload_returns_valid_false(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    token = _sign(_valid_payload(kid), priv_key, kid)
    # Flip one byte in the payload segment (middle segment).
    parts = token.split(".")
    # Append an extra character to corrupt the payload base64url.
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    tampered = ".".join(parts)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": tampered}).json()
    assert body["valid"] is False


def test_verify_tampered_payload_error_code_is_invalid_signature(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    token = _sign(_valid_payload(kid), priv_key, kid)
    parts = token.split(".")
    # Replace the entire signature segment with a different-length dummy to
    # guarantee the ECDSA bytes are invalid (last-char flip can be a no-op for
    # some base64url encodings with trailing padding equivalence).
    sig = parts[2]
    parts[2] = ("B" if sig[0] != "B" else "C") + sig[1:]
    tampered = ".".join(parts)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": tampered}).json()
    codes = [e["code"] for e in body["errors"]]
    assert "invalid_signature" in codes


# ---------------------------------------------------------------------------
# Algorithm enforcement
# ---------------------------------------------------------------------------


def test_verify_alg_none_returns_unsupported_algorithm(ec_keypair, client_with_keys):
    """alg=none MUST be rejected, not accepted (algorithm-confusion defense)."""
    _priv, _pub, kid, _priv_key = ec_keypair
    payload_bytes = json.dumps(_valid_payload(kid), separators=(",", ":")).encode()
    # Craft a fake "none" token manually: header.payload.(empty sig)
    header = (
        base64.urlsafe_b64encode(json.dumps({"alg": "none", "kid": kid}).encode())
        .rstrip(b"=")
        .decode()
    )
    body_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    none_token = f"{header}.{body_b64}."
    resp = client_with_keys.post("/api/passports/verify", json={"jws_token": none_token})
    body = resp.json()
    assert body["valid"] is False
    codes = [e["code"] for e in body["errors"]]
    assert "unsupported_algorithm" in codes


def test_verify_hs256_returns_unsupported_algorithm(ec_keypair, client_with_keys):
    _priv, _pub, kid, _priv_key = ec_keypair
    payload_bytes = json.dumps(_valid_payload(kid), separators=(",", ":")).encode()
    header = (
        base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "kid": kid}).encode())
        .rstrip(b"=")
        .decode()
    )
    body_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    hs_token = f"{header}.{body_b64}.fakesig"
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": hs_token}).json()
    assert body["valid"] is False
    assert any(e["code"] == "unsupported_algorithm" for e in body["errors"])


# ---------------------------------------------------------------------------
# Unknown kid
# ---------------------------------------------------------------------------


def test_verify_unknown_kid_returns_unknown_kid(ec_keypair, client_with_keys):
    _priv, _pub, _kid, priv_key = ec_keypair
    wrong_kid = "attacker-key-9999"
    token = _sign(_valid_payload(wrong_kid), priv_key, wrong_kid)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": token}).json()
    assert body["valid"] is False
    assert any(e["code"] == "unknown_kid" for e in body["errors"])


# ---------------------------------------------------------------------------
# Malformed token
# ---------------------------------------------------------------------------


def test_verify_malformed_token_only_two_parts(client_with_keys):
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": "aaa.bbb"}).json()
    assert body["valid"] is False
    assert any(e["code"] == "invalid_token" for e in body["errors"])


def test_verify_empty_token_returns_422(client_with_keys):
    """An empty string fails Pydantic's minLength=1 → 422, not 200."""
    resp = client_with_keys.post("/api/passports/verify", json={"jws_token": ""})
    assert resp.status_code == 422


def test_verify_missing_body_field_returns_422(client_with_keys):
    resp = client_with_keys.post("/api/passports/verify", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Schema mismatch
# ---------------------------------------------------------------------------


def test_verify_schema_mismatch_missing_required_field(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    bad_payload = _valid_payload(kid)
    del bad_payload["fit_score"]  # required field missing
    token = _sign(bad_payload, priv_key, kid)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": token}).json()
    assert body["valid"] is False
    assert any(e["code"] == "schema_mismatch" for e in body["errors"])


def test_verify_schema_mismatch_unsupported_version(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    bad_payload = _valid_payload(kid)
    bad_payload["schema_version"] = "9.9"  # unsupported version
    token = _sign(bad_payload, priv_key, kid)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": token}).json()
    assert body["valid"] is False
    # "9.9" fails the JSON Schema `const: "1.0"` constraint → schema_mismatch
    assert any(e["code"] == "schema_mismatch" for e in body["errors"])


# ---------------------------------------------------------------------------
# Response shape contract
# ---------------------------------------------------------------------------


def test_verify_response_always_has_required_keys(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    token = _sign(_valid_payload(kid), priv_key, kid)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": token}).json()
    for field in ("valid", "errors"):
        assert field in body, f"Required field '{field}' missing from VerifyResponse"


def test_verify_invalid_response_payload_is_null(ec_keypair, client_with_keys):
    _priv, _pub, kid, priv_key = ec_keypair
    token = _sign(_valid_payload(kid), priv_key, kid)
    parts = token.split(".")
    parts[2] = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
    tampered = ".".join(parts)
    body = client_with_keys.post("/api/passports/verify", json={"jws_token": tampered}).json()
    assert body["payload"] is None
