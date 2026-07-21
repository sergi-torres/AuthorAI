"""Thin IBM Watsonx text-generation client.

IAM auth via ``app.config`` settings, hard 8s timeout per attempt, and
exponential backoff (1s / 2s / 4s) across retries. No RAG, no parallel
orchestration — callers compose that on top.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

from app.config import load_settings

logger = logging.getLogger(__name__)

HARD_TIMEOUT_SECONDS = 8.0
# Three retries after the first failure → four attempts total.
_RETRY_DELAYS_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)
_DEFAULT_URL = "https://us-south.ml.cloud.ibm.com"


class WatsonxError(RuntimeError):
    """Raised when Watsonx generation fails after all retries."""


def _require_credentials() -> tuple[str, str, str]:
    settings = load_settings()
    api_key = settings.watsonx_api_key
    project_id = settings.watsonx_project_id
    url = settings.watsonx_url or _DEFAULT_URL
    if not api_key or not project_id:
        raise WatsonxError(
            "Watsonx is not configured: set WATSONX_API_KEY and WATSONX_PROJECT_ID"
        )
    return api_key, project_id, url


def _build_messages(prompt: str, system_prompt: str | None) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_chat_text(response: dict[str, Any]) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise WatsonxError("Unexpected Watsonx chat response shape") from exc
    if not isinstance(content, str) or not content.strip():
        raise WatsonxError("Watsonx returned empty content")
    return content


def _call_watsonx(
    *,
    prompt: str,
    system_prompt: str | None,
    model_id: str,
    params: dict[str, Any] | None,
    api_key: str,
    project_id: str,
    url: str,
) -> str:
    model = ModelInference(
        model_id=model_id,
        credentials=Credentials(api_key=api_key, url=url),
        project_id=project_id,
        params=params,
        # Own retry/backoff below — disable SDK-level retries.
        max_retries=0,
        # Skip remote model-spec lookup (fails when project has no WML link yet).
        validate=False,
    )
    messages = _build_messages(prompt, system_prompt)
    response = model.chat(messages=messages, params=params)
    return _extract_chat_text(response)


def generate(
    prompt: str,
    system_prompt: str | None,
    model_id: str,
    params: dict[str, Any] | None = None,
) -> str:
    """Generate text from Watsonx.

    Args:
        prompt: User prompt.
        system_prompt: Optional system instruction (chat ``system`` role).
        model_id: Watsonx model id (e.g. ``meta-llama/llama-3-3-70b-instruct``).
        params: Optional generation / chat parameters passed to the SDK.

    Returns:
        Generated text.

    Raises:
        WatsonxError: Missing config, empty response, timeout, or exhausted retries.
    """
    api_key, project_id, url = _require_credentials()
    last_error: BaseException | None = None
    max_attempts = 1 + len(_RETRY_DELAYS_SECONDS)

    for attempt in range(max_attempts):
        try:
            pool = ThreadPoolExecutor(max_workers=1)
            try:
                future = pool.submit(
                    _call_watsonx,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model_id=model_id,
                    params=params,
                    api_key=api_key,
                    project_id=project_id,
                    url=url,
                )
                return future.result(timeout=HARD_TIMEOUT_SECONDS)
            finally:
                # Don't block the retry loop waiting on a hung SDK call.
                pool.shutdown(wait=False, cancel_futures=True)
        except FuturesTimeoutError:
            last_error = TimeoutError(
                f"Watsonx call exceeded {HARD_TIMEOUT_SECONDS:.0f}s hard timeout"
            )
            logger.warning(
                "Watsonx timeout on attempt %s/%s", attempt + 1, max_attempts
            )
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Watsonx error on attempt %s/%s: %s",
                attempt + 1,
                max_attempts,
                type(exc).__name__,
            )

        if attempt < len(_RETRY_DELAYS_SECONDS):
            time.sleep(_RETRY_DELAYS_SECONDS[attempt])

    assert last_error is not None
    if isinstance(last_error, WatsonxError):
        raise last_error
    raise WatsonxError(f"Watsonx generate failed after {max_attempts} attempts") from last_error
