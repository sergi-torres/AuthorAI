"""Unit tests for ai_pipeline/autoria_ai/generator.orchestrate.

All heavy deps (spaCy, sentence-transformers, Watsonx, RAG, passport) are
injected as mocks — no live models or network.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autoria_ai import generator as gen


class _FakeWatsonxError(RuntimeError):
    """Stand-in so tests do not import ibm_watsonx_ai."""


def _install_fake_watsonx_module() -> None:
    if "app" not in sys.modules:
        sys.modules["app"] = types.ModuleType("app")
    if "app.services" not in sys.modules:
        sys.modules["app.services"] = types.ModuleType("app.services")
        sys.modules["app"].services = sys.modules["app.services"]  # type: ignore[attr-defined]

    mod = types.ModuleType("app.services.watsonx_client")
    mod.WatsonxError = _FakeWatsonxError  # type: ignore[attr-defined]
    mod.generate = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.watsonx_client"] = mod
    sys.modules["app.services"].watsonx_client = mod  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _stub_models(monkeypatch: pytest.MonkeyPatch):
    fake_nlp = MagicMock(name="nlp")
    fake_emb = MagicMock(name="emb")
    fake_emb.encode = MagicMock(return_value=[0.1] * 768)

    monkeypatch.setattr(gen, "_nlp", fake_nlp)
    monkeypatch.setattr(gen, "_embedding_model", fake_emb)
    monkeypatch.setattr(gen, "_tok_enc", MagicMock(encode=lambda t: list(range(5))))
    monkeypatch.setattr(gen, "_ensure_models", lambda: (fake_nlp, fake_emb))
    _install_fake_watsonx_module()


def _wx_side_effect(
    prompt: str, system_prompt: str | None, model_id: str, params: Any
) -> str:
    if system_prompt is None:
        return "VANILLA_TEXT"
    return "AUTORIA_TEXT"


def _scores(*values: int):
    it = iter(values)

    def _score(*_a: Any, **_k: Any) -> int:
        return next(it)

    return _score


@pytest.mark.asyncio
async def test_orchestrate_happy_path_shape():
    chunks = [
        {
            "id": "c1",
            "document_id": "d1",
            "chunk_index": 0,
            "text": "It was the best of times.",
        }
    ]
    envelope = {"jws_token": "eyJ.stub", "json_payload": {"fit_score": 80}}
    rag = AsyncMock(return_value=chunks)
    issue = MagicMock(return_value=envelope)

    result = await gen.orchestrate(
        prompt="Write a street scene.",
        style_profile={"author_id": "dickens", "semantic_centroid": [0.0] * 768},
        author_id="dickens",
        author_uuid="11111111-1111-1111-1111-111111111111",
        generate_fn=_wx_side_effect,
        verifier_url="https://autoria.app/verify",
        retrieve_fn=rag,
        build_prompt_fn=lambda _p, _c: "SYS",
        score_fn=_scores(30, 80),
        issue_passport_fn=issue,
    )

    assert set(result.keys()) == {"vanilla", "autoria", "passport"}
    assert result["vanilla"]["text"] == "VANILLA_TEXT"
    assert result["vanilla"]["fit_score"] == 30
    assert result["autoria"]["text"] == "AUTORIA_TEXT"
    assert result["autoria"]["fit_score"] == 80
    assert result["passport"] is envelope
    assert result["vanilla"]["latency_ms"] >= 0
    assert result["autoria"]["latency_ms"] >= 0

    rag.assert_awaited_once()
    assert rag.await_args.kwargs["author_id"] == "11111111-1111-1111-1111-111111111111"

    issue.assert_called_once()
    issue_kwargs = issue.call_args.kwargs
    assert issue_kwargs["contribution_note"]
    assert issue_kwargs["verifier_url"] == "https://autoria.app/verify"
    assert issue_kwargs["fit_score"] == 80
    assert issue_kwargs["rag_sources"][0]["doc_id"] == "d1"
    assert "snippet_text" in issue_kwargs["rag_sources"][0]


@pytest.mark.asyncio
async def test_vanilla_none_autoria_gets_system_prompt():
    calls: list[tuple[str | None, str]] = []

    def wx(prompt: str, system_prompt: str | None, model_id: str, params: Any) -> str:
        calls.append((system_prompt, model_id))
        return "ok"

    await gen.orchestrate(
        prompt="p",
        style_profile={"author_id": "poe"},
        author_id="poe",
        author_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        model_id="meta-llama/llama-3-3-70b-instruct",
        generate_fn=wx,
        retrieve_fn=AsyncMock(return_value=[]),
        build_prompt_fn=lambda _p, _c: "CONDITIONED",
        score_fn=lambda *_a, **_k: 50,
        issue_passport_fn=lambda **_k: {"jws_token": "t", "json_payload": {}},
    )

    assert len(calls) == 2
    system_prompts = {c[0] for c in calls}
    assert None in system_prompts
    assert "CONDITIONED" in system_prompts
    assert all(c[1] == "meta-llama/llama-3-3-70b-instruct" for c in calls)


@pytest.mark.asyncio
async def test_vanilla_failure_degrades_autoria_still_ok():
    def wx(prompt: str, system_prompt: str | None, model_id: str, params: Any) -> str:
        if system_prompt is None:
            raise _FakeWatsonxError("vanilla timeout")
        return "AUTORIA_OK"

    result = await gen.orchestrate(
        prompt="p",
        style_profile={"author_id": "austen"},
        author_id="austen",
        generate_fn=wx,
        retrieve_fn=AsyncMock(return_value=[]),
        build_prompt_fn=lambda _p, _c: "SYS",
        score_fn=lambda *_a, **_k: 70,
        issue_passport_fn=lambda **_k: {"jws_token": "t", "json_payload": {}},
    )

    assert result["vanilla"]["text"] == gen._FAILED_BRANCH_TEXT
    assert result["vanilla"]["fit_score"] == 0
    assert result["autoria"]["text"] == "AUTORIA_OK"
    assert result["passport"]["jws_token"] == "t"


@pytest.mark.asyncio
async def test_autoria_failure_raises():
    def wx(prompt: str, system_prompt: str | None, model_id: str, params: Any) -> str:
        if system_prompt is None:
            return "VANILLA_OK"
        raise _FakeWatsonxError("autoria down")

    with pytest.raises(_FakeWatsonxError, match="autoria down"):
        await gen.orchestrate(
            prompt="p",
            style_profile={"author_id": "dickens"},
            author_id="dickens",
            generate_fn=wx,
            retrieve_fn=AsyncMock(return_value=[]),
            build_prompt_fn=lambda _p, _c: "SYS",
            score_fn=lambda *_a, **_k: 1,
            issue_passport_fn=lambda **_k: {"jws_token": "t", "json_payload": {}},
        )


@pytest.mark.asyncio
async def test_rag_failure_continues_with_empty_chunks():
    cond_chunks: list[list[str]] = []

    def build_prompt(_profile: dict, chunks: list[str]) -> str:
        cond_chunks.append(chunks)
        return "SYS"

    issue = MagicMock(return_value={"jws_token": "t", "json_payload": {}})

    result = await gen.orchestrate(
        prompt="p",
        style_profile={"author_id": "poe"},
        author_id="poe",
        generate_fn=_wx_side_effect,
        retrieve_fn=AsyncMock(side_effect=RuntimeError("db down")),
        build_prompt_fn=build_prompt,
        score_fn=lambda *_a, **_k: 40,
        issue_passport_fn=issue,
    )

    assert result["autoria"]["text"] == "AUTORIA_TEXT"
    assert cond_chunks == [[]]
    assert issue.call_args.kwargs["rag_sources"] == []
