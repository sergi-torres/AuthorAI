"""Smoke tests: happy-path coverage for cleaner, chunker, lexical, syntactic, and stylistic."""

import statistics
import string

import pytest  # type: ignore[import-untyped]
import spacy  # type: ignore[import-untyped]
import tiktoken  # type: ignore[import-untyped]

from autoria_ai.extractor.chunker import chunk_text
from autoria_ai.extractor.cleaner import clean_text
from autoria_ai.extractor.lexical import compute_lexical
from autoria_ai.extractor.stylistic import compute_stylistic
from autoria_ai.extractor.syntactic import compute_syntactic

# ── spaCy models (loaded once at module level) ────────────────────────────────
_NLP_BLANK = spacy.blank("en")
_NLP_FULL = spacy.load("en_core_web_lg")

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
#   5 reps  -> 21 tokens  -> chunk_size=10, overlap=3, step=7
#              windows: [0..9], [7..16], [14..20]  -> 3 chunks
#   6 reps  -> 25 tokens  -> windows: [0..9],[7..16],[14..23],[21..24] -> 4 chunks

_PHRASE = "The quick brown fox "  # 5 tokens/rep (cl100k_base)


def test_chunk_text_correct_chunk_count() -> None:
    # 5 reps x 5 tokens = 21 total tokens; chunk_size=10, overlap=3 -> 3 chunks.
    text = _PHRASE * 5
    chunks = chunk_text(text, chunk_size=10, overlap=3)
    assert len(chunks) == 3


def test_chunk_text_overlap_between_consecutive_chunks() -> None:
    # 6 reps x 5 tokens = 25 total tokens -> 4 chunks.
    # The last `overlap` decoded tokens of chunk[i] must equal
    # the first `overlap` decoded tokens of chunk[i+1].
    enc = tiktoken.get_encoding("cl100k_base")
    text = _PHRASE * 6
    overlap = 3
    chunks = chunk_text(text, chunk_size=10, overlap=overlap)

    assert len(chunks) == 4  # verifies the test corpus is correctly constructed

    for i in range(len(chunks) - 1):
        tail_tokens = enc.encode(chunks[i])[-overlap:]
        head_tokens = enc.encode(chunks[i + 1])[:overlap]
        assert tail_tokens == head_tokens, f"Overlap mismatch between chunk {i} and chunk {i + 1}"


def test_chunk_text_returns_strings_not_token_ids() -> None:
    chunks = chunk_text(_PHRASE * 3, chunk_size=10, overlap=3)
    for chunk in chunks:
        assert isinstance(chunk, str)


def test_chunk_text_empty_input_returns_empty_list() -> None:
    assert chunk_text("") == []


# ── lexical ───────────────────────────────────────────────────────────────────

REQUIRED_KEYS = {"mattr_500", "hapax_ratio", "avg_word_length"}


def _doc(text: str):
    """Blank-model doc - is_alpha and token.text are reliable; lemma_ is ''."""
    return _NLP_BLANK(text)


def _doc_full(text: str):
    """Full-model doc - lemma_ is populated correctly."""
    return _NLP_FULL(text)


def test_lexical_empty_doc_returns_zeros() -> None:
    result = compute_lexical(_doc(""))
    assert result == {"mattr_500": 0.0, "hapax_ratio": 0.0, "avg_word_length": 0.0}


def test_lexical_punct_only_doc_returns_zeros() -> None:
    result = compute_lexical(_doc("... !!! ???"))
    assert result == {"mattr_500": 0.0, "hapax_ratio": 0.0, "avg_word_length": 0.0}


def test_lexical_short_doc_under_500_tokens() -> None:
    text = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"
    result = compute_lexical(_doc_full(text))
    assert result.keys() == REQUIRED_KEYS
    assert result["hapax_ratio"] == pytest.approx(1.0)
    assert result["mattr_500"] == pytest.approx(1.0)
    assert 4.0 < result["avg_word_length"] < 8.0


def test_lexical_return_type_is_dict_of_floats() -> None:
    result = compute_lexical(_doc("The quick brown fox jumps over the lazy dog."))
    assert isinstance(result, dict)
    assert result.keys() == REQUIRED_KEYS
    for v in result.values():
        assert isinstance(v, float)


def test_lexical_avg_word_length_ignores_punctuation() -> None:
    result = compute_lexical(_doc("Hi there."))
    assert result["avg_word_length"] == pytest.approx(3.5)


def test_lexical_hapax_ratio_all_unique() -> None:
    result = compute_lexical(_doc_full("running jumps beautiful darkness whisper"))
    assert result["hapax_ratio"] == pytest.approx(1.0)


def test_lexical_hapax_ratio_no_hapax() -> None:
    result = compute_lexical(_doc_full("cat cats dog dogs bird birds"))
    assert result["hapax_ratio"] == pytest.approx(0.0)


def test_lexical_hapax_ratio_mixed() -> None:
    result = compute_lexical(_doc_full("cat cats dog"))
    assert result["hapax_ratio"] == pytest.approx(0.5)


def test_lexical_mattr_500_with_exactly_500_alpha_tokens() -> None:
    text = " ".join(["word"] * 500)
    result = compute_lexical(_doc(text))
    assert result["mattr_500"] == pytest.approx(1 / 500)


def test_lexical_mattr_500_over_500_tokens() -> None:
    letters = string.ascii_lowercase
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
    assert result["mattr_500"] == pytest.approx(1.0)


def test_lexical_mattr_500_repeated_vocab_over_500_tokens() -> None:
    vocab = [c * 3 for c in "abcdefghij"]
    text = " ".join(vocab * 100)
    result = compute_lexical(_doc(text))
    assert result["mattr_500"] == pytest.approx(10 / 500)


def test_lexical_keys_are_exactly_three() -> None:
    result = compute_lexical(_doc("Hello world"))
    assert set(result.keys()) == REQUIRED_KEYS


# ── syntactic ─────────────────────────────────────────────────────────────────

SYNTACTIC_KEYS = {
    "avg_sentence_length_tokens",
    "std_sentence_length_tokens",
    "subordination_ratio",
    "noun_to_verb_ratio",
    "passive_voice_ratio",
}


def test_syntactic_empty_doc_returns_zeros() -> None:
    doc = _NLP_FULL("")
    result = compute_syntactic(doc)
    assert result == dict.fromkeys(SYNTACTIC_KEYS, 0.0)


def test_syntactic_single_sentence_std_is_zero() -> None:
    doc = _NLP_FULL("The cat sat on the mat.")
    result = compute_syntactic(doc)
    assert result["std_sentence_length_tokens"] == pytest.approx(0.0)


def test_syntactic_no_verbs_noun_to_verb_ratio_is_zero() -> None:
    doc = _NLP_FULL("London Paris Rome.")
    result = compute_syntactic(doc)
    assert isinstance(result["noun_to_verb_ratio"], float)
    assert result["noun_to_verb_ratio"] == pytest.approx(0.0)


def test_syntactic_return_type_is_dict_of_floats() -> None:
    doc = _NLP_FULL("She laughed. He smiled.")
    result = compute_syntactic(doc)
    assert isinstance(result, dict)
    assert result.keys() == SYNTACTIC_KEYS
    for v in result.values():
        assert isinstance(v, float)


def test_syntactic_keys_exactly_five() -> None:
    doc = _NLP_FULL("Hello world.")
    result = compute_syntactic(doc)
    assert set(result.keys()) == SYNTACTIC_KEYS


def test_syntactic_avg_sentence_length_two_equal_sentences() -> None:
    doc = _NLP_FULL("She laughed. He smiled.")
    sents = list(doc.sents)
    lengths = [len(s) for s in sents]
    result = compute_syntactic(doc)
    assert result["avg_sentence_length_tokens"] == pytest.approx(statistics.mean(lengths))
    assert result["std_sentence_length_tokens"] == pytest.approx(statistics.stdev(lengths))


def test_syntactic_avg_and_std_three_sentences() -> None:
    doc = _NLP_FULL("I ran. She walked quickly down the road. They stopped.")
    lengths = [len(s) for s in doc.sents]
    result = compute_syntactic(doc)
    assert result["avg_sentence_length_tokens"] == pytest.approx(statistics.mean(lengths))
    assert result["std_sentence_length_tokens"] == pytest.approx(statistics.stdev(lengths))


def test_syntactic_subordination_ratio_is_nonnegative() -> None:
    doc = _NLP_FULL(
        "She knew that he was lying. "
        "The man who arrived late apologized. "
        "He left because she asked him to."
    )
    result = compute_syntactic(doc)
    assert result["subordination_ratio"] >= 0.0


def test_syntactic_subordination_ratio_normalized_per_sentence() -> None:
    from autoria_ai.extractor.syntactic import _SUBORDINATE_DEPS

    doc = _NLP_FULL(
        "She said that the door was open. "
        "The cat sat on the mat. "
        "He believed that she was right."
    )
    n_sents = len(list(doc.sents))
    subordinate_count = sum(1 for t in doc if t.dep_ in _SUBORDINATE_DEPS)
    expected = subordinate_count / n_sents
    result = compute_syntactic(doc)
    assert result["subordination_ratio"] == pytest.approx(expected)


def test_syntactic_noun_to_verb_ratio_is_positive_for_normal_text() -> None:
    doc = _NLP_FULL("The old man carried the heavy bag.")
    result = compute_syntactic(doc)
    assert result["noun_to_verb_ratio"] > 0.0


def test_syntactic_noun_to_verb_ratio_exact() -> None:
    doc = _NLP_FULL("Dogs bark. Cats sleep. Birds sing loudly.")
    nouns = sum(1 for t in doc if t.pos_ == "NOUN")
    verbs = sum(1 for t in doc if t.pos_ == "VERB")
    expected = nouns / verbs if verbs > 0 else 0.0
    result = compute_syntactic(doc)
    assert result["noun_to_verb_ratio"] == pytest.approx(expected)


def test_syntactic_passive_voice_ratio_bounds() -> None:
    doc = _NLP_FULL("The window was broken by the storm. She opened the door.")
    result = compute_syntactic(doc)
    assert 0.0 <= result["passive_voice_ratio"] <= 1.0


def test_syntactic_passive_voice_ratio_exact() -> None:
    doc = _NLP_FULL(
        "The letter was written by her. "
        "He delivered the package. "
        "The door was opened by the butler."
    )
    sents = list(doc.sents)
    passive_count = sum(1 for sent in sents if any(t.dep_ == "nsubjpass" for t in sent))
    expected = passive_count / len(sents)
    result = compute_syntactic(doc)
    assert result["passive_voice_ratio"] == pytest.approx(expected)


def test_syntactic_all_active_passive_ratio_is_zero() -> None:
    doc = _NLP_FULL("She ran fast. He laughed loudly. They cheered.")
    result = compute_syntactic(doc)
    assert result["passive_voice_ratio"] == pytest.approx(0.0)


# ── stylistic ─────────────────────────────────────────────────────────────────

_PUNCT_MARKS = {",", ".", ";", ":", "—", "?", "!", '"'}
_TRACKED_POS = {"NOUN", "VERB", "ADJ", "ADV", "DET", "ADP", "PRON", "CONJ", "SCONJ"}
_STYLISTIC_TOP_KEYS = {
    "punct_distribution",
    "pos_distribution",
    "dialogue_ratio",
    "first_person_ratio",
}


# ── helpers ───────────────────────────────────────────────────────────────────


def _sdoc(text: str):
    """Blank-model doc — sufficient for punctuation, dialogue, and first-person tests."""
    return _NLP_BLANK(text)


def _sdoc_full(text: str):
    """Full-model doc — required for POS tests."""
    return _NLP_FULL(text)


# ── top-level shape ───────────────────────────────────────────────────────────


def test_stylistic_keys_are_exactly_four() -> None:
    result = compute_stylistic(_sdoc("Hello world."))
    assert set(result.keys()) == _STYLISTIC_TOP_KEYS


def test_stylistic_empty_doc_returns_zeros() -> None:
    result = compute_stylistic(_sdoc(""))
    assert result["dialogue_ratio"] == pytest.approx(0.0)
    assert result["first_person_ratio"] == pytest.approx(0.0)
    assert result["punct_distribution"] == dict.fromkeys(_PUNCT_MARKS, 0.0)
    assert result["pos_distribution"] == {tag: 0.0 for tag in _TRACKED_POS} | {"OTHER": 0.0}


def test_stylistic_return_types() -> None:
    result = compute_stylistic(_sdoc('She said, "Hello." He smiled!'))
    assert isinstance(result["punct_distribution"], dict)
    assert isinstance(result["pos_distribution"], dict)
    assert isinstance(result["dialogue_ratio"], float)
    assert isinstance(result["first_person_ratio"], float)


# ── punct_distribution ────────────────────────────────────────────────────────


def test_stylistic_punct_distribution_has_all_eight_keys() -> None:
    result = compute_stylistic(_sdoc("Hello, world!"))
    assert set(result["punct_distribution"].keys()) == _PUNCT_MARKS


def test_stylistic_punct_distribution_absent_marks_are_zero() -> None:
    # Only "." is present — all other tracked marks must be 0.0.
    result = compute_stylistic(_sdoc("Hello world."))
    pd = result["punct_distribution"]
    assert pd["."] == pytest.approx(1.0)
    for mark in _PUNCT_MARKS - {"."}:
        assert pd[mark] == pytest.approx(0.0)


def test_stylistic_punct_distribution_sums_to_one() -> None:
    result = compute_stylistic(_sdoc("Wait, really? Yes! Fine; done: go—go."))
    total = sum(result["punct_distribution"].values())
    assert total == pytest.approx(1.0, abs=1e-9)


def test_stylistic_punct_distribution_no_punctuation() -> None:
    # No tracked marks → all values 0.0.
    result = compute_stylistic(_sdoc("hello world"))
    assert all(v == pytest.approx(0.0) for v in result["punct_distribution"].values())


def test_stylistic_punct_distribution_exact_counts() -> None:
    # "," appears twice, "." once → comma = 2/3, period = 1/3.
    result = compute_stylistic(_sdoc("one, two, three."))
    pd = result["punct_distribution"]
    assert pd[","] == pytest.approx(2 / 3)
    assert pd["."] == pytest.approx(1 / 3)
    for mark in _PUNCT_MARKS - {",", "."}:
        assert pd[mark] == pytest.approx(0.0)


def test_stylistic_punct_distribution_quote_counted() -> None:
    # Text contains one '"' on each side of dialogue = 2 quote tokens.
    result = compute_stylistic(_sdoc('"Hello."'))
    pd = result["punct_distribution"]
    # Tokens: '"', 'Hello', '.', '"'  → punct marks: '"', '.', '"' → 2 quotes, 1 period.
    assert pd['"'] == pytest.approx(2 / 3)
    assert pd["."] == pytest.approx(1 / 3)


# ── pos_distribution ──────────────────────────────────────────────────────────


def test_stylistic_pos_distribution_has_ten_keys() -> None:
    result = compute_stylistic(_sdoc_full("The cat sat on the mat."))
    assert set(result["pos_distribution"].keys()) == _TRACKED_POS | {"OTHER"}


def test_stylistic_pos_distribution_sums_to_one() -> None:
    result = compute_stylistic(_sdoc_full("She laughed loudly and he smiled."))
    total = sum(result["pos_distribution"].values())
    assert total == pytest.approx(1.0, abs=1e-9)


def test_stylistic_pos_distribution_empty_doc_all_zeros() -> None:
    result = compute_stylistic(_sdoc_full(""))
    assert all(v == pytest.approx(0.0) for v in result["pos_distribution"].values())


def test_stylistic_pos_distribution_punct_only_all_zeros() -> None:
    # All tokens are punctuation → no non-punct tokens → all zeros.
    result = compute_stylistic(_sdoc_full("... !!! ???"))
    assert all(v == pytest.approx(0.0) for v in result["pos_distribution"].values())


def test_stylistic_pos_distribution_values_in_unit_interval() -> None:
    result = compute_stylistic(
        _sdoc_full("The old woman walked slowly through the dark forest and she sang.")
    )
    for v in result["pos_distribution"].values():
        assert 0.0 <= v <= 1.0


def test_stylistic_pos_distribution_other_is_nonnegative() -> None:
    result = compute_stylistic(_sdoc_full("She quickly ran to the bright blue house."))
    assert result["pos_distribution"]["OTHER"] >= 0.0


def test_stylistic_pos_distribution_exact_fractions() -> None:
    # Use the full model on a controlled sentence; verify by recomputing.
    doc = _sdoc_full("Dogs bark loudly.")
    from collections import Counter

    raw = Counter(t.pos_ for t in doc if not t.is_punct)
    total = sum(raw.values())
    expected_noun = raw["NOUN"] / total
    result = compute_stylistic(doc)
    assert result["pos_distribution"]["NOUN"] == pytest.approx(expected_noun)


# ── dialogue_ratio ────────────────────────────────────────────────────────────


def test_stylistic_dialogue_ratio_no_quotes_is_zero() -> None:
    result = compute_stylistic(_sdoc("He walked home slowly."))
    assert result["dialogue_ratio"] == pytest.approx(0.0)


def test_stylistic_dialogue_ratio_all_dialogue() -> None:
    # '"Hello there friend"' — every non-quote token is inside dialogue.
    result = compute_stylistic(_sdoc('"Hello there friend"'))
    assert result["dialogue_ratio"] == pytest.approx(1.0)


def test_stylistic_dialogue_ratio_half_dialogue() -> None:
    # "Hello" narrator — 1 dialogue token ("Hello"), 1 non-dialogue ("narrator")
    # Plus 2 quote tokens (ignored in denominator).
    result = compute_stylistic(_sdoc('"Hello" narrator'))
    assert result["dialogue_ratio"] == pytest.approx(1 / 2)


def test_stylistic_dialogue_ratio_in_unit_interval() -> None:
    result = compute_stylistic(_sdoc('"Wait," she said. "I disagree."'))
    assert 0.0 <= result["dialogue_ratio"] <= 1.0


def test_stylistic_dialogue_ratio_empty_doc_is_zero() -> None:
    result = compute_stylistic(_sdoc(""))
    assert result["dialogue_ratio"] == pytest.approx(0.0)


def test_stylistic_dialogue_ratio_ignores_quote_tokens_in_denominator() -> None:
    # 4 non-quote tokens total: "Wait" (dialogue), "she" (narration), "said" (narration), "Now" (narration).
    # Dialogue count = 1.  Ratio = 1/4.
    result = compute_stylistic(_sdoc('"Wait" she said Now'))
    assert result["dialogue_ratio"] == pytest.approx(1 / 4)


# ── first_person_ratio ────────────────────────────────────────────────────────


def test_stylistic_first_person_ratio_no_fp_is_zero() -> None:
    result = compute_stylistic(_sdoc("She walked to the store."))
    assert result["first_person_ratio"] == pytest.approx(0.0)


def test_stylistic_first_person_ratio_per_1000_tokens() -> None:
    # "I me my mine myself" = 5 first-person tokens out of 5 total → 1000.0.
    result = compute_stylistic(_sdoc("I me my mine myself"))
    assert result["first_person_ratio"] == pytest.approx(1000.0)


def test_stylistic_first_person_ratio_case_insensitive() -> None:
    # "I" and "i" must both be counted.
    result_upper = compute_stylistic(_sdoc("I went home."))
    result_lower = compute_stylistic(_sdoc("i went home."))
    assert result_upper["first_person_ratio"] == pytest.approx(result_lower["first_person_ratio"])


def test_stylistic_first_person_ratio_exact() -> None:
    # "I love my dog" → 4 tokens total, 2 first-person ("I", "my") → 2/4 * 1000 = 500.
    result = compute_stylistic(_sdoc("I love my dog"))
    assert result["first_person_ratio"] == pytest.approx(500.0)


def test_stylistic_first_person_ratio_empty_doc_is_zero() -> None:
    result = compute_stylistic(_sdoc(""))
    assert result["first_person_ratio"] == pytest.approx(0.0)


def test_stylistic_first_person_ratio_includes_all_five_forms() -> None:
    # All 5 forms present: 5 first-person tokens out of 7 total.
    result = compute_stylistic(_sdoc("I hurt me on my mine myself"))
    assert result["first_person_ratio"] == pytest.approx(5 / 7 * 1000)


def test_stylistic_first_person_ratio_is_nonnegative() -> None:
    result = compute_stylistic(_sdoc("The wind blew fiercely."))
    assert result["first_person_ratio"] >= 0.0
