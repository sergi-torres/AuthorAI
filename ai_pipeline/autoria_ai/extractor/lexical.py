"""Lexical feature extraction.

Public API
----------
compute_lexical(doc) -> dict
    Computes mattr_500, hapax_ratio, and avg_word_length from a spaCy Doc.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spacy.tokens  # type: ignore[import-untyped]


def compute_lexical(doc: spacy.tokens.Doc) -> dict:
    """Return lexical metrics for *doc*.

    Parameters
    ----------
    doc:
        A spaCy ``Doc`` object produced by any ``en_core_web_*`` model.
        The model **must not** be loaded inside this function.

    Returns
    -------
    dict with keys:
        ``mattr_500``     - Moving Average TTR, window = 500, over alpha tokens.
        ``hapax_ratio``   - Proportion of lemma types that appear exactly once.
        ``avg_word_length`` - Mean character length of alpha tokens.
        ``mattr_500``     - Moving Average TTR, window = 500, over alpha tokens.
        ``hapax_ratio``   - Proportion of lemma types that appear exactly once.
        ``avg_word_length`` - Mean character length of alpha tokens.

    All three values are ``float``.  An empty doc returns ``0.0`` for every key.
    """
    alpha_tokens = [t for t in doc if t.is_alpha]

    # ── avg_word_length ───────────────────────────────────────────────────────
    if not alpha_tokens:
        return {"mattr_500": 0.0, "hapax_ratio": 0.0, "avg_word_length": 0.0}

    avg_word_length = sum(len(t.text) for t in alpha_tokens) / len(alpha_tokens)

    # ── hapax_ratio ───────────────────────────────────────────────────────────
    freq = Counter(t.lemma_.lower() for t in alpha_tokens)
    hapax_ratio = sum(1 for v in freq.values() if v == 1) / len(freq)

    # ── mattr_500 ─────────────────────────────────────────────────────────────
    # Slide a window of WINDOW tokens across alpha_tokens and average the TTRs.
    # When the corpus is shorter than WINDOW, the single window is the full list
    # (equivalent to plain TTR), which is the standard fallback.
    WINDOW = 500
    words = [t.text.lower() for t in alpha_tokens]
    n = len(words)

    if n <= WINDOW:
        # Single window: plain TTR over all alpha tokens
        mattr_500 = len(set(words)) / n
    else:
        ttr_sum = 0.0
        num_windows = n - WINDOW + 1
        for i in range(num_windows):
            ttr_sum += len(set(words[i : i + WINDOW])) / WINDOW
        mattr_500 = ttr_sum / num_windows

    return {
        "mattr_500": float(mattr_500),
        "hapax_ratio": float(hapax_ratio),
        "avg_word_length": float(avg_word_length),
    }
