"""Unit tests for compute_style_profile (ML mocked where heavy).

Skipped when spaCy / numpy are not installed in the active environment
(backend-only CI images). Full ai_pipeline[dev] install runs them.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

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
    # embedding_umap_2d starts as the pre-projection placeholder; the real
    # centroid/spread is written later by scripts/precompute_umap.py once
    # umap_coords rows exist (WO-07 / 0004_umap_coords.sql).
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


# --- Proper-noun filter (issue #100 / WO-18) ------------------------------
#
# docs/style_features.md 4.1 requires proper nouns to be dropped *inside* the
# lemmatization pass, so character and place names never reach the log-odds
# scorer. Without the filter these names are the top-scoring terms of an
# author's distinctive_vocab -- they identify the novel, not the author's hand.
# This test fails if the NOUN/ADJ/ADV allow-list in _lemmas_from_docs is
# widened to include PROPN: the names below are the only PROPN tokens in the
# sample.

_PROPER_NOUNS = ("havisham", "wemmick", "pemberley")
_COMMON_NOUNS = ("parlour", "candle", "housekeeper", "lantern", "garden")

_NAMED_SENTENCE = (
    "Havisham sat alone in the parlour while Wemmick counted the candles "
    "and the housekeeper carried a heavy lantern toward the garden gate at "
    "Pemberley before the evening meal was served. "
)


def test_lemmatize_corpus_drops_proper_nouns() -> None:
    """Character and place names must not survive into the log-odds input."""
    lemmas = set(
        lemmatize_corpus(documents=[_NAMED_SENTENCE * 200], nlp=_NLP, max_chars=60_000).split()
    )

    leaked = sorted(name for name in _PROPER_NOUNS if name in lemmas)
    assert not leaked, f"proper nouns reached the log-odds input: {leaked}"

    # Guard against the test passing for the wrong reason (empty/degenerate
    # lemma string): the common nouns of the same sentences must survive.
    kept = sorted(noun for noun in _COMMON_NOUNS if noun in lemmas)
    assert kept == sorted(_COMMON_NOUNS), f"common nouns were dropped too: {kept}"


def test_lemmatize_corpus_keeps_only_noun_adj_adv() -> None:
    """Narrative verbs must not reach distinctive_vocab input (§4.1 POS filter)."""
    text = (
        "She said she knew and thought and made the elegant sensible garden "
        "quietly while the amiable lady walked slowly toward the parlour. "
    )
    lemmas = set(lemmatize_corpus(documents=[text * 100], nlp=_NLP, max_chars=60_000).split())
    verb_noise = {"say", "know", "think", "make", "walk"}
    leaked = sorted(v for v in verb_noise if v in lemmas)
    assert not leaked, f"verbs reached the log-odds input: {leaked}"
    assert "garden" in lemmas or "parlour" in lemmas or "lady" in lemmas


# ---------------------------------------------------------------------------
# UMAP projection back-fill (WO-07)
# ---------------------------------------------------------------------------
#
# update_style_profiles() in scripts/precompute_umap.py aggregates per-chunk
# UMAP coords into a { "centroid": [x, y], "spread": float } dict and writes
# it to style_profiles.json_data.embedding_umap_2d via a parameterised UPDATE.
#
# The test uses a synthetic (author_id, coords) fixture so it runs without a
# real database or UMAP installation.  psycopg2 is mocked at the connection
# level: we capture the SQL and parameters passed to cur.execute and verify
# they encode the correct centroid / spread values.

_AUTHOR_A = "aaaaaaaa-0000-0000-0000-000000000001"
_AUTHOR_B = "bbbbbbbb-0000-0000-0000-000000000002"


def _make_coords() -> np.ndarray:
    """Synthetic 2-D coords: 4 points for author A, 3 for author B."""
    return np.array(
        [
            # author A — centroid should be (1.0, 2.0)
            [0.0, 1.0],
            [1.0, 2.0],
            [2.0, 3.0],
            [1.0, 2.0],
            # author B — centroid should be (10.0, 20.0)
            [9.0, 18.0],
            [10.0, 20.0],
            [11.0, 22.0],
        ],
        dtype=np.float64,
    )


def _make_author_ids() -> list[str]:
    return [_AUTHOR_A] * 4 + [_AUTHOR_B] * 3


def test_update_style_profiles_sql_payload() -> None:
    """update_style_profiles writes correct centroid/spread JSON via UPDATE."""
    # Import lazily: the script lives outside the package; add scripts/ to sys.path
    import os
    import sys

    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
    scripts_dir = os.path.normpath(scripts_dir)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    # psycopg2 may not be installed in every CI image — skip gracefully.
    pytest.importorskip("psycopg2")

    # Patch psycopg2.connect so the script never touches a real DB.
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cur
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    # Import after sys.path is set up.
    import precompute_umap

    author_ids = _make_author_ids()
    coords = _make_coords()

    precompute_umap.update_style_profiles(mock_conn, author_ids, coords)

    # One UPDATE call per author, then one commit.
    assert mock_conn.commit.called
    update_calls = list(mock_cur.execute.call_args_list)
    assert len(update_calls) == 2, f"Expected 2 UPDATE calls, got {len(update_calls)}"

    # Collect (payload_dict, author_id) from the two calls.
    results: dict[str, dict] = {}
    for c in update_calls:
        args = c.args  # (sql, (payload_json, author_id))
        payload_json, aid = args[1]
        results[aid] = json.loads(payload_json)

    # Author A: centroid = mean([0,1,2,1], [1,2,3,2]) = [1.0, 2.0]
    centroid_a = results[_AUTHOR_A]["centroid"]
    assert abs(centroid_a[0] - 1.0) < 1e-9, centroid_a
    assert abs(centroid_a[1] - 2.0) < 1e-9, centroid_a
    assert results[_AUTHOR_A]["spread"] >= 0.0

    # Author B: centroid = mean([9,10,11], [18,20,22]) = [10.0, 20.0]
    centroid_b = results[_AUTHOR_B]["centroid"]
    assert abs(centroid_b[0] - 10.0) < 1e-9, centroid_b
    assert abs(centroid_b[1] - 20.0) < 1e-9, centroid_b
    assert results[_AUTHOR_B]["spread"] >= 0.0

    # The two authors must have different centroids.
    assert centroid_a != centroid_b


def test_update_style_profiles_spread_formula() -> None:
    """spread = mean Euclidean distance of each chunk from its author centroid."""
    import os
    import sys

    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
    scripts_dir = os.path.normpath(scripts_dir)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    pytest.importorskip("psycopg2")

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cur
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    import precompute_umap

    # Four points equidistant from centroid (0,0) at radius=1.
    coords = np.array([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]], dtype=np.float64)
    author_ids = [_AUTHOR_A] * 4

    precompute_umap.update_style_profiles(mock_conn, author_ids, coords)

    update_calls = mock_cur.execute.call_args_list
    assert len(update_calls) == 1
    payload_json, _ = update_calls[0].args[1]
    result = json.loads(payload_json)

    # centroid = (0, 0); each point is distance 1 from centre → spread = 1.0
    assert abs(result["centroid"][0]) < 1e-9
    assert abs(result["centroid"][1]) < 1e-9
    assert abs(result["spread"] - 1.0) < 1e-9, f"spread={result['spread']}"
