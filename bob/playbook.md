# 📕 IBM Bob — Power-User Playbook (AutorIA)

> **Read this before Sprint 1 day 1.** Reading time: ~25 minutes.
> **Audience**: P1, P2, P3.
> **Status**: living document — update it when you discover a pattern that works.

This is the operational manual for getting the maximum out of **IBM Bob** on AutorIA. The `bob/README.md` is the *what* (folders, mandatory artifacts); this playbook is the *how* (prompts, patterns, anti-patterns, daily routine).

---

## 0. Why this exists

In the **May 2026 hackathon**, IBM disqualified projects for *"non-meaningful Bob usage"*. The bar IBM judges actually score is:

> Did the team **exploit** Bob's unique capabilities, or did they just **use** it as a fancier autocomplete?

The four levers IBM weighs:

1. **Full repository context** — Bob reads across files, not just the open one.
2. **Persona-based Custom Modes** — preloaded role + context + typical commands.
3. **BobShell** — auditable, exportable sessions.
4. **Multi-model orchestration** — switching models for the right job.

Everything in this playbook is engineered so that, at submission time, our README's *"How We Used IBM Bob"* section can point to concrete evidence on **all four**.

---

## 1. Sprint 0 setup checklist (do this BEFORE July 1)

| # | Step | Time | Owner |
|---|---|---|---|
| 1 | Create Bob account at [`ibm.biz/university-bob`](https://ibm.biz/university-bob) | 5 min, but **provisioning can take hours** — do it first | Each person |
| 2 | Start the mandatory **IBM SkillsBuild** course — this activates Bobcoins (your token budget) | ~2h | Each person |
| 3 | Open the `autorIA` repo in Bob and verify full-repo indexing is complete | 5 min | Each person |
| 4 | Import the 4 Custom Modes from `bob/custom-modes/` into your Bob workspace | 10 min | Each person |
| 5 | Run a smoke test in BobShell — ask any mode a trivial question, export the session, save it locally | 2 min | Each person |
| 6 | Confirm you can export a BobShell session as Markdown (you'll do this every Friday) | 2 min | Each person |

> If step 5 fails for any team member by **Jun 30 EOD**, ping the channel — we cannot start Sprint 1 with anyone blocked on Bob access.

---

## 2. The mental model — Bob is not Cursor / Copilot

Treat Bob as a **junior teammate with read access to the whole repo** — not as autocomplete. The mental shift:

| Autocomplete tools | IBM Bob (used right) |
|---|---|
| Reacts line-by-line | Plans before writing |
| One file at a time | Cross-file, contract-aware |
| Single persona | Switchable Custom Modes |
| No audit trail | BobShell exports go in the repo |
| You drive | You **converse** (questions back are normal) |

Three rules that follow from this:

- **R1 — Speak to Bob in English, always.** Sessions live in the public repo. Spanish sessions = Spanish in the public repo = breaks our language policy + looks unprofessional to the IBM jury.
- **R2 — Use a Custom Mode for any task that maps to one.** Default chat is fine for "what's the syntax of X", not for "implement the lexical extractor". Loaded context is half the magic.
- **R3 — One session per logical task, not per day.** Sessions are the unit of audit; mixing 5 unrelated tasks in one session destroys traceability.

---

## 3. The 4 Custom Modes — when to switch

| If the task is… | Use mode | Primary file(s) you'll touch |
|---|---|---|
| Adding a linguistic feature (TTR, MATTR, subordination, POS dist…) | **StyleExtractor** | `ai_pipeline/autoria_ai/extractor/*.py` |
| Sanity-checking author discriminability or `StyleProfile` schema | **StyleExtractor** | `ai_pipeline/autoria_ai/schemas/style_profile.json` |
| Designing or A/B-testing the conditioned system prompt | **GenerationConductor** | `ai_pipeline/autoria_ai/conditioner.py` |
| RAG retrieval (pgvector / HNSW / top-k) | **GenerationConductor** | `ai_pipeline/autoria_ai/generator.py`, `backend/app/routes/generate.py` |
| Watsonx parallel calls, latency tuning, `fit_score` backend | **GenerationConductor** | `generator.py`, `fit_scorer.py` |
| Iterating demo prompts to maximize vanilla-vs-AutorIA contrast | **GenerationConductor** | `docs/examples/demo_prompts.md` |
| Style DNA radar / UMAP scatter from StyleProfile JSON | **StudioComposer** | `frontend/components/StyleRadarChart.tsx`, `StyleScatter2D.tsx` |
| Side-by-side UI, fit_score bars, generate button wiring | **StudioComposer** | `frontend/components/SideBySideOutput.tsx`, `app/studio/[author]/page.tsx` |
| API client + TS types aligned with `api_contract.yaml` | **StudioComposer** | `frontend/lib/api.ts`, `lib/types.ts` |
| UI strings, i18n, 5-second clarity audit | **StudioComposer** | `frontend/lib/i18n/en.ts` |
| `/verify` page layout, error UX (not crypto logic) | **StudioComposer** | `frontend/app/verify/page.tsx` |
| Anything JWS / ES256 / signing / verification logic | **PassportAuditor** | `ai_pipeline/autoria_ai/passport/*.py` |
| Adversarial review of crypto / JWKS / signature edge cases | **PassportAuditor** | `backend/app/routes/passport.py`, `routes/jwks.py` |
| EU AI Act Art. 50 compliance checks on the Passport schema | **PassportAuditor** | `docs/passport_schema.md` |
| Anything else (a dep bump, a `make` target, a quick syntax doubt) | **Default chat** | — |

**P1's daily driver is StudioComposer.** Pair with PassportAuditor only when `/verify` touches signature semantics, not layout.

**Switching mid-session is fine** — explicitly say `Switching to PassportAuditor mode: …`. The export will reflect the transition and that itself is good evidence to the jury (multi-mode orchestration).

---

## 4. Prompt patterns that actually work

Five patterns covering ~90% of our daily needs. Memorize the names; the structure is what matters.

### 4.1 The **CTRO** pattern (Context · Task · Restriction · Output)

The default shape of any non-trivial request.

```
[Context]     One sentence locating the work in the codebase.
[Task]        What you want, in imperative mood.
[Restriction] What MUST or MUST NOT happen (perf, deps, signatures, schema).
[Output]      Concrete deliverables (file paths, test names, return shapes).
```

✅ **Good**

> **[Context]** In `ai_pipeline/autoria_ai/extractor/lexical.py` we already have TTR.
> **[Task]** Add Moving-Average TTR with window 500 (MATTR-500), spec in `docs/style_features.md` §1.2.
> **[Restriction]** No new dependencies. Output must be in `[0, 1]`. The function must run on Dickens' *Great Expectations* (~180k tokens) in under 15s on a developer laptop.
> **[Output]** Update `lexical.py`. Add a pytest case `test_mattr_500_dickens_range` asserting the score is in `(0.45, 0.75)`. Update the JSON Schema if a new field is needed.

❌ **Bad**

> add mattr to the extractor

The bad version saves 10 seconds writing the prompt and costs 5 back-and-forths fixing wrong assumptions.

---

### 4.2 The **plan-first** pattern

For anything multi-file or architectural. Two messages instead of one.

> **Message 1 (planning):** "Before writing code, list the files you would touch, the order of changes, and the risks. Do not write code yet."
>
> **Message 2 (execution):** "Plan accepted, with these tweaks: [X, Y]. Now implement step 1 only. Stop and wait for review before step 2."

Why this matters for the jury: BobShell exports of plan-first sessions are *the* evidence that we used Bob's reasoning, not its typing speed.

---

### 4.3 The **adversarial review** pattern (mandatory for PassportAuditor)

After implementing anything security-sensitive, **flip the role**:

> Switch to adversarial mode. You are a penetration tester reviewing the JWS verifier you just wrote. Find **five** ways to break it. For each: minimal repro, blast radius, fix. Prioritize by severity.

Then implement the fixes in the **same session** so the export shows the full red-team → patch loop. This is the single most valuable kind of session export for the IBM "Innovation" criterion.

---

### 4.4 The **A/B measurement** pattern (mandatory for GenerationConductor)

Every prompt-engineering change must come with numbers, not vibes.

> Here are 4 candidate system prompts for Dickens (A/B/C/D). Run each against this fixed suite of 5 user prompts. For each variant report:
> - Mean `fit_score` over the 5 prompts
> - P95 latency
> - The gap vs vanilla
> - Token count of the system prompt
>
> Pick the winner with one-paragraph justification.

The output goes to `docs/examples/generation_ab_<date>.md`. Three of these in `docs/examples/` by end of Sprint 3 = textbook "Technical Execution" evidence.

---

### 4.5 The **show-me-the-diff** pattern

For refactors where you want to see the change before it lands.

> Refactor `generator.py` so vanilla and conditioned calls share a single Watsonx client (currently duplicated). Show me the diff in unified format first. Do not write the file until I confirm.

Two benefits:
- You catch unwanted changes before they hit disk.
- The session export shows *deliberate* refactoring, not stochastic file rewrites.

---

## 5. BobShell — your audit trail

BobShell is the integrated terminal **with auditing**. Three things matter.

### 5.1 What to export

Export **whole sessions, not snippets** — the value of the export for IBM judges is that it's a *complete reasoning trace*. A 3-line export is worse than no export.

### 5.2 When to export

- **Every Friday before 18:00**: export your week's most substantive session to `bob/sessions/weekN/<your-initial>.md`. Naming: `p1.md`, `p2.md`, `p3.md`.
- **Right after any landmark moment**: an adversarial review that caught a real bug, a successful A/B that moved `fit_score`, a tricky refactor — export immediately while it's fresh, before something newer overwrites the buffer.

### 5.3 Format

Bob's native Markdown export is fine. Add a 3-line YAML frontmatter at the top so we can scan exports later:

```yaml
---
mode: GenerationConductor
sprint: 3
date: 2026-07-17
task: A/B four Dickens system prompts on a fixed 5-prompt suite
outcome: variant C won (+11 fit_score, +0 latency); landed in PR #57
---
```

### 5.4 Target by submission day

| Artifact | Target | Where |
|---|---|---|
| Custom Modes | 4 | `bob/custom-modes/` |
| Weekly session exports | ≥ 12 (3 people × 4 weeks) | `bob/sessions/weekN/` |
| Representative screenshots | ≥ 3 | `bob/screenshots/` |
| Final usage report | 1 | `bob/usage-report.md` |
| PRs that mention Bob in the template | ≥ 70% | each PR body |

---

## 6. A normal day of work with Bob

```
09:00  Pick up issue from Sprint Ready → In Progress (assign yourself).
09:05  Decide which Custom Mode applies (table §3). Open Bob in that mode.
09:10  Start the session with a CTRO prompt (§4.1).
       For anything multi-file, force plan-first (§4.2).
09:20  Iterate. Commit small (Conventional Commits). When Bob proposes
       changes, ask "show me the diff first" (§4.5) before letting it
       write files.
12:00  If the session has hit a milestone (passes a test, completes a
       feature), pause and export it. Save locally for now; you'll
       move it to bob/sessions/weekN/ on Friday.
13:00–14:00 Lunch.
15:00  Open the PR. In the template, fill the "How IBM Bob helped"
       section honestly — name the mode, link the session export if
       you have one. ≥1 reviewer + green CI → squash-merge.
17:30  If you did something security-sensitive today (anything in
       passport/, jwks/, /verify), run an adversarial review (§4.3)
       as a final pass before EOD. Export it.
18:00  End-of-day async daily in the channel.
Friday 18:00  Sprint mini-review. Move your best session of the week
              to bob/sessions/weekN/<initial>.md.
```

---

## 7. Anti-patterns — what NOT to do

❌ **"Hey Bob, fix this"** with no file mentioned. Bob will guess. The guess will be wrong half the time.

❌ **Marathon sessions covering 6 unrelated tasks.** Export is unusable for the jury. Split.

❌ **Spanish prompts.** Every export ends up in the public repo. *"sesión en español, modo StyleExtractor"* tells the IBM jury we ignored our own policy.

❌ **Accepting "this should work" without a test.** Always end a coding session with: *"add a test asserting the change, run it, paste the output."*

❌ **Leaving the default chat as your daily driver.** If the task maps to a Custom Mode (table §3), use the mode. Custom Modes used = jury checkbox.

❌ **Not exporting because "this week was light."** Write a 4-line note in `bob/sessions/weekN/<initial>.md` explaining what you worked on. Empty weeks visible in the repo are worse than light-but-honest weeks.

❌ **Pasting truncated error messages.** Always paste the full stack trace + the failing command + the env (Python version, OS). Bob without ground truth is a fortune cookie.

❌ **Asking Bob to "be creative" on security code.** PassportAuditor mode is paranoid by design — never override it with "yeah but make it less strict".

❌ **Forgetting the PR template's "How IBM Bob helped" line.** If it stays as `<!-- ... -->`, the PR template is broken and CI should flag it. (If it doesn't, that's a CI gap to file in Sprint 1.)

---

## 8. Advanced moves

### 8.1 Loading custom context mid-session

If Bob needs context outside the Custom Mode's preloaded files:

> Load `docs/passport_schema.md` and `ai_pipeline/autoria_ai/schemas/passport.json` into context. Do not summarize. Confirm when ready.

Wait for the confirm — only then ask the real question.

### 8.2 Forcing Bob to challenge you

For design decisions, especially the irreversible ones:

> Steel-man the *opposite* design choice. Then list 3 reasons our current choice is still right despite that steel-man.

If Bob can't find 3 reasons, your design is weaker than you think.

### 8.3 Model switching

Bob can route to different models. Rough heuristic for AutorIA:

| Task type | Preferred model behind Bob |
|---|---|
| Architecture / multi-file reasoning | Best-available large model |
| Bulk code generation in a known pattern | Granite-class model (faster, cheaper) |
| Adversarial / security review | Best-available large model (do not skimp) |
| Doc writing, microcopy | Granite-class is fine |

If your Bobcoins burn rate is high, the GenerationConductor and PassportAuditor sessions are where you *spend*, not the typing-style ones.

### 8.4 Recovering a derailed session

If Bob goes off-track (rewriting files you didn't ask about, inventing dependencies, hallucinating function names):

> Stop. Revert any uncommitted changes. Re-state the task in one sentence. List the files you intend to touch. Wait for confirmation before continuing.

Faster than fighting through 5 more messages.

---

## 9. The screenshots we owe the jury (≥ 3)

By **Sprint 4**, capture and store in `bob/screenshots/`:

1. **A Custom Mode answering a non-trivial multi-file question.** Frame the screenshot so the mode name + the loaded context indicator are visible.
2. **A BobShell session in action**, ideally the adversarial review one that caught something real.
3. **A multi-step plan-first session** showing Bob outlining files before touching them.

Each goes into `bob/usage-report.md` with a one-line caption tying it to a concrete PR.

---

## 10. Weekly Bob checklist (every Friday before 18:00)

- [ ] Export the week's best session to `bob/sessions/weekN/<initial>.md` (with the YAML frontmatter from §5.3).
- [ ] Skim each of your merged PRs this week — did each mention the right Custom Mode in the template? Add a short note in any that didn't.
- [ ] If you tried a new Bob trick that worked, add it to §4 or §8 of this playbook (PR welcome).
- [ ] Note in the channel: which Custom Mode you spent the most time in this week. We track this to balance modes across the team.

---

## 11. FAQ

### "Default chat or Custom Mode for this random question?"
If the question is about *AutorIA's code*, use a mode. If it's a generic *"how do I X in Python"*, default chat is fine — it's faster and won't pollute the mode's context with off-topic chatter.

### "I made a mistake in a session export I already committed."
Don't rewrite history. Open a follow-up PR fixing the markdown (typo, redaction of an accidental secret) with a `docs(bob)` commit referencing the original commit hash.

### "Bob proposed code that uses a library not in `pyproject.toml`."
Reject it and re-ask: *"use only deps already in pyproject.toml; if none works, propose adding one as a Decision Log entry first."* New deps go via 2/3 vote, not via Bob.

### "Bob keeps hallucinating function names."
Two fixes: (1) load the actual file into context (§8.1), (2) ask Bob to grep for the function before assuming it exists.

### "My session is huge and I don't know what to export."
Use `BobShell summarize --since <timestamp>` to get a synthetic recap, then export the *full* session anyway — the recap is for *you*, the export is for the jury.

### "Can Bob run our tests directly?"
Yes — through BobShell. Pattern: *"run `pytest -q ai_pipeline/tests/test_lexical.py`, paste full output, then propose fixes for any failures."* This is the highest-signal kind of session.

### "Do I have to use Bob for *every* commit?"
No — we target ≥ 70% of PRs *meaningfully* assisted by Bob, not 100%. A dependency bump or typo fix is fine without Bob; just don't claim Bob helped if it didn't.

---

## 12. Where to look when stuck

| Problem | Read |
|---|---|
| Don't know which mode applies | §3 of this doc |
| Prompt isn't working | §4 (try CTRO + plan-first) |
| Don't know what to export | §5 |
| Forgot what we promised IBM | `bob/README.md` + `docs/ONBOARDING.md` §9 |
| Custom Mode itself feels off | The mode's own `.md` in `bob/custom-modes/` — refine it via PR |
| Decision conflicts with current behavior | `docs/decision_log.md` is the tiebreaker |

---

> One last thing: **this playbook is meant to be edited.** If you find a pattern that beats one of the five above, add it. If an anti-pattern bit you, document it. The version of this file on submission day should look different from the one you read today — and that itself is a story we tell the jury.
