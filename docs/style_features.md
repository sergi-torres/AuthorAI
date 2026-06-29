# AutorIA — Style Feature Definitions

> **Owner**: P2 · **Status**: Sprint 0 draft · **Last updated**: 2026-06-29
> **Schema version this document describes**: `StyleProfile v1.0`
> **Stack**: spaCy `en_core_web_lg` · sentence-transformers `all-mpnet-base-v2`

This document is the authoritative reference for every metric stored in a `StyleProfile`. For each feature it defines: what it measures, how it is computed, why it was chosen, and the expected range per preloaded author (Austen / Dickens / Poe). These ranges serve as sanity-check thresholds during extraction and as reference values in the demo.

Features not listed here are **out of scope for v1.0** and must go through a Decision Log entry before being added.

---

## Table of Contents

1. [Lexical features](#1-lexical-features)
2. [Syntactic features](#2-syntactic-features)
3. [Stylistic features](#3-stylistic-features)
4. [Distinctive vocabulary](#4-distinctive-vocabulary)
5. [Semantic features](#5-semantic-features)
6. [fit\_score — composite metric](#6-fit_score--composite-metric)
7. [Expected ranges per author](#7-expected-ranges-per-author)
8. [Computation pipeline](#8-computation-pipeline)
9. [Known limitations](#9-known-limitations)

---

## 1. Lexical features

Lexical features capture **vocabulary richness and word-level choices** — how varied and how complex the author's word selection is, independently of grammar.

### 1.1 `mattr_500` — Moving Average Type-Token Ratio

**What it measures**: vocabulary richness, stabilized across corpus length.

**Why not plain TTR**: plain Type-Token Ratio (unique tokens / total tokens) decreases monotonically as text length grows, making it useless for comparing corpora of different sizes (Austen ~330k words vs Poe ~70k words). MATTR fixes this by computing TTR over a sliding window of 500 tokens and averaging across all windows.

**How it is computed**:
```
mattr_500 = mean( TTR(window_i) for each window of 500 tokens )
where TTR(window_i) = unique_tokens(window_i) / 500
```

**Tool**: computed with the `lexical_diversity` Python package or manually with a sliding window over `doc` tokens.

**Interpretation**: higher = richer vocabulary per 500-token block.

**Expected ranges**:
| Author | Range |
|---|---|
| Austen | 0.62 – 0.68 |
| Dickens | 0.58 – 0.64 |
| Poe | 0.66 – 0.73 |

---

### 1.2 `avg_word_length` — Average Word Length

**What it measures**: the mean number of characters per word, excluding punctuation tokens.

**Why it matters**: Poe deliberately uses long Latinate and archaic words (*phantasm*, *physiognomy*, *luminousness*) to create a Gothic, elevated register. Austen's prose is conversational and prefers shorter words. This single number is immediately interpretable by a non-technical judge.

**How it is computed**:
```python
words = [t.text for t in doc if t.is_alpha]
avg_word_length = sum(len(w) for w in words) / len(words)
```

**Expected ranges**:
| Author | Range |
|---|---|
| Austen | 4.0 – 4.5 |
| Dickens | 4.6 – 5.1 |
| Poe | 5.0 – 5.6 |

---

### 1.3 `hapax_ratio` — Hapax Legomena Ratio

**What it measures**: the proportion of word types that appear **exactly once** in the corpus.

**Why it matters**: a high hapax ratio signals an author who actively avoids repetition and draws from a wide, exotic vocabulary — a hallmark of Poe. It is complementary to `mattr_500`: MATTR measures local richness per window; hapax ratio measures global uniqueness across the full corpus.

**How it is computed**:
```python
from collections import Counter
freq = Counter(t.lemma_.lower() for t in doc if t.is_alpha)
hapax_ratio = sum(1 for v in freq.values() if v == 1) / len(freq)
```

Note: computed over **lemmas**, not raw forms, to avoid counting inflections as separate types.

**Expected ranges**:
| Author | Range |
|---|---|
| Austen | 0.38 – 0.44 |
| Dickens | 0.40 – 0.46 |
| Poe | 0.48 – 0.56 |

---

## 2. Syntactic features

Syntactic features capture **sentence architecture** — how sentences are structured, how complex they are, and what grammatical patterns dominate. All syntactic analysis is performed with spaCy's dependency parser (`en_core_web_lg`).

### 2.1 `avg_sentence_length_tokens` and `std_sentence_length_tokens`

**What they measure**: mean and standard deviation of sentence length in tokens.

**Why both matter**: the mean tells you how long Dickens's sentences are on average (~28 tokens); the standard deviation tells you how much they vary. Dickens has both very long, sprawling sentences and short, punchy ones — high std. Austen is more controlled. These two numbers appear directly in the demo side-by-side comparison.

**How they are computed**:
```python
import statistics
lengths = [len(sent) for sent in doc.sents]
avg = statistics.mean(lengths)
std = statistics.stdev(lengths)
```

**Expected ranges**:
| Author | avg | std |
|---|---|---|
| Austen | 22 – 28 | 10 – 14 |
| Dickens | 25 – 32 | 13 – 17 |
| Poe | 24 – 34 | 14 – 20 |

---

### 2.2 `subordination_ratio` — Subordination Ratio

**What it measures**: the proportion of tokens that are the root of a subordinate clause.

**Why it matters**: subordination is the primary driver of syntactic complexity. Dickens constructs long, nested sentences where one clause depends on another. This ratio captures that tendency directly from the dependency tree.

**How it is computed**:
```python
SUBORDINATE_DEPS = {"advcl", "relcl", "ccomp", "xcomp"}
subordinate = sum(1 for t in doc if t.dep_ in SUBORDINATE_DEPS)
subordination_ratio = subordinate / len(list(doc.sents))
```

Normalized per sentence (not per token) so it is not confounded by sentence length.

**Expected ranges**:
| Author | Range |
|---|---|
| Austen | 0.28 – 0.36 |
| Dickens | 0.34 – 0.44 |
| Poe | 0.22 – 0.32 |

---

### 2.3 `noun_to_verb_ratio` — Noun-to-Verb Ratio

**What it measures**: the ratio of NOUN tokens to VERB tokens across the corpus.

**Why it matters**: a high ratio indicates a **nominal style** — descriptive, scene-setting, rich in objects and characters. A low ratio indicates a more **verbal style** — action-oriented, dynamic. Austen and Dickens are more nominal (they describe scenes and characters at length); Poe's Gothic action sequences are more verbal.

**How it is computed**:
```python
nouns = sum(1 for t in doc if t.pos_ == "NOUN")
verbs = sum(1 for t in doc if t.pos_ == "VERB")
noun_to_verb_ratio = nouns / verbs
```

**Expected ranges**:
| Author | Range |
|---|---|
| Austen | 1.6 – 2.0 |
| Dickens | 1.7 – 2.1 |
| Poe | 1.2 – 1.6 |

---

### 2.4 `passive_voice_ratio` — Passive Voice Ratio

**What it measures**: the proportion of sentences containing at least one passive construction.

**Why it matters**: Poe systematically uses the passive voice to create psychological distance between narrator and event — "it was heard", "the door was opened" — amplifying dread without agency. This is one of the most **author-discriminating** features in the syntactic block.

**How it is computed**:
```python
passive_sentences = sum(
    1 for sent in doc.sents
    if any(t.dep_ == "nsubjpass" for t in sent)
)
passive_voice_ratio = passive_sentences / len(list(doc.sents))
```

**Expected ranges**:
| Author | Range |
|---|---|
| Austen | 0.06 – 0.12 |
| Dickens | 0.08 – 0.14 |
| Poe | 0.18 – 0.28 |

---

## 3. Stylistic features

Stylistic features capture **surface patterns** — punctuation habits, part-of-speech distributions, and narrator perspective. These are fast to compute and highly stable across works by the same author.

### 3.1 `punct_distribution` — Punctuation Distribution

**What it measures**: the relative frequency of each punctuation mark, normalized over all punctuation tokens.

**Why it matters**: punctuation is the author's "breath marks" — it encodes rhythm and pacing at the surface level. The semicolon (`;`) is Dickens's signature pause for dramatic elaboration. The em-dash (`—`) is Poe's interruption and intensification. Austen's high quotation mark frequency (`"`) reflects her dialogue-heavy social novels.

**How it is computed**:
```python
from collections import Counter
PUNCT_MARKS = {",", ".", ";", ":", "—", "?", "!", '"'}
counts = Counter(t.text for t in doc if t.text in PUNCT_MARKS)
total = sum(counts.values())
punct_distribution = {k: v / total for k, v in counts.items()}
```

**Stored as**: a dict with keys `[",", ".", ";", ":", "—", "?", "!", "\""]`.

**Key signals**:
| Mark | Dickens | Poe | Austen |
|---|---|---|---|
| `;` | High | Low | Medium |
| `—` | Low | High | Low |
| `"` | Medium | Low | High |

---

### 3.2 `pos_distribution` — Part-of-Speech Distribution

**What it measures**: the relative frequency of each universal POS tag across all tokens (excluding punctuation).

**Why it matters**: POS distribution captures the grammatical texture of prose — how much the author relies on adjectives, adverbs, pronouns, etc. It is one of the five components of `fit_score` (Jaccard similarity between generated text and profile distributions).

**How it is computed**:
```python
TRACKED_POS = {"NOUN","VERB","ADJ","ADV","DET","ADP","PRON","CONJ","SCONJ"}
counts = Counter(t.pos_ for t in doc if not t.is_punct)
total = sum(counts[p] for p in TRACKED_POS)
pos_distribution = {p: counts[p] / total for p in TRACKED_POS}
pos_distribution["OTHER"] = 1 - sum(pos_distribution.values())
```

**Stored as**: a dict with 10 keys (9 POS tags + `OTHER`).

---

### 3.3 `dialogue_ratio` — Dialogue Ratio

**What it measures**: the proportion of tokens that appear inside quotation marks (direct speech).

**Why it matters**: this single number cleanly separates Austen from the other two. Her novels are driven by dialogue — social sparring, misunderstandings, wit — while Poe is almost entirely first-person interior monologue with minimal direct speech.

**How it is computed**:
```python
in_dialogue = False
dialogue_tokens = 0
total_tokens = 0
for token in doc:
    if token.text == '"':
        in_dialogue = not in_dialogue
        continue
    total_tokens += 1
    if in_dialogue:
        dialogue_tokens += 1
dialogue_ratio = dialogue_tokens / total_tokens
```

**Expected ranges**:
| Author | Range |
|---|---|
| Austen | 0.28 – 0.38 |
| Dickens | 0.20 – 0.28 |
| Poe | 0.05 – 0.14 |

---

### 3.4 `first_person_ratio` — First-Person Pronoun Ratio

**What it measures**: the frequency of first-person singular pronouns (*I, me, my, mine, myself*) per 1,000 tokens.

**Why it matters**: Poe almost exclusively writes in close first-person — the narrator *is* the protagonist, confessing, spiraling, obsessing. Austen writes in third-person omniscient and never uses "I" in narration. This is the sharpest Poe discriminator in the stylistic block.

**How it is computed**:
```python
FIRST_PERSON = {"i", "me", "my", "mine", "myself"}
fp_count = sum(1 for t in doc if t.lower_ in FIRST_PERSON)
first_person_ratio = (fp_count / len(doc)) * 1000  # per 1k tokens
```

**Expected ranges**:
| Author | Range (per 1k tokens) |
|---|---|
| Austen | 0.5 – 3.0 |
| Dickens | 4.0 – 9.0 |
| Poe | 18.0 – 30.0 |

---

## 4. Distinctive vocabulary

### 4.1 `distinctive_vocab` — TF-IDF Signature Words

**What it measures**: the words that are **most characteristic of one author relative to the others** — not just frequent words, but words that are unusually concentrated in that author's corpus.

**Why it matters**: this is the feature the audience *sees* in the demo. When the AutorIA output contains "countenance", "physiognomy", and "presently" for Dickens, the jury can read and feel the difference without understanding a single number.

**How it is computed**: standard TF-IDF where each author's full corpus is one "document" and the collection is all three authors combined.

```python
from sklearn.feature_extraction.text import TfidfVectorizer

corpora = {
    "austen": "<full austen corpus>",
    "dickens": "<full dickens corpus>",
    "poe": "<full poe corpus>"
}

vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 1),
    max_features=50000,
    token_pattern=r"(?u)\b[a-zA-Z]{3,}\b"  # min 3 chars, alpha only
)

tfidf_matrix = vectorizer.fit_transform(corpora.values())
# For each author: sort features by TF-IDF score descending
# Store top-N as distinctive_vocab list
```

**Stored as**: a list of `{ "term": str, "score": float }` objects, sorted by score descending. Top 30 terms per author.

**Preprocessing**: lemmatize before TF-IDF, exclude stopwords, exclude tokens shorter than 3 characters.

---

## 5. Semantic features

Semantic features capture **what the author writes about and the meaning-space they inhabit**, independently of surface form. They are computed with sentence-transformers `all-mpnet-base-v2` (768-dimensional embeddings).

### 5.1 `semantic_centroid` — Author Semantic Centroid

**What it measures**: the mean embedding vector across all ~500-token chunks of the author's corpus. It represents the author's "average semantic position" in the 768-dim embedding space.

**Why it matters**: it is the single most important feature for `fit_score` (35% weight). When the model generates a text conditioned on Dickens, the generated text's embedding should land close to this centroid.

**How it is computed**:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-mpnet-base-v2")

chunk_embeddings = model.encode(chunks)  # chunks: list of ~500-token strings
semantic_centroid = chunk_embeddings.mean(axis=0)  # shape: (768,)
```

**Stored as**: a list of 768 floats in the `StyleProfile` JSON.

---

### 5.2 `embedding_umap_2d` — UMAP 2D Projection

**What it measures**: a 2-dimensional projection of the `semantic_centroid`, used exclusively for the demo visualization (the scatter plot showing authors as clusters).

**Why UMAP**: UMAP (Uniform Manifold Approximation and Projection) preserves local and global structure better than PCA for high-dimensional embeddings. The three authors should form clearly separated clusters at 2D.

**How it is computed**: UMAP is fit once on all chunk embeddings from all three authors combined, then the centroid of each author is projected.

```python
import umap
reducer = umap.UMAP(n_components=2, random_state=42)
all_embeddings = [...]  # all chunks from all authors
reducer.fit(all_embeddings)

centroid_2d = reducer.transform([semantic_centroid])[0]
embedding_umap_2d = {
    "centroid": centroid_2d.tolist(),   # [x, y]
    "spread": float(chunk_embeddings.std())  # intra-author spread
}
```

**Stored as**: `{ "centroid": [float, float], "spread": float }`.

---

## 6. `fit_score` — Composite Metric

The `fit_score` measures how closely a **generated text** matches a target author's `StyleProfile`. It is computed for both the vanilla and AutorIA outputs so the gap is always visible.

```
fit_score (0–1, then ×100) = weighted sum of:

  cosine_sim(embed_generated, semantic_centroid)           × 0.35
  (1 − |asl_generated − asl_profile| / asl_profile)       × 0.20
  (1 − |ttr_generated − mattr_profile| / mattr_profile)   × 0.15
  jaccard(pos_dist_generated, pos_dist_profile)            × 0.15
  vocab_overlap(generated_vocab, distinctive_vocab_top30)  × 0.15
```

Where:
- `asl` = average sentence length in tokens
- `jaccard(A, B)` = sum of min(A[k], B[k]) / sum of max(A[k], B[k]) over all POS tags
- `vocab_overlap` = |generated_lemmas ∩ top30_distinctive| / 30

Output is clipped to [0, 1] and multiplied by 100. Displayed as e.g. **"87% Dickens-fit"**.

---

## 7. Expected ranges per author

Reference table for sanity checks during extraction. Flag any value outside these ranges for manual review.

| Feature | Austen | Dickens | Poe |
|---|---|---|---|
| `mattr_500` | 0.62–0.68 | 0.58–0.64 | 0.66–0.73 |
| `avg_word_length` | 4.0–4.5 | 4.6–5.1 | 5.0–5.6 |
| `hapax_ratio` | 0.38–0.44 | 0.40–0.46 | 0.48–0.56 |
| `avg_sentence_length_tokens` | 22–28 | 25–32 | 24–34 |
| `std_sentence_length_tokens` | 10–14 | 13–17 | 14–20 |
| `subordination_ratio` | 0.28–0.36 | 0.34–0.44 | 0.22–0.32 |
| `noun_to_verb_ratio` | 1.6–2.0 | 1.7–2.1 | 1.2–1.6 |
| `passive_voice_ratio` | 0.06–0.12 | 0.08–0.14 | 0.18–0.28 |
| `dialogue_ratio` | 0.28–0.38 | 0.20–0.28 | 0.05–0.14 |
| `first_person_ratio` (per 1k) | 0.5–3.0 | 4.0–9.0 | 18.0–30.0 |

> **Note**: these ranges are informed estimates based on stylometric literature and manual corpus inspection. They will be updated after Sprint 1 extraction runs on the actual Gutenberg corpora.

---

## 8. Computation pipeline

All features are computed in a single pass through the corpus by `ai_pipeline/extractor.py`. The pipeline runs in this order to minimize redundant tokenization:

```
raw .txt files
    → cleaner.py          (strip Gutenberg headers, normalize quotes/whitespace)
    → chunker.py          (500-token chunks, 50-token overlap, tiktoken cl100k_base)
    → spaCy en_core_web_lg (tokenization, POS, dependency parsing — batch mode)
         ├── lexical_features()     §1.1 – §1.3
         ├── syntactic_features()   §2.1 – §2.4
         └── stylistic_features()   §3.1 – §3.4
    → TfidfVectorizer (sklearn)
         └── distinctive_vocab()    §4.1
    → SentenceTransformer all-mpnet-base-v2
         └── semantic_features()    §5.1 – §5.2
    → StyleProfile JSON (persisted to Postgres)
```

spaCy processing is run in **batch mode** (`nlp.pipe(chunks, batch_size=64)`) to avoid loading the model once per chunk.

---

## 9. Known limitations

**MATTR window size**: 500 tokens is a reasonable default but has not been tuned for 19th-century English. If Austen and Dickens score too similarly, consider reducing to 300.

**Passive voice detection**: spaCy's `nsubjpass` label works well for canonical passives ("it was seen") but misses some complex or inverted passive constructions common in Victorian prose. Acceptable for v1.0.

**Dialogue detection**: the `dialogue_ratio` algorithm assumes straight ASCII quotation marks (`"`). Gutenberg texts sometimes use curly quotes (`"` `"`) — the cleaner must normalize these before extraction.

**UMAP non-determinism**: UMAP results vary slightly across runs even with `random_state=42` if the input data changes. The 2D coordinates are for visualization only and are not used in `fit_score`.

**Corpus size imbalance**: Poe's corpus (~70k words) is 4–5× smaller than Austen and Dickens. Features computed over the full corpus (hapax\_ratio, distinctive\_vocab) may be slightly less stable for Poe. Monitor the Sprint 2 extraction results.
