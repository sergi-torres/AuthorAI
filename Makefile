# AutorIA — common commands.
#
# Windows note: `make` is not installed by default on PowerShell. Either:
#   1) winget install GnuWin32.Make   (or: choco install make / scoop install make)
#   2) use WSL (Ubuntu)
#   3) skip make and run the underlying commands shown in each target by hand
# Decision recorded in docs/decision_log.md.
#
# Usage: `make help` to list targets.

.DEFAULT_GOAL := help
.PHONY: help install install-py install-front keys db-up db-down seed demo \
        dev back front lint format test clean

# ---- Meta -------------------------------------------------------------------

help: ## List all available targets
	@python -c "import re; [print(f'  {m.group(1):<16} {m.group(2)}') for line in open('Makefile') for m in [re.match(r'^([a-zA-Z_-]+):.*?## (.+)', line)] if m]"

# ---- Helpers (cross-platform guards) ----------------------------------------

# Usage: $(call need_dir,ai_pipeline,Sprint 1)
define need_dir
	@python -c "import sys,os; sys.exit('ERROR: $(1)/ not found — scaffold it first ($(2))') if not os.path.isdir('$(1)') else None"
endef

# Usage: $(call need_file,scripts/generate_keys.py,Sprint 1)
define need_file
	@python -c "import sys,os; sys.exit('ERROR: $(1) not found — scaffold it first ($(2))') if not os.path.isfile('$(1)') else None"
endef

# ---- Setup ------------------------------------------------------------------

install: install-py install-front ## Install all deps (Python + spaCy model + frontend)

install-py: ## Install Python deps (ai_pipeline + backend) and the spaCy English model
	$(call need_dir,ai_pipeline,Sprint 1)
	$(call need_dir,backend,Sprint 1)
	pip install -e "ai_pipeline[dev]"
	pip install -e "backend[dev]"
	python -m spacy download en_core_web_lg

install-front: ## Install frontend deps
	$(call need_file,frontend/package.json,Sprint 1)
	cd frontend && npm install

keys: ## Generate the Authorship Passport signing keypair (one-time)
	$(call need_file,scripts/generate_keys.py,Sprint 1)
	python scripts/generate_keys.py

# ---- Local database ---------------------------------------------------------

db-up: ## Start local Postgres + pgvector (Docker)
	$(call need_file,docker-compose.yml,Sprint 1)
	docker compose up -d

db-down: ## Stop the local database
	$(call need_file,docker-compose.yml,Sprint 1)
	docker compose down

seed: ## Seed the DB with the 3 preloaded authors (Austen, Dickens, Poe)
	$(call need_file,scripts/seed_corpus.py,Sprint 1)
	python scripts/seed_corpus.py

# ---- Run --------------------------------------------------------------------

dev: db-up ## Start the DB, then print how to run backend + frontend
	@echo "DB is up. Now open two terminals and run:"
	@echo "   make back     (FastAPI  -> http://localhost:8000)"
	@echo "   make front    (Next.js  -> http://localhost:3000)"

back: ## Run the FastAPI backend (http://localhost:8000)
	$(call need_dir,backend,Sprint 1)
	cd backend && uvicorn app.main:app --reload --port 8000

front: ## Run the Next.js frontend (http://localhost:3000)
	$(call need_file,frontend/package.json,Sprint 1)
	cd frontend && npm run dev

demo: ## Run the AI pipeline end-to-end on the seeded corpus (no web stack)
	$(call need_file,scripts/run_demo.py,Sprint 3)
	python scripts/run_demo.py

# ---- Quality ----------------------------------------------------------------

lint: ## Lint everything (Ruff + ESLint)
	ruff check .
	$(call need_file,frontend/package.json,Sprint 1)
	cd frontend && npm run lint

format: ## Format everything (Black + Prettier)
	black .
	ruff check . --fix
	$(call need_file,frontend/package.json,Sprint 1)
	cd frontend && npx prettier --write .

test: ## Run tests (pytest + frontend)
	pytest -q
	$(call need_file,frontend/package.json,Sprint 1)
	cd frontend && npm test --if-present

# ---- Housekeeping -----------------------------------------------------------

clean: ## Remove caches and build artifacts
	@echo "Cleaning Python + Node caches..."
	-python -c "import shutil,glob; [shutil.rmtree(p, ignore_errors=True) for p in glob.glob('**/__pycache__', recursive=True)]"
	-python -c "import shutil; shutil.rmtree('.pytest_cache', ignore_errors=True); shutil.rmtree('.ruff_cache', ignore_errors=True)"
	-python -c "import shutil; shutil.rmtree('frontend/.next', ignore_errors=True)"

# Note: `make dev` would need to run db-up + back + front in parallel, which is
# awkward and not portable across shells. Run them in 3 terminals instead:
#   make db-up   then   make back   then   make front
