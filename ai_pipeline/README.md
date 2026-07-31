# AutorIA — AI Pipeline (`autoria_ai`)

> **Owner**: P2 (extraction, embeddings) + P3 (generation, crypto)
> **Package**: `autoria-ai` · Python ≥ 3.11 · imported **in-process** by `backend/`, not run as a service

This is the core of AutorIA. Everything the product claims — that it can measure a
voice, reproduce it, score the result, and certify it — is implemented here. The
FastAPI backend is a thin HTTP wrapper over these functions.

**Authoritative specs** (this code implements them; where they disagree, the spec wins):
[`docs/style_features.md`](../docs/style_features.md) (metrics + `fit_score`) ·
[`docs/passport_schema.md`](../docs/passport_schema.md) (crypto) ·
[`docs/api_contract.yaml`](../docs/api_contract.yaml) (shapes crossing the wire).

---

## The three jobs

```
                    ┌───────────────────────────────────────────┐
  corpus (.txt) ──▶ │ 1. ANALYZE   cleaner → chunker →          │ ──▶ StyleProfile v1.0
                    │    extractor/* + embedder → style_profile │     (+768-dim centroid,
                    └───────────────────────────────────────────┘      UMAP 2D, vocabulary)

                    ┌───────────────────────────────────────────┐
  user prompt   ──▶ │ 2. GENERATE  db.retrieve_top_k (RAG) →    │ ──▶ vanilla + autoria text,
                    │    conditioner → generator (2 parallel    │     each with a fit_score
                    │    Watsonx calls) → fit_scorer            │
                    └───────────────────────────────────────────┘

                    ┌───────────────────────────────────────────┐
  generation    ──▶ │ 3. CERTIFY   passport/builder → signer    │ ──▶ JWS ES256 token,
                    │              (ES256) · verifier           │     verifiable offline
                    └───────────────────────────────────────────┘
```

---

## Module map

### 1 · Analyze — `extractor/` + `embedder.py` + `umap_projector.py`

| File | Responsibility |
| --- | --- |
| [`extractor/cleaner.py`](autoria_ai/extractor/cleaner.py) | Strip Project Gutenberg headers/footers and `[Illustration…]` markup; normalize quotes and whitespace |
| [`extractor/chunker.py`](autoria_ai/extractor/chunker.py) | Slice into 500-token chunks, overlap 50 (`tiktoken` `cl100k_base`) — byte-identical to the upload endpoint's chunking |
| [`extractor/lexical.py`](autoria_ai/extractor/lexical.py) | TTR, MATTR-500 (real sliding window), hapax ratio over lemmas, average word length |
| [`extractor/syntactic.py`](autoria_ai/extractor/syntactic.py) | Sentence length mean/σ, subordination ratio, noun:verb, passive voice — from the spaCy dependency parse |
| [`extractor/stylistic.py`](autoria_ai/extractor/stylistic.py) | Punctuation and POS distributions, `dialogue_ratio`, `first_person_ratio` (per 1 000 tokens, so **not** bounded by 1) |
| [`extractor/vocabulary.py`](autoria_ai/extractor/vocabulary.py) | Signature terms: Jeffreys-prior (α = 0.5) **log-odds ratio** against the pooled other authors, NOUN/ADJ/ADV only, scores normalized to `[0, 1]` |
| [`extractor/style_profile.py`](autoria_ai/extractor/style_profile.py) | Assembles every block into a schema-valid `StyleProfile v1.0` plus its canonical hash |
| [`embedder.py`](autoria_ai/embedder.py) | `all-mpnet-base-v2` 768-dim chunk embeddings; the model is **lazy-loaded**, not built at import (issue #104) |
| [`umap_projector.py`](autoria_ai/umap_projector.py) | Global UMAP 2D fit over every embedded chunk → per-author centroid + spread; soft-skips below 16 chunks |

> **Why log-odds and not TF-IDF.** With one "document" per author, every term all
> three use has identical IDF, so TF-IDF collapses into raw frequency and returns
> `say`, `know`, `time` for everyone (measured 3-way top-10 overlap: **5**). Log-odds
> against the pooled others measures a *rate difference* instead. Measured overlap
> after the change: **0**. Full trail — proposal, prototype on the real corpus,
> ratification — in [`docs/decision_log.md`](../docs/decision_log.md), 2026-07-30.

### 2 · Generate — `db.py`, `conditioner.py`, `generator.py`, `fit_scorer.py`

| File | Responsibility |
| --- | --- |
| [`db.py`](autoria_ai/db.py) | Async pgvector access: writes chunk embeddings, and `retrieve_top_k` cosine search (`SET LOCAL hnsw.ef_search`, scoped to one author) |
| [`conditioner.py`](autoria_ai/conditioner.py) | Builds the conditioned system prompt — author metrics translated into natural language, signature vocabulary, RAG passages — packed against a **real 1 200-token budget** (`_MAX_PROMPT_TOKENS`), truncating at a word boundary rather than trusting a 5-chunk cap to bound tokens it never measured (issue #90) |
| [`generator.py`](autoria_ai/generator.py) | `orchestrate()` — embed prompt → RAG → condition → **two parallel Watsonx calls** (`asyncio.gather`) → score both → build the Passport. Degradation is asymmetric: a vanilla failure degrades that column, an AutorIA failure propagates, because without it there is no Passport |
| [`fit_scorer.py`](autoria_ai/fit_scorer.py) | The 5-component weighted 0–100 score: semantic 0.35 · sentence length 0.20 · lexical 0.15 · POS 0.15 · vocabulary 0.15 |

### 3 · Certify — `passport/`

| File | Responsibility |
| --- | --- |
| [`passport/builder.py`](autoria_ai/passport/builder.py) | Assembles the payload: hashes of the prompt, the output and every RAG snippet — never raw text |
| [`passport/keys.py`](autoria_ai/passport/keys.py) | Loads the EC P-256 keypair from a PEM path **or** PEM content, since deploy platforms have no key files |
| [`passport/signer.py`](autoria_ai/passport/signer.py) | JWS **ES256**, header `{alg, kid, typ: "passport+jws"}` |
| [`passport/verifier.py`](autoria_ai/passport/verifier.py) | `alg` **allow-list** (rejects `none`), `kid`→JWKS resolution, signature check, schema validation, structured error codes |

### Schemas

[`schemas/style_profile.json`](autoria_ai/schemas/style_profile.json) and
[`schemas/passport.json`](autoria_ai/schemas/passport.json) are JSON Schema documents
validated at build time — a profile or Passport that does not conform never leaves the pipeline.

---

## Using it

```python
import asyncio
from autoria_ai.extractor.style_profile import compute_style_profile
from autoria_ai.generator import orchestrate

# 1. Analyze. `comparison_lemmas` is what makes the vocabulary *distinctive*:
#    omit it and each author is scored against nothing but themselves.
profile = compute_style_profile(
    author_slug="dickens",
    documents=[doc1, doc2, doc3],
    nlp=nlp,
    comparison_lemmas={"austen": austen_lemmas, "poe": poe_lemmas},
)

# 2 + 3. Generate side by side and mint the Passport.
#    `database_url` is required for RAG — without it retrieval fails soft
#    and the conditioned prompt ships with no example passages.
result = asyncio.run(orchestrate(
    prompt="A foggy London evening in the 1840s, seen from a window.",
    style_profile=profile,
    author_id="dickens",
    database_url=DATABASE_URL,
))
result["vanilla"]["fit_score"], result["autoria"]["fit_score"], result["passport"]["jws_token"]
```

Every collaborator in `orchestrate` (`generate_fn`, `retrieve_fn`, `score_fn`,
`build_prompt_fn`, `issue_passport_fn`) is an injectable keyword argument, which is
how the suite tests the orchestration without calling Watsonx.

---

## Tests

**246 test functions** across 11 files.

```bash
cd ai_pipeline
pytest tests -q                        # full suite
pytest tests -q -m "not integration"   # what CI gates on
```

Two jobs in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) run this suite on
every PR, one of them **against a live `pgvector/pgvector:pg16` service container** —
because the embedding write path was broken for four weeks behind tests that
self-skipped when `DATABASE_URL` was absent (issue #107). CI now fails loudly if
those live-DB tests skip instead of running.

Coverage worth knowing about: `test_vocabulary.py` asserts that a word used at an
equal rate by every author cannot outrank an author-exclusive one; `test_passport.py`
covers tamper rejection and `alg:none` refusal; `test_style_profile_compute.py`
verifies that no proper noun survives the POS filter — and that test was confirmed to
fail when the filter is removed, which is the only way a negative test means anything.

---

## Known limitations

- **Log-odds finds concentration, which is usually but not always style.** Words tied
  to one particular tale (Poe's `balloon`, `ballast`) can rank as signature vocabulary.
  Recorded in [`docs/style_features.md`](../docs/style_features.md) §4.1 as a candidate future issue.
- **`_MAX_LEMMA_CHARS` (800 000)** bounds peak memory per author. That budget is spent on
  a deterministic bisection sample spanning the whole corpus, not on a prefix — before
  issue #100 the cap silently truncated Dickens to 21 % of his corpus.
- **`fit_score` compares a whole-text TTR against a window-normalized MATTR**, so short
  generations are structurally favoured on the lexical component. Measured and recorded
  in the Decision Log (2026-07-30) rather than quietly carried.
