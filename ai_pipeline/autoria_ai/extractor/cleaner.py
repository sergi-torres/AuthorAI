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

    # ── 5. Collapse multiple consecutive blank lines → single blank line ──────
    text = _MULTI_BLANK.sub("\n\n", text)

    return text.strip()
