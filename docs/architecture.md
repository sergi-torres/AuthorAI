# AutorIA — Architecture

> **Status**: draft for Sprint 0 · **Owners**: P1 (frontend), P2 (pipeline), P3 (backend/crypto) · **Last updated**: 2026-06-29
> **Related specs**: [`docs/MVP.md`](MVP.md) · [`docs/api_contract.yaml`](api_contract.yaml) · [`docs/erd.md`](erd.md) · [`docs/passport_schema.md`](passport_schema.md)

This document describes the architecture of AutorIA using the **C4 model**
(Context → Container → Component) plus the key **sequence diagrams** and a
**deployment view**. All diagrams are Mermaid and render directly on GitHub.

If a diagram disagrees with the locked scope in `MVP.md`, MVP.md wins — update
this file.

---

## 0. One-paragraph summary

AutorIA is a **Next.js frontend** talking to a **FastAPI backend** over the
contract in `api_contract.yaml`. The backend wraps a Python **AI pipeline**
(spaCy + sentence-transformers) and **IBM Watsonx** (Llama 3.3 70B), persists to
**Postgres + pgvector** (Supabase), and signs an **Authorship Passport** (JWS
ES256) for every conditioned generation. Anyone can verify a Passport offline
against the public key at `/.well-known/jwks.json`.

---

## 1. C4 Level 1 — System Context

*Who/what uses AutorIA, and what AutorIA depends on.*

```mermaid
graph TB
    creator([Creator / Demo viewer<br/>uses the web app])
    verifier([Third party / Regulator<br/>verifies a Passport])

    subgraph autoria [AutorIA system]
        sys[["AutorIA<br/>Style DNA · Conditioned Generation ·<br/>Authorship Passport"]]
    end

    watsonx[("IBM Watsonx<br/>Llama 3.3 70B + Granite 3 8B<br/>[external LLM]")]
    gutenberg[("Project Gutenberg<br/>public-domain corpus<br/>[external source]")]

    creator -->|"selects author, prompts,<br/>views side-by-side, downloads Passport"| sys
    verifier -->|"pastes token → checks signature"| sys
    sys -->|"generation requests (HTTPS)"| watsonx
    gutenberg -.->|"texts ingested offline (seed)"| sys

    classDef ext fill:#eee,stroke:#999,color:#333;
    class watsonx,gutenberg ext;
```

**Actors**
- **Creator / demo viewer** — selects an author, submits a prompt, reads the
  vanilla-vs-AutorIA comparison, downloads the Passport. No login (no accounts).
- **Verifier** — anyone checking a Passport's authenticity (the EU AI Act Art. 50
  audience). Only needs the token + public JWKS.

**External dependencies**
- **IBM Watsonx** — the LLM provider (creative + auxiliary models). The only
  hard runtime external dependency for generation.
- **Project Gutenberg** — source of the three preloaded corpora; used **offline**
  during seeding, not at request time.

---

## 2. C4 Level 2 — Container

*The deployable/runnable units and how they communicate.*

```mermaid
graph TB
    user([Creator])

    subgraph vercel [Vercel]
        fe["Frontend<br/>Next.js 14 + TS + Tailwind + shadcn<br/>(frontend/)"]
    end

    subgraph railway [Railway]
        be["Backend API<br/>FastAPI + Uvicorn (backend/)"]
        pipe["AI Pipeline (in-process lib)<br/>spaCy + sentence-transformers<br/>(ai_pipeline/)"]
    end

    subgraph supabase [Supabase]
        db[("PostgreSQL 16 + pgvector<br/>authors · documents · chunks ·<br/>style_profiles · passports")]
        vault[["Supabase Vault<br/>EC private key"]]
    end

    watsonx[("IBM Watsonx")]

    user -->|HTTPS| fe
    fe -->|"REST /api/* (JSON)"| be
    fe -->|"GET /.well-known/jwks.json"| be
    be -->|"import / function calls"| pipe
    be -->|"SQLAlchemy 2.0 + asyncpg"| db
    pipe -->|"vector search (pgvector)"| db
    be -->|"HTTPS (ibm-watsonx-ai SDK)"| watsonx
    be -.->|"reads private key at boot"| vault

    classDef ext fill:#eee,stroke:#999,color:#333;
    class watsonx ext;
```

| Container | Tech | Responsibility | Host |
|---|---|---|---|
| **Frontend** | Next.js 14, TypeScript, Tailwind, shadcn/ui, Recharts, D3 | UI: author selector, Style DNA viz, side-by-side, `/verify` | Vercel |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0 + asyncpg | HTTP contract, orchestration, persistence, signing | Railway |
| **AI Pipeline** | spaCy 3.7, sentence-transformers, scikit-learn, umap-learn, tiktoken, python-jose | Extraction, embeddings, RAG, conditioned generation, fit_score, Passport build/sign/verify | in-process with backend |
| **Database** | Postgres 16 + pgvector | Relational + vector storage; HNSW RAG index | Supabase |
| **Vault** | Supabase Vault | Stores the EC private signing key | Supabase |

> The AI pipeline is a **library imported by the backend**, not a separate
> service — one fewer moving part for a 30-day MVP. It could be extracted into
> its own service later without changing the public API.

---

## 3. C4 Level 3 — Component

### 3.1 Backend (`backend/app/`)

```mermaid
graph LR
    subgraph backend [backend/app]
        main["main.py<br/>app + /health"]
        r_auth["routes/authors.py<br/>GET /api/authors<br/>GET …/style-profile"]
        r_ing["routes/ingest.py<br/>POST …/documents"]
        r_gen["routes/generate.py<br/>POST /api/generate"]
        r_pass["routes/passport.py<br/>POST /api/passports/verify"]
        r_jwks["routes/jwks.py<br/>GET /.well-known/jwks.json"]
        dbl["db/ (SQLAlchemy models + session)"]
    end

    pipe["ai_pipeline (lib)"]
    db[("Postgres")]

    r_auth --> dbl
    r_ing --> dbl
    r_ing --> pipe
    r_gen --> pipe
    r_gen --> dbl
    r_pass --> pipe
    r_jwks --> pipe
    dbl --> db
```

### 3.2 AI Pipeline (`ai_pipeline/autoria_ai/`)

```mermaid
graph TB
    subgraph extract [extractor/]
        lex[lexical.py]
        syn[syntactic.py]
        sty[stylistic.py]
        voc[vocabulary.py]
    end
    emb[embedder.py<br/>sentence-transformers + UMAP]
    sp[style_profile.py<br/>assembles StyleProfile v1.0]

    cond[conditioner.py<br/>system prompt builder]
    gen[generator.py<br/>Watsonx + RAG + parallel calls]
    fit[fit_scorer.py<br/>5-component score 0–100]

    subgraph passport [passport/]
        build[builder.py]
        sign[signer.py<br/>JWS ES256]
        verify[verifier.py]
    end

    schemas[schemas/<br/>style_profile.json · passport.json]

    extract --> sp
    emb --> sp
    sp --> cond
    emb --> gen
    cond --> gen
    gen --> fit
    sp --> fit
    gen --> build
    fit --> build
    build --> sign
    sp -. validates .- schemas
    build -. validates .- schemas
```

Mapping of components to specs:
- `extractor/*` + `embedder.py` + `style_profile.py` → **StyleProfile v1.0** (MVP §4.2, `style_features.md`).
- `conditioner.py` + `generator.py` + `fit_scorer.py` → **Conditioned Generation** (MVP §4.3).
- `passport/*` → **Authorship Passport** ([`passport_schema.md`](passport_schema.md)).

---

## 4. Key sequences

### 4.1 Author onboarding / ingest (`POST /api/authors/{id}/documents`)

```mermaid
sequenceDiagram
    actor U as Creator (or seed script)
    participant BE as backend/ingest
    participant P as ai_pipeline
    participant DB as Postgres+pgvector

    U->>BE: upload .txt/.md (or seeded corpus)
    BE->>DB: insert documents(raw_text, ...)
    BE-->>U: 202 { document_id, status: "processing" }
    Note over BE,P: async
    BE->>P: clean → chunk (500 tok / 50 overlap)
    P->>P: embed chunks (768-dim)
    P->>DB: insert chunks(text, embedding, ...)
    P->>P: compute StyleProfile v1.0 (+ hash)
    P->>DB: upsert style_profiles(json_data, hash)
```

### 4.2 Conditioned generation — the core flow (`POST /api/generate`)

```mermaid
sequenceDiagram
    actor U as Creator
    participant FE as Frontend
    participant BE as backend/generate
    participant DB as Postgres+pgvector
    participant G as generator.py
    participant W as IBM Watsonx
    participant PB as passport/builder+signer

    U->>FE: pick author + prompt → "Generate"
    FE->>BE: POST /api/generate { author_id, prompt }
    BE->>DB: load StyleProfile (latest) + embed prompt
    BE->>DB: RAG top-5 chunks (embedding <=> query)
    par parallel Watsonx calls
        G->>W: conditioned prompt (style + passages)
        G->>W: vanilla prompt (no conditioning)
    end
    W-->>G: AutorIA text
    W-->>G: vanilla text
    G->>G: fit_score(both) vs StyleProfile
    BE->>PB: build + sign Passport (AutorIA only, ES256)
    PB->>DB: insert passports(json_data, jws_token)
    BE-->>FE: { vanilla, autoria, passport }
    FE-->>U: side-by-side + "Download Passport"
```

> Latency budget (MVP §4.3 SLA: < 8s P95): the two Watsonx calls run in parallel
> via `asyncio.gather` with per-call timeouts; everything else (RAG, scoring,
> signing) is cheap by comparison. See risk R3 in MVP §11.

### 4.3 Passport verification (`POST /api/passports/verify` + `/verify` UI)

```mermaid
sequenceDiagram
    actor V as Verifier
    participant FE as /verify screen
    participant BE as backend/passport
    participant VR as passport/verifier
    participant J as jwks.py (/.well-known/jwks.json)

    V->>FE: paste jws_token
    FE->>BE: POST /api/passports/verify { jws_token }
    BE->>VR: verify(token)
    VR->>VR: assert alg == ES256 (reject none/others)
    VR->>J: resolve public key by kid (cached, TTL)
    VR->>VR: verify signature + schema-validate payload
    VR-->>BE: { valid, payload, errors[] }
    BE-->>FE: result
    FE-->>V: ✓ valid / ✗ invalid + decoded payload
```

Full normative rules: [`passport_schema.md`](passport_schema.md) §8.

---

## 5. Deployment view

```mermaid
graph TB
    subgraph dev [Local dev]
        dc["docker-compose<br/>pgvector/pgvector:pg16"]
        lfe["next dev :3000"]
        lbe["uvicorn :8000"]
    end

    subgraph prod [Production]
        vc["Vercel<br/>frontend (static + SSR)"]
        rw["Railway<br/>FastAPI + ai_pipeline"]
        sb["Supabase<br/>Postgres+pgvector + Vault"]
    end

    wx[("IBM Watsonx")]

    lfe --> lbe --> dc
    vc -->|HTTPS| rw
    rw --> sb
    rw --> wx

    classDef ext fill:#eee,stroke:#999,color:#333;
    class wx ext;
```

| Environment | Frontend | Backend | Database |
|---|---|---|---|
| **Local** | `make front` (`:3000`) | `make back` (`:8000`) | `make db-up` (Docker pgvector) |
| **Production** | Vercel | Railway | Supabase |

Secrets (Watsonx API key/project id, DB URL, `PASSPORT_*`) come from `.env`
locally and platform secret stores in production. The EC **private** key lives
in Supabase Vault / Railway secrets — never in git (see `passport_schema.md` §6).

---

## 6. Cross-cutting concerns

| Concern | Approach |
|---|---|
| **API contract** | `docs/api_contract.yaml` (OpenAPI 3.1) is the single FE/BE contract; locked in Sprint 1. |
| **Data model** | `docs/erd.md` + `infra/supabase/migrations/0001_init.sql`. |
| **Latency** | Parallel Watsonx calls, HNSW vector index, lean system prompt (< ~1200 tok). Target < 8s P95. |
| **Security / integrity** | JWS ES256; `alg` allow-list; `kid`→JWKS resolution; private key in Vault. |
| **Privacy** | Passport stores **hashes** of prompt/output/snippets, never raw text. |
| **i18n** | All UI strings in `frontend/lib/i18n/en.ts` (English only). |
| **Quality** | Ruff + Black, ESLint + Prettier, pytest happy-path + signature roundtrip; CI on every PR. |
| **Scaling path (post-July)** | Extract `ai_pipeline` into its own service; add caching/streaming; RLS if DB is exposed to untrusted clients. |

---

## 7. Key architectural decisions (and why)

- **Monorepo, pipeline as a library.** Fewer moving parts than microservices;
  the backend imports `ai_pipeline` directly. (Decision Log, 2026-06-25.)
- **One database for relational + vector.** pgvector avoids running a separate
  vector store; HNSW gives fast RAG. (MVP §6.)
- **Same LLM for vanilla and AutorIA.** Only the system prompt differs — an
  honest, judge-credible comparison. (MVP §2.)
- **Asymmetric signing (ES256), not HMAC.** Enables public, offline verification
  — the heart of the EU AI Act Art. 50 claim. (`passport_schema.md` §1, §3.)
- **Hashes, not raw text, in Passports.** Provenance without leaking content.
```
