# 📘 AutorIA — Team Onboarding Guide

> **Last updated**: 2026-06-25
> **For**: P2 and P3 joining the project
> **Reading time**: 40–50 minutes — read it fully before your first commit
> **If you only read one thing**: §3 (Roles), §6 (MVP), §9 (IBM Bob) and §11 (Daily workflow)

---

## Table of Contents

1. [Welcome and challenge context](#1-welcome-and-challenge-context)
2. [What are we building? — AutorIA in 5 minutes](#2-what-are-we-building--autoria-in-5-minutes)
3. [Team, roles and ownership model](#3-team-roles-and-ownership-model)
4. [How we make decisions](#4-how-we-make-decisions)
5. [Methodology — sprints, ceremonies, pair sessions](#5-methodology--sprints-ceremonies-pair-sessions)
6. [The MVP — what's in and what's out (LOCKED)](#6-the-mvp--whats-in-and-whats-out-locked)
7. [Tech stack (locked, not up for debate)](#7-tech-stack-locked-not-up-for-debate)
8. [Repository structure](#8-repository-structure)
9. [IBM Bob — the key tool (this can win or disqualify us)](#9-ibm-bob--the-key-tool-this-can-win-or-disqualify-us)
10. [GitHub Projects — backlog, sprints and workflow](#10-github-projects--backlog-sprints-and-workflow)
11. [Daily workflow — Git, branches, PRs, commits](#11-daily-workflow--git-branches-prs-commits)
12. [Language policy — what goes in English vs Spanish](#12-language-policy--what-goes-in-english-vs-spanish)
13. [Communication — channels and cadence](#13-communication--channels-and-cadence)
14. [Challenge deliverables — what we ship](#14-challenge-deliverables--what-we-ship)
15. [Pre-July-1 checklist (this week)](#15-pre-july-1-checklist-this-week)
16. [Sprint 1 — day 1 plan (July 1)](#16-sprint-1--day-1-plan-july-1)
17. [Anti-patterns — what NOT to do](#17-anti-patterns--what-not-to-do)
18. [FAQ](#18-faq)

> 🗣️ **Note on language**: this document is in English because the public repo and docs follow our language policy (§12). The team's voice channel and chat is Spanish.

---

## 1. Welcome and challenge context

### What this is

We're participating in the **IBM AI Builders Challenge — July 2026**, run by IBM with BeMyApp. Monthly hackathon, different theme each month. July's theme:

> **"Reimagine Creative Industries with AI"**

We build something that helps creators (writers, illustrators, musicians, filmmakers, designers) using AI — with **IBM Bob** as our main development copilot.

### What's at stake (July prizes)

| Prize | Amount |
|---|---|
| 🥇 1st place July | **$2,250** |
| 🥈 Runner-up | $1,250 |
| 🏅 Most Innovative | $750 |
| 🏅 Best Use of Technology | $750 |
| 🏆 **Grand Prize (July + August combined)** | **$5,000** |

Plus visibility in the IBM ecosystem, BeMyApp mention, and a strong portfolio project.

### Key dates

| Date | Event |
|---|---|
| **Jul 1, 2026** | Challenge starts — Sprint 1 kickoff |
| **Jul 31, 2026 — 23:59 EST** | Submission deadline (= 5:59 AM Spain time, Aug 1) |
| **Our internal deadline**: Jul 31, **12:00 Spain time** | Submit in the morning, not at midnight |

### Why we have real chances

We've done exhaustive research on the previous IBM Bob hackathon (May 2026, ~150 projects on lablab.ai):

- **90% were developer tools** (PR reviewers, repo analyzers…) because Bob is a dev copilot. For July there will be a **flood of generic "creator assistants"** (ChatGPT wrappers with pretty UI).
- Winning projects do 2 things almost nobody does well: **(a) solve a concrete problem in a real niche**, not "creators" in the abstract, and **(b) exploit Bob's unique capabilities** (repo context, persona modes, governance/auditability with BobShell).
- Our idea — **AutorIA** — fits both: real niche (auditable authorship under the **EU AI Act**), justified use of Bob (governance, auditability, persona modes).

### Jury criteria (important — we revisit weekly)

| Criterion | What it means | How we score |
|---|---|---|
| **Technical Execution** | Does it work? Well architected? | Real AI pipeline, real cryptographic signing, no smoke |
| **Innovation** | Is it new or yet another wrapper? | "Auditable authorship layer" — almost nobody is building this |
| **Feasibility** | Realistic? Scalable? | Focused MVP, mainstream stack, verifiable demo |
| **Challenge Fit** | Fits "Reimagine Creative Industries"? | Yes — helps creators preserve their authentic voice |
| **Real-World Impact** | Real problem? Real market? | EU AI Act Article 50 mandates disclosure — urgent market |

---

## 2. What are we building? — AutorIA in 5 minutes

### One-liner

> AutorIA learns an author's stylistic DNA from their prior work, generates AI assistance that preserves their voice, and issues a cryptographically signed **"Authorship Passport"** documenting what was AI, what was human, and what sources were referenced — complying with EU AI Act Article 50.

### The problem

1. **Aesthetic conformism**: when a creator uses vanilla ChatGPT/Claude/Llama, the output sounds the same for everyone. They lose their authorial voice.
2. **Imminent legal obligation**: EU AI Act Article 50 requires disclosing AI-generated/assisted content. Lands August 2026 — right when we launch.

### The solution (3 pieces)

**Piece 1 — Style DNA Extraction**
You upload your corpus (3+ long texts). AutorIA extracts your "stylistic DNA":
- Lexical metrics (Type-Token Ratio, word length, hapax…)
- Syntactic metrics (sentence length, subordination, dependency tree depth…)
- Stylistic metrics (punctuation distribution, POS, discourse markers…)
- Distinctive vocabulary (TF-IDF vs reference corpus)
- Author's mean semantic embedding
→ Output: a versioned, visualizable `StyleProfile v1.0` JSON.

**Piece 2 — Conditioned Generation**
You give a prompt ("write about Madrid in 1880"). The system:
1. Retrieves StyleProfile + top-5 relevant passages (RAG over pgvector).
2. Composes a system prompt conditioned on the style.
3. Calls Watsonx (Llama 3.3 70B) **TWICE** in parallel:
   - Without conditioning → "vanilla"
   - With conditioning → "AutorIA"
4. Shows both **side-by-side** with stylistic fit metrics.

**Piece 3 — Authorship Passport**
Every generation emits a JSON manifest signed with **JWS (ES256)**:
```json
{
  "passport_id": "uuid",
  "author_voice": { "id": "dickens", "style_profile_hash": "sha256:..." },
  "generation": { "model": "meta-llama/llama-3-3-70b-instruct", "output_hash": "..." },
  "rag_sources": [...],
  "contribution": { "ai_pct": 100, "human_pct": 0 },
  "fit_score": 0.87
}
```
Publicly verifiable against a public key at `/.well-known/jwks.json`. This is what satisfies the EU AI Act.

### Why this and not something else

We analyzed 12 ideas. AutorIA fits the **5 criteria simultaneously** better than any other:

- **Technical Execution**: Bob orchestrates real pipeline (ingest → analyze → generate → sign)
- **Innovation**: nobody is building the "auditable authorship" layer
- **Feasibility**: Text-only MVP (not multimodal) is buildable in 30 days
- **Challenge Fit**: literally "help creators"
- **Real-World Impact**: EU AI Act makes it urgent and monetizable

And our edge isn't a niche corpus — it's **execution + the signed Authorship Passport**. We use world-famous English authors (Austen, Dickens, Poe) so any English-speaking judge instantly *feels* the voice match, and we pair it with real cryptographic provenance (JWS ES256) that almost nobody is building for the EU AI Act deadline.

### The demo we'll record

3-minute video with this timed structure:

| Time | Content |
|---|---|
| 00:00–00:20 | Problem: "ChatGPT writes the same for everyone" |
| 00:20–00:35 | Solution one-liner + 1-slide architecture |
| 00:35–01:50 | **LIVE DEMO**: Dickens selected → Style DNA visible → prompt → side-by-side appears → fit score 87% Dickens, vanilla 34% → Passport signed → verification |
| 01:50–02:30 | Impact: EU AI Act, creator market, numbers |
| 02:30–03:00 | How we used IBM Bob (4 Custom Modes) + repo + team + closing |

**Success criterion**: a non-expert human must see the difference between left column (vanilla) and right (AutorIA) in **≤5 seconds**. Validated in Sprint 2 with 3 non-technical people as gate.

---

## 3. Team, roles and ownership model

We are **3 computer engineers** (1 software branch + 2 computing branch). Full-time in July (no classes, no work). That's ~720 person-hours total.

### Role philosophy

After much debate, we settled on:

> **Single primary ownership + designated backup + 3 critical pair sessions**

Opposite of "everyone does everything" (which creates endless coordination) **and** opposite of rigid silos (which kills the project if someone gets sick).

### Role assignment

| Primary role | Profile | Core responsibilities | Backup for |
|---|---|---|---|
| **P1 — Frontend + Pitch + Bob Champion** | Software branch | Next.js + Tailwind + shadcn, StyleProfile visualization (radar + UMAP scatter), generation UI, Authorship Passport screen. **Week 4**: video script, final README, demo. **Cross-cutting**: IBM Bob champion (Custom Modes, BobShell logs, "How we used Bob" section). | Backend (API) |
| **P2 — AI/ML Engineer** | Computing branch | Linguistic feature extractor (spaCy: TTR, sentence length, subordination ratio, punctuation distribution, rhetorical markers). Embeddings with sentence-transformers. StyleProfile representation (JSON + vector). UMAP precompute. | AI Generation |
| **P3 — Backend + AI Generation + Crypto** | Computing branch | FastAPI, DB schema (Postgres + pgvector), endpoints, **conditioned generation** (Watsonx orchestration with StyleProfile as prompt-conditioning), **JWS signing** of the Authorship Passport (python-jose ES256). | Feature extraction |

### Why this split

- **Software branch leads frontend + pitch**: software branch is more comfortable with UI, full-stack and communication. Whoever builds the frontend naturally builds the demo. **And crucial**: pitch goes with technical load (frontend) so they aren't underused weeks 1-3.
- **The two computing engineers split the AI core**: P2 *analyzes* (NLP + embeddings), P3 *generates and signs* (LLM + crypto). Distinct specializations, no overlap.
- **Backend lives with P3 (not separated)** because the backend is essentially the generation pipeline wrapper. Splitting them adds internal contract friction.

### What's cross-cutting — EVERYBODY does this

These 4 things are non-negotiable, all 3 do them:

1. **Daily IBM Bob usage**. Everyone uses Bob for their module. P1 only *consolidates* the documentation, but the usage is everyone's.
2. **PR code review**. Every PR is reviewed by at least 1 other person before merge. No exceptions.
3. **Document your own module in the README and in `docs/`**.
4. **Happy-path tests for your own module**. No 80% coverage required, just the happy path.

### Critical pair sessions (not solo)

There are 3 pieces where the cost of a bug is very high. Done **in pairs, in a 2h call**:

| Piece | Pair | Why pair |
|---|---|---|
| **API contract between frontend and backend** | P1 + P3 | If this gets out of sync, a week is lost |
| **`StyleProfile` JSON schema** | P2 + P3 | It's the "common language" between analysis and generation |
| **Authorship Passport sign + verify** | P3 + P1 | P3 signs in backend, P1 verifies in frontend. Crypto without pairing = guaranteed bug |

### Quick decision rule for code

> About to touch someone else's module code? Tell them in the channel first (one line). If they say "ok", go ahead. If they say "wait", you wait. No surprise PRs to other people's modules.

---

## 4. How we make decisions

### The 3 rules

1. **2/3 majority**. If 2 of 3 agree, we move forward. No waiting for unanimous consensus. **We have 30 days, zero margin to argue the same thing 3 times**.
2. **Every product decision goes to the Decision Log**. If in sprint 3 someone asks "why did we pick Llama over Granite?", the answer is there. 2 minutes writing it today saves 20 minutes arguing later.
3. **MVP LOCKED**. Any scope change requires 2/3 vote + Decision Log entry. Prevents scope creep during July.

### The Decision Log

Lives at **`docs/decision_log.md`**. 4-column table:

| Date | Decision | Made by | Rationale |
|---|---|---|---|
| YYYY-MM-DD | What we decided | All / P1 / etc. | Why |

**Anyone can add entries**. Rule: after any important decision, whoever asked for it writes the entry before closing the channel. Always English.

### The 17 decisions already made

Read them in `docs/decision_log.md`. The key ones to keep in your head:

- Idea = **AutorIA** (auditable authorship layer)
- LLM = **IBM Watsonx end-to-end** (Llama 3.3 70B + Granite 3 8B auxiliary)
- **English everywhere** — app UI, repo, README, video, commits, and the generated text. Only the **internal team chat** stays Spanish.
- Multi-author with **3 preloaded**: Jane Austen, Charles Dickens, Edgar Allan Poe
- Stack: Next.js + FastAPI + Postgres+pgvector (Supabase) + JWS ES256
- 4 mandatory Bob Custom Modes: **StyleExtractor**, **GenerationConductor**, **StudioComposer**, **PassportAuditor**

---

## 5. Methodology — sprints, ceremonies, pair sessions

### Overall structure

```
Jun 26-30  →  Sprint 0 — Prep (this week, what we're doing)
Jul 01-07  →  Sprint 1 — Foundation
Jul 08-14  →  Sprint 2 — StyleProfile
Jul 15-21  →  Sprint 3 — Generation + Passport
Jul 22-28  →  Sprint 4 — Polish + Demo
Jul 29-31  →  Buffer — Submit with margin
```

Each sprint is **exactly 1 week**.

### Ceremonies (minimal, async whenever possible)

| When | What | Duration | Mode |
|---|---|---|---|
| **Monday morning** | Sprint kick: everyone picks 3-5 issues from "Sprint Ready" and moves them to "In Progress" | 15 min | Async in channel |
| **Mon–Fri** | Daily async — 2 lines in channel: done yesterday / today / blockers | 2 min/day | Text |
| **Friday 18:00** | Mini-review — status, what's left, what moves | 15 min | Sync (call) |
| **Sunday 18:00** | **Sprint review + planning** — close sprint, move unfinished items, plan next, update Decision Log | 30-40 min | Sync (call) |

> **Rule**: if you can write it, don't call. If it takes >10 min in writing, call.

### Pair sessions

Scheduled once per sprint when relevant, in shared agenda. 2 hours, one call with screen sharing, both writing and reviewing. Output: PR signed by both.

| Sprint | Pair session |
|---|---|
| Sprint 1 | P1 + P3 → close **API contract** (`docs/api_contract.yaml`) |
| Sprint 2 | P2 + P3 → close **StyleProfile schema** v1.0 |
| Sprint 3 | P3 + P1 → **Passport sign + verify** end-to-end |

### Definition of Done (DoD) — per issue

An issue is "Done" when:

- [ ] Code shipped to main (PR merged)
- [ ] Happy-path tests pass
- [ ] Lint passes (`make lint`)
- [ ] Module documentation updated
- [ ] If touches StyleProfile or Passport schema → version bumped
- [ ] If creates new endpoint → `api_contract.yaml` updated
- [ ] PR mentions which Bob Custom Mode was used (in template)

### Definition of Done — per sprint (macro goals)

| Sprint | DoD |
|---|---|
| **Sprint 1 — Foundation** | Repo deployed (front + back with `/health`), DB schema in Supabase, doc upload works, extractor skeleton, 4 Custom Modes created in Bob |
| **Sprint 2 — StyleProfile** | All 4 feature layers (lexical, syntactic, stylistic, vocab) compute. UMAP 2D precomputed. "Style DNA" UI visible with radar + scatter. **Gate**: 3 non-technical humans identify Dickens voice in ≤5s. |
| **Sprint 3 — Generation + Passport** | `/api/generate` end-to-end < 8s P95. Side-by-side UI works. Signed Passport downloadable. `/verify` validates signature. Public JWKS |
| **Sprint 4 — Polish + Demo** | Demo rehearsed 5 times without failure. 3-min video on public YouTube. Final README complete. Bob `usage-report.md` with metrics. Stable public deploy |

---

## 6. The MVP — what's in and what's out (LOCKED)

Full document at **`docs/MVP.md`**. Executive summary:

### Features IN (we DO build this)

1. **Author Onboarding** — Upload .txt/.md, min. 3 texts of 1000+ words. **3 preloaded authors** (Austen, Dickens, Poe).
2. **Style DNA Extraction** — Python pipeline with spaCy + sentence-transformers. Output: `StyleProfile JSON v1.0` with lexical/syntactic/stylistic metrics + distinctive vocabulary + embedding centroid + UMAP 2D coords.
3. **Conditioned Generation** — `/api/generate` calls Watsonx in parallel (vanilla + AutorIA), computes `fit_score` (0-100) on each output.
4. **Authorship Passport** — JSON with metadata + ES256 JWS signature. Verification against `/.well-known/jwks.json`.
5. **Side-by-side UI** — main screen with two columns, comparative metrics, "Download Passport" button.

### Features OUT (we do NOT build this in July)

- ❌ Multimodal (image, audio, video)
- ❌ User accounts, login, multi-user
- ❌ Payments, marketplace, community
- ❌ Mobile responsive (desktop only, demo is desktop)
- ❌ Fine-tuning own models
- ❌ Plagiarism / copyright detection
- ❌ Human-edit tracking + real human/AI % (v1 marks 100% AI)
- ❌ Generation in languages other than English
- ❌ Public verification portal with own domain
- ❌ Exhaustive test coverage (happy path only)
- ❌ Generation streaming
- ❌ Generation caching
- ❌ UI multi-language switching (English only)

> **If in Sprint 2 someone says "what if we add X?" and X is on this list, the answer is: NO**. Unless 2/3 vote + Decision Log entry.

### Hinge decisions (already closed)

| Decision | Value | Why |
|---|---|---|
| LLM | **IBM Watsonx end-to-end**. Primary: `meta-llama/llama-3-3-70b-instruct`. Auxiliary: `ibm/granite-3-8b-instruct` | IBM challenge = points for full-IBM stack |
| Comparison baseline | **Same model WITHOUT style conditioning** | Honest comparison = judges notice |
| App UI + video + generated text | **English** | International IBM jury; judges can read the voice match directly |
| Authors | **Austen, Dickens, Poe** (English, public domain) | Iconic, maximally distinct voices; instantly recognizable |
| Multi-author | 3 preloaded + live upload supported | Cross-author comparison is the demo's "wow" moment |

---

## 7. Tech stack (locked, not up for debate)

### Frontend (P1)

```
Next.js 14 (App Router) + TypeScript
Tailwind CSS + shadcn/ui
Recharts (radar + bars)
D3 / react-scatter-chart (UMAP 2D)
Deploy: Vercel (free tier)
```

### Backend (P3)

```
Python 3.11 + FastAPI + Uvicorn
Pydantic v2
SQLAlchemy 2.0 + asyncpg
Deploy: Railway (~$5/mo)
```

### AI Pipeline (P2)

```
spaCy 3.7 + en_core_web_lg
sentence-transformers + all-mpnet-base-v2 (768-dim, English)
umap-learn (server-side 2D precompute)
scikit-learn (TF-IDF)
tiktoken (approx chunking)
```

### LLM (P3)

```
ibm-watsonx-ai SDK
Creative model: meta-llama/llama-3-3-70b-instruct
Auxiliary model: ibm/granite-3-8b-instruct
Sprint 1 task: validate voice-matching quality with 5 prompts (gate)
```

### Database (P3)

```
PostgreSQL 16 + pgvector
Hosting: Supabase (free, upgrade if it bursts)
Tables: authors, documents, chunks, style_profiles, passports
Index: HNSW on chunks.embedding with vector_cosine_ops
```

### Cryptography (P3)

```
python-jose[cryptography]
Algorithm: ES256 (ECDSA P-256 + SHA-256)
EC keypair generated at seed (script generate_keys.py)
Private → Supabase Vault, NEVER commit
Public → /.well-known/jwks.json
```

### Dev tools

```
IBM Bob (mandatory) — main copilot
GitHub + GitHub Projects + GitHub Actions
Ruff + Black (Python)
ESLint + Prettier (TS)
pytest (Python)
Docker Compose for local DB
```

> **No stack changes without 2/3 vote + Decision Log entry**. Arguing versions mid-July = drama.

---

## 8. Repository structure

Full tree in README "Repository Structure". Key parts:

```
autoria/
├── README.md                  ← first thing judges read
├── LICENSE                    ← MIT
├── .env.example               ← variables without values
├── docker-compose.yml         ← local Postgres+pgvector
├── Makefile                   ← common commands
│
├── ai_pipeline/               ← CORE — P2 owner
│   └── autoria_ai/
│       ├── extractor/         ← lexical, syntactic, stylistic, vocabulary
│       ├── embedder.py
│       ├── style_profile.py
│       ├── conditioner.py
│       ├── generator.py
│       ├── fit_scorer.py
│       └── passport/          ← builder, signer, verifier
│
├── backend/                   ← API — P3 owner
│   └── app/
│       ├── main.py
│       ├── routes/            ← authors, ingest, generate, passport, jwks
│       └── ...
│
├── frontend/                  ← UI — P1 owner
│   ├── app/                   ← / + /studio/[author] + /verify
│   ├── components/
│   └── lib/i18n/en.ts         ← UI strings in English
│
├── bob/                       ← IBM Bob — P3 owner, CRITICAL
│   ├── custom-modes/          ← 3 documented modes
│   ├── sessions/              ← weekly BobShell exports per person
│   └── usage-report.md        ← final report (sprint 4)
│
├── corpus/                    ← demo texts of the 3 authors
├── infra/supabase/migrations/ ← initial SQL
├── scripts/                   ← seed, generate_keys, run_demo, etc.
└── docs/                      ← MVP, decision_log, architecture, etc.
```

### Repo rules

- **`main` is protected**: PR required + 1 review before merge.
- **Every PR must close an issue** with `Closes #N`.
- **No direct push to main**, not even for "a quick fix".
- **Don't commit `.env`, private keys, anything in `keys/`** — `.gitignore` covers them.
- **If you touch someone else's module**, talk to the owner first.

---

## 9. IBM Bob — the key tool (this can win or disqualify us)

> ⚠️ **IN THE MAY 2026 HACKATHON, IBM ELIMINATED PROJECTS FOR "NON-MEANINGFUL BOB USAGE"**. This is serious.

### What Bob is

**IBM Bob** is an AI development partner — a development copilot (rival of Cursor, Copilot, Claude Code). Its differentiator:

- **Full repository context** (not just the open file)
- **Persona-based Custom Modes** (load context + role + commands into a reusable "mode")
- **BobShell** — integrated terminal with audit and session export
- **Governance and auditability** — export logs of what it did when
- **Multi-model orchestration**

### What's expected of us

1. **Use Bob as main copilot every day**. Not glorified autocomplete — actual usage.
2. **Create 4 Custom Modes** demonstrating we understand the tool.
3. **Export BobShell sessions weekly** and commit them to `bob/sessions/`.
4. **Document the usage exhaustively in the README** with screenshots + metrics.

### The 4 Custom Modes we must create (Sprint 1)

| Mode | Owner | Loaded context | When used |
|---|---|---|---|
| **StyleExtractor** | P2 | `style_profile.json` schema + spaCy examples + features to compute | P2 while developing `ai_pipeline/autoria_ai/extractor/*` |
| **GenerationConductor** | P3 | `conditioner.py` + `generator.py` + `fit_scorer.py` + RAG schema | P3 building `/api/generate` |
| **StudioComposer** | P1 | `api_contract.yaml` + `lib/i18n/en.ts` + MVP §4.5 UI spec | P1 building `frontend/app/studio/*`, radar/scatter, side-by-side, `/verify` layout |
| **PassportAuditor** | P3 | JWS ES256 spec + Passport schema + JWKS endpoint | P3 developing `passport/*`; P1 pairs on `/verify` crypto edge cases |

Each mode is documented in **`bob/custom-modes/<mode-name>.md`** with:
- Role description
- Loaded context
- Typical commands
- Expected outputs

### MANDATORY artifacts in the repo

```
bob/
├── README.md                    ← how our Bob integration works
├── custom-modes/
│   ├── style-extractor.md
│   ├── generation-conductor.md
│   ├── studio-composer.md
│   └── passport-auditor.md
├── sessions/                    ← created on the first Friday of Sprint 1
│   ├── week1/                   ← 3 files: p1.md, p2.md, p3.md
│   ├── week2/                   ← same
│   ├── week3/                   ← same
│   └── week4/                   ← same
├── screenshots/                 ← 3+ screenshots of Bob working (created in Sprint 1)
└── usage-report.md              ← final report with metrics (sprint 4)
```

**Minimum goal by end of July**:
- 4 documented Custom Modes
- 12+ BobShell exports (3 people × 4 weeks)
- 3+ screenshots
- "How We Used IBM Bob" section in README

### Metrics we'll report

| Metric | How measured | Target |
|---|---|---|
| PRs assisted by Bob | Marked in PR template | ≥ 70% of PRs |
| Custom Modes created | Files in `bob/custom-modes/` | 4 |
| BobShell sessions exported | Files in `bob/sessions/` | ≥ 12 |
| Representative screenshots | In `bob/screenshots/` | ≥ 3 |

### Usage policy

- **Speak to Bob in English** (always, even if it feels awkward). Sessions live in the public repo.
- **Export BobShell every Friday** to `bob/sessions/weekN/<your-initial>.md`.
- **If Bob helped significantly on a PR**, note it in the PR template.

> **🔥 Read [`bob/playbook.md`](../bob/playbook.md) before Sprint 1 day 1.** It's the operational manual: setup checklist, the 5 prompt patterns we use, BobShell export workflow with frontmatter, advanced moves (model switching, adversarial reviews, plan-first), weekly checklist and FAQ. ~25 min — non-negotiable for anyone touching Bob.

---

## 10. GitHub Projects — backlog, sprints and workflow

Our Project is **"AutorIA July Sprint"**. Linked to the `autoria` repo.

### Configured views

| View | Type | Purpose |
|---|---|---|
| **📋 Backlog** | Table | See everything pending, grouped by Sprint, sorted by Priority |
| **🏃 Current Sprint** | Board (kanban) | Your daily view. Filtered by current Sprint, columns = Status |
| **🗓️ Roadmap** | Roadmap | Timeline of the 4 sprints |
| **🤝 By Owner** | Table | Who has what assigned, grouped by Assignee |

### Custom fields on each issue

| Field | Values |
|---|---|
| **Status** | Backlog → Sprint Ready → In Progress → In Review → Done |
| **Sprint** | Sprint 0 (prep), Sprint 1, Sprint 2, Sprint 3, Sprint 4, Buffer, Backlog |
| **Size** | XS (<2h), S (2-4h), M (4-8h), L (1-2d), XL (2-3d) |
| **Module** | ai_pipeline, backend, frontend, bob, docs, infra, demo |
| **Priority** | P0 — blocker, P1 — must, P2 — should, P3 — nice |

Plus, **each issue has a Milestone** (Sprint 1, Sprint 2, etc.) which is the real due date.

### Issue lifecycle

```
Backlog                    ← Issue created, no sprint yet
    ↓ (Sunday sprint planning)
Sprint Ready               ← Assigned to a sprint, ready to pick
    ↓ (Monday morning, someone picks it)
In Progress                ← Assignee is working
    ↓ (PR opened)
In Review                  ← PR awaiting review
    ↓ (PR merged)
Done                       ← Auto-closed via "Closes #N" in PR
```

### Golden rules

1. **No work without an issue**. If you start doing something, create the issue first (30 seconds).
2. **One assignee per issue**. If it needs pairing, note in body (`Pair with @user`).
3. **If an issue has been "In Progress" >3 days**, mark it blocked or split it.
4. **Every PR closes at least one issue** with `Closes #N`.
5. **No moving to Done without merge**. "In Review" is a mandatory intermediate column.
6. **If unplanned work appears**, create a retroactive issue. The Project must reflect everything.
7. **At Sunday sprint review**, unfinished work either moves to Backlog or to the next sprint. Never silently dragged.

### Create a new issue (CLI or web)

**Web**: "New issue" → choose "Feature" or "Bug" template → fill title + body → label + milestone → "Submit" → go to Project and add to view.

**CLI** (faster):
```bash
gh issue create \
  --repo <owner>/autorIA \
  --title "ml: add MATTR-500 to lexical extractor" \
  --body  "Add Moving Average TTR (window=500) to ai_pipeline/autoria_ai/extractor/lexical.py. Update StyleProfile schema v1.0." \
  --label "ml,size:S,prio:P1" \
  --milestone "Sprint 2 — StyleProfile" \
  --assignee @me
```

Then go to the Project in web and add it manually to the view, fill `Sprint` and `Module`.

### Available labels

| Category | Labels |
|---|---|
| Module | `infra`, `backend`, `frontend`, `ml`, `bob`, `docs`, `demo` |
| Size | `size:XS`, `size:S`, `size:M`, `size:L`, `size:XL` |
| Priority | `prio:P0`, `prio:P1`, `prio:P2`, `prio:P3` |
| Type | `bug`, `blocked` |

---

## 11. Daily workflow — Git, branches, PRs, commits

### Branch convention

```
main                           ← protected, only merge via approved PR
feat/<module>-<description>    ← features
fix/<module>-<description>     ← bugs
docs/<description>             ← docs only
chore/<description>            ← deps, infra, non-functional
```

Examples:
```
feat/ai-syntactic-features
feat/frontend-style-radar
fix/passport-jwks-rotation
docs/architecture-c4-diagrams
chore/bump-spacy-3.7.4
```

### Conventional Commits (mandatory)

All commits follow:
```
<type>(<scope>): <description in imperative mood, lowercase>

[optional body explaining WHY]
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`

Scopes we use: `ai`, `back`, `front`, `bob`, `infra`, `docs`, `crypto`, `db`

Good examples:
```
feat(ai): add lexical features extractor with TTR and MATTR
fix(crypto): correct JWKS key id rotation on key reload
docs(bob): export week-2 sessions for P1 and P2
chore(deps): bump sentence-transformers to 3.1.0
test(ai): add fixtures for distinctive vocab extractor
```

Bad examples:
```
update                         ← says nothing
fix bug                        ← which bug?
arreglo del extractor          ← Spanish, no
WIP                            ← shouldn't exist in main history
```

### End-to-end feature flow

```
1. Pick issue from "Sprint Ready" → move to "In Progress" + self-assign
2. git checkout main && git pull
3. git checkout -b feat/ai-lexical-extractor
4. Work with Bob (using StyleExtractor Mode if relevant)
5. Frequent small commits in Conventional Commits style
6. git push -u origin feat/ai-lexical-extractor
7. gh pr create --fill (or via web)
8. PR template: fill ALL required checkboxes
   ✅ Tests pass locally
   ✅ Lint passes
   ✅ Schema/version bumped (if applicable)
   ✅ .env.example updated (if applicable)
   ✅ Bob mode used: <which>
9. Move issue to "In Review"
10. Another teammate reviews, approves (or requests changes)
11. CI must pass (lint + tests). If it fails, fix it
12. Merge to main (prefer squash merge, message = PR title)
13. Delete the branch
14. Issue moves to "Done" automatically via "Closes #N"
```

### PR rules

- **PR ≤ 400 changed lines when possible**. Giant PRs aren't reviewed properly.
- **PR title = Conventional Commit** (e.g. `feat(ai): add lexical features extractor`).
- **PR body**: what + why + screenshots if UI + "How Bob helped" + issue link.
- **Reviews ≤ 24h**. If you don't review within 24h you're blocking.
- **Don't merge your own PR without another's review**, not even "because urgent".

### Sync with main

Before starting anything each day:
```bash
git checkout main
git pull
```

When your branch has been open >1 day, rebase to avoid conflicts:
```bash
git checkout feat/my-feature
git fetch origin
git rebase origin/main
# resolve conflicts if any
git push --force-with-lease
```

---

## 12. Language policy — what goes in English vs Spanish

### Master rule

> Everything a human reads — the **app UI, the demo video, and the generated text** — goes in **English**. The only Spanish left in the project is our **internal team chat**.

### Quick table

| Element | Language |
|---|---|
| Code (vars, functions, classes, comments) | **English** |
| Commit messages | **English** |
| Branch names | **English** |
| PR titles + bodies | **English** |
| Issue titles + bodies | **English** |
| `README.md`, `LICENSE`, all of `/docs/` | **English** |
| Decision Log | **English** |
| Bob sessions (chat with Bob) | **English** |
| Backend logs, API errors | **English** |
| OpenAPI spec, JSON Schemas | **English** (JSON keys in English too) |
| **UI strings (buttons, labels, user messages)** | **🇬🇧 English** |
| **Demo video voice + on-screen text** | **🇬🇧 English** |
| **Generated literary text** (model output) | **🇬🇧 English** |
| Prompts/system prompts to Watsonx | **🇬🇧 English** |
| Internal chat (WhatsApp/Discord) | **🇪🇸 Spanish** (we're 3 Spaniards) |

### UI strings — mandatory pattern

We don't hardcode UI text inside React components. **All** UI strings go in `frontend/lib/i18n/en.ts`:

```typescript
export const STRINGS = {
  studio: {
    generateButton: "Generate",
    vanillaColumnTitle: "Llama 3.3 (unconditioned)",
    autoriaColumnTitle: "AutorIA — {author}'s voice",
    fitScoreLabel: "Style fit",
  },
  passport: {
    downloadButton: "Download Authorship Passport",
    verifyTitle: "Authorship Passport verification",
  },
};
```

Note: keep **all** user-visible text out of components and in `en.ts` — buttons, labels, errors, tooltips.

---

## 13. Communication — channels and cadence

### Channels

- **Single channel** (the one we use — WhatsApp/Telegram/Discord). No 3 parallel channels.
- **GitHub Issues / PRs** for anything technical that must be traceable.
- **Decision Log** for decisions affecting the product.

### Cadence

| When | What | Mode |
|---|---|---|
| Every morning before starting | Read the channel, catch up | Async (2 min) |
| Once a day | Write 2 lines: done yesterday / today / blockers | Async |
| Friday 18:00 | Mini-review of the week | Sync (15 min) |
| Sunday 18:00 | Sprint review + planning of next | Sync (30-40 min) |
| Scheduled pair sessions | 1 per sprint, on shared agenda | Sync (2h) |

### Communication rules

1. **If you can write it, don't call**. Async > meetings.
2. **If it takes >10 min in writing, call**. To avoid dying typing.
3. **Meetings have agenda and fixed duration**. No "let's just talk".
4. **No meeting >30 min** during July, except pair sessions.
5. **Critical blockers** (something blocking you >2h) → immediate ping, don't wait for daily.

---

## 14. Challenge deliverables — what we ship

On July 31 (ideally noon Spain time, NOT 23:59) we upload to the BeMyApp portal:

### Mandatory deliverables

| Deliverable | Details | Owner |
|---|---|---|
| **Working prototype** | Public deploy URL (Vercel) | P1 |
| **Public GitHub repo** | `autorIA` repo URL with complete README | P3 |
| **Public video** | Max 3 min, public YouTube/Vimeo, English voiceover | P1 |
| **IBM SkillsBuild course** | Completed by ≥1 member (better if all 3) | All |
| **Pitch deck** | (Optional but recommended) 5-7 slides PDF | P1 |

### What we CAN'T forget

- **Mandatory README sections** (see `README.md`).
- **"How we used IBM Bob" section** with metrics and screenshots — **without it, disqualification**.
- **4 documented Custom Modes** in `bob/custom-modes/`.
- **≥12 BobShell exports** in `bob/sessions/`.
- **MIT License** in `LICENSE`.
- **Public deploy accessible without login**.
- **The video public on YouTube**, not private or unlisted.

---

## 15. Pre-July-1 checklist (this week)

This week (Jun 26-30) is **Sprint 0 — Prep**. Goal: arrive at July 1 with zero setup friction.

### Per person

**P1 — Frontend + Pitch + Bob Champion**
- [ ] Read this document fully
- [ ] Read `docs/MVP.md` fully
- [ ] Read `docs/decision_log.md` fully
- [ ] Create IBM Bob account (`ibm.biz/university-bob`) and verify access
- [ ] Start the mandatory IBM SkillsBuild course
- [ ] Local frontend setup (`cd frontend && npx create-next-app@latest .` + shadcn + Recharts)
- [ ] Draft the 3 files `bob/custom-modes/*.md`
- [ ] Quick wireframes in Excalidraw → export to `docs/wireframes/`

**P2 — AI/ML Engineer**
- [ ] Read this document fully
- [ ] Read `docs/MVP.md` fully, especially §4.2 (StyleProfile schema)
- [ ] Create IBM Bob account and verify access
- [ ] Start IBM SkillsBuild course
- [ ] Local pipeline setup (`cd ai_pipeline && pip install -e . && python -c "import spacy; spacy.load('en_core_web_lg')"`)
- [ ] Download and clean corpus of the 3 authors into `corpus/{austen,dickens,poe}/`
- [ ] Start `docs/style_features.md` with exact metric list + formulas
- [ ] Quality validation: test `Llama 3.3 70b` via Watsonx with 5 voice-matching prompts, score 1-10

**P3 — Backend + Generation + Crypto**
- [ ] Read this document fully
- [ ] Read `docs/MVP.md` fully, especially §4.4 (Passport) and §7 (API contract)
- [ ] Create IBM Bob account and verify access
- [ ] Start IBM SkillsBuild course
- [ ] Local backend setup (`cd backend && pip install -e . && uvicorn app.main:app --reload`)
- [ ] Start local Postgres+pgvector (`docker compose up -d`)
- [ ] Apply initial migration (`psql ... < infra/supabase/migrations/0001_init.sql`)
- [ ] Generate EC keypair for Passport (`make keys`) — private NEVER goes to repo
- [ ] Activate Watsonx (register + API key + Project ID in `.env`)
- [ ] Start `docs/api_contract.yaml` (OpenAPI 3.1)
- [ ] Start `docs/erd.md` (Mermaid `erDiagram`)

### Shared (better in pair)

- [ ] **P1 + P3**: close `docs/api_contract.yaml` (1h call on Saturday)
- [ ] **P2 + P3**: close final `style_profile.json` schema (1h call on Sunday)
- [ ] **All**: Sunday Jun 30, sprint planning call for Sprint 1 (move "Sprint Ready" issues, assign)

### Consequences if not done by July 1

| Item | Consequence if missing |
|---|---|
| IBM Bob active | Start July without the main tool |
| Watsonx API key | Can't generate anything → Sprint 1 lost |
| SkillsBuild course started | Bobcoins take time to activate → can't use Bob fully |
| Corpus downloaded | Extractor has no data to run on |
| API contract closed | Frontend and backend can't work in parallel |
| StyleProfile schema closed | P2 can't start the extractor |

---

## 16. Sprint 1 — day 1 plan (July 1)

### Morning (9:00-13:00) — Sprint kick-off

| Time | Who | What |
|---|---|---|
| 9:00 | All | 30-min call — confirm sprint plan, issue assignment, pair session time |
| 9:30 | All | Each person imports their Custom Mode(s) into Bob — P1: **StudioComposer**, P2: **StyleExtractor**, P3: **GenerationConductor** + **PassportAuditor** |
| 10:30 | P1 | Vercel setup + first frontend deploy ("AutorIA — coming soon" with shadcn + Tailwind) |
| 10:30 | P3 | Railway + Supabase production setup + first backend deploy (`/health` responds) |
| 10:30 | P2 | Start `lexical.py` extractor (TTR, MATTR-500, hapax, avg_word_length) |
| 13:00 | All | Check-in on channel (text): "alive, no blockers" / "alive, blocked by X" |

### Afternoon (14:00-19:00)

| Time | Who | What |
|---|---|---|
| 14:00 | P1 | `/` page with author selector (3 static cards) |
| 14:00 | P2 | Continue lexical + start syntactic (sentence length, subordination with spaCy) |
| 14:00 | P3 | `POST /api/authors/{id}/documents` — upload + persist raw text |
| 18:00 | All | Mini check-in in channel: "what's merged today" |
| 18:30 | All | Voice-matching validation: test Llama 3.3 70B with 5 prompts (gate) |

### End of day

- ✅ Repo with green CI
- ✅ Frontend deployed on Vercel ("coming soon" but with shadcn)
- ✅ Backend deployed on Railway with `/health` 200
- ✅ DB in Supabase with schema applied
- ✅ 4 Custom Modes active in Bob (each person uses their own + pairs on PassportAuditor)
- ✅ 3-5 PRs merged (no fluff, real code)
- ✅ Daily async written in channel by all 3

---

## 17. Anti-patterns — what NOT to do

### In code

❌ **Push directly to main** — always PR
❌ **Giant PRs (>800 lines)** — split into sub-tasks
❌ **Touch someone else's module without telling them** — always 1 line in channel first
❌ **Hardcode UI strings in components** — always via `lib/i18n/en.ts`
❌ **Commit `.env`, private keys, generated files** — `.gitignore` covers them
❌ **Commits "WIP", "update", "fix"** — Conventional Commits always
❌ **Skip tests "just this once"** — happy path is non-negotiable

### In coordination

❌ **"Wait to see what the other says"** — 2/3 majority decides now
❌ **Meetings >30 min** — fixed agenda or no meeting
❌ **Argue MVP scope** — it's LOCKED
❌ **Start work without an issue** — Project must reflect everything
❌ **"I thought we agreed on..."** — it's in the Decision Log or it wasn't agreed

### With IBM Bob

❌ **Use Bob as autocomplete** — use Custom Modes, not a Cursor editor
❌ **Speak to Bob in Spanish** — sessions live in the public repo
❌ **Don't export BobShell** — every Friday to `bob/sessions/weekN/`
❌ **Leave "How we used IBM Bob" for the last day** — build incrementally

### With time

❌ **Work all-nighters the last days** — record the video while awake
❌ **Polish frontend until day 30** — Sprint 4 is polish, not redesign
❌ **Upload submission at 23:59 on July 31** — noon Spain time, not later

---

## 18. FAQ

### "What if the current sprint doesn't finish?"
On Sunday, unfinished issues either move to "Sprint N+1" or back to "Backlog" if priority dropped. Never silently dragged. What matters is that the sprint HAS a closure, even partial.

### "What if I get sick a week?"
Your role has a backup designated (P1→P3, P2→P3, P3→P2). The daily async ensures your backup knows the state. Pair sessions ensure >1 person has touched critical pieces. Not ideal but the project doesn't collapse.

### "What if Watsonx doesn't match the author's voice well?"
Plan B in MVP: stronger conditioning / more RAG passages, then `llama-3-1-405b-instruct` or `granite-3-8b-instruct` via Watsonx. If all fail, fallback to Mistral Large via Watsonx. **But**: we validate this Sprint 1 day 2, not Sprint 4.

### "What if a seemingly essential feature emerges that's not in the MVP?"
5-min call with all 3, 2/3 vote. If it passes → Decision Log entry + add. If not → `docs/roadmap.md` for "post-July".

### "Can I use a non-Watsonx model for something?"
Not by default. Stack is Watsonx end-to-end. If you think there's a very strong reason (e.g. a punctual translation where Watsonx fails), bring to 2/3 vote.

### "What if I disagree with a decision made before I joined?"
Decision Log is historical, not immovable. You can propose a revisit — if majority agrees, it changes with a new entry at new date. **But**: if the decision already has code implementing it, the cost of changing is high. Think twice.

### "When does the repo go public?"
Public from day 1 (Jun 24/25). Shows process, not just deliverable. Judges can see how we work.

### "Can I work in someone else's module?"
As backup, yes. As initiative, tell the owner first. The rule: 1 line in channel before touching. If "ok", go.

### "How do we measure if the demo is good enough?"
Sprint 2 gate: show the side-by-side UI to 3 non-technical humans. If all 3 identify "which sounds more like Dickens" in ≤5s, we pass. If not, iterate until we do.

### "What if something doesn't work on the last day?"
Buffer Jul 29-31 exists exactly for this. Day 29: full submission dry-run. Day 30: fix surprises. Day 31 morning: submit. If we get to day 31 with something seriously broken, contingency: use pre-recordings in the video, simplify the demo, etc. The submission goes in no matter what.

---

## 📎 Key links

| Resource | URL |
|---|---|
| Repo | `https://github.com/<owner>/autorIA` |
| GitHub Project | `https://github.com/<owner>/projects/<n>` (AutorIA July Sprint) |
| Challenge | `https://aibuilderschallenge-bob.bemyapp.com` |
| Sponsor portal | `https://aibuilderschallenge-bobhub.bemyapp.com/#/sponsors/1-july-challenge` |
| IBM Bob | `https://ibm.biz/university-bob` |
| IBM SkillsBuild course | (link to the mandatory course once registered) |
| Watsonx | `https://us-south.ml.cloud.ibm.com` |
| Supabase project | (project URL) |
| Vercel project | (deploy URL) |
| Railway project | (deploy URL) |
| Decision Log | `docs/decision_log.md` |
| MVP doc | `docs/MVP.md` |

---

## One last thing

If after reading this something doesn't add up, isn't obvious, or you want to change something: **say it on the channel TODAY**. The best edit of this document is the one you make before July 1. After that, any change costs sprint time.

> Welcome to the team. We're going to win this. 🚀
