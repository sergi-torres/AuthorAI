# Contributing to AutorIA

> The day-to-day working guide. For the bigger picture (challenge, product, roles), read [`docs/ONBOARDING.md`](docs/ONBOARDING.md). For the locked product scope, read [`docs/MVP.md`](docs/MVP.md).
> This is the **operational reference**: how we set up, work a normal day, branch, commit, review, use the backlog, run our tools, and which language goes where.
>
> _Language note: this guide is in English because it's a public artifact (judges read it). Our voice/chat channel is Spanish. See §9._

---

## TL;DR (the 10-second version)

1. Pick an issue from **Sprint Ready** → move it to **In Progress** → assign yourself.
2. `git checkout main && git pull` → `git checkout -b feat/<module>-<desc>`.
3. Work (with IBM Bob). Commit small, in [Conventional Commits](#5-commits), in English.
4. Format + lint + test locally before pushing.
5. Push → open a PR (`Closes #N`) → fill the template → move issue to **In Review**.
6. A teammate reviews within 24h. CI must be green.
7. Squash-merge to `main` → delete branch → issue auto-moves to **Done**.

**Golden rules**: no work without an issue · no direct push to `main` · no merging your own PR without review.

---

## 1. First-time setup (do once per machine)

> Prerequisites: **Git**, **Python 3.11**, **Node 20+**, **Docker Desktop**, and a code editor (Cursor / VS Code).

```powershell
# 1. Clone
git clone https://github.com/<owner>/autorIA.git
cd autorIA

# 2. Environment variables
copy .env.example .env        # PowerShell (use `cp` on macOS/Linux)
#    → fill in real values (Watsonx API key, DB URL, etc.)

# 3. Python deps (per package: ai_pipeline and backend)
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell  (source .venv/bin/activate on macOS/Linux)
pip install -e ai_pipeline[dev]
pip install -e backend[dev]
python -m spacy download en_core_web_lg

# 4. Frontend deps
cd frontend && npm install && cd ..

# 5. Passport signing keys (one-time, never commit the private key)
python scripts/generate_keys.py

# 6. Local database (Postgres + pgvector via Docker)
docker compose up -d

# 7. Seed the 3 demo authors
python scripts/seed_corpus.py
```

Editor extensions (highly recommended — auto-format on save): **Ruff**, **Black Formatter**, **Prettier**, **Python**. See §8.4.

> ⚠️ Some of the above (`.env.example`, `scripts/`, `docker-compose.yml`, the actual `pyproject.toml` files inside `ai_pipeline/` and `backend/`) are landed incrementally during **Sprint 1**. Until those exist the corresponding `make` targets will fail with a clear error. This section describes the steady state once Sprint 1 scaffolding is in place.

---

## 2. A day of work (the normal loop)

A concrete walkthrough of an average working day. This is the routine everyone follows.

### ☀️ Start of day (~10 min)
1. **Read the channel** — catch up on the async daily messages and any blockers.
2. **Sync your `main`**:
   ```powershell
   git checkout main
   git pull
   ```
3. **Post your daily** (2 lines in the channel): what you did yesterday / what you'll do today / any blocker.
4. **Open the board** (🏃 Current Sprint view). Confirm what you're working on.

### 🛠️ Pick up work
5. **Take an issue** from `Sprint Ready` (or continue your `In Progress` one). Move it to **In Progress** and self-assign. If there's no issue for what you're about to do, **create it first** (30 seconds).
6. **Create a branch** off fresh `main`:
   ```powershell
   git checkout -b feat/ai-lexical-extractor
   ```

### 💻 While coding
7. **Work with IBM Bob** — use the relevant Custom Mode (StyleExtractor / GenerationConductor / StudioComposer / PassportAuditor), not plain autocomplete. Speak to Bob in English.
8. **Commit small and often** as sub-steps work (see §5). Example rhythm:
   ```powershell
   git add ai_pipeline/autoria_ai/extractor/lexical.py
   git commit -m "feat(ai): add TTR and MATTR-500 to lexical extractor"
   ```
9. **Run your tools as you go** (see §8):
   ```powershell
   ruff check . --fix     # lint + autofix
   black .                # format
   pytest -q              # tests
   ```

### 📤 Ship it
10. **Final local check** before pushing — format, lint, tests all green.
11. **Push** your branch:
    ```powershell
    git push -u origin feat/ai-lexical-extractor
    ```
12. **Open a PR** (`gh pr create` or via web). Fill the template, include `Closes #N`, note which Bob mode helped. Move the issue to **In Review**.
13. **Ping the team** in the channel: "PR up for #42, ready for review".

### 👀 Review others
14. **Review teammates' open PRs** (within 24h). A quick review unblocks them. Approve, or request specific changes.

### 🌙 End of day (~5 min)
15. **Merge anything approved + green** (squash-merge), delete the branch.
16. **Update the board** — anything finished is `Done`, anything in flight stays `In Progress`.
17. **Leave a note in the channel** if you finish mid-task, so your backup knows the state.

> If you're **blocked >2h**, don't sit on it — ping immediately, don't wait for tomorrow's daily.

---

## 3. Repository model

- **Monorepo**: `ai_pipeline/` (P2), `backend/` (P3), `frontend/` (P1), plus `bob/`, `corpus/`, `docs/`, `infra/`, `scripts/`.
- **`main` is protected**: merges only via approved PR + green CI.
- **Owners**: each module has a single primary owner (see `docs/ONBOARDING.md` §3). Touching someone else's module? Tell them in the channel first (one line).

---

## 4. Branches

### When to create a branch
- **One branch per issue.** As soon as you start work, branch off the latest `main`.
- Never commit directly to `main`. Never reuse a branch for an unrelated issue.

### Naming convention
```
<type>/<module>-<short-description>
```

| Type | Use for |
|---|---|
| `feat/` | new functionality |
| `fix/` | bug fixes |
| `docs/` | documentation only |
| `chore/` | deps, config, tooling (non-functional) |
| `refactor/` | code change with no behavior change |
| `test/` | adding or fixing tests |

Modules: `ai`, `back`, `front`, `bob`, `infra`, `docs`, `crypto`, `db`, `demo`.

**Examples**
```
feat/ai-lexical-extractor
feat/front-style-radar
fix/crypto-jwks-rotation
docs/update-onboarding
chore/deps-bump-spacy
```

### Lifecycle
```powershell
git checkout main; git pull               # always start fresh
git checkout -b feat/ai-lexical-extractor
# ... work ...
git push -u origin feat/ai-lexical-extractor
# ... open PR, get review, merge ...
git checkout main; git pull
git branch -d feat/ai-lexical-extractor   # delete local after merge
```

If your branch lives >1 day, rebase on `main` to avoid conflict pileups:
```powershell
git fetch origin
git rebase origin/main
git push --force-with-lease
```

---

## 5. Commits

### When to commit
- **Small and often.** One commit = one logical change. If you can't describe it in one line, split it.
- Commit when a sub-step works (a test passes, a function is complete), not in one giant end-of-day blob.
- Don't commit broken code to a shared branch. WIP commits are fine on your own feature branch but get squashed on merge.

### Format — Conventional Commits (mandatory)
```
<type>(<scope>): <imperative, lowercase, no period>

[optional body explaining WHY, not what]
```

- **Types**: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`
- **Scopes**: `ai`, `back`, `front`, `bob`, `infra`, `docs`, `crypto`, `db`, `demo`
- **In English**, imperative mood ("add", not "added"/"añade").

**Good**
```
feat(ai): add lexical features extractor with TTR and MATTR
fix(crypto): reject JWS tokens with alg=none
docs(bob): export week-2 sessions for P1 and P3
chore(deps): bump sentence-transformers to 3.1.0
test(ai): add fixtures for distinctive vocab extractor
refactor(back): extract watsonx client into its own module
```

**Bad**
```
update                  # says nothing
fix bug                 # which bug?
arreglo del extractor   # Spanish
WIP                     # don't merge this to main
asdf                    # no
```

---

## 6. Pull Requests

### When to open
- When the issue's work is complete and CI passes locally (format + lint + tests).
- Draft PRs are welcome earlier for early feedback — mark them as **Draft**.

### ✅ Before you open a PR (run through this, in order)

Don't open the PR until every step passes — it saves your reviewer's time and keeps CI green.

1. **Sync with `main`** so you're not reviewing stale code:
   ```powershell
   git fetch origin
   git rebase origin/main      # resolve any conflicts now, not in the PR
   ```
2. **Format** the code:
   ```powershell
   black .                     # Python
   cd frontend && npx prettier --write . && cd ..   # TS
   ```
3. **Lint** (and autofix what's safe):
   ```powershell
   ruff check . --fix          # Python
   cd frontend && npm run lint && cd ..             # TS
   ```
4. **Test** — happy path must pass:
   ```powershell
   pytest -q                   # Python
   cd frontend && npm test --if-present && cd ..    # TS
   ```
   (Or just `make lint && make test` if you have `make`.)
5. **Self-review your diff** — read it top to bottom:
   ```powershell
   git diff origin/main...HEAD
   ```
   Remove debug prints, commented-out code, `TODO`s you meant to finish, and anything unrelated to the issue.
6. **Check the side-effects** — if you changed any of these, update the matching artifact (it's in the PR checklist):
   - StyleProfile / Passport schema → bump the version + update the schema doc
   - a new env var → add it to `.env.example`
   - an endpoint → update `docs/api_contract.yaml`
7. **No secrets** — confirm no `.env`, keys, tokens, or generated files are staged (`git status`).
8. **Commits are clean** — Conventional Commits, in English. Squash noise locally if needed.
9. **Note how IBM Bob helped** — you'll need it for the PR template (and the README later).

If all 9 pass, push and open the PR.

### Size
- **Aim for ≤ 400 changed lines.** Large PRs don't get reviewed properly. Split big work into stacked PRs.

### Rules
- **Title = Conventional Commit** (e.g. `feat(ai): add lexical features extractor`).
- **Body** must include: what + why, `Closes #N`, screenshots for UI changes, which Bob Custom Mode helped.
- **Every PR closes at least one issue.**
- **At least 1 teammate approves** before merge. Never merge your own PR unreviewed.
- **CI must be green** (lint + tests).
- **Reviews within 24h.** Sitting on a teammate's PR >24h means you're blocking them.
- **Squash-merge** by default. Squash message = PR title (clean history).
- **Delete the branch** after merge.

### Opening a PR with the CLI
```powershell
gh pr create            # opens editor pre-filled with the PR template
# or
gh pr create --web      # opens the browser with the template
```
> Don't use `gh pr create --fill` — it skips the template (fills body from commits).

### The PR template (auto-loaded from `.github/PULL_REQUEST_TEMPLATE.md`)
When you open a PR, GitHub pre-fills the description with our template. Replace the comments and tick the boxes:
- [ ] Tests pass locally
- [ ] Lint passes
- [ ] Schema bumped + docs updated (if StyleProfile/Passport changed)
- [ ] `.env.example` updated (if new env var)
- [ ] API contract updated (if new/changed endpoint)
- [ ] Bob Custom Mode noted
- [ ] Reviewed by ≥1 teammate

---

## 7. Backlog & GitHub Projects

Our board is **"AutorIA July Sprint"**, linked to this repo.

### Issue lifecycle (the Status field)
```
Backlog → Sprint Ready → In Progress → In Review → Done
```
- **Backlog**: captured, not scheduled.
- **Sprint Ready**: scheduled into a sprint, ready to pick.
- **In Progress**: someone is actively working it (has an assignee).
- **In Review**: PR open, awaiting review.
- **Done**: PR merged (auto-set via `Closes #N`).

### Custom fields on every issue
| Field | Values |
|---|---|
| **Sprint** | Sprint 0 / 1 / 2 / 3 / Buffer / Backlog |
| **Size** | XS (<2h) / S (2-4h) / M (4-8h) / L (1-2d) / XL (2-3d) |
| **Module** | ai_pipeline / backend / frontend / bob / docs / infra / demo |
| **Priority** | P0 blocker / P1 must / P2 should / P3 nice |

Plus a **Milestone** (the sprint with its real due date).

### Rules of the board
1. **No work without an issue.** Starting something? Create the issue first (30s).
2. **One assignee per issue.** Needs pairing? Note `Pair with @user` in the body.
3. **In Progress > 3 days?** Mark `blocked` or split it.
4. **Unplanned work?** Create a retroactive issue so the board reflects reality.
5. **No moving to Done without a merge.** `In Review` is a mandatory step.
6. **At Sprint end review**, unfinished issues move to next sprint or back to Backlog — never silently dragged.

### Creating an issue (CLI)
```powershell
gh issue create `
  --repo <owner>/autorIA `
  --title "ai: add MATTR-500 to lexical extractor" `
  --body  "Add Moving-Average TTR (window=500). Acceptance: output in [0,1], test on Dickens corpus." `
  --label "ml,size:S,prio:P1" `
  --milestone "Sprint 1 — Foundation + StyleProfile" `
  --assignee @me
```
Then add it to the Project and fill `Sprint`, `Size`, `Module`, `Priority`.

### Labels
`infra` `backend` `frontend` `ml` `bob` `docs` `demo` · `size:XS|S|M|L|XL` · `prio:P0|P1|P2|P3` · `bug` `blocked`

---

## 8. Dev tools — how to use them

### 8.1 Python — Ruff + Black

- **Ruff** = linter (unused imports, bugs, bad practices) + import sorting. Very fast.
- **Black** = opinionated formatter. No style debates — Black decides.

```powershell
# Setup (once, in the active venv)
pip install ruff black

# Daily usage (run from ai_pipeline/ or backend/)
ruff check .            # show problems
ruff check . --fix      # auto-fix what's safe (imports, etc.)
black .                 # format everything
```

Config lives in each package's `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]

[tool.black]
line-length = 100
target-version = ["py311"]
```
> Keep `line-length = 100` identical in both so they don't fight.

### 8.2 TypeScript — ESLint + Prettier

- **ESLint** = linter (TS/React errors, hooks misuse, unused vars). Comes preconfigured by `create-next-app`.
- **Prettier** = formatter (the Black of JS/TS).

```powershell
# Setup (after create-next-app)
cd frontend
npm install --save-dev --save-exact prettier
npm install --save-dev eslint-config-prettier

# Daily usage
npm run lint                  # ESLint
npx prettier --write .        # format
npx prettier --check .        # check only (CI)
```

`frontend/.prettierrc`:
```json
{ "semi": true, "singleQuote": false, "printWidth": 100, "tabWidth": 2 }
```
And add `"prettier"` last in `extends` in `.eslintrc.json` so ESLint and Prettier don't clash:
```json
{ "extends": ["next/core-web-vitals", "prettier"] }
```

### 8.3 Makefile — shortcuts (⚠️ Windows note)

The `Makefile` is just shortcuts so you don't memorize long commands.

> **`make` is not installed on Windows/PowerShell by default.** Three options:
> 1. **Install it**: `winget install GnuWin32.Make` (or `choco install make` / `scoop install make`) — simplest.
> 2. **Use WSL** (Ubuntu) — good if you'll deploy on Linux anyway.
> 3. **Skip the Makefile** — run the underlying commands directly.
>
> Team decision: pick one and note it in `docs/decision_log.md`.

If you have `make`:
```powershell
make help      # list available targets
make install   # install all deps
make dev       # run DB + backend + frontend
make lint      # ruff + eslint
make format    # black + prettier
make test      # pytest + npm test
```

### 8.4 Editor integration (saves the most time)

In Cursor / VS Code, install: **Ruff** (`charliermarsh.ruff`), **Black Formatter** (`ms-python.black-formatter`), **Prettier** (`esbenp.prettier-vscode`), **Python** (`ms-python.python`).

Commit a shared `.vscode/settings.json`:
```json
{
  "editor.formatOnSave": true,
  "[python]": { "editor.defaultFormatter": "ms-python.black-formatter" },
  "[typescript]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "[typescriptreact]": { "editor.defaultFormatter": "esbenp.prettier-vscode" }
}
```

### 8.5 (Recommended) pre-commit hook

Runs Ruff + Black automatically before each commit, so unformatted code never lands:
```powershell
pip install pre-commit
# create .pre-commit-config.yaml, then:
pre-commit install
```
This enforces our "lint passes before the PR" rule automatically.

### 8.6 Conventions

- Python 3.11, type hints everywhere, `pydantic` for data models.
- Frontend: components PascalCase, hooks `useX`, **UI strings only via `lib/i18n/en.ts`** (never hardcoded).
- No secrets in code. `.env` is gitignored. Private keys live in `keys/` (gitignored).

---

## 9. Language policy

> Everything is **English** — code, docs, app UI, demo video, *and the generated literary text*. The only Spanish left in the project is our **internal team chat**.

| Element | Language |
|---|---|
| Code, comments, var/function names | English |
| Commit messages, branch names | English |
| PR & issue titles/bodies | English |
| `README`, `docs/`, `CONTRIBUTING`, decision log | English |
| IBM Bob sessions (chat with Bob) | English |
| API errors, logs, JSON keys | English |
| **Product UI strings** | **English** (via `frontend/lib/i18n/en.ts`) |
| **Demo video voice + on-screen text** | **English** |
| **Generated literary text** (model output) | **English** (English authors: Austen, Dickens, Poe) |
| Prompts/system prompts sent to Watsonx | **English** |
| Internal team chat | Spanish |

---

## 10. Sprints & ceremonies

Each sprint is 7-10 days (Sprint 1 is 10 days, Sprints 2-3 are 7 days).

| When | What | Mode |
|---|---|---|
| Sprint kickoff | Sprint kick — pick 3-5 issues, move to In Progress | Async |
| Mon–Fri | Daily — 2 lines: done / today / blockers | Async |
| Friday 18:00 | Mini-review | Sync, 15 min |
| Sprint end (Tuesday 18:00) | Sprint review + planning | Sync, 30-40 min |
| Per sprint | 1 pair session on a critical piece (two in Sprint 1) | Sync, 2h |

Communication: if you can write it, don't call. If it takes >10 min in writing, call. Blocked >2h? Ping immediately.

---

## 11. Definition of Done (per issue)

- [ ] Code merged to `main` via reviewed PR
- [ ] Happy-path tests pass
- [ ] Lint + format pass
- [ ] Module docs updated
- [ ] Schema/version bumped if StyleProfile or Passport changed
- [ ] API contract updated if endpoints changed
- [ ] Bob usage noted in the PR

---

## 12. Quick Do / Don't

**Do**
- ✅ Create an issue before starting
- ✅ Branch per issue, Conventional Commits, small PRs
- ✅ Format + lint + test before pushing
- ✅ Review teammates' PRs within 24h
- ✅ Use Bob daily and note it on PRs
- ✅ Keep UI strings in `i18n/en.ts`
- ✅ Write decisions to `docs/decision_log.md`

**Don't**
- ❌ Push directly to `main`
- ❌ Merge your own PR unreviewed
- ❌ Open PRs >800 lines
- ❌ Touch another module without a heads-up
- ❌ Commit `.env`, keys, or generated files
- ❌ Write commits/PRs/issues/Bob sessions in Spanish
- ❌ Re-litigate the locked MVP scope
- ❌ Submit at 23:59 on July 31 (we submit at noon Spain time)

---

> Something unclear? Raise it in the channel **today** — improving this guide before July 1 is free; doing it mid-sprint costs time.
