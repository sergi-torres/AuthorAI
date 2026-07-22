"""Tests for the Watsonx client (mocked unit + live integration)."""

from __future__ import annotations

import os
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.watsonx_client import (
    _RETRY_DELAYS_SECONDS,
    HARD_TIMEOUT_SECONDS,
    WatsonxError,
    generate,
)

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
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _watsonx_creds_present() -> bool:
    _load_dotenv_file(_ENV_FILE)
    return bool(os.getenv("WATSONX_API_KEY") and os.getenv("WATSONX_PROJECT_ID"))


def test_generate_missing_config_raises(monkeypatch):
    monkeypatch.delenv("WATSONX_API_KEY", raising=False)
    monkeypatch.delenv("WATSONX_PROJECT_ID", raising=False)
    with pytest.raises(WatsonxError, match="not configured"):
        generate("hi", None, "meta-llama/llama-3-3-70b-instruct")


def test_generate_success_uses_chat_and_returns_text(monkeypatch):
    monkeypatch.setenv("WATSONX_API_KEY", "test-key")
    monkeypatch.setenv("WATSONX_PROJECT_ID", "test-project")
    monkeypatch.setenv("WATSONX_URL", "https://example.ml.cloud.ibm.com")

    mock_model = MagicMock()
    mock_model.chat.return_value = {"choices": [{"message": {"content": "  hello from watsonx  "}}]}

    with (
        patch("app.services.watsonx_client.Credentials") as creds_cls,
        patch("app.services.watsonx_client.ModelInference", return_value=mock_model) as model_cls,
    ):
        text = generate(
            "Say hello",
            "You are concise.",
            "meta-llama/llama-3-3-70b-instruct",
            params={"temperature": 0.2},
        )

    assert text == "  hello from watsonx  "
    creds_cls.assert_called_once_with(api_key="test-key", url="https://example.ml.cloud.ibm.com")
    model_cls.assert_called_once()
    assert model_cls.call_args.kwargs["max_retries"] == 0
    assert model_cls.call_args.kwargs["validate"] is False
    mock_model.chat.assert_called_once_with(
        messages=[
            {"role": "system", "content": "You are concise."},
            {"role": "user", "content": "Say hello"},
        ],
        params={"temperature": 0.2},
    )


def test_generate_retries_with_backoff_then_succeeds(monkeypatch):
    monkeypatch.setenv("WATSONX_API_KEY", "test-key")
    monkeypatch.setenv("WATSONX_PROJECT_ID", "test-project")

    mock_model = MagicMock()
    mock_model.chat.side_effect = [
        RuntimeError("transient"),
        {"choices": [{"message": {"content": "ok"}}]},
    ]

    sleeps: list[float] = []

    with (
        patch("app.services.watsonx_client.ModelInference", return_value=mock_model),
        patch("app.services.watsonx_client.Credentials"),
        patch("app.services.watsonx_client.time.sleep", side_effect=sleeps.append),
    ):
        text = generate("prompt", None, "ibm/granite-3-8b-instruct")

    assert text == "ok"
    assert sleeps == [1.0]
    assert mock_model.chat.call_count == 2


def test_generate_exhausts_retries(monkeypatch):
    monkeypatch.setenv("WATSONX_API_KEY", "test-key")
    monkeypatch.setenv("WATSONX_PROJECT_ID", "test-project")

    mock_model = MagicMock()
    mock_model.chat.side_effect = RuntimeError("down")

    sleeps: list[float] = []

    with (
        patch("app.services.watsonx_client.ModelInference", return_value=mock_model),
        patch("app.services.watsonx_client.Credentials"),
        patch("app.services.watsonx_client.time.sleep", side_effect=sleeps.append),
        pytest.raises(WatsonxError, match="failed after"),
    ):
        generate("prompt", None, "ibm/granite-3-8b-instruct")

    assert sleeps == list(_RETRY_DELAYS_SECONDS)
    assert mock_model.chat.call_count == 1 + len(_RETRY_DELAYS_SECONDS)


def test_generate_hard_timeout(monkeypatch):
    monkeypatch.setenv("WATSONX_API_KEY", "test-key")
    monkeypatch.setenv("WATSONX_PROJECT_ID", "test-project")

    sleeps: list[float] = []

    with (
        patch("app.services.watsonx_client.ModelInference"),
        patch("app.services.watsonx_client.Credentials"),
        patch("app.services.watsonx_client.time.sleep", side_effect=sleeps.append),
        patch("app.services.watsonx_client.ThreadPoolExecutor") as executor_cls,
        pytest.raises(WatsonxError, match="failed after"),
    ):
        executor = MagicMock()
        executor_cls.return_value = executor
        future = MagicMock()
        future.result.side_effect = FuturesTimeoutError()
        executor.submit.return_value = future
        generate("prompt", None, "ibm/granite-3-8b-instruct")

    assert sleeps == list(_RETRY_DELAYS_SECONDS)
    assert future.result.call_count == 1 + len(_RETRY_DELAYS_SECONDS)
    for call in future.result.call_args_list:
        assert call.kwargs["timeout"] == HARD_TIMEOUT_SECONDS


@pytest.mark.integration
@pytest.mark.skipif(
    not _watsonx_creds_present(),
    reason="WATSONX_API_KEY / WATSONX_PROJECT_ID not set",
)
def test_generate_live_watsonx():
    """Hit real Watsonx — requires credentials in the environment or repo `.env`."""
    _load_dotenv_file(_ENV_FILE)
    text = generate(
        prompt="Reply with exactly one word: pong",
        system_prompt="You are a terse assistant. Answer with a single word only.",
        model_id="ibm/granite-3-8b-instruct",
        params={"max_tokens": 16, "temperature": 0},
    )
    assert isinstance(text, str)
    assert text.strip()
