"""Unit tests for compute_style_profile (ML mocked where heavy).

Skipped when spaCy / numpy are not installed in the active environment
(backend-only CI images). Full ai_pipeline[dev] install runs them.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

np = pytest.importorskip("numpy")
spacy = pytest.importorskip("spacy")

from autoria_ai.extractor.style_profile import (  # noqa: E402
    compute_style_profile,
    lemmatize_corpus,
    profile_hash,
)

try:
    _NLP = spacy.load("en_core_web_lg")
except OSError:
    pytest.skip("en_core_web_lg not installed", allow_module_level=True)

_SAMPLE = (
    "It is a truth universally acknowledged, that a single man in possession "
    "of a good fortune, must be in want of a wife. However little known the "
    "feelings or views of such a man may be on his first entering a "
    "neighbourhood, this truth is so well fixed in the minds of the "
    "surrounding families, that he is considered the rightful property of "
    "some one or other of their daughters. "
) * 40


@pytest.fixture
def mock_embeddings():
    def _fake(texts: list[str]):
        n = len(texts)
        if n == 0:
            return np.zeros((0, 768), dtype=np.float32)
        rng = np.random.default_rng(0)
        return rng.normal(size=(n, 768)).astype(np.float32)

    with patch("autoria_ai.extractor.style_profile.embed_chunks", side_effect=_fake):
        yield


def test_compute_style_profile_shape(mock_embeddings) -> None:
    profile = compute_style_profile(
        author_slug="austen",
        documents=[_SAMPLE],
        nlp=_NLP,
        comparison_lemmas={"dickens": "fog city london poor orphan " * 200},
    )
    assert profile["schema_version"] == "1.0"
    assert profile["author_id"] == "austen"
    assert profile["corpus_stats"]["n_documents"] == 1
    assert profile["corpus_stats"]["n_tokens"] > 0
    assert 0.0 < profile["lexical"]["avg_word_length"] < 20.0
    assert len(profile["semantic_centroid"]) == 768
    assert profile["embedding_umap_2d"] == {"centroid": [0.0, 0.0], "spread": 0.0}
    assert set(profile["stylistic"]["punct_distribution"].keys()) >= {",", ".", '"'}


def test_profile_hash_stable(mock_embeddings) -> None:
    profile = compute_style_profile(
        author_slug="poe",
        documents=[_SAMPLE],
        nlp=_NLP,
        computed_at="2026-07-27T12:00:00+00:00",
    )
    h1 = profile_hash(profile)
    h2 = profile_hash(profile)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_compute_style_profile_rejects_empty() -> None:
    with pytest.raises(ValueError):
        compute_style_profile(author_slug="x", documents=[], nlp=_NLP)


# --- Corpus sampling (issue #100 / WO-18) ---------------------------------
#
# docs/style_features.md 4.1: "each author's full corpus is one document".
# The max_chars cap bounds peak memory, but it must not degenerate into a
# prefix of the corpus -- that made distinctive_vocab the vocabulary of
# whichever novel happened to be first in the manifest.

_MARKERS = ("kitchen", "mountain", "elephant")


def _marked_document(marker: str) -> str:
    """~5k tokens of neutral prose whose only distinctive noun is *marker*."""
    return (
        f"The {marker} was quiet that morning and the pale light fell across "
        f"the table where the {marker} rested beside the open window. "
    ) * 200


def test_lemmatize_corpus_samples_every_document() -> None:
    """A capped lemma string must draw on more than one document per author."""
    documents = [_marked_document(m) for m in _MARKERS]
    # Cap far below the corpus size: enough for several chunks, nowhere near
    # all of them. Prefix truncation would spend the whole budget on doc #1.
    lemmas = lemmatize_corpus(documents=documents, nlp=_NLP, max_chars=12_000)

    sampled = {marker for marker in _MARKERS if marker in lemmas.split()}
    assert len(sampled) > 1, f"capped corpus sampled only {sampled or 'nothing'}"
    assert sampled == set(_MARKERS), f"documents missing from the sample: {sampled}"
