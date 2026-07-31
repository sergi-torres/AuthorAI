# How We Used IBM Bob — AutorIA Final Report

> **Status**: final · **Owner**: P1 (Bob Champion) · **Compiled**: 2026-07-31
> Every number in this report is countable in this repository. Where a claim rests on
> an artifact, the artifact is linked.

This document is the long form of the **"How we used IBM Bob"** section of the
[root README](../README.md), which is self-contained and can be read on its own.

---

## Summary

We treated Bob as the **main copilot**, not as autocomplete, and the integration is
structural rather than incidental. Four **Custom Modes** were created in Sprint 1 —
one per technical pillar of the product (**analyze → generate → present → certify**)
— each loading a different slice of our own specification. That detail is the whole
trick: because each mode was anchored to `api_contract.yaml`, `style_features.md`,
`passport_schema.md` or the design system, Bob argued from *our* documents instead of
from generic priors, and the standing instruction in each mode is that **the document
wins over the ticket**. Most of our contract drift got caught by Bob quoting a spec
back at us.

The working rhythm was: pick an issue, open the matching Custom Mode, make Bob plan
before writing (several of our session prompts literally start with *"Before writing
any code, list the files to create/touch"*), implement, then export the BobShell
session into `bob/sessions/`. Every PR carries a mandatory **"How IBM Bob helped"**
section enforced by [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md),
so usage is documented at the moment it happens rather than reconstructed in week 4.

The highest-value work Bob did was not writing code. It was **auditing**: a full
completeness audit of 29 closed issues against running code, which downgraded 15 of
them and produced 18 scoped work orders; the statistical diagnosis that killed our
TF-IDF vocabulary ranking; and adversarial review of our own JWS verifier. Those three
are described in detail below.

---

## Metrics

| Metric | Target | **Final** |
| --- | --- | --- |
| Custom Modes created | 4 | **4** ✅ |
| BobShell sessions exported | ≥ 12 | **26** ✅ |
| Recorded message exchanges across those sessions | — | **1 468** |
| Session date range | July | **2026-07-08 → 2026-07-27** |
| Representative screenshots | ≥ 3 | **8** ✅ |
| Merged PRs on `main` | — | **63** (248 commits) |
| PRs required to document Bob's contribution | every PR | enforced by the PR template |

Sessions by owner and sprint:

| | P1 (frontend) | P2 (ML) | P3 (backend/crypto) | Total |
| --- | --- | --- | --- | --- |
| **Sprint 1** | 4 | 7 | 5 | 16 |
| **Sprint 2** | 3 | 2 | 5 | 10 |
| **Total** | **7** | **9** | **10** | **26** |

---

## The 4 Custom Modes — what they did

### StyleExtractor (owner: P2) — *analyze*

**Loaded context**: `schemas/style_profile.json`, spaCy feature examples, `docs/style_features.md`.

Built the whole feature-extraction layer, one module per session with the spec pasted
in as the contract. The prompts are narrow and testable by design — e.g.
`lexical.json`: *"Implement `ai_pipeline/autoria_ai/extractor/lexical.py`. The file must
expose a single public function…"* — which is why each extractor came back with a
single public entry point and its tests rather than a sprawl.

**Concrete outcome**: the five extractors (`lexical`, `syntactic`, `stylistic`,
`vocabulary`, `style_profile`) plus `embedder.py`, together covered by 246 test
functions. MATTR-500 is a real sliding window, not the shortcut approximation the
first draft proposed.

**Sessions**: [`Sprint_1/P2/`](sessions/Sprint_1/P2/) — `lexical`, `syntactic`, `stylistic`, `vocabulary`, `Cleaner_and_chuncker`, `embedder`, `conditioner`.

### GenerationConductor (owner: P3) — *generate*

**Loaded context**: `conditioner.py`, `generator.py`, `fit_scorer.py`, the RAG schema, Watsonx config.

Owned the orchestration: the two parallel Watsonx calls, RAG retrieval over pgvector,
the conditioned system prompt, and `fit_score` calibration. The `api-generate` session
opens by naming what already exists and must be reused — *"Several pieces already
exist and must be…"* — which is how we avoided Bob rewriting working modules to suit a
new call site.

**Concrete outcome**: `POST /api/generate` with `asyncio.gather`, asymmetric failure
degradation (a vanilla failure degrades one column; an AutorIA failure surfaces,
because without it there is no Passport), and the review session on issue #22 that
hardened the Watsonx client's 8 s timeout and 1/2/4 s backoff.

**Sessions**: [`Sprint_2/P3/`](sessions/Sprint_2/P3/) — `api-generate`, `review_issue_22`, `seed_fix`; [`Sprint_1/P2/conditioner.json`](sessions/Sprint_1/P2/conditioner.json); [`Sprint_2/P2/fit_scorer.json`](sessions/Sprint_2/P2/fit_scorer.json).

### StudioComposer (owner: P1) — *present*

**Loaded context**: `docs/api_contract.yaml`, `lib/i18n/en.ts`, the StyleProfile schema, MVP §4.5.

Built every screen. One session opens literally *"You are **StudioComposer**…"* — the
mode is not a label we applied afterwards. Its most useful constraint was the design
system: all strings through `en.ts`, all colour through tokens, every async surface
with loading / error / empty states. Bob enforced that more consistently than we did.

**Concrete outcome**: the author gallery, the Style DNA panel (radar + UMAP scatter +
vocabulary table), the consolidated studio screen, the side-by-side with comparative
metrics, and the `/verify` page. Also the refactor that merged Style DNA and generation
into **one** screen after the two-route split proved to be an easy-to-miss navigation hop.

**Sessions**: [`Sprint_1/P1/`](sessions/Sprint_1/P1/) — `author-selector`, `style-dna-panel`, `generate-studio`, `generate-studio-fix`; [`Sprint_2/P1/`](sessions/Sprint_2/P1/) — `comparative-metrics-and-vocab`, `download-passport`, `verify-passport-screen`.

### PassportAuditor (owner: P3, paired with P1 on `/verify`) — *certify*

**Loaded context**: the JWS ES256 spec, `passport_schema.md` §§2–8, the JWKS rules.

The brief here was adversarial: **attack the verifier, do not admire it**. The
`jwks_verify` session starts by naming the exact spec sections and then
*"Before writing any code, list files to create/touch…"* — plan first, because crypto
written eagerly is crypto written wrong.

**Concrete outcome**: the `alg` allow-list that rejects `alg:none` with
`unsupported_algorithm`, strict `kid`→JWKS resolution, schema validation of the decoded
payload, and structured error codes the frontend translates. Issue #99 — a *flaky*
tamper test, where the "tampered" signature was sometimes still valid — came out of
this mode and is exactly the kind of bug that would otherwise have shipped green.

**Sessions**: [`Sprint_2/P3/`](sessions/Sprint_2/P3/) — `passport_builder`, `jwks_verify`.

---

## Three problems Bob solved best

### 1. It caught a statistical dead end before the jury did

`distinctive_vocab` — the signature-word list a non-technical juror actually reads —
was returning `say`, `know`, `time` for all three authors. Working in StyleExtractor
and GenerationConductor modes, the diagnosis came back as a property of the algorithm
rather than a tuning problem: with only three "documents" (one corpus per author), any
term all three use has an identical IDF, so TF-IDF **mathematically collapses** into
raw frequency. No amount of tuning `max_features` or `stop_words` can fix that.

The fix was a Jeffreys-prior log-odds ratio against the pooled other authors, plus a
NOUN/ADJ/ADV filter. It was prototyped **against the real corpus before being adopted**
— which is how we also found that Project Gutenberg's `[Illustration]` markup was being
counted as Austen vocabulary (193 occurrences, hidden until then behind TF-IDF's
frequency bias).

**Measured**: 3-way top-10 overlap **5 → 0**; every pairwise overlap also 0. Trail in
[`docs/decision_log.md`](../docs/decision_log.md) (2026-07-30) and
[`docs/style_features.md`](../docs/style_features.md) §4.1.

### 2. It turned "are we actually done?" into an executable plan

Late in the project we asked Bob to audit our 29 closed issues against the code — not
by reading diffs, but by **running** the linters, the test suites and a live
cryptographic round-trip. The result is
[`docs/completeness_audit.md`](../docs/completeness_audit.md): 14 verified, 12 partial,
1 implemented-but-disconnected, 1 never implemented at all.

It found that `pytest backend/tests` had been failing at *collection* for weeks,
because CI had no pytest job and only ran on `pull_request` — so "the tests pass" had
been an unproven claim since the day it broke. It also found that RAG never executed in
production (`DATABASE_URL` never reached the retriever, and the failure was swallowed
by a `except Exception`), that the UMAP script wrote to a table nobody read, and that
the frontend silently substituted invented fixtures for real profiles on a legitimate
404.

Those became 18 scoped work orders — symptom, evidence, root cause, files to touch,
definition of done — filed as issues #82–#100 and fixed. **This is the single highest-value
thing Bob did on this project**, and none of it was code generation.

### 3. It reviewed our cryptography adversarially

Asked to break the Passport verifier rather than confirm it, PassportAuditor mode
produced the attack list we then had to defend against: `alg:none` downgrade, a `kid`
resolving to no key, a tampered payload carrying a valid-looking signature, and the
flaky-fixture problem of issue #99. The normative rules now in
[`docs/passport_schema.md`](../docs/passport_schema.md) §8 exist because of those sessions.

Verified live on 2026-07-31 against the deployed API: a valid Passport returns
`{"valid": true}`, and the same token with one character changed returns
`{"valid": false, "errors":[{"code":"invalid_signature"}]}`.

---

## Where Bob struggled

Written plainly, because a report where the tool is flawless is a report nobody believes.

- **Long-lived architectural context.** Bob is excellent inside a Custom Mode's loaded
  slice and noticeably weaker across a 5-package monorepo. Ask it something that spans
  `frontend/`, `backend/` and `ai_pipeline/` at once and it will confidently answer for
  the part it can see. Our workaround was to make the documents authoritative and to
  state in every mode that the spec outranks the ticket.

- **Confident claims with nothing behind them.** Our worst process failure was a Bob-
  assisted issue (#11, the R1 voice-matching gate) closed as complete when the named
  deliverable had never existed in any branch. That is not a Bob defect — it is what
  happens when a plausible narrative is accepted as evidence. The fix was procedural:
  measure, then claim. CI grew real pytest jobs (including one against a live pgvector
  container), and *measure, don't estimate* now runs through the whole Decision Log.
  It is also why `baseline_eval.md` records ten verbatim generations with blank score
  cells — an agent grading its own model's output would reproduce the original failure
  in a new costume.

- **Our own discipline slipped before Bob's did.** `bob/README.md` says sessions are
  exported weekly and that we speak to Bob in English. In practice exports cluster around
  implementation pushes rather than Fridays, the folder convention drifted from `weekN/`
  to `Sprint_N/`, and at least one session prompt (`Sprint_2/P2/fit_scorer.json`) opens
  in Spanish. We are recording that instead of quietly tidying it, since the sessions
  are in the repo and anyone can check.

- **Sprint 3 artifacts thinned out.** The 26 exports cover 8–27 July. The final week
  went into deployment, the audit follow-ups and the submission, and it is
  under-represented in `sessions/`.

---

## Selected screenshots

Eight captures live in [`screenshots/`](screenshots/):

**Sprint 1** — [`autoria-author-selector-v1.png`](screenshots/Sprint_1/autoria-author-selector-v1.png) ·
[`autoria-issue9-deliverables.png`](screenshots/Sprint_1/autoria-issue9-deliverables.png) ·
[`style-dna-austen-ready-light.png`](screenshots/Sprint_1/style-dna-austen-ready-light.png) ·
[`style-dna-poe-ready-light.png`](screenshots/Sprint_1/style-dna-poe-ready-light.png) ·
[`style-dna-dark.png`](screenshots/Sprint_1/style-dna-dark.png) ·
[`style-dna-empty-state.png`](screenshots/Sprint_1/style-dna-empty-state.png)

**Sprint 2** — [`StyleDNA.png`](screenshots/Sprint_2/StyleDNA.png) ·
[`Voice-generation.png`](screenshots/Sprint_2/Voice-generation.png)

> **Note on reading these.** They are contemporaneous Sprint 1–2 captures, kept as a
> record of what Bob produced at that point. They therefore show the **pre-2026-07-30
> UI**, when the vocabulary column was still labelled "TF-IDF" and the Style DNA panel
> could fall back to fixture data. Both were changed afterwards (see the Decision Log
> entries of 2026-07-27 and 2026-07-30). For current behaviour, use the live app.

---

## Session exports

All 26 BobShell exports are raw, unedited JSON under [`sessions/`](sessions/):

| Sprint | Owner | Sessions |
| --- | --- | --- |
| 1 | P1 | `author-selector` · `style-dna-panel` · `generate-studio` · `generate-studio-fix` |
| 1 | P2 | `Cleaner_and_chuncker` · `lexical` · `syntactic` · `stylistic` · `vocabulary` · `embedder` · `conditioner` |
| 1 | P3 | `supabase_ini` · `first_api_contract_paths` · `upload_author_docs` · `style_profile_retrieval` · `style_profile_recompute` |
| 2 | P1 | `comparative-metrics-and-vocab` · `download-passport` · `verify-passport-screen` |
| 2 | P2 | `fit_scorer` · `umap` |
| 2 | P3 | `passport_builder` · `jwks_verify` · `api-generate` · `review_issue_22` · `seed_fix` |

Plus [`sessions/Sprint_1/baseline_eval.md`](sessions/Sprint_1/baseline_eval.md) — the R1
voice-matching evaluation: ten verbatim generations (five prompts × vanilla/conditioned),
per-call latency, RAG provenance by document and chunk, and source-file hashes so the
run is reproducible.

---

## Verdict

**Yes — and specifically for the parts we did not expect.** Code generation was the
least interesting thing Bob did for AutorIA. What paid for itself was using it as an
*auditor*: pointing it at our own closed issues with instructions to run the code
rather than read it produced a defect list we would not have found by review, in a
project where all three of us believed we were nearly done.

The pattern we would carry to another project is the one that worked here: **load the
specification into the mode, tell the model the specification outranks the ticket, make
it plan before it writes, and make it prove claims by execution.** The failure mode to
guard against is the mirror of that — an assistant is very good at producing a
convincing account of work that was never done, and the only defence is a CI job that
can actually go red.

Our operational manual is [`playbook.md`](playbook.md); the workspace guide is
[`README.md`](README.md).
