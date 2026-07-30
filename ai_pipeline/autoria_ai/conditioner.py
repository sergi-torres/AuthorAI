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
    "You are writing as {author_id}. Every sentence must be indistinguishable "
    "from their published prose. Obey ALL of the following constraints — they are "
    "non-negotiable:\n"
    "1. SENTENCE LENGTH: Target an average of exactly {avg_sentence_length} words per sentence. "
    "Match the rhythm and length of the provided passages.\n"
    "2. SYNTACTIC COMPLEXITY: {subordination_rule}.\n"
    "3. NARRATIVE MODE: {dialogue_rule}\n"
    "4. SIGNATURE VOCABULARY — these words are statistically unique to {author_id}'s "
    "writing. Weave as many as naturally possible into your prose: {vocab_list}.\n"
    "5. TONE AND REGISTER: Match the emotional register, irony level, and narrative "
    "distance demonstrated in the example passages below.\n\n"
    "AUTHENTIC EXAMPLE PASSAGES from {author_id} "
    "(study rhythm, diction and voice — do not copy verbatim):\n"
    "---\n"
    "{chunks}\n"
    "---\n\n"
    "Write ONLY the requested text in {author_id}'s voice. "
    "No preamble, no meta-commentary, no explanations."
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
    """Compose the conditioned system prompt for the Watsonx LLM."""
    # -- author id -------------------------------------------------------------
    author_id: str = style_profile.get("author_id", "unknown")

    # -- avg sentence length ---------------------------------------------------
    syntactic: dict = style_profile.get("syntactic", {})
    avg_sentence_length: float = syntactic.get("avg_sentence_length_tokens", 20.0)
    avg_sl_str = (
        str(int(avg_sentence_length))
        if avg_sentence_length == int(avg_sentence_length)
        else f"{avg_sentence_length:.1f}"
    )

    # -- subordination rule (natural language translation) ---------------------
    subordination_ratio: float = syntactic.get("subordination_ratio", 0.0)
    if subordination_ratio >= 0.3:
        subordination_rule = (
            "heavy use of subordinate clauses, BUT you MUST still use periods (.) to end sentences "
            "and avoid massive run-on sentences. Do not exceed the target average sentence length."
        )
    elif subordination_ratio >= 0.15:
        subordination_rule = "moderate use of subordinate clauses"
    else:
        subordination_rule = "straightforward clause structure with few subordinate clauses"
    # -- dialogue rule (dialogue_ratio lives under stylistic, not syntactic) ---
    stylistic: dict = style_profile.get("stylistic", {})
    dialogue_ratio: float = stylistic.get("dialogue_ratio", 0.0)
    if dialogue_ratio >= 0.15:
        dialogue_rule = "Integrate conversational dialogue frequently, mirroring the author's formatting and pacing."
    elif dialogue_ratio >= 0.05:
        dialogue_rule = "Use dialogue sparingly and only when appropriate to the scene."
    else:
        dialogue_rule = "Focus heavily on prose and internal exposition; avoid dialogue unless strictly necessary."

    #  -- distinctive vocab (top 10-15 terms to avoid token bloat) -------------
    raw_vocab: list[dict] = style_profile.get("distinctive_vocab", [])
    top_terms: list[str] = [
        entry["term"] for entry in raw_vocab[:_MAX_VOCAB_TERMS] if "term" in entry
    ]
    vocab_list: str = ", ".join(top_terms) if top_terms else "vivid and precise language"

    # -- rag chunks: count cap first (existing safeguard), then token budget --
    count_capped_chunks: list[str] = rag_chunks[:_MAX_CHUNKS]

    fixed_prompt = _TEMPLATE.format(
        author_id=author_id,
        avg_sentence_length=avg_sl_str,
        max_sentence_length=str(int(avg_sentence_length * 1.5)),
        subordination_rule=subordination_rule,
        dialogue_rule=dialogue_rule,
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
        max_sentence_length=str(int(avg_sentence_length * 1.5)),
        subordination_rule=subordination_rule,
        dialogue_rule=dialogue_rule,
        vocab_list=vocab_list,
        chunks=chunks_text,
    )

    while _token_count(prompt) > _MAX_PROMPT_TOKENS and safe_chunks:
        safe_chunks = safe_chunks[:-1]
        chunks_text = _CHUNK_SEPARATOR.join(safe_chunks) if safe_chunks else _NO_CHUNKS_FALLBACK
        prompt = _TEMPLATE.format(
            author_id=author_id,
            avg_sentence_length=avg_sl_str,
            max_sentence_length=str(int(avg_sentence_length * 1.5)),
            subordination_rule=subordination_rule,
            dialogue_rule=dialogue_rule,
            vocab_list=vocab_list,
            chunks=chunks_text,
        )

    return prompt
