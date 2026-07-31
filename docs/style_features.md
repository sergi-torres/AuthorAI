# AutorIA — Style Feature Definitions

> **Owner**: P2 · **Status**: current — every range in §7 is a measurement, not an estimate · **Last updated**: 2026-07-30
> **Schema version this document describes**: `StyleProfile v1.0`
> **Stack**: spaCy `en_core_web_lg` · sentence-transformers `all-mpnet-base-v2`

This document is the authoritative reference for every metric stored in a `StyleProfile`. For each feature it defines: what it measures, how it is computed, why it was chosen, and the measured range per preloaded author (Austen / Dickens / Poe). These ranges serve as sanity-check thresholds during extraction and as reference values in the demo; since 2026-07-29 they are read from the computed profiles rather than estimated.

Features not listed here are **out of scope for v1.0** and must go through a Decision Log entry before being added.

---

## Table of Contents

1. [Lexical features](#1-lexical-features)
2. [Syntactic features](#2-syntactic-features)
3. [Stylistic features](#3-stylistic-features)
4. [Distinctive vocabulary](#4-distinctive-vocabulary)
5. [Semantic features](#5-semantic-features)
6. [fit\_score — composite metric](#6-fit_score--composite-metric)
7. [Measured ranges per author](#7-measured-ranges-per-author)
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

**Measured ranges** (seeded corpus, 2026-07-29):
| Author | Range |
|---|---|
| Austen | 0.49 – 0.57 |
| Dickens | 0.49 – 0.57 |
| Poe | 0.52 – 0.60 |

---

### 1.2 `avg_word_length` — Average Word Length

**What it measures**: the mean number of characters per word, excluding punctuation tokens.

**Why it matters**: Poe deliberately uses long Latinate and archaic words (*phantasm*, *physiognomy*, *luminousness*) to create a Gothic, elevated register. Austen's prose is conversational and prefers shorter words. This single number is immediately interpretable by a non-technical judge.

**How it is computed**:
```python
words = [t.text for t in doc if t.is_alpha]
avg_word_length = sum(len(w) for w in words) / len(words)
```

**Measured ranges** (seeded corpus, 2026-07-29):
| Author | Range |
|---|---|
| Austen | 3.99 – 4.69 |
| Dickens | 3.86 – 4.53 |
| Poe | 4.12 – 4.84 |

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

**Measured ranges** (seeded corpus, 2026-07-29):
| Author | Range |
|---|---|
| Austen | 0.65 – 0.73 |
| Dickens | 0.65 – 0.73 |
| Poe | 0.71 – 0.79 |

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

**Measured ranges** (seeded corpus, 2026-07-29):
| Author | avg | std |
|---|---|---|
| Austen | 27.6 – 32.4 | 20.5 – 24.1 |
| Dickens | 24.8 – 29.2 | 17.9 – 21.0 |
| Poe | 28.4 – 33.4 | 19.2 – 22.6 |

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

**Measured ranges** (seeded corpus, 2026-07-29):
| Author | Range |
|---|---|
| Austen | 1.67 – 1.96 |
| Dickens | 1.42 – 1.67 |
| Poe | 1.27 – 1.49 |

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

**Measured ranges** (seeded corpus, 2026-07-29):
| Author | Range |
|---|---|
| Austen | 1.06 – 1.24 |
| Dickens | 1.09 – 1.28 |
| Poe | 1.71 – 2.01 |

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

**Measured ranges** (seeded corpus, 2026-07-29):
| Author | Range |
|---|---|
| Austen | 0.13 – 0.21 |
| Dickens | 0.07 – 0.15 |
| Poe | 0.15 – 0.23 |

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

**Measured ranges** (seeded corpus, 2026-07-29):
| Author | Range |
|---|---|
| Austen | 0.27 – 0.35 |
| Dickens | 0.31 – 0.39 |
| Poe | 0.20 – 0.28 |

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


> **Measurement contradicts this rationale.** On the seeded corpora the order is Dickens 29.9 > Poe 24.8 > Austen 20.9 per 1k tokens — Poe is *not* the highest, and Austen, who "never uses 'I' in narration", still scores 20.9. The metric counts pronouns everywhere, including inside dialogue, and these are dialogue-heavy novels; it therefore measures how much the characters say "I", not how first-person the narration is. Read it as a stylistic signal, not as a narration-perspective detector. The same caution applies to `noun_to_verb_ratio` (§2.3 expects Poe lowest; measured, Poe is highest at 1.86) and to `dialogue_ratio` (§3.3 expects Poe lowest at 0.05–0.14; measured 0.245).

**Measured ranges** (seeded corpus, 2026-07-29) (per 1k tokens):
| Author | Range |
|---|---|
| Austen | 19.3 – 22.6 |
| Dickens | 27.5 – 32.3 |
| Poe | 22.8 – 26.7 |

---

## 4. Distinctive vocabulary

### 4.1 `distinctive_vocab` — Log-Odds-Ratio Signature Words (Jeffreys prior)

**What it measures**: the words that are **most characteristic of one author relative to the others** — words used at a higher *rate* by that author than by the rest combined.

**Why it matters**: this is the feature the audience *sees* in the demo — it is rendered directly in the Style DNA panel, so whatever it ranks first is what a non-technical juror reads.

**Algorithm history** — this section originally specified TF-IDF (each author's corpus as one "document," idf over the 3-document collection). That algorithm is **replaced as of 2026-07-30** (see `docs/decision_log.md`) by log-odds-ratio. A first Monroe/Colaresi/Quinn (2008) weighted z-score variant was prototyped the same day; measured side-by-side against a Jeffreys-prior (α=0.5) variant with a NOUN/ADJ/ADV-only lemma filter, the Jeffreys+POS-filter combination produced the more juror-readable signature lists and was adopted (scores normalized to [0, 1]). The reason TF-IDF had to go: with only 3 documents, any term present in all three has `df = 3/3` and therefore the *same* idf, which collapses the ranking to raw frequency — measured 3-way top-10 overlap under TF-IDF was **5** (`know`, `little`, `make`, `say`, `time`), against a ≤3 target.

**How it is computed**: for each author, compare per-word rates against the pooled other authors, with a Jeffreys prior (α = 0.5) to avoid `log(0)`. Keep only terms with positive log-odds, then normalize by the maximum raw score in that run so the stored range is `[0, 1]`.

```python
import math
from collections import Counter

alpha = 0.5  # Jeffreys prior
# Each value is the author's corpus already lemmatized and POS-filtered
# to NOUN/ADJ/ADV (see Preprocessing below).
author_counts = Counter(author_tokens)
other_counts = Counter(other_tokens)
total_a = sum(author_counts.values())
total_o = sum(other_counts.values())

for term, count_a in author_counts.items():
    count_o = other_counts.get(term, 0)
    p_a = (count_a + alpha) / (total_a + 2 * alpha)
    p_o = (count_o + alpha) / (total_o + 2 * alpha)
    log_odds = math.log(p_a / (1 - p_a)) - math.log(p_o / (1 - p_o))
    # keep log_odds > 0; normalize by max(raw) → score in [0, 1]
```

Implemented in `ai_pipeline/autoria_ai/extractor/vocabulary.py::compute_distinctive_vocab`.

**Stored as**: a list of `{ "term": str, "score": float }` objects, sorted by score descending, **only terms with positive log-odds**, scores normalized to `[0, 1]` within each author's run. Top 30 terms per author.

**Preprocessing**: lemmatize before scoring; keep only spaCy ``NOUN`` / ``ADJ`` / ``ADV`` (narrative verbs like `say`/`know`/`think` appear in all literary prose and add noise, not signal); exclude English stopwords; exclude tokens shorter than 3 characters; exclude a small set of corpus-metadata lemmas (`copyright`, `chapter`, `illustration`, …). Proper nouns are excluded as a consequence of the POS allow-list (decision 2026-07-28: character/place names are plot, not style).

**Corpus cleaning companion**: Project Gutenberg's illustrated editions embed `[Illustration]` / `[Illustration: caption]` markup inline. `cleaner.py::clean_text` strips these blocks before lemmatization; the metadata stop list above is a second line of defence if a lemma still slips through.

**How "full corpus" is realised**: `_MAX_LEMMA_CHARS` (800 000 lemma characters per author) bounds the seed's peak memory. That budget is spent on chunks drawn from **across the whole corpus**, in a deterministic bisection order (issue #100).

**Measured output** — run 2026-07-30 on the full `corpus/` with the Jeffreys log-odds scorer + NOUN/ADJ/ADV filter (`top_n=10` shown; production stores top 30). Scores are `[0, 1]`-normalized within each author.

| # | austen | score | dickens | score | poe | score |
|---|---|---|---|---|---|---|
| 1 | madam | 1.00 | trooper | 1.00 | color | 1.00 |
| 2 | regiment | 0.89 | convict | 0.90 | thicket | 0.99 |
| 3 | surprize | 0.87 | beadle | 0.89 | gray | 0.97 |
| 4 | voluntarily | 0.84 | sergeant | 0.88 | velocity | 0.97 |
| 5 | civility | 0.83 | forge | 0.86 | diameter | 0.97 |
| 6 | imprudent | 0.82 | client | 0.84 | solution | 0.94 |
| 7 | matrimony | 0.81 | courtyard | 0.79 | endeavor | 0.93 |
| 8 | surprized | 0.78 | professional | 0.79 | ballast | 0.93 |
| 9 | shire | 0.77 | workhouse | 0.78 | balloon | 0.91 |
| 10 | flattery | 0.76 | keeper | 0.78 | negro | 0.90 |

**Read this honestly.** The three-way top-10 overlap is **0** (down from 5 under TF-IDF), and every pairwise overlap is also 0. The lists read as recognisably different registers to a non-technical reader: Austen's courtship/society lexicon (`matrimony`, `civility`, `surprize`), Dickens' institutional/social world (`workhouse`, `beadle`, `convict`), Poe's scientific/gothic diction (`velocity`, `ballast`, `balloon`). A Monroe z-score variant without the POS filter ranked high-frequency narrative verbs (`say`, `think`, `talk`) first — statistically valid, but poorer for the Style DNA panel a jury reads.

**Known limitation**: log-odds finds words *concentrated in one author's corpus*, which is not always *authorial style* — plot- or story-specific nouns can still surface (Poe's `balloon`/`ballast` track particular tales). Down-weighting terms concentrated in one *document* within an author's own corpus remains a candidate future issue.

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
  (1 − |ttr_generated − mattr_profile|)                    × 0.15
  jaccard(pos_dist_generated, pos_dist_profile)            × 0.15
  vocab_overlap(generated_vocab, distinctive_vocab_top15)  × 0.15
```

Where:
- `asl` = average sentence length in tokens
- `jaccard(A, B)` = sum of min(A[k], B[k]) / sum of max(A[k], B[k]) over all POS tags
- `vocab_overlap` = min(1.0, |generated_lemmas ∩ top15_distinctive| / 5.0)

Output is clipped to [0, 1] and multiplied by 100. Displayed as e.g. **"87% Dickens-fit"**.

---

## 7. Measured ranges per author

Reference table for sanity checks during extraction. Flag any value outside these ranges for manual review.

| Feature | Austen | Dickens | Poe |
|---|---|---|---|
| `mattr_500` | 0.49 – 0.57 | 0.49 – 0.57 | 0.52 – 0.60 |
| `avg_word_length` | 3.99 – 4.69 | 3.86 – 4.53 | 4.12 – 4.84 |
| `hapax_ratio` | 0.65 – 0.73 | 0.65 – 0.73 | 0.71 – 0.79 |
| `avg_sentence_length_tokens` | 27.6 – 32.4 | 24.8 – 29.2 | 28.4 – 33.4 |
| `std_sentence_length_tokens` | 20.5 – 24.1 | 17.9 – 21.0 | 19.2 – 22.6 |
| `subordination_ratio` | 1.67 – 1.96 | 1.42 – 1.67 | 1.27 – 1.49 |
| `noun_to_verb_ratio` | 1.06 – 1.24 | 1.09 – 1.28 | 1.71 – 2.01 |
| `passive_voice_ratio` | 0.13 – 0.21 | 0.07 – 0.15 | 0.15 – 0.23 |
| `dialogue_ratio` | 0.27 – 0.35 | 0.31 – 0.39 | 0.20 – 0.28 |
| `first_person_ratio` (per 1k) | 19.3 – 22.6 | 27.5 – 32.3 | 22.8 – 26.7 |

> **These are measurements, not estimates.** They were read from the `style_profiles` rows computed on 2026-07-29 over the full seeded Gutenberg corpora, which is the update this section always said was pending. Bands are the measured value ±8% (±0.04 for sub-unit ratios): wide enough to survive a recompute, tight enough to catch a regression.
>
> The estimates they replace were wrong on almost every metric — `hapax_ratio` was given as 0.38–0.44 for Austen where the pipeline measures 0.695, `subordination_ratio` as 0.28–0.36 where it measures 1.814 (it counts subordinate clauses *per sentence*, so it is routinely > 1), and `first_person_ratio` as 0.5–3.0 where it measures 20.9. Nothing had ever been checked against the extractors, and the frontend's radar domains were derived from these numbers — which is why two of the six axes clamped to their maximum for all three authors and every author drew the same shape.

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
    → Jeffreys log-odds-ratio (α=0.5, scores [0, 1])
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
