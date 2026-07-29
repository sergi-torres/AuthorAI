# Local development — reproducible setup and known traps

> **Scope** (#101): how to bring `ai_pipeline` + `backend` up on a dev machine
> reproducibly, whether real parity with the Railway deploy image is needed,
> and the known divergences between "runs on my machine" and "runs on
> Railway" so a local measurement is never mistaken for a deploy one.
>
> **Out of scope**: the Railway deploy image itself and the Vercel frontend
> deploy — both live in `docs/DEPLOYMENT.md` (WO-02 / #83).

---

## 1. Context and decision

**Decided 2026-07-28**: the target deploy is **Vercel (frontend) + Railway
(backend)** — see `docs/decision_log.md`. A fully containerised, Railway-parity
local stack is explicitly **not** pursued: the existing dev `.venv` workflow
(`make install-py` / `make install-front`) is accepted as good enough for
day-to-day feature work, on the condition that its divergences from the
deploy target are written down (this document) instead of silently assumed
away. Nothing in the Sprint Definition of Done depends on a local deploy, so
this is priority: low, and does not block the July 31 submission.

If a full container-parity local stack is ever wanted (e.g. to debug a
Railway-only failure), start from `railway.toml`'s `buildCommand` and
`requirements-deploy.txt` and run them inside a `linux/amd64` container —
that is the actual deploy target, not a docker-compose approximation of it.

---

## 2. Reproducible local setup

```bash
# Python deps for both packages + the spaCy model (not on PyPI, see below)
make install-py
#   = pip install -e "ai_pipeline[dev]"
#     pip install -e "backend[dev]"
#     python -m spacy download en_core_web_lg

# Frontend deps
make install-front
```

Two things `make install-py` gets right that are easy to get wrong by hand:

- **`en_core_web_lg` is not a PyPI package.** `pip install en_core_web_lg`
  404s. It must be fetched with `python -m spacy download en_core_web_lg`,
  which resolves the model release matching whichever spaCy version was just
  installed. Installing spaCy and the model as two unrelated steps (e.g. a
  stale model left over from a previous spaCy major) fails at *runtime*
  (`OSError [E050]` from `autoria_ai.generator._ensure_models()`), not at
  install time — see `.github/workflows/ci.yml`'s spaCy/model version guard
  for the same class of failure caught in CI.
- **`sentence-transformers`' `all-mpnet-base-v2` (~418 MB) downloads from the
  HuggingFace hub on first use**, cached under `~/.cache/huggingface`
  afterwards (see `autoria_ai/embedder.py` — loaded lazily, not at import,
  #104). The first `pytest ai_pipeline/tests` or first `/api/generate` after
  a fresh `.venv` pays this once per cache location, not once per run.

Everything else (`make keys`, `make seed`, `make back` / `make front`) is
unchanged from `README.md`'s Getting Started.

---

## 3. Known divergences between local and deployed

These are measured facts, not guesses — record any new one you hit here
rather than rediscovering it later.

### 3.1 A local `pip install` size means nothing about the Railway image

`requirements-deploy.txt` resolves to a **very different** dependency set
depending on the platform doing the resolving, because PyPI dependency
metadata carries environment markers (`sys_platform`, `platform_system`) that
`pip` evaluates against **the machine running `pip`**, not the deploy target:

- Resolved **on Windows or macOS** (a normal dev machine): `torch` pulls its
  CPU build family with **zero** `nvidia-*` / `triton` packages — a few
  hundred MB.
- Resolved **on Linux x86_64 without the `+cpu` pin** (Railway's actual
  platform): the same file would pull the CUDA build of `torch`, which
  hard-depends on 15 `nvidia-*` wheels plus `triton` — **~2.6 GB** of GPU
  runtime that Railway's plan cannot even build, let alone run (AutorIA never
  touches a GPU). This is exactly the regression WO-02 / #83 fixed by pinning
  `torch==2.13.0+cpu` from the PyTorch CPU wheel index — see
  `requirements-deploy.txt`'s header for the exact measured byte counts.

**The trap**: `pip install --dry-run --platform manylinux2014_x86_64 ...` run
from a Windows/macOS shell does **not** make `pip` believe it is Linux for
marker-evaluation purposes — `--platform` only affects wheel *tag* selection,
not `sys_platform` / `platform_system` marker evaluation, which is still done
against the *host* interpreter. So this command reports "no `nvidia-*`
packages" on a Windows machine even when the real Linux resolution would pull
2.6 GB, and a local check can wrongly declare the deploy image healthy.

**The correct check** — cross-resolve as if running on the actual deploy
platform:

```bash
pip install uv   # one-time
uv pip compile --python-platform x86_64-unknown-linux-gnu requirements-deploy.txt
```

This is the exact command WO-02 / #83 used to produce the byte counts in
`requirements-deploy.txt`'s header, and the one to re-run after touching any
dependency in that file, `ai_pipeline/pyproject.toml`, or
`backend/pyproject.toml` — a local `pip install` will not catch a regression
of this shape.

### 3.2 A `.venv` with editable installs can silently import the wrong tree

`pip install -e "ai_pipeline[dev]"` / `pip install -e "backend[dev]"` write
`__editable__.autoria_ai.pth` / `__editable__.autoria_backend.pth` (or an
`.egg-link`, on older pip) into `.venv/Lib/site-packages` (POSIX:
`.venv/lib/pythonX.Y/site-packages`). Those files contain an **absolute path
to the checkout they were created from** — not a relative one, and not one
scoped to whatever directory you happen to run Python from.

**The trap**: if you `git worktree add` a second checkout to work on a branch
in parallel and reuse (or copy) the main checkout's `.venv` — or point a new
one at the same interpreter search path — `import autoria_ai` / `import app`
still resolves to the **main checkout's** files, regardless of which
worktree's `pytest` you invoked. Tests report green against code you never
touched, and edits in the worktree are silently never exercised.

**Mitigation**: create a fresh `.venv` (and re-run `make install-py`) inside
every worktree — never copy or symlink one across checkouts. If a test run
from inside a worktree looks suspiciously unaffected by a change you just
made there, check what an editable-install marker actually points at:

```bash
# .venv/Lib/site-packages on Windows, .venv/lib/pythonX.Y/site-packages on POSIX
type .venv\Lib\site-packages\__editable__.autoria_ai.pth        # Windows
cat  .venv/lib/python3.11/site-packages/__editable__.autoria_ai.pth  # POSIX
```

If the path printed is not the checkout you are standing in, that `.venv`
belongs to a different tree.

### 3.3 `.venv` tooling versions can drift from CI

`ruff` and `black` are pinned in three places that must move together:
`requirements-dev.txt`, `.pre-commit-config.yaml`, and
`.github/workflows/ci.yml` (job `lint-python`). A `.venv` that installed them
at a different point in time (or via a different path than
`requirements-dev.txt`) can drift from all three — `black --check .` then
passes locally and fails in CI, because formatting rules change between
majors.

**Check before trusting a local lint/format pass**:

```bash
pip show ruff black   # compare the two "Version:" lines against requirements-dev.txt
```

If they differ, `pip install -r requirements-dev.txt` (the shared pin) fixes
it — do this after every `git pull` that touches `requirements-dev.txt`,
`.pre-commit-config.yaml`, or the CI workflow, not just once at setup time.

---

## 4. Summary — what to trust locally, what not to

| Question | Trust the `.venv` locally? |
| --- | --- |
| "Does spaCy/sentence-transformers/the extractor logic work?" | Yes |
| "Do the happy-path tests pass?" | Yes (inside the checkout that owns the `.venv` — see §3.2) |
| "Will this fit in the Railway image / avoid pulling `torch`+CUDA?" | **No** — use `uv pip compile --python-platform x86_64-unknown-linux-gnu` (§3.1) |
| "Is my formatting/lint result what CI will report?" | Only if `pip show ruff black` matches `requirements-dev.txt` (§3.3) |
| "Did my worktree change actually get exercised?" | Only if that worktree has its own `.venv` (§3.2) |
