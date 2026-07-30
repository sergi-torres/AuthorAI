"""Distinctive vocabulary extraction — §4.1 of docs/style_features.md.

Public API
----------
compute_distinctive_vocab(corpora_lemmas, author_id, top_n=30) -> list[dict]
    Returns the top-*n* log-odds-ratio signature terms for *author_id* relative
    to the other authors in *corpora_lemmas*.

Algorithm change (2026-07-30)
-----------------------------
Replaced TF-IDF with **log-odds-ratio** (Jeffreys prior, α=0.5).

Why log-odds-ratio is better here:
- TF-IDF with 3 documents is dominated by raw term frequency.  A word like
  "good" that appears 8 000 times in Austen and 6 000 times in Dickens will
  outscore "elegance" (300 vs 10 occurrences) because its absolute count is
  larger even after IDF.
- Log-odds-ratio directly measures *how much more likely* a term is in this
  author's corpus than in the others combined.  A word used at the same rate
  by every author scores ≈ 0 regardless of frequency.  A word ten times more
  common in Poe than in Austen+Dickens combined scores high even if it is rare
  in absolute terms.

Formula
-------
  p_a  = (count_in_author   + α) / (total_author_tokens   + 2α)
  p_o  = (count_in_others   + α) / (total_other_tokens    + 2α)
  log_odds = log(p_a / (1 − p_a)) − log(p_o / (1 − p_o))

Scores are normalized by dividing by the maximum raw log-odds in this run so
the output range is [0, 1].

Lemma input is expected already POS-filtered to NOUN/ADJ/ADV (and free of
corpus-metadata stops) by ``style_profile._lemmas_from_docs`` — see §4.1.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Matches the POS-filtered lemma string produced by _lemmas_from_docs:
# alpha-only, minimum 3 characters.
_TOKEN_RE = re.compile(r"(?u)\b[a-zA-Z]{3,}\b")

# Jeffreys prior — avoids log(0) and is less biased than add-1 for sparse counts.
_SMOOTH: float = 0.5


def compute_distinctive_vocab(
    corpora_lemmas: dict[str, str],
    author_id: str,
    top_n: int = 30,
) -> list[dict]:
    """Return the top-*n* log-odds-ratio signature terms for *author_id*.

    Parameters
    ----------
    corpora_lemmas:
        Mapping of ``author_id → lemmatized corpus text``.  Each value is the
        full lemmatized corpus already produced by a prior spaCy pass — this
        function does **not** load spaCy or re-lemmatize anything.
    author_id:
        Key in *corpora_lemmas* whose top terms are returned.
    top_n:
        Maximum number of terms to return (default 30, per §4.1).

    Returns
    -------
    list[dict]
        Each element is ``{"term": str, "score": float}`` where *score* is
        normalized to [0, 1] by dividing by the maximum raw log-odds in this
        run.  Sorted by score descending.  The list may be shorter than *top_n*
        when fewer than *top_n* terms have a positive log-odds ratio.

    Notes
    -----
    * Terms in sklearn's English stop-word list are excluded.
    * No spaCy model is loaded here; the caller owns the model lifecycle.
    """
    if author_id not in corpora_lemmas:
        raise KeyError(f"author_id {author_id!r} not found in corpora_lemmas")

    # ── tokenize ──────────────────────────────────────────────────────────────
    author_tokens = _TOKEN_RE.findall(corpora_lemmas[author_id])
    other_tokens: list[str] = []
    for slug, text in corpora_lemmas.items():
        if slug != author_id:
            other_tokens.extend(_TOKEN_RE.findall(text))

    author_counts: Counter[str] = Counter(author_tokens)
    other_counts: Counter[str] = Counter(other_tokens)

    total_a = max(sum(author_counts.values()), 1)
    total_o = max(sum(other_counts.values()), 1)

    # ── log-odds-ratio ─────────────────────────────────────────────────────────
    raw_scores: dict[str, float] = {}
    for term, count_a in author_counts.items():
        if term in ENGLISH_STOP_WORDS:
            continue
        count_o = other_counts.get(term, 0)

        # Proportions with Jeffreys prior (add α to numerator and 2α to total)
        p_a = (count_a + _SMOOTH) / (total_a + 2 * _SMOOTH)
        p_o = (count_o + _SMOOTH) / (total_o + 2 * _SMOOTH)

        # Log-odds: log(p/(1-p)) − log(q/(1-q))
        log_odds = math.log(p_a / (1.0 - p_a)) - math.log(p_o / (1.0 - p_o))

        # Only keep terms that are more characteristic of this author, not less.
        if log_odds > 0:
            raw_scores[term] = log_odds

    if not raw_scores:
        return []

    # ── normalize to [0, 1] ───────────────────────────────────────────────────
    max_score = max(raw_scores.values())
    ranked = sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)

    return [
        {"term": term, "score": round(score / max_score, 4)}
        for term, score in ranked[:top_n]
    ]
