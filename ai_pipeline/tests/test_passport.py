"""Tests for Authorship Passport sign / verify (offline ES256)."""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key

from autoria_ai.passport.signer import sign_passport
from autoria_ai.passport.verifier import MAX_TOKEN_CHARS, verify_passport


@pytest.fixture()
def ec_keypair(tmp_path: Path):
    priv = generate_private_key(SECP256R1())
    pub = priv.public_key()
    priv_path = tmp_path / "priv.pem"
    pub_path = tmp_path / "pub.pem"
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
    return priv_path, pub_path, "test-kid-2026", priv


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _payload() -> dict:
    return {
        "schema_version": "1.0",
        "passport_id": str(uuid.uuid4()),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "author_voice": {
            "id": "dickens",
            "style_profile_hash": _sha("style"),
            "style_profile_version": "1.0",
        },
        "generation": {
            "model_provider": "ibm/watsonx",
            "model_id": "meta-llama/llama-3-3-70b-instruct",
            "user_prompt_hash": _sha("prompt"),
            "output_hash": _sha("output"),
            "output_length_tokens": 42,
        },
        "rag_sources": [
            {
                "doc_id": "great_expectations",
                "chunk_id": 0,
                "snippet_hash": _sha("snippet"),
            }
        ],
        "contribution": {"human_pct": 0, "ai_pct": 100, "note": "v1"},
        "fit_score": 87,
        "verifier_url": "https://autoria.app/verify",
    }


def test_roundtrip_sign_verify(ec_keypair):
    priv_path, pub_path, kid, _ = ec_keypair
    payload = _payload()
    token = sign_passport(payload, private_key_path=priv_path, kid=kid)
    result = verify_passport(token, public_key_path=pub_path, expected_kid=kid)
    assert result.valid is True
    assert result.errors == []
    assert result.payload is not None
    assert result.payload["schema_version"] == "1.0"


def test_tampered_payload_rejected(ec_keypair):
    priv_path, pub_path, kid, _ = ec_keypair
    token = sign_passport(_payload(), private_key_path=priv_path, kid=kid)
    parts = token.split(".")
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    tampered = ".".join(parts)
    result = verify_passport(tampered, public_key_path=pub_path, expected_kid=kid)
    assert result.valid is False
    assert any(e.code == "invalid_signature" for e in result.errors)


def test_alg_none_rejected(ec_keypair):
    _priv, pub_path, kid, _ = ec_keypair
    header = (
        base64.urlsafe_b64encode(json.dumps({"alg": "none", "kid": kid}).encode())
        .rstrip(b"=")
        .decode()
    )
    body = base64.urlsafe_b64encode(json.dumps(_payload()).encode()).rstrip(b"=").decode()
    none_token = f"{header}.{body}."
    result = verify_passport(none_token, public_key_path=pub_path, expected_kid=kid)
    assert result.valid is False
    assert any(e.code == "unsupported_algorithm" for e in result.errors)


def test_oversized_token_rejected(ec_keypair):
    _priv, pub_path, kid, _ = ec_keypair
    huge = "a" * (MAX_TOKEN_CHARS + 1)
    result = verify_passport(huge, public_key_path=pub_path, expected_kid=kid)
    assert result.valid is False
    assert any(e.code == "invalid_token" for e in result.errors)
