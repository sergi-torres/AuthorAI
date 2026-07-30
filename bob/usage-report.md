# How We Used IBM Bob — AutorIA Final Report

> **Status**: final (submission week, July 2026).
> **Owner**: P1 (Bob Champion), with evidence from P2 + P3 session exports.

This document is the canonical artifact for the **"How we used IBM Bob"** section of the README. The README links here.

---

## Summary

We treated IBM Bob as a **junior teammate with full-repo context**, not as autocomplete. From day one of Sprint 1 we imported four Custom Modes — one per technical pillar (`analyze → generate → present → certify`) — and ran almost all non-trivial work inside BobShell with a fixed prompt pattern (CTRO: Context · Task · Restriction · Output). Every Friday (and at issue close) we exported sessions into `bob/sessions/` so judges can audit the trail.

Bob accelerated the three hardest parts of AutorIA: (1) implementing a locked linguistic `StyleProfile` without drifting from `docs/style_features.md`, (2) building an honest vanilla-vs-conditioned generation path on Watsonx with a measurable `fit_score`, and (3) shipping a JWS ES256 Authorship Passport that verifies offline against JWKS. Frontend work under StudioComposer turned those outputs into a demo a non-expert can read in seconds.

The operational discipline mattered as much as the models: PR template requires a "How IBM Bob helped" section, Custom Modes load the locked specs, and Decision Log entries record when Bob-assisted work changed a closed algorithm. That combination is what we mean by *exploiting* Bob rather than just *using* it.

---

## Metrics

| Metric | Target | Final |
|---|---|---|
| Total PRs assisted by Bob | ≥ 70% of PRs | **~92%** (58 / 63 merged PRs mention Bob / Custom Mode / BobShell in title or body) |
| Custom Modes created | 4 | **4** — StyleExtractor, GenerationConductor, StudioComposer, PassportAuditor |
| BobShell sessions exported | ≥ 12 | **26** JSON exports under `bob/sessions/` (+ `Sprint_1/baseline_eval.md` voice-gate evidence) |
| Sessions by owner | — | P1: 7 · P2: 9 · P3: 10 |
| Custom Mode usage (from export `modeId`) | — | style-extractor 8 · generation-conductor 6 · studio-composer 6 · passport-auditor 2 · default agent 2 |
| Representative evidence artifacts | ≥ 3 screenshots | **Session exports used as primary audit trail** (PNG gallery not captured; see [Session exports](#session-exports)) |
| Focused Bob spans (≥ 30 min) | track in dailies | Routine: one session per issue / logical task; several multi-hour crypto and Style DNA sessions (see PassportAuditor + StudioComposer below) |

---

## The 4 Custom Modes — what they did

### StyleExtractor (owner: P2)

Drove the entire `ai_pipeline/autoria_ai/extractor/*` stack: cleaner/chunker, lexical/syntactic/stylistic features, embeddings, distinctive vocabulary, and the composite `fit_score`. Sessions consistently forced Bob to follow `docs/style_features.md` even when GitHub issue text was stale (e.g. outdated flat weights vs the locked 5-component formula).

**Concrete win:** implementing `fit_scorer.py` under StyleExtractor with an explicit override — *"issue description is OUTDATED; follow `style_features.md` §6"* — produced a testable scorer (semantic 0.35 / syntactic 0.20 / lexical 0.15 / stylistic 0.15 / vocabulary 0.15) instead of a wrong-but-green implementation of the issue text.

Representative session: [`bob/sessions/Sprint_2/p2/fit_scorer.json`](sessions/Sprint_2/p2/fit_scorer.json) · also [`Sprint_1/P2/lexical.json`](sessions/Sprint_1/P2/lexical.json), [`vocabulary.json`](sessions/Sprint_1/P2/vocabulary.json), [`umap.json`](sessions/Sprint_2/p2/umap.json).

### GenerationConductor (owner: P3)

Owned conditioned-prompt composition, Watsonx orchestration, RAG wiring, and `POST /api/generate`. The mode's bias toward *measure, don't guess* shaped how we tuned the system prompt (token budget, dialogue/subordination wording, distinctive-vocab injection) and kept the A/B honest: same `meta-llama/llama-3-3-70b-instruct` on both columns.

**Concrete win:** the conditioner + generate path sessions produced the parallel vanilla/AutorIA response shape the UI depends on, with Passport issuance on the conditioned branch only — the demo hinge in under one round-trip.

Representative session: [`bob/sessions/Sprint_2/P3/api-generate.json`](sessions/Sprint_2/P3/api-generate.json) · also [`Sprint_1/P2/conditioner.json`](sessions/Sprint_1/P2/conditioner.json), [`Sprint_1/P3/style_profile_retrieval.json`](sessions/Sprint_1/P3/style_profile_retrieval.json).

### StudioComposer (owner: P1)

Built the judge-facing surface: author gallery, Style DNA panel (radar + UMAP scatter + metrics), side-by-side studio, comparative metrics, distinctive-vocab highlights, Passport download, and `/verify` layout. Prompts loaded `docs/design-system.md` + `api_contract.yaml` so components stayed contract-typed and i18n-clean (`en.ts` only).

**Concrete 5-second clarity win:** consolidating Style DNA and generation onto a single `/author/[id]` studio (instead of a separate generate route) removed a navigation hop and put radar, scatter, prompt, and vanilla/AutorIA columns on one screen — the layout the demo timeline in `docs/MVP.md` §3 actually needs.

Representative session: [`bob/sessions/Sprint_1/P1/style-dna-panel.json`](sessions/Sprint_1/P1/style-dna-panel.json) · also [`generate-studio.json`](sessions/Sprint_1/P1/generate-studio.json), [`Sprint_2/P1/verify-passport-screen.json`](sessions/Sprint_2/P1/verify-passport-screen.json), [`comparative-metrics-and-vocab.json`](sessions/Sprint_2/P1/comparative-metrics-and-vocab.json).

### PassportAuditor (owner: P3, pair with P1 on `/verify`)

Adversarial crypto mode for JWS ES256 signing, JWKS publication, verification error codes, and payload hashing rules (hashes only — never raw prompt/output in the Passport). Plan-first prompts ("list files and risks before writing code") caught key-management footguns early.

**Concrete security catch:** sessions explicitly forbade generating a new ECDSA keypair on every FastAPI boot (which would silently break every verification) and required offline verification via `PASSPORT_PUBLIC_KEY_PATH` / local JWKS with typed error codes (`invalid_signature`, `unknown_kid`, `unsupported_algorithm`, …). That discipline later paid off when deploy needed PEM-content env vars because `keys/**` is gitignored.

Representative session: [`bob/sessions/Sprint_2/P3/jwks_verify.json`](sessions/Sprint_2/P3/jwks_verify.json) · also [`passport_builder.json`](sessions/Sprint_2/P3/passport_builder.json).

---

## Three problems Bob solved best

1. **Style DNA panel from a locked design system (hours → one focused session)**  
   Issue #43 asked for radar + UMAP scatter + metric chips inside `/author/[id]`. StudioComposer was given the full design-system + contract constraints up front and delivered typed API helpers, normalization domains, empty/error/loading states, and Recharts v3 components without inventing per-chunk scatter points the contract does not expose.  
   Evidence: [`sessions/Sprint_1/P1/style-dna-panel.json`](sessions/Sprint_1/P1/style-dna-panel.json).

2. **Passport builder that cannot leak content**  
   PassportAuditor planned `builder.py` against schema §2–6 before coding: canonical JSON hashing for StyleProfile, `sha256:<hex>` for prompt/output/snippets, reuse of existing signer/JWKS — and refused scope creep into `/generate` or frontend. The result is a Passport that proves provenance without storing the literary text.  
   Evidence: [`sessions/Sprint_2/P3/passport_builder.json`](sessions/Sprint_2/P3/passport_builder.json).

3. **`fit_score` that matches the locked formula, not the stale ticket**  
   StyleExtractor was pointed at `docs/style_features.md` §6 when the GitHub issue still described wrong weights. Bob implemented the five weighted components with clamps, mocks for spaCy/embeddings in tests, and a 0–100 integer output — the number the side-by-side UI shows judges.  
   Evidence: [`sessions/Sprint_2/p2/fit_scorer.json`](sessions/Sprint_2/p2/fit_scorer.json).

---

## Where Bob struggled

- **Stale issue text vs locked docs.** Bob will faithfully implement the prompt you give it. When a GitHub issue disagreed with `style_features.md` or `api_contract.yaml`, an uncorrected prompt produced the wrong green path. Mitigation: CTRO prompts that name the authoritative doc and say "issue text is wrong if it conflicts."
- **Heavy ML cold starts.** Sessions that touched spaCy / sentence-transformers paid download and load time; we learned to mock models in unit tests and lazy-load embeddings in the API process (see deploy/local-dev work in Sprint 2–3).
- **TF-IDF distinctive vocab looked "done" until measured.** Early extractor sessions shipped a mathematically valid TF-IDF path that collapsed with only three author-documents. Fixing it required a Decision Log ratification (Jeffreys log-odds) — Bob drafted candidates, but humans had to measure top-10 overlap on the real corpus before merging.
- **Screenshots as PNGs.** We prioritized BobShell JSON exports (machine-auditable, include `modeId`, costs, and full prompts) over a curated `bob/screenshots/` gallery. Judges should treat the session files below as the primary evidence.

---

## Selected evidence (open these first)

| # | What to look at | Why it matters |
|---|---|---|
| 1 | [`sessions/Sprint_1/P1/style-dna-panel.json`](sessions/Sprint_1/P1/style-dna-panel.json) | StudioComposer — full Style DNA implementation prompt + completed task list |
| 2 | [`sessions/Sprint_2/P3/jwks_verify.json`](sessions/Sprint_2/P3/jwks_verify.json) | PassportAuditor — plan-first crypto, offline verify, typed error codes (`modeId: passport-auditor`) |
| 3 | [`sessions/Sprint_2/p2/fit_scorer.json`](sessions/Sprint_2/p2/fit_scorer.json) | StyleExtractor — locked `fit_score` formula override (`modeId: style-extractor`) |
| 4 | [`sessions/Sprint_2/P3/api-generate.json`](sessions/Sprint_2/P3/api-generate.json) | GenerationConductor — end-to-end generate path |
| 5 | [`sessions/Sprint_1/baseline_eval.md`](sessions/Sprint_1/baseline_eval.md) | Voice-matching gate evidence (vanilla vs conditioned on fixed prompts) |

Custom Mode definitions (imported into each teammate's Bob workspace):

- [`custom-modes/style-extractor.md`](custom-modes/style-extractor.md)
- [`custom-modes/generation-conductor.md`](custom-modes/generation-conductor.md)
- [`custom-modes/studio-composer.md`](custom-modes/studio-composer.md)
- [`custom-modes/passport-auditor.md`](custom-modes/passport-auditor.md)

Operational playbook: [`playbook.md`](playbook.md).

---

## Session exports

Exports are organized by sprint and owner (not the early `weekN/` sketch). Each `.json` is a raw BobShell export.

| Sprint | Focus | P1 | P2 | P3 |
|---|---|---|---|---|
| **Sprint 1** | Foundation, extractors, Style DNA UI, API contract paths | `author-selector`, `style-dna-panel`, `generate-studio` (+ fix) | `Cleaner_and_chuncker`, `lexical`, `syntactic`, `stylistic`, `vocabulary`, `embedder`, `conditioner` | `supabase_ini`, `first_api_contract_paths`, `upload_author_docs`, `style_profile_retrieval`, `style_profile_recompute` |
| **Sprint 2** | Generation, Passport, verify UI, scoring, UMAP | `comparative-metrics-and-vocab`, `download-passport`, `verify-passport-screen` | `fit_scorer`, `umap` | `api-generate`, `jwks_verify`, `passport_builder`, `review_issue_22`, `seed_fix` |

Also: [`Sprint_1/baseline_eval.md`](sessions/Sprint_1/baseline_eval.md) — recorded vanilla/conditioned generations for the R1 voice-match gate.

**Totals:** 26 BobShell JSON exports · 7 P1 + 9 P2 + 10 P3.

---

## Verdict

We would use IBM Bob again on any project that has **locked specs, multiple owners, and an audit requirement**. Custom Modes were the force multiplier: they kept spaCy work linguistic, generation work empirical, UI work contract-honest, and crypto work adversarial. The habit of exporting BobShell sessions into the public repo made Bob usage *demonstrable* rather than anecdotal — which is exactly the bar this challenge sets.
