"""Smoke tests: happy-path coverage for cleaner and chunker."""

from autoria_ai.extractor.cleaner import clean_text
from autoria_ai.extractor.chunker import chunk_text


# ── cleaner ──────────────────────────────────────────────────────────────────

_PG_SAMPLE = """\
This is a Project Gutenberg header that should be removed.
Some licensing blurb that nobody wants.

*** START OF THE PROJECT GUTENBERG EBOOK EMMA ***

It is a truth universally acknowledged.

She had a lively, playful disposition.

"What a fine thing for our girls!"

The door was opened--and a tall man entered.

*** END OF THE PROJECT GUTENBERG EBOOK EMMA ***

Producer notes and end matter that should be removed.
"""


def test_clean_text_strips_pg_header_and_footer() -> None:
    result = clean_text(_PG_SAMPLE)
    assert "universally acknowledged" in result
    assert "START OF THE PROJECT GUTENBERG" not in result
    assert "END OF THE PROJECT GUTENBERG" not in result
    assert "Producer notes" not in result
    assert "licensing blurb" not in result


def test_clean_text_normalizes_curly_quotes() -> None:
    result = clean_text("\u201cHello,\u201d she said.")
    assert '"Hello,"' in result
    assert "\u201c" not in result
    assert "\u201d" not in result


def test_clean_text_normalizes_double_dash_to_em_dash() -> None:
    result = clean_text("He paused--then spoke.")
    assert "\u2014" in result  # em-dash present
    assert "--" not in result


def test_clean_text_collapses_multiple_blank_lines() -> None:
    result = clean_text("Line one.\n\n\n\n\nLine two.")
    # At most one blank line between paragraphs (two consecutive \n characters).
    assert "\n\n\n" not in result
    assert "Line one." in result
    assert "Line two." in result


# ── chunker ──────────────────────────────────────────────────────────────────
#
# Test corpus: "The quick brown fox " repeated N times.
# tiktoken cl100k_base tokenizes this phrase as exactly 5 tokens per repetition:
#   ["The", " quick", " brown", " fox", " "]
# So:
#   5 reps  → 21 tokens  → chunk_size=10, overlap=3, step=7
#             windows: [0..9], [7..16], [14..20]  → 3 chunks
#   6 reps  → 25 tokens  → windows: [0..9],[7..16],[14..23],[21..24] → 4 chunks

_PHRASE = "The quick brown fox "  # 5 tokens/rep (cl100k_base)


def test_chunk_text_correct_chunk_count() -> None:
    # 5 reps × 5 tokens = 21 total tokens; chunk_size=10, overlap=3 → 3 chunks.
    text = _PHRASE * 5
    chunks = chunk_text(text, chunk_size=10, overlap=3)
    assert len(chunks) == 3


def test_chunk_text_overlap_between_consecutive_chunks() -> None:
    # 6 reps × 5 tokens = 25 total tokens → 4 chunks.
    # The last `overlap` decoded tokens of chunk[i] must equal
    # the first `overlap` decoded tokens of chunk[i+1].
    import tiktoken  # type: ignore[import-untyped]

    enc = tiktoken.get_encoding("cl100k_base")
    text = _PHRASE * 6
    overlap = 3
    chunks = chunk_text(text, chunk_size=10, overlap=overlap)

    assert len(chunks) == 4  # verifies the test corpus is correctly constructed

    for i in range(len(chunks) - 1):
        tail_tokens = enc.encode(chunks[i])[-overlap:]
        head_tokens = enc.encode(chunks[i + 1])[:overlap]
        assert tail_tokens == head_tokens, (
            f"Overlap mismatch between chunk {i} and chunk {i + 1}"
        )


def test_chunk_text_returns_strings_not_token_ids() -> None:
    chunks = chunk_text(_PHRASE * 3, chunk_size=10, overlap=3)
    for chunk in chunks:
        assert isinstance(chunk, str)


def test_chunk_text_empty_input_returns_empty_list() -> None:
    assert chunk_text("") == []


# ── lexical ───────────────────────────────────────────────────────────────────
#
# Lemmatization requires a real model.  We load en_core_web_lg (already a
# project dependency) once at module level.  Tests that do NOT need lemmas use
# spacy.blank("en") so they remain fast even if the large model is unavailable.

import pytest
import spacy

from autoria_ai.extractor.lexical import compute_lexical

_NLP_BLANK = spacy.blank("en")
_NLP_FULL = spacy.load("en_core_web_lg")  # needed for lemma_ tests

# ── helpers ───────────────────────────────────────────────────────────────────

REQUIRED_KEYS = {"mattr_500", "hapax_ratio", "avg_word_length"}


def _doc(text: str):
    """Blank-model doc — is_alpha and token.text are reliable; lemma_ is ''."""
    return _NLP_BLANK(text)


def _doc_full(text: str):
    """Full-model doc — lemma_ is populated correctly."""
    return _NLP_FULL(text)


# ── edge cases ────────────────────────────────────────────────────────────────


def test_lexical_empty_doc_returns_zeros() -> None:
    result = compute_lexical(_doc(""))
    assert result == {"mattr_500": 0.0, "hapax_ratio": 0.0, "avg_word_length": 0.0}


def test_lexical_punct_only_doc_returns_zeros() -> None:
    # No alpha tokens at all
    result = compute_lexical(_doc("... !!! ???"))
    assert result == {"mattr_500": 0.0, "hapax_ratio": 0.0, "avg_word_length": 0.0}


def test_lexical_short_doc_under_500_tokens() -> None:
    # 10 distinct words — fewer than the 500-token MATTR window.
    # Use full model so lemma_ is populated and hapax_ratio is meaningful.
    text = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"
    result = compute_lexical(_doc_full(text))
    assert REQUIRED_KEYS == result.keys()
    # All 10 lemmas appear once → hapax_ratio == 1.0
    assert result["hapax_ratio"] == pytest.approx(1.0)
    # Single window → plain TTR == 1.0 (all unique)
    assert result["mattr_500"] == pytest.approx(1.0)
    # All words are 5-7 chars; avg must be in that range
    assert 4.0 < result["avg_word_length"] < 8.0


# ── happy path ────────────────────────────────────────────────────────────────


def test_lexical_return_type_is_dict_of_floats() -> None:
    result = compute_lexical(_doc("The quick brown fox jumps over the lazy dog."))
    assert isinstance(result, dict)
    assert REQUIRED_KEYS == result.keys()
    for v in result.values():
        assert isinstance(v, float)


def test_lexical_avg_word_length_ignores_punctuation() -> None:
    # "Hi" (2) and "there" (5) → avg = 3.5; punctuation token "." excluded
    result = compute_lexical(_doc("Hi there."))
    assert result["avg_word_length"] == pytest.approx(3.5)


def test_lexical_hapax_ratio_all_unique() -> None:
    # Every word appears exactly once (full model for real lemmas)
    result = compute_lexical(_doc_full("running jumps beautiful darkness whisper"))
    assert result["hapax_ratio"] == pytest.approx(1.0)


def test_lexical_hapax_ratio_no_hapax() -> None:
    # Each surface form maps to the same lemma twice → no hapax.
    # Use full model: "cats"→"cat", "dogs"→"dog", "birds"→"bird"
    result = compute_lexical(_doc_full("cat cats dog dogs bird birds"))
    assert result["hapax_ratio"] == pytest.approx(0.0)


def test_lexical_hapax_ratio_mixed() -> None:
    # "cat"/"cats" → lemma "cat" (count 2, not hapax)
    # "dog" → lemma "dog" (count 1, hapax)
    # → 1 hapax out of 2 lemma types = 0.5
    result = compute_lexical(_doc_full("cat cats dog"))
    assert result["hapax_ratio"] == pytest.approx(0.5)


def test_lexical_mattr_500_with_exactly_500_alpha_tokens() -> None:
    # 500 identical words: all same type → TTR = 1/500
    text = " ".join(["word"] * 500)
    result = compute_lexical(_doc(text))
    assert result["mattr_500"] == pytest.approx(1 / 500)


def test_lexical_mattr_500_over_500_tokens() -> None:
    # 600 purely-alphabetic unique words trigger the sliding-window path.
    # Generate words as e.g. "aaa", "aab", … using letters only.
    import string

    letters = string.ascii_lowercase
    # Build 600 unique 3-letter words using combinations with repetition
    words = []
    for a in letters:
        for b in letters:
            for c in letters:
                words.append(a + b + c)
                if len(words) == 600:
                    break
            if len(words) == 600:
                break
        if len(words) == 600:
            break

    result = compute_lexical(_doc(" ".join(words)))
    # All tokens are unique → every window has 500 unique types → MATTR == 1.0
    assert result["mattr_500"] == pytest.approx(1.0)


def test_lexical_mattr_500_repeated_vocab_over_500_tokens() -> None:
    # 1 000 tokens from a 10-word alphabetic vocabulary.
    # Each window of 500 contains exactly 10 unique types → TTR = 10/500 = 0.02
    vocab = [c * 3 for c in "abcdefghij"]  # ["aaa","bbb","ccc",…,"jjj"]
    text = " ".join(vocab * 100)  # 1 000 alpha tokens
    result = compute_lexical(_doc(text))
    assert result["mattr_500"] == pytest.approx(10 / 500)


def test_lexical_keys_are_exactly_three() -> None:
    result = compute_lexical(_doc("Hello world"))
    assert set(result.keys()) == REQUIRED_KEYS
