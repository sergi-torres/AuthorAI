"""Syntactic feature extraction.

Public API
----------
compute_syntactic(doc) -> dict
    Computes sentence-length stats, subordination ratio, noun-to-verb ratio,
    and passive-voice ratio from a spaCy Doc.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spacy.tokens  # type: ignore[import-untyped]

_SUBORDINATE_DEPS: frozenset[str] = frozenset({"advcl", "relcl", "ccomp", "xcomp"})

_EMPTY_RESULT: dict = {
    "avg_sentence_length_tokens": 0.0,
    "std_sentence_length_tokens": 0.0,
    "subordination_ratio": 0.0,
    "noun_to_verb_ratio": 0.0,
    "passive_voice_ratio": 0.0,
}


def compute_syntactic(doc: spacy.tokens.Doc) -> dict:
    """Return syntactic metrics for *doc*.

    Parameters
    ----------
    doc:
        A spaCy ``Doc`` object produced by any ``en_core_web_*`` model with the
        dependency parser enabled.  The model **must not** be loaded inside this
        function.

    Returns
    -------
    dict with keys:
        ``avg_sentence_length_tokens``  - mean sentence length in tokens.
        ``std_sentence_length_tokens``  - standard deviation of sentence length.
            Returns ``0.0`` when there is only one sentence (stdev undefined).
        ``subordination_ratio``         - subordinate clause tokens per sentence.
            Dep labels counted: advcl, relcl, ccomp, xcomp.  Normalized per
            sentence (not per token) so it is not confounded by sentence length.
        ``noun_to_verb_ratio``          - NOUN count / VERB count across all
            tokens.  Returns ``0.0`` when there are no VERB tokens.
        ``passive_voice_ratio``         - proportion of sentences that contain
            at least one token with ``dep_ == "nsubjpass"``.

    All values are ``float``.  An empty doc (no tokens, no sentences) returns
    ``0.0`` for every key.

    Notes
    -----
    * ``statistics.stdev`` is used for sentence-length std, matching the
      definition in docs/style_features.md §2.1 (sample std, ddof=1).
    * No spaCy model is loaded here; the caller owns the model lifecycle.
    """
    # -- sentence lengths ------------------------------------------------------
    lengths = [len(sent) for sent in doc.sents]

    if not lengths:
        return dict(_EMPTY_RESULT)

    n_sents = len(lengths)
    avg_sentence_length_tokens = statistics.mean(lengths)
    # statistics.stdev requires at least 2 data points (sample std, ddof=1).
    std_sentence_length_tokens = statistics.stdev(lengths) if n_sents > 1 else 0.0

    # -- subordination ratio ---------------------------------------------------
    # Count tokens whose dep_ label marks them as roots of a subordinate clause,
    # then normalize per sentence so the metric is not driven by sentence length.
    subordinate_count = sum(1 for t in doc if t.dep_ in _SUBORDINATE_DEPS)
    subordination_ratio = subordinate_count / n_sents

    # -- noun-to-verb ratio ----------------------------------------------------
    nouns = sum(1 for t in doc if t.pos_ == "NOUN")
    verbs = sum(1 for t in doc if t.pos_ == "VERB")
    noun_to_verb_ratio = nouns / verbs if verbs > 0 else 0.0

    # -- passive voice ratio ---------------------------------------------------
    passive_sentences = sum(1 for sent in doc.sents if any(t.dep_ == "nsubjpass" for t in sent))
    passive_voice_ratio = passive_sentences / n_sents

    return {
        "avg_sentence_length_tokens": float(avg_sentence_length_tokens),
        "std_sentence_length_tokens": float(std_sentence_length_tokens),
        "subordination_ratio": float(subordination_ratio),
        "noun_to_verb_ratio": float(noun_to_verb_ratio),
        "passive_voice_ratio": float(passive_voice_ratio),
    }
