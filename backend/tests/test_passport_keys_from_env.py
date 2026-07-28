"""Keys supplied as PEM *content* must work everywhere a key path works.

`.gitignore` excludes `keys/**` and `*.pem`, so a deployed image contains no
key files at all: Railway and Vercel inject values, not files. Until now every
key lookup went through `PASSPORT_*_KEY_PATH`, which meant that in production
`/.well-known/jwks.json` answered 500 and `POST /api/generate` could not sign
the passport — the demo's centrepiece.

These tests pin the deployed configuration: PEM content in the environment,
no file on disk anywhere.
"""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from autoria_ai.passport.keys import resolve_pem
from autoria_ai.passport.signer import sign_passport
from autoria_ai.passport.verifier import verify_passport


@pytest.fixture()
def pem_pair() -> tuple[str, str, str]:
    """An EC P-256 keypair as PEM strings — never written to disk."""
    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = (
        priv.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return priv_pem, pub_pem, "test-kid-env"


def _clear_key_env(monkeypatch) -> None:
    for name in (
        "PASSPORT_PRIVATE_KEY_PEM",
        "PASSPORT_PUBLIC_KEY_PEM",
        "PASSPORT_PRIVATE_KEY_PATH",
        "PASSPORT_PUBLIC_KEY_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# resolve_pem
# ---------------------------------------------------------------------------


def test_resolve_pem_reads_inline_content(monkeypatch, pem_pair):
    _, pub_pem, _ = pem_pair
    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PEM", pub_pem)
    assert (
        resolve_pem(pem_env="PASSPORT_PUBLIC_KEY_PEM", path_env="PASSPORT_PUBLIC_KEY_PATH")
        == pub_pem.strip().encode()
    )


def test_resolve_pem_accepts_escaped_newlines(monkeypatch, pem_pair):
    """Dashboards and .env files often escape newlines; a PEM with literal
    backslash-n must still parse, or the operator gets an opaque error."""
    _, pub_pem, _ = pem_pair
    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PEM", pub_pem.strip().replace("\n", "\\n"))
    pem = resolve_pem(pem_env="PASSPORT_PUBLIC_KEY_PEM", path_env="PASSPORT_PUBLIC_KEY_PATH")
    serialization.load_pem_public_key(pem)  # raises if the normalisation failed


def test_resolve_pem_prefers_content_over_stale_file(monkeypatch, tmp_path, pem_pair):
    """A key baked into an image must never outrank the operator's variable."""
    _, pub_pem, _ = pem_pair
    other = ec.generate_private_key(ec.SECP256R1()).public_key()
    stale = tmp_path / "stale.pub.pem"
    stale.write_bytes(
        other.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PEM", pub_pem)
    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PATH", str(stale))
    assert (
        resolve_pem(pem_env="PASSPORT_PUBLIC_KEY_PEM", path_env="PASSPORT_PUBLIC_KEY_PATH")
        == pub_pem.strip().encode()
    )


def test_resolve_pem_names_both_variables_when_unset(monkeypatch):
    _clear_key_env(monkeypatch)
    with pytest.raises(RuntimeError) as exc:
        resolve_pem(pem_env="PASSPORT_PUBLIC_KEY_PEM", path_env="PASSPORT_PUBLIC_KEY_PATH")
    assert "PASSPORT_PUBLIC_KEY_PEM" in str(exc.value)
    assert "PASSPORT_PUBLIC_KEY_PATH" in str(exc.value)


# ---------------------------------------------------------------------------
# Full round trip with no key file on disk — the deployed shape
# ---------------------------------------------------------------------------


def test_sign_and_verify_with_env_pem_only(monkeypatch, pem_pair):
    priv_pem, pub_pem, kid = pem_pair
    _clear_key_env(monkeypatch)
    monkeypatch.setenv("PASSPORT_PRIVATE_KEY_PEM", priv_pem)
    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PEM", pub_pem)
    monkeypatch.setenv("PASSPORT_KID", kid)

    payload = {
        "schema_version": "1.0",
        "passport_id": "0e2f1b4a-52a8-4a2e-9c5b-1f0d3b7a9e11",
        "issued_at": "2026-07-28T22:00:00Z",
    }
    token = sign_passport(payload, kid=kid)
    result = verify_passport(token, expected_kid=kid, schema={"type": "object"})
    assert result.valid, result.errors
    assert result.payload == payload


def test_jwks_endpoint_serves_key_from_env_pem(monkeypatch, pem_pair):
    """The deployed shape: no key file exists, only the environment."""
    _priv_pem, pub_pem, kid = pem_pair
    _clear_key_env(monkeypatch)
    monkeypatch.setenv("PASSPORT_PUBLIC_KEY_PEM", pub_pem)
    monkeypatch.setenv("PASSPORT_KID", kid)

    import app.config as cfg

    monkeypatch.setattr(cfg, "settings", cfg.load_settings())
    from app.main import app

    resp = TestClient(app).get("/.well-known/jwks.json")
    assert resp.status_code == 200, resp.text
    jwk = resp.json()["keys"][0]
    assert jwk["kid"] == kid
    assert jwk["alg"] == "ES256"
    assert jwk["crv"] == "P-256"
    assert "d" not in jwk, "private scalar must never be served"
