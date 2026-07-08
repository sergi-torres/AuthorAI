"""Token-based sliding-window chunker using tiktoken cl100k_base encoding."""

import tiktoken  # type: ignore[import-untyped]

# Encoder is loaded once at module import — never inside chunk_text.
_ENCODER: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Split *text* into overlapping token windows and return decoded strings."""
    if chunk_size <= overlap:
        raise ValueError(f"chunk_size ({chunk_size}) must be greater than overlap ({overlap})")

    tokens: list[int] = _ENCODER.encode(text)
    total: int = len(tokens)

    if total == 0:
        return []

    step: int = chunk_size - overlap
    chunks: list[str] = []
    start: int = 0

    while start < total:
        window = tokens[start : start + chunk_size]
        chunks.append(_ENCODER.decode(window))
        # Stop after the window that reached or passed the end of the token list.
        if start + chunk_size >= total:
            break
        start += step

    return chunks
