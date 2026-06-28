# 🤖 IBM Bob — AutorIA Integration Workspace

> ⚠️ **This directory is the most important deliverable for IBM judges.**
> In the May 2026 hackathon, IBM disqualified projects for "non-meaningful use of Bob."
> Don't let that happen to us.

---

## Structure

```
bob/
├── README.md                    ← you are here
├── custom-modes/                ← 4 Custom Modes we created
│   ├── style-extractor.md
│   ├── generation-conductor.md
│   ├── studio-composer.md
│   └── passport-auditor.md
├── sessions/                    ← weekly BobShell exports per person
│   ├── week1/
│   ├── week2/
│   ├── week3/
│   └── week4/
├── screenshots/                 ← representative captures of Bob in action
└── usage-report.md              ← final report (Sprint 4) with metrics + analysis
```

> The `sessions/`, `screenshots/` and `custom-modes/` subfolders are created on demand — `sessions/weekN/` is added the first Friday of each sprint, `screenshots/` once we capture our first one in Sprint 1.

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

## Weekly BobShell exports

Every Friday (or before the Sunday sprint review), each team member exports their BobShell session to `bob/sessions/weekN/<initial>.md` (`p1.md`, `p2.md`, `p3.md`). Format: the raw BobShell export (markdown is fine).

**Target by end of July**: 4 weeks × 3 people = **12 session exports**.

If a week's session is light, write a short note explaining what you worked on (e.g. "this week was mostly debugging existing code with Bob, no major new flows").

---

## Screenshots

Pick 3+ representative screenshots showing Bob working on a non-trivial task — e.g.:

- A Custom Mode answering a complex multi-file question
- A BobShell session orchestrating a refactor
- Bob generating tests for a tricky module

Save them in `screenshots/`. Reference them in `usage-report.md`.

---

## Final usage report

Compiled in **Sprint 4** (Jul 22-28). Lives in `usage-report.md`. Contents:

- **Numbers**: PRs assisted, Custom Modes created, sessions exported
- **Concrete examples**: 3-5 problems we solved with Bob that would have taken much longer without
- **Honest assessment**: where Bob excelled, where it struggled
- **Screenshots**: 3+ with captions

This report is linked from the README's "How We Used IBM Bob" section.

---

## Daily usage rules (see `docs/ONBOARDING.md` §9)

- Use Bob as **main copilot**, not glorified autocomplete.
- **Speak to Bob in English** — sessions live in the public repo.
- **Use the Custom Modes**, not just default chat — that's how we demonstrate "exploitation."
- **Note Bob usage on every PR** via the template (`How IBM Bob helped`).
- **Export weekly**.

---

## 📕 Want to use Bob like a power user?

Read **[`bob/playbook.md`](playbook.md)** — the full operational manual: setup checklist, the 5 prompt patterns we use, BobShell export workflow, anti-patterns, advanced moves, weekly checklist and FAQ. **~25 min read. Do it before Sprint 1 day 1.**
