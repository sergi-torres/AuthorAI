"""Conditioned system-prompt builder.

Public API
----------
build_system_prompt(style_profile, rag_chunks) -> str
    Composes the Watsonx (Llama 3.3 70B) system prompt that conditions the LLM
    to adopt an author's exact style, following the template in docs/MVP.md §4.3.

Latency contract
----------------
The returned string is kept under ~1200 tokens (architecture.md §6).  The
safeguard is applied by truncating ``rag_chunks`` to at most 5 items before
they are interpolated.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_CHUNKS: int = 5
_MAX_VOCAB_TERMS: int = 15

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
        At most ``_MAX_CHUNKS`` (5) are used; any extras are silently dropped to
        keep the prompt within the ~1200-token latency budget.

    Returns
    -------
    str
        A fully-rendered system prompt string ready to be passed as the
        ``system`` parameter of a Watsonx chat-completion call.
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

    #  -- distinctive vocab (top 10–15 terms to avoid token bloat) -------------
    raw_vocab: list[dict] = style_profile.get("distinctive_vocab", [])
    top_terms: list[str] = [
        entry["term"] for entry in raw_vocab[:_MAX_VOCAB_TERMS] if "term" in entry
    ]
    vocab_list: str = ", ".join(top_terms) if top_terms else "vivid and precise language"

    # -- rag chunks (enforce hard cap of 5) ------------------------------------
    safe_chunks: list[str] = rag_chunks[:_MAX_CHUNKS]
    chunks_text = " | ".join(safe_chunks) if safe_chunks else "(no example passages provided)"

    return _TEMPLATE.format(
        author_id=author_id,
        avg_sentence_length=avg_sl_str,
        subordination_rule=subordination_rule,
        vocab_list=vocab_list,
        chunks=chunks_text,
    )
