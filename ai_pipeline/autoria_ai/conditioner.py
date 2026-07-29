"""Conditioned system-prompt builder.

Public API
----------
build_system_prompt(style_profile, rag_chunks) -> str
    Composes the Watsonx (Llama 3.3 70B) system prompt that conditions the LLM
    to adopt an author's exact style, following the template in docs/MVP.md §4.3.

Latency contract
-----------------
The returned string is kept at or under ``_MAX_PROMPT_TOKENS`` (1200 tokens,
cl100k_base) — the stricter of the two figures in circulation (architecture.md
§6 says "< ~1200 tok"; issue #23 said "< 2000"). Two safeguards apply, in
order:

1. ``rag_chunks`` is capped to at most ``_MAX_CHUNKS`` (5) items. This bounds
   the *number* of passages but, since each chunk can be up to ~500 tokens
   (the RAG chunking window — see ``backend/app/routes/authors.py`` and
   ``scripts/seed_corpus.py``), does **not** by itself bound token count: 5
   chunks alone can exceed 2500 tokens before the rest of the template is
   even added.
2. The capped chunks are then packed against the *actual* remaining token
   budget (total budget minus everything else the template renders). Chunks
   that fit whole are kept as-is; the first chunk that doesn't fit is
   truncated to the last full sentence (or, failing that, the last full
   word) within budget rather than being cut off mid-word or dropped
   outright; any chunks after that are omitted.
"""

from __future__ import annotations

import re

import tiktoken

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_CHUNKS: int = 5
_MAX_VOCAB_TERMS: int = 15

# docs/architecture.md §6: "lean system prompt (< ~1200 tok)". This is the
# stricter of the two numbers in circulation (issue #23 cites "< 2000"); the
# more restrictive one wins per the module's dispatch instructions.
_MAX_PROMPT_TOKENS: int = 1200

# Loaded once at import, matching the pattern used by
# autoria_ai/extractor/chunker.py and autoria_ai/extractor/style_profile.py.
_ENCODER = tiktoken.get_encoding("cl100k_base")

_CHUNK_SEPARATOR = " | "
_NO_CHUNKS_FALLBACK = "(no example passages provided)"

# Sentence end: terminal punctuation, optional closing quote/bracket, then
# whitespace. Used to back a truncated passage off to a clean boundary.
_SENTENCE_END_RE = re.compile(r"[.!?][\"'\u201d\u2019)\]]*\s")

# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

_TEMPLATE = (
    "Write in the style of author {author_id}. "
    "Your writing must have: average sentence length ~{avg_sentence_length} tokens "
    "with high variation, {subordination_rule}, and vocabulary including terms like "
    "{vocab_list}. "
    "Here are example passages: {chunks}. "
    "Write only in that style; do not explain."
)


def _token_count(text: str) -> int:
    return len(_ENCODER.encode(text))


def _clip_to_boundary(text: str) -> str:
    """Back `text` off to its last full sentence, else its last full word.

    Returns "" if neither a sentence nor a word boundary exists (e.g. `text`
    is a single partial word), so the caller can drop it instead of emitting
    a fragment.
    """
    matches = list(_SENTENCE_END_RE.finditer(text))
    if matches:
        return text[: matches[-1].end()].rstrip()
    last_space = text.rfind(" ")
    if last_space > 0:
        return text[:last_space].rstrip()
    return ""


def _fit_chunks_to_token_budget(chunks: list[str], budget_tokens: int) -> list[str]:
    """Pack `chunks` in order into `budget_tokens`, truncating the first one
    that doesn't fit whole to a clean boundary, and dropping the rest.
    """
    if budget_tokens <= 0:
        return []

    kept: list[str] = []
    used = 0
    for chunk in chunks:
        sep_cost = _token_count(_CHUNK_SEPARATOR) if kept else 0
        remaining = budget_tokens - used - sep_cost
        if remaining <= 0:
            break

        chunk_tokens = _ENCODER.encode(chunk)
        if len(chunk_tokens) <= remaining:
            kept.append(chunk)
            used += sep_cost + len(chunk_tokens)
            continue

        truncated = _ENCODER.decode(chunk_tokens[:remaining]).strip()
        clipped = _clip_to_boundary(truncated)
        if clipped:
            kept.append(clipped)
        break

    return kept


def build_system_prompt(style_profile: dict, rag_chunks: list[str]) -> str:
    """Compose the conditioned system prompt for the Watsonx LLM.

    Parameters
    ----------
    style_profile:
        A StyleProfile v1.0 dict (see ``autoria_ai/schemas/style_profile.json``).
        Missing keys are handled with safe fallbacks so the function never raises
        on a partial profile.
    rag_chunks:
        Retrieved example passages (top-k by cosine similarity from pgvector).
        At most ``_MAX_CHUNKS`` (5) are considered; the result is then packed
        into the remaining token budget (see module docstring), so the
        returned prompt never exceeds ``_MAX_PROMPT_TOKENS`` tokens
        regardless of how long the individual chunks are.

    Returns
    -------
    str
        A fully-rendered system prompt string ready to be passed as the
        ``system`` parameter of a Watsonx chat-completion call, guaranteed to
        be at most ``_MAX_PROMPT_TOKENS`` tokens under cl100k_base.
    """
    # -- author id -------------------------------------------------------------
    author_id: str = style_profile.get("author_id", "unknown")

    # -- avg sentence length ---------------------------------------------------
    syntactic: dict = style_profile.get("syntactic", {})
    avg_sentence_length: float = syntactic.get("avg_sentence_length_tokens", 20.0)
    # Format as integer-like when it's a whole number, otherwise one decimal.
    avg_sl_str = (
        str(int(avg_sentence_length))
        if avg_sentence_length == int(avg_sentence_length)
        else f"{avg_sentence_length:.1f}"
    )

    # -- subordination rule (natural language translation) ---------------------
    subordination_ratio: float = syntactic.get("subordination_ratio", 0.0)
    if subordination_ratio >= 0.3:
        subordination_rule = "heavy use of subordinate clauses"
    elif subordination_ratio >= 0.15:
        subordination_rule = "moderate use of subordinate clauses"
    else:
        subordination_rule = "straightforward clause structure with few subordinate clauses"

    #  -- distinctive vocab (top 10-15 terms to avoid token bloat) -------------
    raw_vocab: list[dict] = style_profile.get("distinctive_vocab", [])
    top_terms: list[str] = [
        entry["term"] for entry in raw_vocab[:_MAX_VOCAB_TERMS] if "term" in entry
    ]
    vocab_list: str = ", ".join(top_terms) if top_terms else "vivid and precise language"

    # -- rag chunks: count cap first (existing safeguard), then token budget --
    count_capped_chunks: list[str] = rag_chunks[:_MAX_CHUNKS]

    # Everything except `chunks` is fixed at this point, so the true chunk
    # budget is whatever tokens are left after rendering the rest of the
    # template with the "no passages" fallback in place of the real chunks.
    fixed_prompt = _TEMPLATE.format(
        author_id=author_id,
        avg_sentence_length=avg_sl_str,
        subordination_rule=subordination_rule,
        vocab_list=vocab_list,
        chunks=_NO_CHUNKS_FALLBACK,
    )
    fixed_cost = _token_count(fixed_prompt) - _token_count(_NO_CHUNKS_FALLBACK)
    chunk_budget = max(0, _MAX_PROMPT_TOKENS - fixed_cost)

    safe_chunks = _fit_chunks_to_token_budget(count_capped_chunks, chunk_budget)
    chunks_text = _CHUNK_SEPARATOR.join(safe_chunks) if safe_chunks else _NO_CHUNKS_FALLBACK

    prompt = _TEMPLATE.format(
        author_id=author_id,
        avg_sentence_length=avg_sl_str,
        subordination_rule=subordination_rule,
        vocab_list=vocab_list,
        chunks=chunks_text,
    )

    # Defense in depth: BPE merges across the chunk/template boundary can
    # shift the count by a token or two relative to the estimate above. If
    # that ever pushes the total over budget, drop the last chunk and retry
    # rather than ship a prompt over the contract.
    while _token_count(prompt) > _MAX_PROMPT_TOKENS and safe_chunks:
        safe_chunks = safe_chunks[:-1]
        chunks_text = _CHUNK_SEPARATOR.join(safe_chunks) if safe_chunks else _NO_CHUNKS_FALLBACK
        prompt = _TEMPLATE.format(
            author_id=author_id,
            avg_sentence_length=avg_sl_str,
            subordination_rule=subordination_rule,
            vocab_list=vocab_list,
            chunks=chunks_text,
        )

    return prompt
