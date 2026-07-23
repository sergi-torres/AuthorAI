"""Tests for ai_pipeline/autoria_ai/extractor/vocabulary.py.

Coverage
--------
* Happy path: a word that is distinctively concentrated in one author's corpus
  rises to the top of that author's results and does not dominate the others.
* Output length is <= top_n (and can be less for a sparse corpus).
* Each item has exactly the keys {"term", "score"} with the correct types.
* Scores are sorted strictly descending (or equal, which is also fine).
* Stopwords are never present in results.
* Tokens shorter than 3 characters are never present in results.
* Unknown author_id raises KeyError.
"""

from __future__ import annotations

import pytest

from autoria_ai.extractor.vocabulary import compute_distinctive_vocab

# ---------------------------------------------------------------------------
# Shared test corpora
# ---------------------------------------------------------------------------

# "countenance" appears many times in AUTHOR_A but never in the others.
# "raven" appears many times in AUTHOR_C but never in the others.
_CORPORA: dict[str, str] = {
    "author_a": (
        "countenance countenance countenance countenance countenance "
        "countenance countenance countenance countenance countenance "
        "the quick brown fox jumped over the lazy dog and then ran away "
        "towards the distant hills while the sun was shining brightly "
    ),
    "author_b": (
        "london street cobblestone children orphan twist poverty workhouse "
        "the quick brown fox jumped over the lazy dog and then walked home "
        "through the foggy streets while the rain was falling steadily down "
    ),
    "author_c": (
        "raven raven raven raven raven raven raven raven raven raven "
        "nevermore chamber shadow midnight chamber shadow midnight tomb "
        "the quick brown fox jumped over the lazy dog and wandered around "
        "the darkened corridor while the candle flickered and went out "
    ),
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _terms(result: list[dict]) -> list[str]:
    return [item["term"] for item in result]


# ---------------------------------------------------------------------------
# Happy path: distinctive word rises to the top
# ---------------------------------------------------------------------------


def test_distinctive_word_tops_author_a() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    assert "countenance" in _terms(result), (
        "'countenance' must appear in author_a's top terms because it is "
        "concentrated exclusively in author_a's corpus"
    )


def test_distinctive_word_is_first_for_author_a() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    assert (
        result[0]["term"] == "countenance"
    ), "'countenance' should be the highest-scoring term for author_a"


def test_distinctive_word_tops_author_c() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_c", top_n=30)
    assert "raven" in _terms(result), "'raven' must appear in author_c's top terms"


def test_countenance_not_top_for_author_b() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_b", top_n=30)
    terms = _terms(result)
    # "countenance" never appears in author_b's corpus, so its TF-IDF is 0.
    assert "countenance" not in terms


def test_raven_not_top_for_author_a() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    assert "raven" not in _terms(result)


# ---------------------------------------------------------------------------
# Output length
# ---------------------------------------------------------------------------


def test_output_length_does_not_exceed_top_n() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    assert len(result) <= 30


def test_output_length_respects_custom_top_n() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=5)
    assert len(result) <= 5


def test_sparse_corpus_length_can_be_less_than_top_n() -> None:
    """A tiny corpus with fewer than top_n distinct valid tokens must still work."""
    tiny: dict[str, str] = {
        "alpha": "hello world",
        "beta": "foo bar",
        "gamma": "baz qux",
    }
    result = compute_distinctive_vocab(tiny, "alpha", top_n=30)
    assert len(result) <= 30  # may be much shorter; must not error


# ---------------------------------------------------------------------------
# Shape: {"term": str, "score": float}
# ---------------------------------------------------------------------------


def test_each_item_has_term_and_score_keys() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    assert len(result) > 0, "result must not be empty for a non-trivial corpus"
    for item in result:
        assert set(item.keys()) == {"term", "score"}, f"unexpected keys in item: {set(item.keys())}"


def test_term_values_are_strings() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    for item in result:
        assert isinstance(item["term"], str)


def test_score_values_are_floats() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    for item in result:
        assert isinstance(item["score"], float)


def test_score_values_are_positive() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    for item in result:
        assert item["score"] > 0.0


# ---------------------------------------------------------------------------
# Scores sorted descending
# ---------------------------------------------------------------------------


def test_scores_are_sorted_descending() -> None:
    result = compute_distinctive_vocab(_CORPORA, "author_a", top_n=30)
    scores = [item["score"] for item in result]
    assert scores == sorted(scores, reverse=True), "scores must be sorted descending"


def test_scores_sorted_descending_for_all_authors() -> None:
    for author_id in _CORPORA:
        result = compute_distinctive_vocab(_CORPORA, author_id, top_n=30)
        scores = [item["score"] for item in result]
        assert scores == sorted(
            scores, reverse=True
        ), f"scores not sorted descending for {author_id}"


# ---------------------------------------------------------------------------
# Stopwords never appear
# ---------------------------------------------------------------------------

# A small sample of sklearn's English stopword list.
_SAMPLE_STOPWORDS = {"the", "and", "was", "over", "then", "while", "its", "our"}


def test_stopwords_absent_from_results() -> None:
    for author_id in _CORPORA:
        result = compute_distinctive_vocab(_CORPORA, author_id, top_n=30)
        terms = set(_terms(result))
        overlap = terms & _SAMPLE_STOPWORDS
        assert not overlap, f"stopwords found in {author_id} results: {overlap}"


# ---------------------------------------------------------------------------
# Tokens shorter than 3 characters never appear
# ---------------------------------------------------------------------------


def test_short_tokens_absent_from_results() -> None:
    """Tokens with fewer than 3 characters must be excluded by token_pattern."""
    corpora_with_short_tokens: dict[str, str] = {
        "aa": "to be or not to be that is the question wonder wonder wonder",
        "bb": "it is an honor to act in the play and wonder about things",
        "cc": "wonder wonder wonder wonder wonder wonder wonder wonder here",
    }
    # "to", "be", "or", "is", "an", "in", "it" are all < 3 chars
    for author_id in corpora_with_short_tokens:
        result = compute_distinctive_vocab(corpora_with_short_tokens, author_id, top_n=30)
        for item in result:
            assert len(item["term"]) >= 3, f"term {item['term']!r} is shorter than 3 characters"


def test_single_char_tokens_absent() -> None:
    corpora: dict[str, str] = {
        "x": "a b c the quick brown fox jumps over the lazy dog wonder wonder",
        "y": "i j k the quick brown fox jumps over the lazy cat shining shining",
        "z": "x y z the quick brown fox jumps over the lazy hen glowing glowing",
    }
    for author_id in corpora:
        result = compute_distinctive_vocab(corpora, author_id, top_n=30)
        for item in result:
            assert len(item["term"]) >= 3


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unknown_author_id_raises_key_error() -> None:
    with pytest.raises(KeyError):
        compute_distinctive_vocab(_CORPORA, "nonexistent_author", top_n=30)
