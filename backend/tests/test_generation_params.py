"""Contract tests for the generation parameters sent to Watsonx.

``ModelInference.chat()`` silently drops any key it does not recognise: an
unknown parameter raises nothing and changes nothing, so a misspelt cap is
indistinguishable from an enforced one until an output actually reaches it.
That is how ``max_new_tokens`` survived in ``_GENERATION_PARAMS`` while the
real cap stayed at the service default of 1024 (issue #106).

Two tests, one static and one live:

- ``test_generation_params_match_chat_schema`` is the positive control. It
  fails on any key the chat schema does not declare, which is exactly the
  check that would have caught #106 at the time it was introduced.
- ``test_max_tokens_cap_is_enforced_live`` proves the cap has an effect
  against the real service, by asking for a long answer under a tiny cap.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import pytest
from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

from app.services.watsonx_client import generate
from autoria_ai.generator import _GENERATION_PARAMS

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"


def _load_dotenv_file(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without overriding existing values."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _watsonx_creds_present() -> bool:
    _load_dotenv_file(_ENV_FILE)
    return bool(os.getenv("WATSONX_API_KEY") and os.getenv("WATSONX_PROJECT_ID"))


def _chat_schema_fields() -> set[str]:
    return {f.name for f in dataclasses.fields(TextChatParameters)}


def test_generation_params_match_chat_schema():
    """Every key we send must exist in the chat schema, or it is discarded."""
    unknown = set(_GENERATION_PARAMS) - _chat_schema_fields()
    assert not unknown, (
        f"{sorted(unknown)} are not fields of TextChatParameters and will be "
        f"ignored in silence by ModelInference.chat(). "
        f"Valid fields: {sorted(_chat_schema_fields())}"
    )


def test_output_cap_is_declared():
    """The output cap must be present — an absent key falls back to 1024."""
    assert _GENERATION_PARAMS.get("max_tokens") == 512
    assert "max_new_tokens" not in _GENERATION_PARAMS


@pytest.mark.integration
@pytest.mark.skipif(
    not _watsonx_creds_present(),
    reason="WATSONX_API_KEY / WATSONX_PROJECT_ID not set",
)
def test_max_tokens_cap_is_enforced_live():
    """Ask for far more than the cap allows and check the answer is cut short.

    Without an enforced cap the model answers to its own default (1024
    tokens) and this assertion fails, which is the point: it distinguishes a
    working cap from an ignored one.
    """
    _load_dotenv_file(_ENV_FILE)
    text = generate(
        prompt="Write a detailed 800-word essay about the history of the printing press.",
        system_prompt=None,
        model_id="meta-llama/llama-3-3-70b-instruct",
        params={"max_tokens": 16, "temperature": 0},
    )
    assert text.strip(), "model returned nothing"
    # 16 tokens of English prose is well under 40 whitespace-separated words;
    # an uncapped answer to this prompt runs into the hundreds.
    assert len(text.split()) < 40, f"cap not enforced, got {len(text.split())} words: {text!r}"
