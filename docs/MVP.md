# AutorIA — MVP v1 (LOCKED)

> **Locked**: 2026-06-24 · **Owners**: P1, P2, P3 · **Status**: locked for July
> **Change policy**: any change to this scope requires a **2/3 vote + a Decision Log entry** ([`docs/decision_log.md`](decision_log.md)).

---

## 0. How to read this document

This is the **single source of truth for what we build in July** — no more, no less. If something isn't in §4 ("Features IN"), we don't build it; if it's in §5 ("Features OUT"), we don't reopen it.

**Read in this order:**
1. **§1–§3** to understand *what* AutorIA is and *what the demo looks like* (the demo drives everything).
2. **§4** for the exact functional scope you'll implement.
3. **§6–§7** for the stack and API contract you'll code against.
4. **§9–§11** for the plan, the finish line (Definition of Done), and the risks.

If you only have 2 minutes: read the **one-liner (§1)**, the **demo timeline (§3)**, and the **Definition of Done (§10)**.

---

## Glossary (shared vocabulary)

| Term | What it means in AutorIA |
|---|---|
| **StyleProfile** | A JSON "fingerprint" of an author's writing: lexical, syntactic, stylistic and semantic metrics computed from their corpus. The core asset of the product. |
| **Style DNA** | The user-facing name for the StyleProfile, visualized (radar chart + 2D map). |
| **fit_score** | A **0–100** score measuring how closely a generated text matches a StyleProfile. Shown as e.g. "87% Dickens-fit". Higher = more in-voice. |
| **Vanilla / baseline** | The same LLM (Llama 3.3 70B) generating **without** style conditioning. Our honest comparison point. |
| **Conditioned generation** | Generation **with** the StyleProfile + retrieved example passages injected into the prompt. |
| **RAG** | Retrieval-Augmented Generation: we fetch the most relevant chunks of the author's real work and give them to the model as examples. |
| **Chunk** | A ~500-token slice of a document, stored with its embedding for retrieval. |
| **Embedding** | A 768-dim numeric vector representing the meaning of a text, used for similarity search. |
| **Authorship Passport** | A signed JSON document certifying what was AI-generated, with which model, from which sources — for **EU AI Act Art. 50** transparency. |
| **JWS / ES256** | The signature format (JSON Web Signature) and algorithm (ECDSA P-256 + SHA-256) used to sign the Passport so anyone can verify it. |
| **JWKS** | The public-key endpoint (`/.well-known/jwks.json`) that lets a verifier check our signatures. |

---

## 1. One-liner

> **AutorIA learns an author's stylistic DNA from their prior work, generates AI assistance that preserves their voice, and issues a cryptographically signed "Authorship Passport"** documenting what was AI, what was human, and what sources were referenced — complying with **EU AI Act Article 50**.

**Why this wins:** it hits the challenge theme ("Reimagine Creative Industries with AI"), it's *technically* substantial (NLP + RAG + cryptography), and it's *legally* timely (Art. 50 transparency obligations land in 2026). The demo makes the value obvious in 5 seconds.

---

## 2. Hinge decisions (LOCKED)

These three decisions shape everything else. They are locked; changing one is a 2/3 vote.

- **LLM: IBM Watsonx, end-to-end.**
  - Primary (creative writing): `meta-llama/llama-3-3-70b-instruct`
  - Auxiliary (structured/classification tasks): `ibm/granite-3-8b-instruct`
  - Baseline ("vanilla"): the **same** `llama-3-3-70b` but **without** style conditioning.
  - *Why same model on both sides:* it's an honest comparison. The only variable is our style conditioning — judges notice and respect that.

- **Language: everything in English — UI, docs, video, and the generated text.**
  - The app UI, the README/docs, the **demo video (English voiceover + on-screen text)**, and the **model-generated literary text** are all in **English**. The only Spanish left in the project is our internal team chat. See `CONTRIBUTING.md` §9.
  - *Why all-English:* the IBM jury is international and English-speaking. With world-famous **English-language authors**, the jury can directly *read and feel* the voice match (Dickens vs vanilla), not just trust the metrics — a stronger, more visceral demo than relying on Spanish text they can't parse.

- **Multi-author: 3 preloaded authors + live add.**
  - **Jane Austen, Charles Dickens, Edgar Allan Poe** ship preloaded — three maximally distinct, instantly recognizable English voices (Regency social irony · Victorian maximalism · Gothic first-person intensity). The UI lets us add a new author live during the demo (`.txt` upload), but there are **no user accounts**.
  - *Why these three:* their styles are far apart (so the 2D clusters separate cleanly and the difference is obvious), all are unambiguously public domain (died 1817 / 1870 / 1849), and all are massively available on Project Gutenberg.
  - *Why:* preloaded authors guarantee a flawless demo; live-add shows it generalizes.

---

## 3. Target demo (drives every decision)

Everything we build must serve this **3-minute video**. If a feature doesn't show up here, question whether we need it.

```
00:00–00:20  Problem (ChatGPT writes the same for everyone)
00:20–00:35  Solution one-liner + 1-slide architecture
00:35–01:50  LIVE DEMO (timed):
  [00:35] Select Dickens, show Style DNA (radar + 2D viz)
  [00:55] Prompt: "Write a paragraph about a foggy London evening
          in the 1840s, with a character watching the street
          from a window"
  [01:05] Side-by-side appears: left = vanilla Llama, right = AutorIA
  [01:20] Metrics below: sentence length 12 vs 28, TTR 0.71 vs 0.58
          (matches Dickens 0.59); distinctive vocab: "countenance",
          "physiognomy", "presently" (right column only)
  [01:30] 2D point: vanilla lands in a generic cluster, AutorIA inside
          the Dickens cluster
  [01:40] Click "Generate Passport": JSON appears, /verify screen
          shows ✓ valid signature
01:50–02:30  Impact: EU AI Act Art. 50, creator market, specific
             numbers (X creators in Europe, Y ongoing lawsuits)
02:30–03:00  How we used IBM Bob (4 Custom Modes + BobShell logs),
             team, repo, call to action
```

**Demo success criterion (the bar we must clear):** a non-NLP-expert human sees the difference between vanilla and AutorIA in **≤5 seconds**.
**How we validate it (Sprint 1 gate):** show the side-by-side screen to **3 non-technical people**. If **3/3** correctly pick "which sounds more like Dickens" in ≤5s, we pass. If not, we iterate on the conditioning before moving on.

---

## 4. Features IN — closed functional scope

This is the complete list of what we build. Each sub-section has a **plain-language summary** first, then the technical detail.

### 4.1 Author Onboarding

**In plain terms:** the system can ingest an author's texts (preloaded or uploaded live), clean them, slice them into chunks, embed them, and compute that author's StyleProfile.

- **Accepted inputs:** `.txt`, `.md` (PDF is nice-to-have, not required).
- **Minimum corpus:** 3 texts of >1000 words, OR 1 text of >30,000 words.
- **3 preloaded authors** (auto-seeded on first boot):
  - **Jane Austen** — *Pride and Prejudice*, *Emma*, *Sense and Sensibility*. ~330k words.
  - **Charles Dickens** — *Great Expectations*, *A Tale of Two Cities*, *Oliver Twist*. ~300k words.
  - **Edgar Allan Poe** — ~15 selected tales (*The Fall of the House of Usher*, *The Tell-Tale Heart*, *The Masque of the Red Death*, …). ~70k words.
- **Source:** Project Gutenberg (public domain, verified — all three authors died well before 1900).
- **Processing on ingest:**
  1. **Cleanup** — strip Gutenberg headers/footers, normalize quotes and whitespace.
  2. **Chunking** — 500 tokens, overlap 50 (tiktoken `cl100k_base` as an approximation).
  3. **Embeddings** — one 768-dim vector per chunk (sentence-transformers).
  4. **StyleProfile** — compute the global author profile (see §4.2).
  5. **Persist** — to Postgres + pgvector.

### 4.2 Style DNA Extraction → StyleProfile

**In plain terms:** for each author we compute a structured "fingerprint" of *how* they write — vocabulary richness, sentence structure, punctuation habits, signature words, and a semantic centroid. This is the asset that makes our generation different from vanilla.

Built with **spaCy `en_core_web_lg`** (linguistic features) + **sentence-transformers `all-mpnet-base-v2`** (semantics, 768-dim).

`StyleProfile` JSON schema (versioned, **v1.0**):

```json
{
  "schema_version": "1.0",
  "author_id": "dickens",
  "computed_at": "2026-07-15T...",
  "corpus_stats": { "n_documents": 3, "n_tokens": 184523, "n_sentences": 9821 },
  "lexical": {
    "ttr": 0.184,
    "mattr_500": 0.612,
    "avg_word_length": 4.83,
    "hapax_ratio": 0.421
  },
  "syntactic": {
    "avg_sentence_length_tokens": 28.4,
    "std_sentence_length_tokens": 14.2,
    "subordination_ratio": 0.38,
    "avg_dep_tree_depth": 4.7,
    "noun_to_verb_ratio": 1.83
  },
  "stylistic": {
    "punct_distribution": {
      ",": 0.42, ".": 0.18, ";": 0.07, ":": 0.04,
      "—": 0.06, "?": 0.01, "!": 0.01, "\"": 0.21
    },
    "pos_distribution": {
      "NOUN": 0.21, "VERB": 0.16, "ADJ": 0.09, "ADV": 0.07,
      "DET": 0.13, "ADP": 0.14, "PRON": 0.07, "CONJ": 0.05,
      "SCONJ": 0.04, "OTHER": 0.04
    },
    "discourse_markers": ["in short", "to be sure", "as it were", "presently"]
  },
  "distinctive_vocab": [
    { "term": "countenance", "score": 0.084 },
    { "term": "physiognomy", "score": 0.073 }
  ],
  "semantic_centroid": [0.012, -0.043, "..."],
  "embedding_umap_2d": { "centroid": [3.2, -1.7], "spread": 0.84 }
}
```

**What each block captures** (detailed feature definitions belong in `docs/style_features.md`, to be written in Sprint 0/1):
- `lexical` — vocabulary richness (TTR, MATTR-500, hapax ratio, word length).
- `syntactic` — sentence architecture (length + variation, subordination, dependency-tree depth, noun/verb balance).
- `stylistic` — punctuation and part-of-speech distributions + recurring discourse markers.
- `distinctive_vocab` — signature words (TF-IDF vs a base corpus).
- `semantic_centroid` / `embedding_umap_2d` — where the author "lives" in meaning-space (the 2D point on the demo map).

**`fit_score` — how we measure "in-voice" (0–100):**

```
fit_score (0–1, then ×100) = weighted sum of:
  cosine_sim(emb_gen, semantic_centroid)        × 0.35
  (1 − normalized_distance(ttr_gen, ttr_profile)) × 0.15
  (1 − normalized_distance(asl_gen, asl_profile)) × 0.20   # asl = avg sentence length
  jaccard(pos_dist_gen, pos_dist_profile)         × 0.15
  vocab_overlap(gen_vocab, distinctive_vocab)     × 0.15
```

Output is scaled to **0–100** and shown in the UI as e.g. **"87% Dickens-fit"**. We compute it for *both* the vanilla and AutorIA outputs so the gap is visible.

### 4.3 Conditioned Generation

**In plain terms:** given an author and a prompt, we generate two paragraphs in parallel — one plain (vanilla) and one conditioned on the author's style + real example passages — score both, and mint a Passport for the AutorIA one.

**Endpoint:** `POST /api/generate` · **Body:** `{ "author_id": "dickens", "prompt": "..." }`

**Flow:**
1. Load the author's StyleProfile.
2. **RAG retrieval** — top-5 chunks most relevant to the prompt (cosine similarity over embeddings, pgvector HNSW index).
3. Compose the conditioned system prompt:
   ```
   "Write in the style of author X. Your writing must have:
    average sentence length ~28 tokens with high variation,
    heavy use of subordinate clauses, and vocabulary including
    terms like [countenance, physiognomy, ...]. Here are 5 example
    passages: [chunks]. Write only in that style; do not explain."
   ```
4. Watsonx call — Llama 3.3 70B, `temperature=0.85`, `max_tokens=400`.
5. **Parallel** call to the *same* model **without** the style prompt (just "Write about: {prompt}") → vanilla baseline.
6. Compute `fit_score` (0–100) for both generations.
7. Generate the Authorship Passport for the AutorIA generation.
8. Return:
   ```json
   {
     "vanilla":  { "text": "...", "fit_score": 34 },
     "autoria":  { "text": "...", "fit_score": 87 },
     "passport": { "jws_token": "...", "json_payload": { } }
   }
   ```

**SLA:** response < 8s (P95). If we can't hit it, see Risk **R3** in §11.

### 4.4 Authorship Passport

**In plain terms:** a tamper-evident JSON certificate proving *this text was AI-generated, by this model, from these sources*. Anyone can verify the signature without trusting us. This is our EU AI Act Art. 50 angle and a strong differentiator.

JSON schema (**v1.0**):

```json
{
  "schema_version": "1.0",
  "passport_id": "uuid-v4",
  "generated_at": "ISO-8601",
  "author_voice": {
    "id": "dickens",
    "style_profile_hash": "sha256:...",
    "style_profile_version": "1.0"
  },
  "generation": {
    "model_provider": "ibm/watsonx",
    "model_id": "meta-llama/llama-3-3-70b-instruct",
    "user_prompt_hash": "sha256:...",
    "output_hash": "sha256:...",
    "output_length_tokens": 312
  },
  "rag_sources": [
    { "doc_id": "great_expectations", "chunk_id": 42, "snippet_hash": "..." }
  ],
  "contribution": {
    "human_pct": 0,
    "ai_pct": 100,
    "note": "v1: 100% AI-assisted. Human-edit tracking is in the roadmap."
  },
  "fit_score": 87,
  "verifier_url": "https://autoria.app/verify"
}
```

- **Signing:** JWS with `python-jose`, algorithm **ES256** (ECDSA P-256 + SHA-256).
- **Keys:** EC keypair generated at first backend boot, private key in Supabase Vault; public key exposed at `/.well-known/jwks.json`.
- **Verification:** the `/verify` screen accepts pasted JSON or an uploaded file, validates the signature against JWKS, and shows the formatted content with a **✓ verified / ✗ invalid** mark.

> Privacy note: we store **hashes** of the prompt and output, not the raw text — the Passport proves provenance without leaking content. (Full crypto detail → `docs/passport_schema.md`, to be written in Sprint 0/1.)

### 4.5 Side-by-side Comparison UI (the main screen)

**In plain terms:** one screen where you pick an author, see their Style DNA, type a prompt, and watch vanilla vs AutorIA appear side by side with their fit scores — then download the Passport.

```
[ Header: selected author + dropdown to change ]
[ Style DNA panel (collapsible): radar chart + 2D viz + metrics ]
[ Textarea: user prompt ]
[ Button: "Generate" ]
[ Two columns:
    Left:  "Llama 3.3 vanilla"        → text + fit_score bar
    Right: "AutorIA (Dickens voice)"  → text + fit_score bar ]
[ Button: "Download Authorship Passport" → JSON + link to /verify ]
```

---

## 5. Features OUT — explicitly NOT in July

Each is justified so we don't reopen the discussion mid-sprint.

| Out of scope | Why |
|---|---|
| Multimodal (image/audio/video) | Another full month of work. |
| User accounts, login, multi-user | Doesn't improve the "fit" criterion judges care about. |
| Payments, marketplace, community | Future product, not the MVP. |
| Mobile responsive | The demo is desktop; ~5 days for zero jury value. |
| Fine-tuning our own models | API calls only. |
| Plagiarism / copyright detection | Different idea ("RightsGuard"), out of scope. |
| Real human/AI % + human-edit tracking | v2; v1 is 100% AI. |
| Generation in languages other than English | The corpus and product are English-only for July. |
| Public verification portal w/ own domain | Local `/verify` screen only. |
| Exhaustive test coverage (>80%) | Happy-path + signature tests only. |
| Generation streaming | Blocking response simplifies everything. |
| Generation caching | Each generation is fresh (except demo fallback, R5). |
| UI multi-language / i18n switching | UI is English only (single `en.ts` strings file). |

---

## 6. Stack confirmed

### Frontend
- Next.js 14 (App Router) + TypeScript
- Tailwind CSS + shadcn/ui
- Recharts (radar + bar charts)
- D3 / react-scatter-chart (2D embedding viz)
- Deploy: Vercel (free)

### Backend
- Python 3.11 + FastAPI + Uvicorn
- Pydantic v2
- SQLAlchemy 2.0 + asyncpg
- Deploy: Railway (hobby plan, ~$5/mo)

### AI Pipeline
- spaCy 3.7 + `en_core_web_lg`
- sentence-transformers + `all-mpnet-base-v2` (768-dim, English)
- `umap-learn` (server-side 2D precompute, not client)
- scikit-learn (TF-IDF for distinctive vocab)
- tiktoken (approximate chunking)

### LLM
- `ibm-watsonx-ai` SDK
- Creative: `meta-llama/llama-3-3-70b-instruct`
- Auxiliary: `ibm/granite-3-8b-instruct`
- **SPRINT 1 TASK:** validate voice-matching quality with 5 real prompts (does the conditioned output read like the target author?); if Llama < 6/10 human eval, escalate (see R1).

### Database
- PostgreSQL 16 + pgvector
- Hosting: Supabase (free tier → $25/mo if needed)
- Tables:
  ```
  authors        (id, name, slug, bio, created_at)
  documents      (id, author_id, title, source_url, raw_text, n_tokens, created_at)
  chunks         (id, document_id, text, embedding vector(768), token_start, token_end)
  style_profiles (id, author_id, version, json_data, hash, computed_at)
  passports      (id, author_id, json_data, jws_token, created_at)
  ```
- Index: HNSW on `chunks.embedding` with `vector_cosine_ops`. (Full ERD → `docs/erd.md`.)

### Cryptography
- `python-jose[cryptography]` for JWS
- Algorithm ES256 (ECDSA P-256 + SHA-256)
- EC keypair generated on first boot (`scripts/generate_keys.py`)
- Storage: Supabase Vault (private) + `/.well-known/jwks.json` (public)

### Dev Tools
- IBM Bob (mandatory) — main copilot
- GitHub + GitHub Projects (backlog) + GitHub Actions (CI)
- Ruff (Python lint) + Black (Python format)
- ESLint + Prettier (frontend)
- pytest (backend/pipeline tests)

> Tooling usage and the daily workflow live in [`CONTRIBUTING.md`](../CONTRIBUTING.md).

---

## 7. API Contract (LOCKED in Sprint 1, no changes after)

```
GET  /api/authors
     → 200: [ { id, name, slug, has_style_profile, n_documents } ]

GET  /api/authors/{author_id}/style-profile
     → 200: StyleProfile JSON v1.0
     → 404: if not yet computed

POST /api/authors/{author_id}/documents
     Body: multipart .txt/.md, or JSON { title, text }
     → 202: { document_id, status: "processing" }
     (kicks off async embedding + StyleProfile recompute)

POST /api/generate
     Body: { author_id: string, prompt: string }
     → 200: {
       vanilla:  { text, fit_score, latency_ms },
       autoria:  { text, fit_score, latency_ms },
       passport: { jws_token, json_payload }
     }

POST /api/passports/verify
     Body: { jws_token: string }
     → 200: { valid: bool, payload: PassportJSON, errors: [] }

GET  /.well-known/jwks.json
     → 200: standard JWKS with the public key
```

> The full OpenAPI 3.1 spec will live in `docs/api_contract.yaml` (written in Sprint 0/1). Once locked in Sprint 1, this contract does not change — frontend and backend code against it independently.

---

## 8. IBM Bob — integration plan (not decorative)

> Bob usage is **judged and verified first** by IBM. Projects without real Bob integration have been disqualified. This is mandatory, not optional.

### Custom Modes (created Sprint 1; P3 owns the repo config, individual owners below)

| Mode | Context loaded | Primary user | Sample command |
|---|---|---|---|
| **StyleExtractor** | StyleProfile schema + spaCy feature examples | P2 (extraction module) | "Add MATTR-500 computation to the extractor, follow schema v1.0" |
| **GenerationConductor** | `conditioner.py` + `generator.py` + `fit_scorer.py` + RAG schema | P3 (generation) | "A/B four system-prompt variants for Dickens on 5 fixed prompts; report mean fit_score and vanilla gap" |
| **StudioComposer** | `api_contract.yaml` + `lib/i18n/en.ts` + MVP §4.5 UI spec | P1 (frontend) | "Implement StyleRadarChart from StyleProfile JSON; all labels via en.ts; normalize 6 axes to [0,1]" |
| **PassportAuditor** | JWS ES256 spec + Passport schema + JWKS | P3 (signing) + P1 (`/verify`) | "Verify the verifier rejects tokens with a `kid` not in JWKS" |

### Mandatory repo artifacts (in `bob/`)

```
bob/
  custom-modes/
    style-extractor.md
    generation-conductor.md
    studio-composer.md
    passport-auditor.md
  sessions/
    week1/  p1.md  p2.md  p3.md   (BobShell exports)
    week2/  ...                    (same for 4 weeks)
  usage-report.md                  (final, Sprint 3: screenshots + metrics)
```

### Metrics to report in the README
- Total PRs with Bob assistance
- Number of Custom Modes created (target: **4**)
- Number of BobShell sessions exported (target: **12+**)
- 3 representative screenshots of Bob working

---

## 9. Initial backlog (feeds GitHub Projects)

Labels: `[front] [back] [ml] [bob] [demo] [docs] [infra]` · Sizes: XS<2h, S 2-4h, M 4-8h, L 1-2d, XL 2-3d.

### Sprint 1 — Jul 5–14 — Foundation & Full StyleProfile (Long Sprint)
- `[infra][L]` Repo + monorepo, Vercel + Railway
- `[infra][M]` Supabase project + pgvector + initial schema migration
- `[infra][S]` GitHub Actions: lint + basic tests on every PR
- `[back][M]` Health endpoints + `GET /api/authors` (mock 3 authors)
- `[back][L]` `POST /api/authors/{id}/documents` (upload + persist raw)
- `[ml][M]` Clean and chunk the 3 corpora (seed script)
- `[ml][M]` Feature extractor skeleton (lexical only)
- `[front][M]` Base layout + author selector page (cards)
- `[bob][M]` Create 4 Custom Modes, first BobShell export per person
- `[bob][S]` Validate Llama-3.3-70b voice-matching quality, 5 prompts
- `[ml][L]` Syntactic features with spaCy (dep parsing, subordination)
- `[ml][M]` POS and punctuation distribution
- `[ml][L]` Distinctive vocabulary TF-IDF vs base corpus
- `[ml][M]` Per-chunk embeddings + pgvector storage + HNSW index
- `[ml][M]` UMAP 2D author precompute (server-side)
- `[back][M]` `GET /api/authors/{id}/style-profile` + persistence
- `[back][S]` Manual StyleProfile recompute endpoint
- `[front][L]` "Style DNA" screen: radar + 2D scatter + metrics
- `[front][M]` Main screen skeleton with prompt + button
- `[demo][M]` **5-sec validation with 3 non-technical humans (GATE)**
- `[bob][M]` BobShell exports week 1 & week 2

### Sprint 2 — Jul 15–21 — Generation + Passport
- `[back][L]` Watsonx integration (auth + retry + timeout)
- `[ml][M]` Conditioned system prompt composition
- `[ml][M]` `fit_score` computation (5 components)
- `[back][L]` `POST /api/generate` (parallel vanilla + AutorIA)
- `[back][L]` Passport JWS generation + signing (ES256)
- `[back][M]` `/.well-known/jwks.json` + `POST /api/passports/verify`
- `[front][L]` Side-by-side UI with comparative metrics
- `[front][M]` `/verify` screen for the Passport
- `[front][S]` "Download Passport" button with formatted JSON
- `[demo][M]` Timed demo rehearsal ×2
- `[bob][M]` BobShell exports week 3

### Sprint 3 — Jul 22–28 — Polish + Demo
- `[front][L]` Visual polish (typography, spacing, microinteractions)
- `[front][M]` Loading / error / empty states
- `[demo][L]` Refine demo prompts, timed rehearsal ×5
- `[demo][L]` Screen recording + English voiceover + edit the 3-min video
- `[demo][M]` On-screen English captions for key metrics/labels
- `[docs][L]` Final complete README (all challenge sections)
- `[bob][L]` `usage-report.md` with final screenshots and metrics
- `[bob][M]` BobShell exports week 4
- `[infra][M]` Stable public deploy + (optional) custom domain

### Buffer — Jul 29–31
- **Jul 29:** full submission dry-run
- **Jul 30:** fix surprises
- **Jul 31:** morning submit (12:00 Spain time, **not** 23:59)

---

## 10. MVP Definition of Done

The project is "done" when **all** of these are true:

- [ ] 3 preloaded authors, each with a computed and visualizable StyleProfile
- [ ] Side-by-side generation works end-to-end in **<8s P95**
- [ ] Authorship Passport issued, downloaded, and **verifies** with a valid signature
- [ ] Visible vanilla-vs-AutorIA difference: **≥3/3 non-technical humans** identify it in **≤5s** (Sprint 1 gate)
- [ ] Live 90s demo rehearsed **5 times without failure** (Sprint 3)
- [ ] Public repo with a complete README including the "How we used IBM Bob" section
- [ ] 4 Custom Modes documented in `bob/custom-modes/`
- [ ] ≥12 BobShell exports in `bob/sessions/`
- [ ] 3-min video on public YouTube with English voiceover
- [ ] Mandatory IBM SkillsBuild course completed by ≥1 member
- [ ] Submission sent before **July 31, 12:00 Spain time**

---

## 11. Risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| **R1** | Llama-3.3-70b doesn't convincingly match a target voice | Validate Sprint 1 day 2. If <6/10, plan B: stronger conditioning / more RAG passages, `llama-3-1-405b`, or `granite-3-8b`; last resort Mistral Large via Watsonx. |
| **R2** | Stylistic metrics don't distinguish authors | Validate Sprint 1 with a blind A/B. If Austen ≈ Dickens (both 19thc British), add bigram/trigram distinctive features. (Poe is the easy separation.) |
| **R3** | Generation >15s, demo doesn't flow | P3 measures latency Sprint 2 day 1. If >10s: switch parallel→sequential with optimistic loading, and/or use `granite-8b` for the baseline (faster). |
| **R4** | Live demo fails during recording | Sprint 3: record each step separately as an editable fallback. Final video may mix live + pre-recorded. |
| **R5** | Watsonx rate-limit / load spike | Exponential backoff (Sprint 2). For the demo, pre-record two famous generations as a local cache fallback. |
| **R6** | A teammate is sick for a week | Each role has a designated backup; pair on critical pieces; the async daily keeps the backup current. |
