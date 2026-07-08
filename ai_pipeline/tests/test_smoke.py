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
