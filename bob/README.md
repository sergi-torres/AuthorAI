# 🤖 IBM Bob — AutorIA Integration Workspace

> ⚠️ **This directory is the most important deliverable for IBM judges.**
> In the May 2026 hackathon, IBM disqualified projects for "non-meaningful use of Bob."
> Don't let that happen to us.

**👉 Start with [`usage-report.md`](usage-report.md)** — the final report with metrics,
what each Custom Mode built, three problems Bob solved, and an honest account of where
it struggled. The [root README](../README.md) carries the short version.

---

## Structure

```
bob/
├── README.md                    ← you are here
├── usage-report.md              ← FINAL REPORT — read this first
├── playbook.md                  ← our operational manual for using Bob
├── custom-modes/                ← the 4 Custom Modes we created
│   ├── style-extractor.md          analyze  (P2)
│   ├── generation-conductor.md     generate (P3)
│   ├── studio-composer.md          present  (P1)
│   └── passport-auditor.md         certify  (P3 + P1)
├── sessions/                    ← 26 raw BobShell exports, by sprint and owner
│   ├── Sprint_1/{P1,P2,P3}/        16 sessions
│   ├── Sprint_1/baseline_eval.md   R1 voice-matching evaluation
│   └── Sprint_2/{P1,P2,P3}/        10 sessions
└── screenshots/                 ← 8 captures, Sprint_1/ and Sprint_2/
```

> **Naming note.** The original plan in `docs/MVP.md` §8 called these folders
> `sessions/week1…week4/`. In practice we exported per sprint and per owner, so the
> layout on disk is `Sprint_N/PX/`. The disk layout is the real one; the MVP text was
> not retro-edited.

---

## The 4 Custom Modes (Sprint 1)

Each Custom Mode targets one technical pillar of AutorIA: **analyze → generate → present → certify**.

| Mode | Pillar | Owner | Used by | Loaded context |
|---|---|---|---|---|
| **StyleExtractor** | Analyze | P2 | P2 primarily | `style_profile.json` schema + spaCy examples + features spec |
| **GenerationConductor** | Generate | P3 | P3 primarily | `conditioner.py`, `generator.py`, `fit_scorer.py` + RAG schema + Watsonx config |
| **StudioComposer** | Present | P1 | P1 primarily | `api_contract.yaml`, `lib/i18n/en.ts`, StyleProfile schema, MVP §4.5 UI spec |
| **PassportAuditor** | Certify | P3 | P3 + P1 (`/verify` crypto) | JWS ES256 spec + Passport schema + JWKS endpoint |

Each Custom Mode is documented in `custom-modes/<mode-name>.md` with role, loaded context, typical commands and expected outputs.

---

## BobShell exports — **26 delivered** (target: 12)

Each team member exports their BobShell session as raw JSON into
`bob/sessions/Sprint_N/PX/<topic>.json`. Unedited — the export is the evidence.

| | P1 (frontend) | P2 (ML) | P3 (backend/crypto) | Total |
| --- | --- | --- | --- | --- |
| **Sprint 1** | 4 | 7 | 5 | 16 |
| **Sprint 2** | 3 | 2 | 5 | 10 |
| **Total** | **7** | **9** | **10** | **26** |

Spanning **2026-07-08 → 2026-07-27**, with **1 468** recorded message exchanges.

Also here: [`sessions/Sprint_1/baseline_eval.md`](sessions/Sprint_1/baseline_eval.md) —
the R1 voice-matching evaluation. Ten verbatim generations (5 prompts × vanilla /
conditioned), per-call latency, RAG provenance down to the chunk, and source-file
hashes so the run is reproducible.

---

## Screenshots — **8 delivered** (target: 3)

`screenshots/Sprint_1/` (6) and `screenshots/Sprint_2/` (2), captioned in
[`usage-report.md`](usage-report.md).

> They are contemporaneous Sprint 1–2 captures and show the **pre-2026-07-30 UI** —
> the vocabulary column was still labelled "TF-IDF" and the Style DNA panel could fall
> back to fixture data. Both were changed later (Decision Log, 2026-07-27 and
> 2026-07-30). For current behaviour use the live app at
> [quebasto.com](https://quebasto.com/).

---

## Final usage report

[`usage-report.md`](usage-report.md), compiled 2026-07-31:

- **Numbers** — modes, sessions, exchanges, screenshots, PRs
- **Per mode** — what each Custom Mode actually built, with linked sessions
- **Three problems Bob solved best** — the TF-IDF diagnosis, the completeness audit
  that produced 18 work orders, and adversarial review of our own JWS verifier
- **Where Bob struggled** — including where *our* discipline slipped, not just Bob's
- **Verdict**

Linked from the root README's "How We Used IBM Bob" section.

---

## Daily usage rules (see `docs/ONBOARDING.md` §9)

- Use Bob as **main copilot**, not glorified autocomplete.
- **Speak to Bob in English** — sessions live in the public repo.
- **Use the Custom Modes**, not just default chat — that's how we demonstrate "exploitation."
- **Note Bob usage on every PR** via the template (`How IBM Bob helped`).
- **Export your sessions** into `sessions/Sprint_N/PX/` as you finish a piece of work.

---

## 📕 Want to use Bob like a power user?

Read **[`bob/playbook.md`](playbook.md)** — the full operational manual: setup checklist, the 5 prompt patterns we use, BobShell export workflow, anti-patterns, advanced moves, recurring checklist and FAQ. **~25 min read.**
