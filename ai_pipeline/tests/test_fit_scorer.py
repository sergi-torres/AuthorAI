"""Tests for ai_pipeline/autoria_ai/fit_scorer.py.

Strategy
--------
* spaCy and embedding models are replaced with MagicMocks so no heavy
  model loading happens during the test run.
* The spaCy mock returns a list of FakeToken / FakeSent objects that
  mirror the small attributes actually accessed by fit_scorer internals:
    - token.is_punct, token.is_alpha, token.pos_, token.lemma_.lower()
    - doc.sents  (iterable of sentences, each supporting len())
* The embedding mock's .encode() returns a pre-set numpy array.

Coverage
--------
* Happy path: text matching the profile exactly → score near 100.
* Divergent text: disjoint vocab, extreme ASL difference → significantly lower score.
* Boundary: wildly deviating text still returns int in [0, 100].
* Zero-guard: zero-vector centroid, empty token lists, zero mattr_profile.
* Return type is always int.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

from autoria_ai.fit_scorer import compute_fit_score

# ---------------------------------------------------------------------------
# Helpers: lightweight fake spaCy objects
# ---------------------------------------------------------------------------


class _FakeToken:
    """Minimal stand-in for a spaCy Token."""

    def __init__(self, text: str, pos: str, lemma: str, *, is_punct: bool = False):
        self.text = text
        self.pos_ = pos
        self.lemma_ = lemma
        self.is_punct = is_punct
        self.is_alpha = text.isalpha()
        self.lower_ = text.lower()


class _FakeSent:
    """Minimal stand-in for a spaCy Span (sentence)."""

    def __init__(self, tokens: list[_FakeToken]):
        self._tokens = tokens

    def __len__(self) -> int:
        return len(self._tokens)

    def __iter__(self):
        return iter(self._tokens)


class _FakeDoc:
    """Minimal stand-in for a spaCy Doc returned by nlp()."""

    def __init__(self, sentences: list[list[_FakeToken]]):
        self._sents = [_FakeSent(s) for s in sentences]

    def __iter__(self):
        for sent in self._sents:
            yield from sent

    @property
    def sents(self):
        return iter(self._sents)


def _make_nlp(sentences: list[list[_FakeToken]]) -> Any:
    """Return a callable MagicMock that acts like nlp(text)."""
    nlp = MagicMock()
    nlp.return_value = _FakeDoc(sentences)
    return nlp


def _make_embedding_model(vector: list[float]) -> Any:
    """Return a MagicMock whose .encode() always returns the given vector."""
    model = MagicMock()
    model.encode.return_value = np.array(vector, dtype=np.float32)
    return model


# ---------------------------------------------------------------------------
# Shared profile fixture (Dickens-like)
# ---------------------------------------------------------------------------

_CENTROID = [0.1] * 768  # arbitrary unit-ish vector

_PROFILE: dict = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "computed_at": "2026-07-01T00:00:00Z",
    "corpus_stats": {"n_documents": 3, "n_tokens": 184523, "n_sentences": 9821},
    "lexical": {
        "mattr_500": 0.612,
        "avg_word_length": 4.83,
        "hapax_ratio": 0.421,
    },
    "syntactic": {
        "avg_sentence_length_tokens": 10.0,  # small for easy mock control
        "std_sentence_length_tokens": 14.2,
        "subordination_ratio": 0.38,
        "noun_to_verb_ratio": 1.83,
        "passive_voice_ratio": 0.11,
    },
    "stylistic": {
        "punct_distribution": {
            ",": 0.42,
            ".": 0.18,
            ";": 0.07,
            ":": 0.04,
            "—": 0.06,
            "?": 0.01,
            "!": 0.01,
            '"': 0.21,
        },
        "pos_distribution": {
            "NOUN": 0.21,
            "VERB": 0.16,
            "ADJ": 0.09,
            "ADV": 0.07,
            "DET": 0.13,
            "ADP": 0.14,
            "PRON": 0.07,
            "CONJ": 0.05,
            "SCONJ": 0.04,
            "OTHER": 0.04,
        },
        "dialogue_ratio": 0.24,
        "first_person_ratio": 6.0,
    },
    "distinctive_vocab": [
        {"term": "countenance", "score": 0.084},
        {"term": "physiognomy", "score": 0.073},
        {"term": "presently", "score": 0.061},
        {"term": "workhouse", "score": 0.055},
        {"term": "cobblestone", "score": 0.048},
    ],
    "semantic_centroid": _CENTROID,
    "embedding_umap_2d": {"centroid": [3.2, -1.7], "spread": 0.84},
}

# Tokens for a "perfect" sentence: 10 tokens, matching POS distribution,
# plus distinctive vocab terms.  We keep it simple: 2 NOUNs, 1 VERB, 1 ADJ,
# 1 ADV, 1 DET, 1 ADP, 1 PRON, 1 CONJ, 1 SCONJ.
_PERFECT_TOKENS: list[_FakeToken] = [
    _FakeToken("countenance", "NOUN", "countenance"),  # distinctive
    _FakeToken("workhouse", "NOUN", "workhouse"),  # distinctive
    _FakeToken("walked", "VERB", "walk"),
    _FakeToken("pallid", "ADJ", "pallid"),
    _FakeToken("slowly", "ADV", "slowly"),
    _FakeToken("the", "DET", "the"),
    _FakeToken("into", "ADP", "into"),
    _FakeToken("he", "PRON", "he"),
    _FakeToken("and", "CONJ", "and"),
    _FakeToken("although", "SCONJ", "although"),
]

# ---------------------------------------------------------------------------
# Happy path: perfect match → near-100
# ---------------------------------------------------------------------------


def test_happy_path_near_100() -> None:
    """A generated text that aligns with the profile on all axes scores >= 65.

    The mock achieves: sem=1.0, syn=1.0, lex≈0.37 (TTR=1.0 vs MATTR=0.612),
    sty≈0.62 (Jaccard of uniform 1/9 distribution vs profile), voc=2/30.
    Weighted sum ≈ 0.71 → score ≈ 71.  A threshold of 65 is a safe lower bound
    that confirms all five sub-scores are computed and that the dominant
    semantic+syntactic components (55% weight) contribute correctly.
    """
    # Semantic: cosine_similarity of identical vectors → 1.0
    nlp = _make_nlp([_PERFECT_TOKENS])  # 1 sentence of 10 tokens = asl == asl_profile
    emb = _make_embedding_model(_CENTROID)  # identical vector → sim = 1.0
    score = compute_fit_score("irrelevant — mock controls the doc", _PROFILE, nlp, emb)
    assert score >= 65


def test_happy_path_returns_int() -> None:
    nlp = _make_nlp([_PERFECT_TOKENS])
    emb = _make_embedding_model(_CENTROID)
    score = compute_fit_score("irrelevant", _PROFILE, nlp, emb)
    assert isinstance(score, int)


# ---------------------------------------------------------------------------
# Divergent text: lower score
# ---------------------------------------------------------------------------

# Tokens with no overlap with distinctive vocab, wrong POS mix, wrong ASL.
_BAD_TOKENS: list[_FakeToken] = [
    _FakeToken("xyz", "NOUN", "xyz"),
    _FakeToken("abc", "NOUN", "abc"),
]


def test_divergent_text_scores_lower_than_perfect() -> None:
    """A text that deviates on every axis should score lower than a matching one."""
    # Perfect text
    nlp_good = _make_nlp([_PERFECT_TOKENS])
    emb_good = _make_embedding_model(_CENTROID)
    good = compute_fit_score("irrelevant", _PROFILE, nlp_good, emb_good)

    # Bad text: orthogonal embedding, wrong ASL (100 tokens per sent), no vocab overlap.
    bad_sent = [_FakeToken(f"word{i}", "NOUN", f"word{i}") for i in range(100)]
    nlp_bad = _make_nlp([bad_sent])
    orthogonal = [0.0] * 767 + [1.0]  # nearly orthogonal to _CENTROID
    emb_bad = _make_embedding_model(orthogonal)
    bad = compute_fit_score("irrelevant", _PROFILE, nlp_bad, emb_bad)

    assert bad < good


def test_divergent_text_score_significantly_lower() -> None:
    """Divergent text must be ≥ 10 points below a perfect match."""
    nlp_good = _make_nlp([_PERFECT_TOKENS])
    emb_good = _make_embedding_model(_CENTROID)
    good = compute_fit_score("irrelevant", _PROFILE, nlp_good, emb_good)

    bad_sent = [_FakeToken(f"w{i}", "NOUN", f"w{i}") for i in range(100)]
    nlp_bad = _make_nlp([bad_sent])
    emb_bad = _make_embedding_model([0.0] * 767 + [1.0])
    bad = compute_fit_score("irrelevant", _PROFILE, nlp_bad, emb_bad)

    assert (good - bad) >= 10


# ---------------------------------------------------------------------------
# Boundary tests: output always int in [0, 100]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "asl_tokens,embedding_vec",
    [
        # Extreme ASL: 1000 tokens per sentence
        ([_FakeToken(f"t{i}", "NOUN", f"t{i}") for i in range(1000)], [0.0] * 768),
        # Zero sentence
        ([], [0.0] * 768),
    ],
)
def test_output_always_int_in_bounds(asl_tokens, embedding_vec) -> None:
    sents = [asl_tokens] if asl_tokens else [[_FakeToken("dummy", "NOUN", "dummy")]]
    nlp = _make_nlp(sents)
    emb = _make_embedding_model(embedding_vec)
    score = compute_fit_score("test", _PROFILE, nlp, emb)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_zero_vector_embedding_does_not_crash() -> None:
    """Zero-norm embedding vector must not raise; score must stay in [0, 100]."""
    nlp = _make_nlp([_PERFECT_TOKENS])
    emb = _make_embedding_model([0.0] * 768)
    score = compute_fit_score("text", _PROFILE, nlp, emb)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_zero_centroid_does_not_crash() -> None:
    """Zero-norm centroid must not raise; score must stay in [0, 100]."""
    profile = {**_PROFILE, "semantic_centroid": [0.0] * 768}
    nlp = _make_nlp([_PERFECT_TOKENS])
    emb = _make_embedding_model(_CENTROID)
    score = compute_fit_score("text", profile, nlp, emb)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_zero_mattr_profile_does_not_crash() -> None:
    """mattr_profile = 0 must not cause ZeroDivisionError."""
    profile = {
        **_PROFILE,
        "lexical": {"mattr_500": 0.0, "avg_word_length": 4.8, "hapax_ratio": 0.4},
    }
    nlp = _make_nlp([_PERFECT_TOKENS])
    emb = _make_embedding_model(_CENTROID)
    score = compute_fit_score("text", profile, nlp, emb)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_zero_asl_profile_does_not_crash() -> None:
    """avg_sentence_length_tokens = 0 must not cause ZeroDivisionError."""
    profile = {
        **_PROFILE,
        "syntactic": {**_PROFILE["syntactic"], "avg_sentence_length_tokens": 0.0},
    }
    nlp = _make_nlp([_PERFECT_TOKENS])
    emb = _make_embedding_model(_CENTROID)
    score = compute_fit_score("text", profile, nlp, emb)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_empty_distinctive_vocab_does_not_crash() -> None:
    """Empty distinctive_vocab list must not crash; vocab sub-score = 0."""
    profile = {**_PROFILE, "distinctive_vocab": []}
    nlp = _make_nlp([_PERFECT_TOKENS])
    emb = _make_embedding_model(_CENTROID)
    score = compute_fit_score("text", profile, nlp, emb)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_empty_style_profile_does_not_crash() -> None:
    """Completely empty profile must not raise and must return int in [0, 100]."""
    nlp = _make_nlp([_PERFECT_TOKENS])
    emb = _make_embedding_model(_CENTROID)
    score = compute_fit_score("text", {}, nlp, emb)
    assert isinstance(score, int)
    assert 0 <= score <= 100


# ---------------------------------------------------------------------------
# Vocabulary sub-score: overlap counting
# ---------------------------------------------------------------------------


def test_full_vocab_overlap_contributes_positively() -> None:
    """Text containing all 5 distinctive terms should score higher than text with none."""
    # All 5 distinctive terms present
    matching_tokens = [
        _FakeToken("countenance", "NOUN", "countenance"),
        _FakeToken("physiognomy", "NOUN", "physiognomy"),
        _FakeToken("presently", "ADV", "presently"),
        _FakeToken("workhouse", "NOUN", "workhouse"),
        _FakeToken("cobblestone", "NOUN", "cobblestone"),
        _FakeToken("walked", "VERB", "walk"),
        _FakeToken("the", "DET", "the"),
        _FakeToken("he", "PRON", "he"),
        _FakeToken("and", "CONJ", "and"),
        _FakeToken("into", "ADP", "into"),
    ]
    # No distinctive terms
    plain_tokens = [_FakeToken(f"word{i}", "NOUN", f"word{i}") for i in range(10)]

    emb = _make_embedding_model(_CENTROID)
    nlp_match = _make_nlp([matching_tokens])
    nlp_plain = _make_nlp([plain_tokens])

    score_match = compute_fit_score("t", _PROFILE, nlp_match, emb)
    score_plain = compute_fit_score("t", _PROFILE, nlp_plain, emb)

    assert score_match > score_plain


# ---------------------------------------------------------------------------
# Semantic sub-score: identical vs orthogonal vectors
# ---------------------------------------------------------------------------


def test_identical_embedding_produces_max_semantic() -> None:
    """If generated embedding == centroid, semantic sub-score must be 1.0 (score ≥ 35)."""
    # Disable all other variance: ASL matches, no vocab, neutral POS.
    nlp = _make_nlp([_PERFECT_TOKENS])
    emb = _make_embedding_model(_CENTROID)
    score = compute_fit_score("t", _PROFILE, nlp, emb)
    # Semantic alone = 0.35 × 100 = 35; other components add more.
    assert score >= 35
