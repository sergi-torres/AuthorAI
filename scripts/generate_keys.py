#!/usr/bin/env python3
"""Generate the Authorship Passport EC P-256 keypair and public JWKS.

Writes (repo-root relative):
  keys/passport.priv.pem   — private key (gitignored; never commit)
  keys/passport.pub.pem    — public key PEM
  keys/jwks.public.json    — public JWK Set (safe to commit)

Usage (from repo root):
  python scripts/generate_keys.py
  make keys
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key

REPO_ROOT = Path(__file__).resolve().parent.parent
KEYS_DIR = REPO_ROOT / "keys"


def _b64url_uint(n: int, length: int = 32) -> str:
    return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode("ascii")


def generate(kid: str | None = None, keys_dir: Path = KEYS_DIR) -> str:
    keys_dir.mkdir(parents=True, exist_ok=True)
    if kid is None:
        kid = f"autoria-{datetime.now(UTC).strftime('%Y-%m')}"

    private_key = generate_private_key(SECP256R1())
    public_key = private_key.public_key()

    priv_path = keys_dir / "passport.priv.pem"
    pub_path = keys_dir / "passport.pub.pem"
    jwks_path = keys_dir / "jwks.public.json"

    priv_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    numbers = public_key.public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "EC",
                "crv": "P-256",
                "x": _b64url_uint(numbers.x),
                "y": _b64url_uint(numbers.y),
                "use": "sig",
                "alg": "ES256",
                "kid": kid,
            }
        ]
    }
    jwks_path.write_text(json.dumps(jwks, indent=2) + "\n", encoding="utf-8")

    # Restrict private key permissions on POSIX; no-op on Windows.
    with contextlib.suppress(OSError):
        priv_path.chmod(0o600)

    print(f"kid={kid}")
    print(f"wrote {priv_path.relative_to(REPO_ROOT)}")
    print(f"wrote {pub_path.relative_to(REPO_ROOT)}")
    print(f"wrote {jwks_path.relative_to(REPO_ROOT)}")
    print()
    print("Add to .env (paths relative to repo root when running uvicorn from backend/):")
    print(f'PASSPORT_PRIVATE_KEY_PATH="{priv_path.as_posix()}"')
    print(f'PASSPORT_PUBLIC_KEY_PATH="{pub_path.as_posix()}"')
    print(f'PASSPORT_KID="{kid}"')
    return kid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kid",
        default=None,
        help="Key id (default: autoria-YYYY-MM in UTC)",
    )
    parser.add_argument(
        "--keys-dir",
        type=Path,
        default=KEYS_DIR,
        help="Output directory (default: <repo>/keys)",
    )
    args = parser.parse_args(argv)

    if (args.keys_dir / "passport.priv.pem").exists():
        print(
            f"ERROR: {args.keys_dir / 'passport.priv.pem'} already exists. "
            "Refuse to overwrite. Delete it first if you intend to rotate.",
            file=sys.stderr,
        )
        return 1

    generate(kid=args.kid, keys_dir=args.keys_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
