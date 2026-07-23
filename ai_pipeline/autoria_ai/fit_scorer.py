"""fit_score — Composite authorial-fit metric.

Public API
----------
compute_fit_score(generated_text, style_profile, nlp, embedding_model) -> int
    Returns an integer in [0, 100] measuring how closely a generated text
    matches a target author's StyleProfile v1.0.

Algorithm (docs/style_features.md §6)
--------------------------------------
fit_score = semx0.35 + synx0.20 + lexx0.15 + styx0.15 + vocx0.15

Each sub-score is clamped to [0, 1] before weighting.
Final score is rounded and clamped to [0, 100] (int).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.spatial.distance import cosine as cosine_distance

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_POS_TAGS = ("NOUN", "VERB", "ADJ", "ADV", "DET", "ADP", "PRON", "CONJ", "SCONJ", "OTHER")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _semantic_score(
    generated_text: str,
    centroid: list[float],
    embedding_model: Any,
) -> float:
    """Cosine similarity between the generated text embedding and the author centroid."""
    centroid_vec = np.array(centroid, dtype=np.float32)
    generated_vec = np.array(embedding_model.encode(generated_text), dtype=np.float32).ravel()
    # scipy cosine returns distance; convert to similarity.
    # Guard against zero vectors (cosine_distance raises on zero norm).
    if np.linalg.norm(generated_vec) == 0.0 or np.linalg.norm(centroid_vec) == 0.0:
        return 0.0
    return float(1.0 - cosine_distance(generated_vec, centroid_vec))


def _syntactic_score(doc: Any, asl_profile: float) -> float:
    """1 - |asl_generated - asl_profile| / asl_profile."""
    if asl_profile == 0.0:
        return 0.0
    lengths = [len(sent) for sent in doc.sents]
    if not lengths:
        return 0.0
    asl_generated = sum(lengths) / len(lengths)
    return float(1.0 - abs(asl_generated - asl_profile) / asl_profile)


def _lexical_score(doc: Any, mattr_profile: float) -> float:
    """1 - |ttr_generated - mattr_profile| / mattr_profile.

    ttr_generated = unique_lemmas / total_lemmas  (punctuation excluded).
    """
    if mattr_profile == 0.0:
        return 0.0
    lemmas = [t.lemma_.lower() for t in doc if not t.is_punct]
    if not lemmas:
        return 0.0
    ttr_generated = len(set(lemmas)) / len(lemmas)
    return float(1.0 - abs(ttr_generated - mattr_profile) / mattr_profile)


def _pos_distribution(doc: Any) -> dict[str, float]:
    """Relative frequency of each tracked POS tag (excluding punctuation).

    Follows the same logic as docs/style_features.md §3.2.
    """
    tracked = {"NOUN", "VERB", "ADJ", "ADV", "DET", "ADP", "PRON", "CONJ", "SCONJ"}
    counts: dict[str, int] = dict.fromkeys(_POS_TAGS, 0)
    for token in doc:
        if token.is_punct:
            continue
        if token.pos_ in tracked:
            counts[token.pos_] += 1
        else:
            counts["OTHER"] += 1

    total_tracked = sum(counts[p] for p in tracked)
    if total_tracked == 0:
        return dict.fromkeys(_POS_TAGS, 0.0)

    dist: dict[str, float] = {p: counts[p] / total_tracked for p in tracked}
    dist["OTHER"] = 1.0 - sum(dist.values())
    return dist


def _stylistic_score(doc: Any, pos_dist_profile: dict[str, float]) -> float:
    """Jaccard similarity between generated and profile POS distributions.

    Jaccard(A, B) = Σ min(A[k], B[k]) / Σ max(A[k], B[k])
    over the union of keys in both dicts.
    """
    pos_dist_gen = _pos_distribution(doc)

    all_keys = set(pos_dist_gen) | set(pos_dist_profile)
    numerator = sum(min(pos_dist_gen.get(k, 0.0), pos_dist_profile.get(k, 0.0)) for k in all_keys)
    denominator = sum(max(pos_dist_gen.get(k, 0.0), pos_dist_profile.get(k, 0.0)) for k in all_keys)
    if denominator == 0.0:
        return 0.0
    return float(numerator / denominator)


def _vocabulary_score(doc: Any, distinctive_vocab: list[dict]) -> float:
    """len(generated_lemmas ∩ top30_distinctive) / 30."""
    top30: set[str] = {entry["term"] for entry in distinctive_vocab[:30] if "term" in entry}
    if not top30:
        return 0.0
    generated_lemmas = {t.lemma_.lower() for t in doc if t.is_alpha}
    return float(len(generated_lemmas & top30) / 30)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_fit_score(
    generated_text: str,
    style_profile: dict,
    nlp: Any,  # loaded spaCy model (en_core_web_lg)
    embedding_model: Any,  # loaded sentence-transformers model
) -> int:
    """Compute the composite fit_score for a generated text against a StyleProfile."""
    # 1. Ejecutar spaCy UNA sola vez
    doc = nlp(generated_text)
    # -- semantic (0.35) -------------------------------------------------------
    # Este usa sentence-transformers, así que le pasamos el texto en crudo
    centroid: list[float] = style_profile.get("semantic_centroid", [])
    sem = _clamp01(_semantic_score(generated_text, centroid, embedding_model))

    # -- syntactic (0.20) ------------------------------------------------------
    syntactic: dict = style_profile.get("syntactic", {})
    asl_profile: float = syntactic.get("avg_sentence_length_tokens", 0.0)
    syn = _clamp01(_syntactic_score(doc, asl_profile))

    # -- lexical (0.15) --------------------------------------------------------
    lexical: dict = style_profile.get("lexical", {})
    mattr_profile: float = lexical.get("mattr_500", 0.0)
    lex = _clamp01(_lexical_score(doc, mattr_profile))

    # -- stylistic (0.15) — POS Jaccard ----------------------------------------
    stylistic: dict = style_profile.get("stylistic", {})
    pos_dist_profile: dict[str, float] = stylistic.get("pos_distribution", {})
    sty = _clamp01(_stylistic_score(doc, pos_dist_profile))

    # -- vocabulary (0.15) -----------------------------------------------------
    distinctive_vocab: list[dict] = style_profile.get("distinctive_vocab", [])
    voc = _clamp01(_vocabulary_score(doc, distinctive_vocab))

    # -- composite -------------------------------------------------------------
    raw = sem * 0.35 + syn * 0.20 + lex * 0.15 + sty * 0.15 + voc * 0.15
    return int(max(0, min(100, round(raw * 100))))
