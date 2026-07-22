"""Tests for GET /.well-known/jwks.json.

Uses an ephemeral EC P-256 keypair written to a tmp directory so no real key
file is required on disk.  ``app.config.settings`` is monkey-patched to point
at the ephemeral public key PEM.
"""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256R1,
    generate_private_key,
)
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Shared ephemeral keypair fixture (session-scoped — generated once)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ec_keypair(tmp_path_factory):
    """Generate a P-256 keypair; write both PEM files; return (priv_path, pub_path, kid)."""
    key_dir = tmp_path_factory.mktemp("keys")
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
    return str(priv_path), str(pub_path), "test-kid-2026"


@pytest.fixture()
def client_with_keys(ec_keypair, monkeypatch):
    """TestClient with settings patched to use the ephemeral keypair."""
    _priv, pub_path, kid = ec_keypair
    import app.config as cfg

    # Reload settings with patched env so the module-level ``settings``
    # singleton is replaced for the duration of this test.
    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PATH", pub_path)
    monkeypatch.setenv("PASSPORT_KID", kid)
    monkeypatch.setattr(cfg, "settings", cfg.load_settings())

    # Re-import main *after* patching so the routers read the patched settings.
    from app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_jwks_returns_200(client_with_keys):
    resp = client_with_keys.get("/.well-known/jwks.json")
    assert resp.status_code == 200


def test_jwks_content_type_is_json(client_with_keys):
    resp = client_with_keys.get("/.well-known/jwks.json")
    assert "application/json" in resp.headers["content-type"]


def test_jwks_cache_control_header_is_set(client_with_keys):
    resp = client_with_keys.get("/.well-known/jwks.json")
    assert resp.headers.get("cache-control") == "public, max-age=3600"


def test_jwks_response_has_keys_array(client_with_keys):
    body = client_with_keys.get("/.well-known/jwks.json").json()
    assert "keys" in body
    assert isinstance(body["keys"], list)
    assert len(body["keys"]) >= 1


def test_jwks_key_has_all_required_fields(client_with_keys, ec_keypair):
    _priv, _pub, _kid = ec_keypair
    key = client_with_keys.get("/.well-known/jwks.json").json()["keys"][0]
    for field in ("kty", "crv", "x", "y", "use", "alg", "kid"):
        assert field in key, f"Missing required JWK field: {field}"


def test_jwks_key_values_are_correct(client_with_keys, ec_keypair):
    _priv, _pub, kid = ec_keypair
    key = client_with_keys.get("/.well-known/jwks.json").json()["keys"][0]
    assert key["kty"] == "EC"
    assert key["crv"] == "P-256"
    assert key["use"] == "sig"
    assert key["alg"] == "ES256"
    assert key["kid"] == kid


def test_jwks_x_y_are_valid_base64url(client_with_keys):
    key = client_with_keys.get("/.well-known/jwks.json").json()["keys"][0]
    for coord in ("x", "y"):
        val = key[coord]
        # Pad and decode; should not raise.
        padded = val + "=" * (4 - len(val) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        # P-256 coordinates are 32 bytes.
        assert len(decoded) == 32, f"{coord} coordinate should be 32 bytes; got {len(decoded)}"


def test_jwks_returns_no_private_material(client_with_keys):
    """The 'd' field (private scalar) must never appear in the JWKS response."""
    raw = client_with_keys.get("/.well-known/jwks.json").text
    assert '"d"' not in raw, "Private scalar 'd' must not appear in JWKS response"


def test_jwks_returns_500_when_key_path_missing(monkeypatch):
    """If PASSPORT_PUBLIC_KEY_PATH is unset the endpoint must 500, not serve empty keys."""
    import app.config as cfg

    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PATH", "/nonexistent/path/key.pem")
    monkeypatch.setattr(cfg, "settings", cfg.load_settings())

    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/.well-known/jwks.json")
    assert resp.status_code == 500
