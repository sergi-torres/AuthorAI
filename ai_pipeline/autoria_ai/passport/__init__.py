"""Authorship Passport signing and offline verification (ES256 / JWS)."""

from autoria_ai.passport.signer import sign_passport
from autoria_ai.passport.verifier import VerifyError, VerifyResult, verify_passport

__all__ = [
    "VerifyError",
    "VerifyResult",
    "sign_passport",
    "verify_passport",
]
