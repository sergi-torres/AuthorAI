"""Text cleaning utilities: strips Gutenberg boilerplate and normalizes surface noise."""

import re

# Anchors used by Project Gutenberg edition headers and footers.
# The patterns are case-insensitive and allow for trailing edition text
# such as "*** START OF THE PROJECT GUTENBERG EBOOK EMMA ***".
_PG_START = re.compile(
    r"\*{3}\s*START OF THE PROJECT GUTENBERG EBOOK.*",
    re.IGNORECASE,
)
_PG_END = re.compile(
    r"\*{3}\s*END OF THE PROJECT GUTENBERG EBOOK.*",
    re.IGNORECASE,
)

# Illustrated Gutenberg editions (e.g. Pride and Prejudice, Sense and
# Sensibility, Great Expectations in this corpus) embed bracketed image
# placeholders — bare "[Illustration]" or "[Illustration: caption text]" —
# inline wherever a plate appeared in the printed book. These are page-layout
# artifacts, not prose, but were surviving into the lemmatized corpus used for
# distinctive_vocab: 193 occurrences of the word "illustration" put it in
# Austen's TF-IDF/log-odds top terms, which is not a style signal by any
# definition (docs/decision_log.md, 2026-07-30 distinctive_vocab entries).
# The caption can itself contain one bracketed sub-run (Gutenberg's own
# "[_Copyright 1894 by George Allen._]" credit line nested inside the
# illustration block), so the pattern allows exactly one level of nested
# brackets rather than stopping at the first "]" it finds.
_PG_ILLUSTRATION = re.compile(
    r"\[Illustration(?:[^\[\]]|\[[^\[\]]*\])*\]",
    re.IGNORECASE,
)

# Two or more consecutive blank lines (any mix of spaces/tabs between newlines).
_MULTI_BLANK = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Strip Gutenberg boilerplate, normalize quotes and dashes, collapse blank lines."""

    # ── 1. Strip Project Gutenberg header ────────────────────────────────────
    # Everything up to AND including the START sentinel line is discarded.
    match = _PG_START.search(text)
    if match:
        text = text[match.end() :]

    # ── 2. Strip Project Gutenberg footer ────────────────────────────────────
    # Everything from the END sentinel line onwards is discarded.
    match = _PG_END.search(text)
    if match:
        text = text[: match.start()]

    # ── 3. Normalize curly / typographic quotation marks → straight ASCII " ──
    # Required so dialogue_ratio (§3.3) and punct_distribution (§3.1) work
    # correctly on raw Gutenberg text that ships with Unicode curly quotes.
    text = text.replace("\u201c", '"').replace("\u201d", '"')  # " "

    # ── 4. Normalize double-dash → em-dash ───────────────────────────────────
    # Gutenberg texts often encode em-dashes as "--"; convert before spaCy so
    # the punct_distribution em-dash bucket (§3.1) captures them.
    text = text.replace("--", "\u2014")  # — (U+2014 EM DASH)

    # ── 5. Strip "[Illustration]" / "[Illustration: caption]" blocks ─────────
    text = _PG_ILLUSTRATION.sub("", text)

    # ── 6. Collapse multiple consecutive blank lines → single blank line ──────
    text = _MULTI_BLANK.sub("\n\n", text)

    return text.strip()
