"""Stylistic feature extraction.

Public API
----------
compute_stylistic(doc) -> dict
    Computes punct_distribution, pos_distribution, dialogue_ratio, and
    first_person_ratio from a spaCy Doc.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spacy.tokens  # type: ignore[import-untyped]

# ── constants ──────────────────────────────────────────────────────────────────

_PUNCT_MARKS: frozenset[str] = frozenset({",", ".", ";", ":", "—", "?", "!", '"'})

_TRACKED_POS: tuple[str, ...] = (
    "NOUN",
    "VERB",
    "ADJ",
    "ADV",
    "DET",
    "ADP",
    "PRON",
    "CONJ",
    "SCONJ",
)

_FIRST_PERSON: frozenset[str] = frozenset({"i", "me", "my", "mine", "myself"})

# Canonical zero-valued dicts used for empty-doc early-return (never mutated).
_EMPTY_PUNCT: dict[str, float] = {mark: 0.0 for mark in _PUNCT_MARKS}
_EMPTY_POS: dict[str, float] = {tag: 0.0 for tag in _TRACKED_POS} | {"OTHER": 0.0}


def compute_stylistic(doc: spacy.tokens.Doc) -> dict:
    """Return stylistic metrics for *doc*.

    Parameters
    ----------
    doc:
        A spaCy ``Doc`` object.  The model **must not** be loaded inside this
        function.

    Returns
    -------
    dict with keys:
        ``punct_distribution``  - dict[str, float] with exactly 8 keys
            (the tracked punctuation marks).  Values are relative frequencies
            over all punctuation tokens; they sum to ~1.0.  Marks absent from
            *doc* are included with value 0.0.
        ``pos_distribution``    - dict[str, float] with exactly 10 keys
            (9 universal POS tags + "OTHER").  Values are relative frequencies
            over all non-punctuation tokens; they sum to 1.0.
        ``dialogue_ratio``      - float in [0, 1].  Proportion of
            non-punctuation tokens that appear between straight ASCII
            double-quote tokens (``"``).
        ``first_person_ratio``  - float ≥ 0.  Count of first-person singular
            pronouns per 1,000 tokens (total doc length, not just alpha).

    An empty doc returns 0.0 / empty distributions for every metric.

    Notes
    -----
    * ``dialogue_ratio`` uses ``token.text == '"'`` (straight ASCII quote,
      U+0022) as the toggle signal, matching the cleaner's normalisation.
    * ``first_person_ratio`` uses ``token.lower_`` so it is case-insensitive
      and does not depend on POS tagging.
    * No spaCy model is loaded here; the caller owns the model lifecycle.
    """
    if len(doc) == 0:
        return {
            "punct_distribution": dict(_EMPTY_PUNCT),
            "pos_distribution": dict(_EMPTY_POS),
            "dialogue_ratio": 0.0,
            "first_person_ratio": 0.0,
        }

    # ── punct_distribution ────────────────────────────────────────────────────
    # Count every token whose text is one of the tracked marks, then normalize.
    raw_punct: Counter[str] = Counter(t.text for t in doc if t.text in _PUNCT_MARKS)
    punct_total = sum(raw_punct.values())
    if punct_total > 0:
        punct_distribution: dict[str, float] = {
            mark: raw_punct[mark] / punct_total for mark in _PUNCT_MARKS
        }
    else:
        punct_distribution = dict(_EMPTY_PUNCT)

    # ── pos_distribution ──────────────────────────────────────────────────────
    # Count POS tags for non-punctuation tokens; normalize over tracked tags;
    # assign the remainder to "OTHER".
    raw_pos: Counter[str] = Counter(t.pos_ for t in doc if not t.is_punct)
    tracked_total = sum(raw_pos[tag] for tag in _TRACKED_POS)
    all_non_punct = sum(raw_pos.values())

    if all_non_punct > 0:
        pos_distribution: dict[str, float] = {
            tag: raw_pos[tag] / all_non_punct for tag in _TRACKED_POS
        }
        # OTHER = everything that is not punctuation and not in _TRACKED_POS.
        # Using 1 - sum(tracked) keeps the total at exactly 1.0.
        pos_distribution["OTHER"] = 1.0 - (tracked_total / all_non_punct)
    else:
        pos_distribution = dict(_EMPTY_POS)

    # ── dialogue_ratio ────────────────────────────────────────────────────────
    # Toggle in_dialogue on each straight ASCII quote token; count non-quote
    # tokens that appear while in_dialogue is True.  The denominator is every
    # non-quote token (both inside and outside dialogue).
    in_dialogue = False
    dialogue_tokens = 0
    non_quote_total = 0

    for token in doc:
        if token.text == '"':
            in_dialogue = not in_dialogue
            continue
        non_quote_total += 1
        if in_dialogue:
            dialogue_tokens += 1

    dialogue_ratio = dialogue_tokens / non_quote_total if non_quote_total > 0 else 0.0

    # ── first_person_ratio ────────────────────────────────────────────────────
    # Count {i, me, my, mine, myself} (case-insensitive via lower_) then scale
    # to per-1,000 tokens using the full doc length as the denominator.
    fp_count = sum(1 for t in doc if t.lower_ in _FIRST_PERSON)
    first_person_ratio = (fp_count / len(doc)) * 1000.0

    return {
        "punct_distribution": punct_distribution,
        "pos_distribution": pos_distribution,
        "dialogue_ratio": float(dialogue_ratio),
        "first_person_ratio": float(first_person_ratio),
    }
