"""Assemble a StyleProfile v1.0 from an author's cleaned corpus texts.

Public API
----------
compute_style_profile(author_slug, documents, nlp, ...) -> dict
    Runs lexical / syntactic / stylistic extractors, distinctive vocab,
    and semantic centroid.  ``embedding_umap_2d`` is a placeholder
    (``{centroid:[0,0], spread:0}``) — real UMAP lives in
    ``scripts/precompute_umap.py``.
lemmatize_corpus(documents, nlp, ...) -> str
    One author's corpus as a single lemmatized string, ready to be used as
    another author's ``comparison_lemmas`` entry (docs/style_features.md §4.1).

Pipeline (docs/style_features.md §8)
------------------------------------
cleaned documents → chunk (500 / 50) → spaCy ``nlp.pipe`` on chunks
→ aggregate linguistic features → TF-IDF distinctive vocab →
sentence-transformers centroid over chunks.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import tiktoken

from autoria_ai.embedder import EMBEDDING_DIM, embed_chunks
from autoria_ai.extractor.chunker import chunk_text
from autoria_ai.extractor.lexical import compute_lexical
from autoria_ai.extractor.stylistic import compute_stylistic
from autoria_ai.extractor.syntactic import compute_syntactic
from autoria_ai.extractor.vocabulary import compute_distinctive_vocab

# Soft cap so spaCy does not OOM on full Victorian novels in one Doc.
# Features are still computed over many chunks via nlp.pipe; this only
# limits how much raw text we keep when building the lemma string for TF-IDF.
#
# The cap is a memory bound, not a corpus definition: it is spent on chunks
# drawn from across the whole corpus (``_spread_order``), never on a prefix.
# See docs/style_features.md §4.1 "Preprocessing" and issue #100.
_MAX_LEMMA_CHARS: int = 800_000

# Cap centroid embedding cost on huge corpora (evenly subsampled).
_MAX_CENTROID_CHUNKS: int = 400

_ENCODER = tiktoken.get_encoding("cl100k_base")


def _weighted_mean(dicts: list[dict[str, Any]], weights: list[float]) -> dict[str, Any]:
    """Average numeric leaves; recurse one level for nested dicts (distributions)."""
    if not dicts:
        return {}
    total_w = sum(weights) or 1.0
    keys = dicts[0].keys()
    out: dict[str, Any] = {}
    for key in keys:
        sample = dicts[0][key]
        if isinstance(sample, dict):
            nested_keys = sample.keys()
            nested: dict[str, float] = {}
            for nk in nested_keys:
                nested[nk] = (
                    sum(d[key].get(nk, 0.0) * w for d, w in zip(dicts, weights, strict=True))
                    / total_w
                )
            out[key] = nested
        else:
            out[key] = sum(float(d[key]) * w for d, w in zip(dicts, weights, strict=True)) / total_w
    return out


def _spread_order(n: int) -> list[int]:
    """Permutation of ``range(n)`` whose every prefix is spread over the range.

    Bisection (van der Corput) order: ``0, n/2, n/4, 3n/4, n/8, …``.  Taking
    the first *k* elements therefore samples the *whole* sequence rather than
    its opening — the property :func:`_lemmas_from_docs` needs so that a
    truncated lemma budget is not spent entirely on the first document of the
    corpus (issue #100: the 800k-char cap fell at 21% of Dickens' chunks, so
    ``distinctive_vocab`` was the vocabulary of *Great Expectations* alone).

    Cheap and deterministic: no extra spaCy work, no extra memory, and the
    same chunks are selected on every run for a given corpus.
    """
    if n <= 0:
        return []
    order: list[int] = [0]
    seen: set[int] = {0}
    denom = 2
    while len(order) < n and denom <= 2 * n:
        for num in range(1, denom, 2):
            idx = (num * n) // denom
            if idx < n and idx not in seen:
                seen.add(idx)
                order.append(idx)
        denom *= 2
    order.extend(i for i in range(n) if i not in seen)
    return order


def _in_spread_order(items: list[Any]) -> list[Any]:
    """*items* reordered by :func:`_spread_order`."""
    return [items[i] for i in _spread_order(len(items))]


def _lemmas_from_docs(docs: Iterable[Any], max_chars: int = _MAX_LEMMA_CHARS) -> str:
    """Space-joined lower lemmas (alpha, non-proper, len>=3) for TF-IDF input.

    *docs* may be a lazy iterable (e.g. the generator returned by
    ``nlp.pipe``): the function stops consuming it as soon as *max_chars*
    is reached, so the cost is bounded by the cap, not by corpus size.
    Callers are responsible for handing the docs over in spread order
    (:func:`_in_spread_order`) so that an early stop still samples the whole
    corpus.

    ``PROPN`` tokens are dropped.  Character and place names are genuinely
    concentrated in one author's corpus, so TF-IDF ranks them first — but they
    identify the *novel*, not the author's hand, and ``distinctive_vocab`` is
    the one feature a non-technical juror reads directly
    (docs/style_features.md §4.1; decision 2026-07-28 in docs/decision_log.md).
    The filter lives here, where spaCy's POS tag is already computed, so it is
    free and stays correct for authors added later — unlike a hand-maintained
    word blacklist applied after the TF-IDF.
    """
    parts: list[str] = []
    size = 0
    for doc in docs:
        for tok in doc:
            if tok.pos_ == "PROPN":
                continue
            if tok.is_alpha and len(tok.lemma_) >= 3:
                piece = tok.lemma_.lower()
                parts.append(piece)
                size += len(piece) + 1
                if size >= max_chars:
                    return " ".join(parts)
    return " ".join(parts)


def lemmatize_corpus(
    *,
    documents: list[str],
    nlp: Any,
    chunk_texts: list[str] | None = None,
    max_chars: int = _MAX_LEMMA_CHARS,
) -> str:
    """Lemmatize *documents* into the single TF-IDF "document" of §4.1.

    docs/style_features.md §4.1 defines ``distinctive_vocab`` as TF-IDF where
    each author's full corpus is one document and the collection is all three
    authors combined.  Callers that own more than one author's corpus (the
    seeding script) use this to build the ``comparison_lemmas`` mapping that
    :func:`compute_style_profile` expects, without having to reimplement the
    lemma rules — alpha-only, lowercase, ``len >= 3``, no ``PROPN`` — or the
    ``_MAX_LEMMA_CHARS`` cap that bounds peak memory per author.

    The spaCy pass streams and stops at *max_chars*, so lemmatizing a
    comparison corpus costs a fraction of a full feature pass over it.  The
    chunks are fed in :func:`_spread_order`, so the chunks that fit inside the
    cap are drawn from every document of the corpus instead of from whichever
    novel happens to come first (issue #100).

    Returns an empty string when *documents* produce no chunks.
    """
    full_text = "\n\n".join(documents)
    chunks = chunk_texts if chunk_texts is not None else chunk_text(full_text)
    if not chunks:
        return ""
    sampled = _in_spread_order(chunks)
    return _lemmas_from_docs(nlp.pipe(sampled, batch_size=64), max_chars=max_chars)


def _subsample(items: list[str], max_n: int) -> list[str]:
    if len(items) <= max_n:
        return items
    if max_n <= 1:
        return items[:1]
    step = (len(items) - 1) / (max_n - 1)
    return [items[round(i * step)] for i in range(max_n)]


def compute_style_profile(
    *,
    author_slug: str,
    documents: list[str],
    nlp: Any,
    comparison_lemmas: dict[str, str] | None = None,
    chunk_texts: list[str] | None = None,
    computed_at: str | None = None,
) -> dict[str, Any]:
    """Build a StyleProfile v1.0 dict for *author_slug*.

    Parameters
    ----------
    author_slug:
        Stable API id (``austen`` / ``dickens`` / ``poe`` / …).
    documents:
        Cleaned document texts (already through ``clean_text`` when seeded).
    nlp:
        Loaded spaCy model (``en_core_web_lg``).  Caller owns lifecycle.
    comparison_lemmas:
        Optional ``{slug: lemmatized_corpus}`` for TF-IDF.  When omitted or
        containing only this author, distinctive_vocab may be empty / weak.
    chunk_texts:
        Precomputed ~500-token chunks.  When ``None``, documents are chunked
        with ``chunk_text`` (500 / 50).
    computed_at:
        ISO-8601 UTC timestamp; defaults to now.
    """
    if not documents:
        raise ValueError("compute_style_profile requires at least one document")

    full_text = "\n\n".join(documents)
    chunks = chunk_texts if chunk_texts is not None else chunk_text(full_text)
    if not chunks:
        raise ValueError("corpus produced zero chunks")

    docs = list(nlp.pipe(chunks, batch_size=64))
    weights = [float(max(len(d), 1)) for d in docs]

    lexical = _weighted_mean([compute_lexical(d) for d in docs], weights)
    syntactic = _weighted_mean([compute_syntactic(d) for d in docs], weights)
    stylistic = _weighted_mean([compute_stylistic(d) for d in docs], weights)

    # Spread order, same as lemmatize_corpus: this author's own TF-IDF
    # "document" must be built the same way as the comparison corpora it is
    # scored against, and the cap must not fall inside the first novel (#100).
    author_lemmas = _lemmas_from_docs(_in_spread_order(docs))
    corpora = dict(comparison_lemmas or {})
    corpora[author_slug] = author_lemmas
    try:
        distinctive = compute_distinctive_vocab(corpora, author_slug, top_n=30)
    except Exception:
        distinctive = []

    centroid_chunks = _subsample(chunks, _MAX_CENTROID_CHUNKS)
    embeddings = embed_chunks(centroid_chunks)
    if embeddings.size == 0:
        centroid = [0.0] * EMBEDDING_DIM
    else:
        centroid = embeddings.mean(axis=0).astype(float).tolist()

    n_tokens = len(_ENCODER.encode(full_text))
    n_sentences = sum(len(list(d.sents)) for d in docs)

    return {
        "schema_version": "1.0",
        "author_id": author_slug,
        "computed_at": computed_at or datetime.now(UTC).isoformat(),
        "corpus_stats": {
            "n_documents": len(documents),
            "n_tokens": n_tokens,
            "n_sentences": max(n_sentences, 1),
        },
        "lexical": {
            "mattr_500": float(lexical.get("mattr_500", 0.0)),
            "avg_word_length": float(lexical.get("avg_word_length", 0.0)),
            "hapax_ratio": float(lexical.get("hapax_ratio", 0.0)),
        },
        "syntactic": {
            "avg_sentence_length_tokens": float(syntactic.get("avg_sentence_length_tokens", 0.0)),
            "std_sentence_length_tokens": float(syntactic.get("std_sentence_length_tokens", 0.0)),
            "subordination_ratio": float(syntactic.get("subordination_ratio", 0.0)),
            "passive_voice_ratio": float(syntactic.get("passive_voice_ratio", 0.0)),
            "noun_to_verb_ratio": float(syntactic.get("noun_to_verb_ratio", 0.0)),
        },
        "stylistic": stylistic,
        "distinctive_vocab": distinctive,
        "semantic_centroid": centroid,
        # Placeholder — scripts/precompute_umap.py owns real 2-D coords.
        "embedding_umap_2d": {"centroid": [0.0, 0.0], "spread": 0.0},
    }


def profile_hash(profile: dict[str, Any]) -> str:
    """Canonical sha256 hash — must match passport/builder.py."""
    canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
