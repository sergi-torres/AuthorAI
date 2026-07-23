"""Tests for ai_pipeline/autoria_ai/conditioner.py.

Coverage
--------
* Happy path: correct author name, avg sentence length, and distinctive words
  all appear in the returned prompt string.
* Chunk cap: no more than 5 chunks appear even when 10 are passed.
* Empty chunks: function does not crash and returns a valid string.
* Missing keys: function does not crash when style_profile fields are absent.
* Subordination thresholds: natural-language rule translates correctly for
  high, medium, and low subordination_ratio values.
* Return type is always str.
"""

from __future__ import annotations

from autoria_ai.conditioner import build_system_prompt

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_MOCK_STYLE_PROFILE: dict = {
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
        "avg_sentence_length_tokens": 28.4,
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
    "semantic_centroid": [0.0] * 768,
    "embedding_umap_2d": {"centroid": [3.2, -1.7], "spread": 0.84},
}

_MOCK_CHUNKS: list[str] = [
    "It was the best of times, it was the worst of times.",
    "Oliver Twist asked for more, his countenance pale and drawn.",
    "The fog crept over the cobblestones as the workhouse loomed.",
]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_returns_string() -> None:
    result = build_system_prompt(_MOCK_STYLE_PROFILE, _MOCK_CHUNKS)
    assert isinstance(result, str)


def test_contains_author_id() -> None:
    result = build_system_prompt(_MOCK_STYLE_PROFILE, _MOCK_CHUNKS)
    assert "dickens" in result


def test_contains_avg_sentence_length() -> None:
    result = build_system_prompt(_MOCK_STYLE_PROFILE, _MOCK_CHUNKS)
    # avg_sentence_length_tokens = 28.4 → rendered as "28.4"
    assert "28.4" in result


def test_contains_distinctive_vocab_terms() -> None:
    result = build_system_prompt(_MOCK_STYLE_PROFILE, _MOCK_CHUNKS)
    assert "countenance" in result
    assert "physiognomy" in result


def test_contains_chunk_text() -> None:
    result = build_system_prompt(_MOCK_STYLE_PROFILE, _MOCK_CHUNKS)
    assert "It was the best of times" in result


# ---------------------------------------------------------------------------
# Chunk cap: max 5 chunks even when more are passed
# ---------------------------------------------------------------------------


def test_chunk_cap_at_five_when_ten_passed() -> None:
    ten_chunks = [f"Example passage number {i}." for i in range(10)]
    result = build_system_prompt(_MOCK_STYLE_PROFILE, ten_chunks)
    # The first 5 must be present; the 6th must not.
    for i in range(5):
        assert f"Example passage number {i}." in result
    for i in range(5, 10):
        assert f"Example passage number {i}." not in result


def test_exactly_five_chunks_all_included() -> None:
    five_chunks = [f"Passage {i}." for i in range(5)]
    result = build_system_prompt(_MOCK_STYLE_PROFILE, five_chunks)
    for chunk in five_chunks:
        assert chunk in result


# ---------------------------------------------------------------------------
# Empty chunks: must not crash
# ---------------------------------------------------------------------------


def test_empty_chunks_does_not_crash() -> None:
    result = build_system_prompt(_MOCK_STYLE_PROFILE, [])
    assert isinstance(result, str)
    assert len(result) > 0


def test_empty_chunks_contains_fallback_text() -> None:
    result = build_system_prompt(_MOCK_STYLE_PROFILE, [])
    assert "no example passages provided" in result


# ---------------------------------------------------------------------------
# Missing style_profile keys: graceful fallbacks
# ---------------------------------------------------------------------------


def test_missing_author_id_uses_fallback() -> None:
    result = build_system_prompt({}, [])
    assert isinstance(result, str)
    assert "unknown" in result


def test_missing_syntactic_block_uses_fallback() -> None:
    profile = {"author_id": "austen"}
    result = build_system_prompt(profile, [])
    assert isinstance(result, str)
    # Default avg sentence length fallback (20) must appear.
    assert "20" in result


def test_missing_distinctive_vocab_uses_fallback() -> None:
    profile = {"author_id": "poe", "syntactic": {"avg_sentence_length_tokens": 18.0}}
    result = build_system_prompt(profile, [])
    assert isinstance(result, str)
    # The vocab fallback phrase must appear.
    assert "vivid and precise language" in result


def test_completely_empty_profile_does_not_crash() -> None:
    result = build_system_prompt({}, [])
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Subordination ratio → natural-language rule
# ---------------------------------------------------------------------------


def test_high_subordination_ratio_produces_heavy_rule() -> None:
    profile = {
        "author_id": "dickens",
        "syntactic": {"avg_sentence_length_tokens": 28.0, "subordination_ratio": 0.38},
        "distinctive_vocab": [],
    }
    result = build_system_prompt(profile, [])
    assert "heavy use of subordinate clauses" in result


def test_medium_subordination_ratio_produces_moderate_rule() -> None:
    profile = {
        "author_id": "austen",
        "syntactic": {"avg_sentence_length_tokens": 22.0, "subordination_ratio": 0.20},
        "distinctive_vocab": [],
    }
    result = build_system_prompt(profile, [])
    assert "moderate use of subordinate clauses" in result


def test_low_subordination_ratio_produces_straightforward_rule() -> None:
    profile = {
        "author_id": "poe",
        "syntactic": {"avg_sentence_length_tokens": 16.0, "subordination_ratio": 0.05},
        "distinctive_vocab": [],
    }
    result = build_system_prompt(profile, [])
    assert "few subordinate clauses" in result


# ---------------------------------------------------------------------------
# Vocab cap: at most 15 terms included
# ---------------------------------------------------------------------------


def test_vocab_cap_at_fifteen_terms() -> None:
    many_terms = [{"term": f"word{i}", "score": float(20 - i)} for i in range(20)]
    profile = {**_MOCK_STYLE_PROFILE, "distinctive_vocab": many_terms}
    result = build_system_prompt(profile, [])
    # word0..word14 must appear; word15..word19 must not.
    for i in range(15):
        assert f"word{i}" in result
    for i in range(15, 20):
        assert f"word{i}" not in result
