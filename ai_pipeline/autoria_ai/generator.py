"""Generation orchestrator — the single entry-point for POST /api/generate.

Public API
----------
orchestrate(prompt, style_profile, author_id, ...) -> dict
    Run two parallel Watsonx calls (vanilla + style-conditioned), score both
    with fit_score, mint an Authorship Passport for the AutorIA output, and
    return a dict matching the ``GenerateResponse`` wire shape.

warmup_models()
    Eager-load spaCy + sentence-transformers.  Call from FastAPI lifespan so
    the first user request does not pay cold-start under the 10s FE timeout.

Model loading
-------------
Models are loaded lazily on first use (or via ``warmup_models``).  They are
process-level singletons — never reload per request.

Parallelism
-----------
Watsonx ``generate`` is sync; both branches run via ``asyncio.to_thread``.
If only the vanilla branch fails, Autoria + passport still return (vanilla
degraded).  If Autoria fails, ``WatsonxError`` is raised (passport required).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Callable
from typing import Any

import tiktoken

logger = logging.getLogger(__name__)

WATSONX_MODEL_ID: str = "meta-llama/llama-3-3-70b-instruct"

_GENERATION_PARAMS: dict[str, Any] = {
    "max_new_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.9,
}

_CONTRIBUTION_NOTE = (
    "v1: 100% AI-assisted. Human-edit tracking is in the roadmap."
)
_DEFAULT_VERIFIER_URL = "https://autoria.app/verify"
_FAILED_BRANCH_TEXT = "[Generation failed for this branch]"

# Process-level singletons — populated by warmup_models() / _ensure_models().
_nlp: Any | None = None
_embedding_model: Any | None = None
_tok_enc: Any | None = None


def _ensure_models() -> tuple[Any, Any]:
    """Load spaCy + sentence-transformers once; return (nlp, embedding_model)."""
    global _nlp, _embedding_model, _tok_enc
    if _nlp is None:
        import spacy

        logger.info("Loading spaCy en_core_web_lg ...")
        _nlp = spacy.load("en_core_web_lg")
        logger.info("spaCy en_core_web_lg ready.")
    if _embedding_model is None:
        # Reuse embedder singleton (loads all-mpnet-base-v2 once).
        from autoria_ai.embedder import _MODEL as emb

        _embedding_model = emb
        logger.info("sentence-transformers embedding model ready.")
    if _tok_enc is None:
        _tok_enc = tiktoken.get_encoding("cl100k_base")
    return _nlp, _embedding_model


def warmup_models() -> None:
    """Eager-load NLP models (call from FastAPI lifespan / startup)."""
    _ensure_models()


def _count_tokens(text: str) -> int:
    _, _ = _ensure_models()
    assert _tok_enc is not None
    return len(_tok_enc.encode(text))


def _default_wx_generate(
    prompt: str,
    system_prompt: str | None,
    model_id: str,
    params: dict[str, Any] | None,
) -> str:
    """Resolve Watsonx client at call time (keeps ai_pipeline importable alone)."""
    from app.services.watsonx_client import generate as wx_generate

    return wx_generate(prompt, system_prompt, model_id, params)


def _resolve_verifier_url(explicit: str | None = None) -> str:
    return (
        explicit
        or os.getenv("PASSPORT_VERIFIER_URL")
        or _DEFAULT_VERIFIER_URL
    )


async def orchestrate(
    prompt: str,
    style_profile: dict[str, Any],
    author_id: str,
    *,
    author_uuid: str | None = None,
    model_id: str = WATSONX_MODEL_ID,
    database_url: str | None = None,
    generate_fn: Callable[..., str] | None = None,
    verifier_url: str | None = None,
    retrieve_fn: Callable[..., Any] | None = None,
    build_prompt_fn: Callable[..., str] | None = None,
    score_fn: Callable[..., int] | None = None,
    issue_passport_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the full generate pipeline and return a ``GenerateResponse``-shaped dict.

    Parameters
    ----------
    prompt:
        The raw user creative prompt (1-4000 chars).
    style_profile:
        Latest StyleProfile v1.0 dict for *author_id*.
    author_id:
        Author slug (e.g. ``"dickens"``).  Stored in the passport as-is.
    author_uuid:
        ``authors.id`` UUID used to scope RAG to that author's documents.
        When omitted, RAG falls back to global ANN (not recommended in prod).
    model_id:
        Watsonx model identifier used for both branches.
    database_url:
        asyncpg DSN for pgvector RAG lookup.
    generate_fn:
        Optional override for Watsonx ``generate`` (tests inject a mock).
    verifier_url:
        Passport ``verifier_url``; falls back to env / default.
    retrieve_fn / build_prompt_fn / score_fn / issue_passport_fn:
        Optional overrides for unit tests (default: real pipeline modules).

    Raises
    ------
    WatsonxError
        If the AutorIA (conditioned) branch fails after retries — passport
        cannot be issued without it.  Vanilla-only failure degrades that
        branch instead of failing the whole request.
    """
    if retrieve_fn is None:
        from autoria_ai.db import retrieve_top_k as retrieve_fn
    if build_prompt_fn is None:
        from autoria_ai.conditioner import build_system_prompt as build_prompt_fn
    if score_fn is None:
        from autoria_ai.fit_scorer import compute_fit_score as score_fn
    if issue_passport_fn is None:
        from autoria_ai.passport.builder import issue_passport as issue_passport_fn

    nlp, embedding_model = _ensure_models()
    wx = generate_fn or _default_wx_generate

    # -- Step 1: embed the prompt for RAG retrieval ----------------------------
    prompt_embedding = await asyncio.to_thread(embedding_model.encode, prompt)

    # -- Step 2: retrieve top-5 chunks scoped to this author -------------------
    chunks: list[dict[str, Any]] = []
    try:
        chunks = await retrieve_fn(
            prompt_embedding,
            k=5,
            author_id=author_uuid,
            database_url=database_url,
        )
    except Exception:
        logger.warning(
            "RAG retrieval failed for author '%s'; continuing with empty chunks.",
            author_id,
            exc_info=True,
        )

    if not chunks:
        logger.warning(
            "No RAG chunks returned for author '%s' (DB may have no embeddings yet).",
            author_id,
        )

    if not style_profile.get("semantic_centroid"):
        logger.warning(
            "StyleProfile for '%s' has an empty semantic_centroid; "
            "semantic component of fit_score will be 0.",
            author_id,
        )

    # -- Step 3: build the conditioned system prompt ---------------------------
    rag_texts = [c["text"] for c in chunks]
    system_prompt = build_prompt_fn(style_profile, rag_texts)

    # -- Step 4: parallel Watsonx calls — same model, same params --------------
    t0 = time.monotonic()
    vanilla_result, autoria_result = await asyncio.gather(
        asyncio.to_thread(wx, prompt, None, model_id, _GENERATION_PARAMS),
        asyncio.to_thread(wx, prompt, system_prompt, model_id, _GENERATION_PARAMS),
        return_exceptions=True,
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    if isinstance(autoria_result, BaseException):
        # Passport is required → cannot degrade Autoria away.
        try:
            from app.services.watsonx_client import WatsonxError as WxErr
        except ImportError:  # pragma: no cover
            WxErr = RuntimeError  # type: ignore[misc, assignment]
        if isinstance(autoria_result, WxErr):
            raise autoria_result
        raise WxErr(f"AutorIA generation failed: {autoria_result}") from autoria_result

    autoria_text = autoria_result
    if isinstance(vanilla_result, BaseException):
        logger.warning(
            "Vanilla branch failed for author '%s'; degrading that side: %s",
            author_id,
            vanilla_result,
        )
        vanilla_text = _FAILED_BRANCH_TEXT
        vanilla_failed = True
    else:
        vanilla_text = vanilla_result
        vanilla_failed = False

    # -- Step 5: fit_score for both branches (sequential; shared nlp) ----------
    if vanilla_failed:
        vanilla_score = 0
    else:
        vanilla_score = score_fn(vanilla_text, style_profile, nlp, embedding_model)
    autoria_score = score_fn(autoria_text, style_profile, nlp, embedding_model)

    # -- Step 6: mint Authorship Passport for the AutorIA output only ----------
    rag_sources = [
        {
            "doc_id": str(c["document_id"]),
            "chunk_id": c["chunk_index"],
            "snippet_text": c["text"],
        }
        for c in chunks
    ]

    envelope = issue_passport_fn(
        author_id=author_id,
        style_profile=style_profile,
        model_id=model_id,
        user_prompt=prompt,
        output_text=autoria_text,
        output_length_tokens=_count_tokens(autoria_text),
        rag_sources=rag_sources,
        fit_score=autoria_score,
        contribution_note=_CONTRIBUTION_NOTE,
        verifier_url=_resolve_verifier_url(verifier_url),
    )

    return {
        "vanilla": {
            "text": vanilla_text,
            "fit_score": vanilla_score,
            "latency_ms": elapsed_ms,
        },
        "autoria": {
            "text": autoria_text,
            "fit_score": autoria_score,
            "latency_ms": elapsed_ms,
        },
        "passport": envelope,
    }
