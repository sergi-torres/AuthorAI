"""Distinctive vocabulary extraction — §4.1 of docs/style_features.md.

Public API
----------
compute_distinctive_vocab(corpora_lemmas, author_id, top_n=30) -> list[dict]
    Returns the top-*n* TF-IDF signature terms for *author_id* relative to the
    other authors in *corpora_lemmas*.
"""

from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# TfidfVectorizer settings per docs/style_features.md §4.1 (locked).
_TOKEN_PATTERN = r"(?u)\b[a-zA-Z]{3,}\b"
_MAX_FEATURES = 50_000


def compute_distinctive_vocab(
    corpora_lemmas: dict[str, str],
    author_id: str,
    top_n: int = 30,
) -> list[dict]:
    """Return the top-*n* TF-IDF signature terms for *author_id*.

    Parameters
    ----------
    corpora_lemmas:
        Mapping of ``author_id → lemmatized corpus text``.  Each value is the
        full lemmatized corpus already produced by a prior spaCy pass — this
        function does **not** load spaCy or re-lemmatize anything.
    author_id:
        Key in *corpora_lemmas* whose top terms are returned.
    top_n:
        Maximum number of terms to return (default 30, per §4.1).

    Returns
    -------
    list[dict]
        Each element is ``{"term": str, "score": float}``, sorted by score
        descending.  The list may be shorter than *top_n* when the corpus
        contains fewer than *top_n* distinct valid tokens.

    Notes
    -----
    * Each author's full corpus is treated as **one TF-IDF document**, so the
      three-author collection is a three-document corpus.
    * The vectorizer uses ``stop_words="english"``, ``ngram_range=(1, 1)``,
      ``max_features=50000``, and ``token_pattern=r"(?u)\\b[a-zA-Z]{3,}\\b"``
      (alpha-only, minimum 3 characters) — exactly as specified in §4.1.
    * No spaCy model is loaded here; the caller owns the model lifecycle.
    """
    if author_id not in corpora_lemmas:
        raise KeyError(f"author_id {author_id!r} not found in corpora_lemmas")

    # Stable ordering so the TF-IDF row index is predictable.
    authors = list(corpora_lemmas.keys())
    corpus_docs = [corpora_lemmas[a] for a in authors]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 1),
        max_features=_MAX_FEATURES,
        token_pattern=_TOKEN_PATTERN,
    )

    tfidf_matrix = vectorizer.fit_transform(corpus_docs)  # shape: (n_authors, n_features)
    feature_names: list[str] = vectorizer.get_feature_names_out().tolist()

    author_idx = authors.index(author_id)
    # Convert the sparse row to a dense 1-D array.
    scores: np.ndarray = np.asarray(tfidf_matrix[author_idx].todense()).flatten()

    # Sort feature indices by TF-IDF score descending.
    ranked_indices = np.argsort(scores)[::-1]

    result: list[dict] = []
    for idx in ranked_indices:
        if len(result) >= top_n:
            break
        score = float(scores[idx])
        if score == 0.0:
            # Remaining features are all zero — nothing more to add.
            break
        result.append({"term": feature_names[idx], "score": score})

    return result
