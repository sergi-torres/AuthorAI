# Auditoría de issues cerradas — autorIA

> **Fecha:** 2026-07-27 · **Alcance:** 29 issues cerradas (`stateReason: COMPLETED`), rama `main` @ `6bf05f9` · **Método:** lectura completa de los documentos rectores → inventario de criterios de aceptación desde los cuerpos de las issues → localización y lectura del código → ejecución real de lint/tests/roundtrip criptográfico · **Naturaleza:** solo lectura. No se ha modificado código, no se ha tocado GitHub, no se ha abierto ningún PR.
>
> Las 14 issues abiertas quedan fuera de alcance y no se han leído.

---

## Contexto del proyecto (Paso 0)

**Qué construye.** AutorIA extrae la "DNA estilística" de un autor a partir de su corpus, genera texto condicionado a esa voz con IBM Watsonx (Llama 3.3 70B), lo compara lado a lado contra el mismo modelo sin condicionar ("vanilla"), y emite un **Authorship Passport** firmado en JWS/ES256 que documenta qué fue IA, con qué modelo y desde qué fuentes — el ángulo de cumplimiento del **EU AI Act Art. 50**.

**Módulos.** Monorepo con cinco piezas: `ai_pipeline/` (extractores léxico/sintáctico/estilístico, vocabulario TF-IDF, embeddings, conditioner, generator, fit_scorer, passport build/sign/verify), `backend/` (FastAPI: `/health`, `/api/authors*`, `/api/generate`, `/api/passports/verify`, `/.well-known/jwks.json`), `frontend/` (Next.js 14: selector de autores, pantalla studio con Style DNA + side-by-side, `/verify`), `infra/` (migraciones Supabase/pgvector) y `scripts/` (`seed_corpus.py`, `precompute_umap.py`, `generate_keys.py`), más `bob/` y `corpus/`. El pipeline es una **librería importada en proceso** por el backend, no un servicio (`docs/architecture.md:110-112`).

**Definition of Done del MVP,** citado literalmente (`docs/MVP.md:490-504`):

> `docs/MVP.md:492` — "The project is "done" when **all** of these are true:"
> `docs/MVP.md:494` — "[ ] 3 preloaded authors, each with a computed and visualizable StyleProfile"
> `docs/MVP.md:495` — "[ ] Side-by-side generation works end-to-end in **<8s P95**"
> `docs/MVP.md:496` — "[ ] Authorship Passport issued, downloaded, and **verifies** with a valid signature"
> `docs/MVP.md:497` — "[ ] Visible vanilla-vs-AutorIA difference: **≥3/3 non-technical humans** identify it in **≤5s** (Sprint 1 gate)"
> `docs/MVP.md:498` — "[ ] Live 90s demo rehearsed **5 times without failure** (Sprint 3)"
> `docs/MVP.md:499` — "[ ] Public repo with a complete README including the "How we used IBM Bob" section"
> `docs/MVP.md:500-501` — "[ ] 4 Custom Modes documented in `bob/custom-modes/`" · "[ ] ≥12 BobShell exports in `bob/sessions/`"
> `docs/MVP.md:502-504` — vídeo de 3 min en YouTube, curso IBM SkillsBuild, envío antes del 31-jul 12:00.

**Documento rector por área** (usado para resolver conflictos entre el texto de la issue y la especificación):

| Área | Documento que manda |
|---|---|
| Endpoints, códigos de estado, formas de request/response | `docs/api_contract.yaml` (LOCKED) |
| Features de estilo, fórmulas, rangos, pesos de `fit_score` | `docs/style_features.md` |
| Passport: payload, JWS, JWKS, algoritmo de verificación | `docs/passport_schema.md` |
| Esquema de BD, índices, cascadas | `docs/erd.md` + `infra/supabase/migrations/0001_init.sql` |
| Pantallas, tokens de color, componentes, i18n | `docs/design-system.md` |
| Alcance y finish line | `docs/MVP.md` |
| Cableado entre módulos | `docs/architecture.md` |
| Comandos de instalación / test / lint | `README.md`, `CONTRIBUTING.md`, `Makefile` |
| Despliegue y variables de entorno | `docs/DEPLOYMENT.md` + `.env.example` |
| Cambios de alcance ya votados | `docs/decision_log.md` |

Donde el cuerpo de una issue contradice a su documento rector (p. ej. #24 pide pesos 20/20/20/20/20 y `style_features.md:389-396` fija 0.35/0.20/0.15/0.15/0.15), **manda el documento** y así se ha juzgado.

---

## Verificación básica

Ninguna de las 29 issues cerradas tiene **ni un solo comentario** (`gh issue list --state closed --json number,comments` devuelve vacío para todas). No existen promesas de cierre documentadas en el tracker: todo lo declarado vive en títulos de PR y mensajes de commit.

| Comprobación | Comando | Resultado real |
|---|---|---|
| Lint Python | `ruff check .` | **`All checks passed!`** (ruff 0.15.21 local; CI fija 0.15.20; `requirements-dev.txt:6` fija **0.6.9** — desalineado, pero pasa) |
| Formato Python | `black --check .` | **`All done! 59 files would be left unchanged.`** (black 26.5.1 local = CI; `requirements-dev.txt:7` fija **24.8.0** — desalineado, pero pasa) |
| Tests backend | `pytest backend/tests` | **❌ ERROR DE COLECCIÓN — la suite no llega a ejecutarse.** `ImportError: cannot import name '_RETRY_DELAYS_SECONDS' from 'app.services.watsonx_client' (unknown location)` · `Interrupted: 1 error during collection` |
| Tests backend (aislando el causante) | `pytest backend/tests --ignore=tests/test_generate.py` | `1 failed, 60 passed in 89.69s` — el fallo es `test_generate_live_watsonx` |
| Tests backend (solo el causante) | `pytest backend/tests/test_generate.py` | `37 passed` |
| Watsonx en vivo | (dentro del test anterior) | `Status code: 403 {"code":"no_associated_service_instance_error","message":"project_id 614cdac6-…-c00773883b4c is not associated with a WML instance"}` tras 4 intentos |
| Tests pipeline | `pytest ai_pipeline/tests` | **`214 passed, 3 skipped in 26.45s`** (los 3 skips: `DATABASE_URL not set - skipping live-DB tests`, `test_embedder.py:216,294,357`) |
| Tests frontend | `cd frontend && npm run test` | **`Test Files 3 passed (3) · Tests 43 passed (43)`** |
| Typecheck frontend | `npx tsc --noEmit` | **exit 0**, sin errores |
| Lint frontend | `npx eslint .` | **exit 0**, sin errores |
| Corpus | `python scripts/seed_corpus.py --dry-run` | **`OK`** (exit 0) — austen 643 533 tokens/4 ficheros, dickens 1 147 910/4, poe 259 034/2 |
| Passport roundtrip | build → sign → `POST /api/passports/verify` (TestClient) | `VERIFY valid= True errors= []` |
| Passport manipulado | firma alterada → verify | `valid= False [{'code': 'invalid_signature'}]` |
| Passport `alg:none` | cabecera forzada → verify | `valid= False [{'code': 'unsupported_algorithm', 'message': "Algorithm 'none' is not accepted; only ES256 is allowed"}]` |
| JWKS | `GET /.well-known/jwks.json` (TestClient) | `200 · Cache-Control: public, max-age=3600 · kid=autoria-2026-07 · alg=ES256` |

**Lo que CI ejecuta realmente** (`.github/workflows/ci.yml`): dos jobs, `lint-python` (ruff + black) y `lint-frontend` (`npm ci`, `npm run lint`, `npx tsc --noEmit`, `npm run test`). **No hay ningún job de pytest.** El fichero solo se dispara `on: pull_request: branches: [main]` — nunca en push a `main`. Consecuencia directa: el error de colección de `backend/tests` **nunca se ha comprobado en remoto**, y por eso lleva sin detectarse.

**Nota sobre las dos trampas conocidas.** (a) El desajuste de versiones de black/ruff es real pero **no** es la causa de ningún fallo: con las versiones instaladas localmente (idénticas a las de CI salvo el patch de ruff) ambos comandos pasan limpios. (b) Lo que sí es peor que un test rojo — y ocurre — es el fallo de colección: la afirmación "los tests del backend pasan" es **falsa** hoy.

---

## Tabla de veredictos

| Issue | Título | Módulo | Veredicto | WO | Evidencia |
|---|---|---|---|---|---|
| #2 | Repo + monorepo, Vercel + Railway | infra | ⚠️ Parcial | WO-01, WO-02 | `frontend/src/lib/api.ts:30` lee `NEXT_PUBLIC_API_URL`; `.env.example:33` y `docs/DEPLOYMENT.md:62` definen `NEXT_PUBLIC_API_BASE_URL`. `railway.toml` `buildCommand = "pip install -r backend/requirements.txt"`, fichero que no incluye spacy/sentence-transformers/sqlalchemy/asyncpg/pgvector |
| #3 | Supabase + pgvector + migración inicial | infra | ✅ Verificado | — | `infra/supabase/migrations/0001_init.sql` crea las 5 tablas + `chunks_embedding_hnsw_idx` con `m=16, ef_construction=64`; 0002 refuerza el índice, 0003 añade `content_hash`. Aplicación al Supabase real: no verificable aquí (sin `DATABASE_URL`) |
| #4 | GitHub Actions: lint + tests en cada PR | infra | ⚠️ Parcial | WO-03, WO-04 | `.github/workflows/ci.yml` no contiene ningún paso `pytest` pese a que la issue lo exige literalmente; tampoco `prettier --check` |
| #5 | Health + `GET /api/authors` | backend | ✅ Verificado | — | `backend/app/routes/health.py:24`, `backend/app/routes/authors.py:216-248`; `backend/tests/test_health.py` + `test_authors.py` pasan |
| #6 | `POST /api/authors/{id}/documents` | backend | ✅ Verificado | — | `backend/app/routes/authors.py:293-376` (202 + BackgroundTask, conforme a `api_contract.yaml:192-198` y decision_log 2026-07-13); `backend/tests/test_document_upload.py` pasa |
| #7 | Limpiar y trocear los 3 corpus (seed) | ml | ⚠️ Parcial | WO-05 | `scripts/seed_corpus.py` real y validado (`--dry-run` → `OK`), pero `Makefile:61-63` invoca `python scripts/seed_corpus.py` **sin flags** → solo etapas 1-3; sin embeddings ni StyleProfiles |
| #8 | Extractor léxico | ml | ✅ Verificado | — | `ai_pipeline/autoria_ai/extractor/lexical.py:18-73` (MATTR-500 con ventana deslizante real, hapax sobre lemas, avg_word_length); cubierto en `ai_pipeline/tests/test_smoke.py` |
| #9 | Layout base + selector de autores | frontend | ✅ Verificado | — | `frontend/src/app/page.tsx`, `AuthorGrid.tsx`, `AuthorCard.tsx`, `AddAuthorCard.tsx`; `lib/authors.ts:45-55` con fallback declarado en `design-system.md:272` |
| #10 | 4 Custom Modes + primer export BobShell | bob | ✅ Verificado | — | `bob/custom-modes/{style-extractor,generation-conductor,studio-composer,passport-auditor}.md`, cada uno con "Loaded context", owner y ≥4 comandos de ejemplo; 16 exports en `bob/sessions/Sprint_1/P{1,2,3}/` |
| #11 | Validar voice-matching de Llama-3.3-70b, 5 prompts | bob | ❌ No implementado | WO-14 | El entregable nombrado, `bob/sessions/week1/baseline_eval.md`, **no existe**. Búsquedas: `find . -iname "*baseline*"` (0 aciertos en el repo), grep de `baseline\|voice-match\|5 prompts\|405b\|6/10` en `bob/**/*.md` (0 aciertos relevantes), `git log --all --diff-filter=A --name-only \| grep -i "baseline\|week1"` (0 aciertos: nunca existió), y no hay PR asociado a #11 |
| #12 | Features sintácticas con spaCy | ml | ✅ Verificado | — | `ai_pipeline/autoria_ai/extractor/syntactic.py:29-94`, fiel a `style_features.md` §2.1-§2.4. "dep-tree depth" y "coordination ratio" del texto de la issue quedan fuera por `style_features.md:9` ("Features not listed here are out of scope for v1.0") |
| #13 | POS y distribución de puntuación | ml | ✅ Verificado | — | `ai_pipeline/autoria_ai/extractor/stylistic.py:41-141`, incluye `dialogue_ratio` y `first_person_ratio` que exige `api_contract.yaml:597-622` |
| #14 | Vocabulario distintivo TF-IDF | ml | ⚠️ Parcial | WO-08 | `ai_pipeline/autoria_ai/extractor/vocabulary.py:20-88` correcto, pero `scripts/seed_corpus.py:634` llama a `compute_style_profile(...)` **sin** `comparison_lemmas` → TF-IDF sobre 1 solo documento → IDF constante → el ranking degenera a frecuencia bruta |
| #15 | Embeddings por chunk + pgvector + HNSW | ml | ✅ Verificado | — | `ai_pipeline/autoria_ai/embedder.py:30-64`, `db.py:241-324` (`SET LOCAL hnsw.ef_search`, `<=>`, scope por autor); índice en `0001_init.sql`/`0002`. El benchmark p95<200 ms (`test_embedder.py:359`) **no es verificable aquí**: `SKIPPED — DATABASE_URL not set` |
| #16 | Precómputo UMAP 2D (servidor) | ml | 🔌 Desconectado | WO-07 | `scripts/precompute_umap.py:263-271` escribe `public.umap_coords`, tabla que **nadie lee** (grep de `umap_coords` en todo el repo: solo el propio script) y que no está en ninguna migración. Mientras tanto `ai_pipeline/autoria_ai/extractor/style_profile.py:177-178` deja `"embedding_umap_2d": {"centroid": [0.0, 0.0], "spread": 0.0}` fijo. Sin tests |
| #17 | `GET .../style-profile` + persistencia | backend | ✅ Verificado | — | `backend/app/routes/authors.py:251-290` (última fila por `computed_at desc`, 404 conforme al contrato); `backend/tests/test_style_profile.py` pasa |
| #18 | Endpoint de recompute manual | backend | ⚠️ Parcial | WO-07 | `backend/app/routes/authors.py:379-426` + `105-138` ya llaman al pipeline real (PR #81), pero la issue exige "lexical → syntactic → stylistic → vocabulary → embeddings → **UMAP**" y el UMAP sigue siendo el cero fijo de `style_profile.py:178` |
| #19 | Pantalla principal con prompt + botón | frontend | ✅ Verificado | — | `frontend/src/components/GenerateStudio.tsx` + `PromptComposer.tsx` + `SideBySideOutput.tsx`, cableado a `POST /api/generate` vía `lib/api.ts:113-132`. Ruta consolidada en `/author/[id]` por decision_log 2026-07-21 |
| #22 | Integración Watsonx (auth + retry + timeout) | backend | ⚠️ Parcial | WO-10 | `backend/app/services/watsonx_client.py:23-25,110-156` implementa 8 s de timeout duro y backoff 1/2/4 s, con tests unitarios verdes. El test de integración exigido por la issue **existe y falla**: `403 no_associated_service_instance_error` contra el `WATSONX_PROJECT_ID` configurado |
| #23 | Composición del system prompt condicionado | ml | ⚠️ Parcial | WO-09 | `ai_pipeline/autoria_ai/conditioner.py:89-90` solo trunca a 5 chunks; no cuenta tokens en ninguna parte. 5 chunks × ~500 tokens ≈ 2 500 + plantilla, por encima del "Must fit within 2000 tokens" de la issue y del "< ~1200 tok" de `architecture.md:315`. Ningún test lo comprueba (grep de `2000`/`token` en `test_conditioner.py`: solo valores de perfil) |
| #24 | `fit_score` (5 componentes) | ml | ✅ Verificado | — | `ai_pipeline/autoria_ai/fit_scorer.py:163` — `sem*0.35 + syn*0.20 + lex*0.15 + sty*0.15 + voc*0.15`, exactamente `style_features.md:389-396`; 13 tests verdes |
| #25 | `POST /api/generate` (paralelo) | backend | ⚠️ Parcial | WO-06 | `backend/app/routes/generate.py:94-209` + `ai_pipeline/autoria_ai/generator.py:200-204` (`asyncio.gather` real). Pero la ruta nunca pasa `database_url` a `orchestrate`, y `db.py:83` hace `os.environ["DATABASE_URL"]`; el backend **no carga `.env`** (`backend/app/config.py:54-68`, sin dotenv en todo el runtime) → `retrieve_fn` lanza, se traga en `generator.py:174-179` y el RAG queda siempre vacío |
| #26 | Passport JWS + firma ES256 | backend | ✅ Verificado | — | `ai_pipeline/autoria_ai/passport/{builder,signer}.py`; roundtrip ejecutado: cabecera `{'alg':'ES256','kid':'autoria-2026-07','typ':'passport+jws'}`, `VERIFY valid= True`. 53+4 tests verdes |
| #27 | `/.well-known/jwks.json` + verify | backend | ✅ Verificado | — | Ejecutado: JWKS `200`, `Cache-Control: public, max-age=3600`; token manipulado → `invalid_signature`; `alg:none` → `unsupported_algorithm`. `verifier.py:100-114` implementa la allow-list y la resolución de `kid` de `passport_schema.md` §8 |
| #28 | UI side-by-side con métricas comparativas | frontend | ⚠️ Parcial | WO-12 | Columnas, `FitScoreBar` y `ComparativeMetricsTable` reales; pero `frontend/src/components/GenerateStudio.tsx:49` — `const [distinctiveTerms] = useState<readonly string[]>([])` — nunca se rellena, así que `DistinctiveVocabHighlight` recibe siempre `[]` y el resaltado de vocabulario distintivo (AC explícito) no se produce jamás |
| #29 | Pantalla `/verify` del Passport | frontend | ⚠️ Parcial | WO-15 | Funcionalidad completa (`frontend/src/app/verify/page.tsx`: pegar + subir, badge ✅/❌, tabla decodificada, toggle de JSON crudo). Desvía de `design-system.md`: `verify/page.tsx:505-506` usa `border-amber-500/40 bg-amber-500/10 text-amber-600` en vez del token `--warning` ("No hardcoded hex/oklch in components — tokens only", §1), sin `BadgeCheck`/`ShieldAlert` (§6) ni `.animate-stamp-in` (§5) |
| #41 | Pantalla "Style DNA": radar + scatter + métricas | frontend | ⚠️ Parcial | WO-11 | Radar, scatter y tabla top-10 implementados. Pero `frontend/src/components/StyleDnaPanel.tsx:374-391` sustituye el perfil por fixtures inventados ante **cualquier** fallo, incluido un 404 legítimo, contradiciendo la decisión registrada en `design-system.md:276` ("On network failure only (not a real 404)") y la cabecera del propio fichero de fixtures (`fixtures/style-profiles.ts:8-9`) |
| #42 | Botón "Download Passport" con JSON formateado | frontend | ⚠️ Parcial | WO-13 | La descarga existe y está testeada (`frontend/src/lib/passport.ts:25-39`, `passport.test.ts`). Falta la segunda mitad del AC: "render decoded Passport JSON in a collapsible syntax-highlighted panel **on screen**". No existe `PassportCard.tsx` pese a figurar en `design-system.md:212` |
| #43 | "Style DNA": radar + 2D scatter + métricas | frontend | ✅ Verificado | — | Duplicado de #41 con cuerpo más corto (solo radar + scatter). Ambos entregables existen: `StyleRadarChart.tsx`, `StyleScatter2D.tsx`. El hueco de honestidad de datos se rastrea en #41/WO-11 |

**Recuento:** ✅ 14 · ⚠️ 12 · 🔌 1 · ❌ 1 · 🥸 0 · 🧪 0 · ❔ 0.

---

## Detalle por issue (solo las que NO son ✅)

### #2 — Repo + monorepo, Vercel + Railway · ⚠️ Parcial

**Se pidió:** monorepo con `frontend/` + `backend/` + `ai_pipeline/`, Vercel para el front, Railway para el back, y "verify env vars (WATSONX_API_KEY, SUPABASE_URL, SUPABASE_KEY) are injected in both platforms".

**Se encuentra:** el monorepo es correcto y completo. `railway.toml` documenta explícitamente el Root Directory vacío, `/internal/env-check` (`backend/app/routes/diagnostics.py`) da el chequeo de secretos sin filtrar valores, y `docs/DEPLOYMENT.md` es una guía real.

**Hueco (a) — el frontend desplegado no puede hablar con el backend.** `frontend/src/lib/api.ts:30`:

```ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```

Ese nombre de variable **no aparece en ningún otro sitio del repo**. Lo que sí está definido en todas partes es `NEXT_PUBLIC_API_BASE_URL` (`.env.example:33`, `docs/DEPLOYMENT.md:30,62,89`). En Vercel se inyectará `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_API_URL` quedará `undefined`, y **todas** las llamadas del navegador irán a `http://localhost:8000`.

**Hueco (b) — el backend desplegado no puede generar.** `railway.toml` construye con `pip install -r backend/requirements.txt`, y ese fichero (`backend/requirements.txt:4-12`) declara solo fastapi, uvicorn, pydantic, supabase, tiktoken, python-multipart, ibm-watsonx-ai, python-jose, jsonschema. Faltan **todas** las dependencias de `ai_pipeline/pyproject.toml` que `orchestrate` necesita: `sqlalchemy`, `asyncpg`, `pgvector`, `spacy`, `sentence-transformers`, `scikit-learn`, `numpy`. `generator.py:150-151` importa `autoria_ai.db` *fuera* de cualquier `try` → en Railway, `POST /api/generate` revienta con `ImportError` antes de llegar a Watsonx.

**Impacto:** bloquea el "public deploy" y, con él, toda demostración en vivo. Es el hueco de mayor alcance del informe.

---

### #4 — GitHub Actions: lint + tests en cada PR · ⚠️ Parcial

**Se pidió, literalmente:** "Python: Ruff + Black. Frontend: ESLint + Prettier. Tests: `pytest backend/tests/` and `npm test` in `frontend/`. PRs cannot merge if any check fails."

**Se encuentra:** `.github/workflows/ci.yml` tiene exactamente dos jobs. `lint-python` ejecuta `ruff check .` y `black --check .`. `lint-frontend` ejecuta `npm run lint`, `npx tsc --noEmit` y `npm run test`.

**Hueco:** no existe **ningún** paso de `pytest`, ni para `backend/tests` ni para `ai_pipeline/tests`. Tampoco hay `prettier --check`. Y el workflow solo se dispara `on: pull_request` — no en push a `main`.

**Impacto:** es la causa raíz de que nadie haya visto que `pytest backend/tests` no llega ni a coleccionar. Todo "los tests pasan" en este repo es, para el backend, una declaración sin prueba desde el día que se introdujo el fallo.

---

### #7 — Limpiar y trocear los 3 corpus (seed script) · ⚠️ Parcial

**Se pidió:** `scripts/seed_corpus.py` que limpie cabeceras Gutenberg, normalice comillas, trocee a 500/50 con tiktoken, y **siembre Supabase** con los tres autores.

**Se encuentra:** el script es sólido — manifiesto de 10 ficheros, `clean_text`, troceado idéntico byte a byte al del endpoint de upload (`seed_corpus.py:482-507` ↔ `backend/app/routes/authors.py:141-183`), idempotencia por `content_hash`, 31 tests verdes, y `--dry-run` que pasa: `[austen] 643533 · [dickens] 1147910 · [poe] 259034` tokens limpios.

**Hueco:** las etapas 4 (embeddings) y 5 (perfiles) son **opt-in**, y el comando documentado no las activa. `Makefile:61-63`:

```make
seed: ## Seed the DB with the 3 preloaded authors (Austen, Dickens, Poe)
	$(call need_file,scripts/seed_corpus.py,Sprint 2)
	python scripts/seed_corpus.py
```

Siguiendo `README.md:171-177` al pie de la letra (`make seed` → `make dev`), la base queda con `authors`/`documents`/`chunks` pero con `chunks.embedding` todo NULL y `style_profiles` vacía.

**Impacto en cadena:** `GET /api/authors/{id}/style-profile` → 404 → el front cae a fixtures (ver #41). `POST /api/generate` → 404 "StyleProfile not yet computed". `retrieve_top_k` → 0 chunks (no hay embeddings) → generación sin RAG. Es decir: **el camino de arranque documentado no produce un sistema funcional.**

---

### #11 — Validar voice-matching de Llama-3.3-70b, 5 prompts · ❌ No implementado

**Se pidió:** pasar 5 prompts fijos por `llama-3-3-70b-instruct` sin condicionar, puntuar el parecido de voz 1-10, aplicar la puerta "si baseline < 6/10, escalar a `llama-3-1-405b`", y **documentarlo en `bob/sessions/week1/baseline_eval.md`**.

**Se encuentra: nada.** Búsquedas realizadas antes de concluir la ausencia:

1. Por nombre de fichero: `find . -iname "*baseline*"` → único acierto, `.venv/Lib/site-packages/networkx/...`, ajeno al proyecto.
2. Por contenido: grep insensible a mayúsculas de `baseline|voice-match|5 prompts|llama-3-1-405b|6/10` sobre `bob/**/*.md` → dos aciertos genéricos (`bob/playbook.md:146`, `bob/custom-modes/generation-conductor.md:95`) que describen la *metodología*, no resultados.
3. En el historial: `git log --all --diff-filter=A --name-only --pretty=format: | grep -i "baseline\|week1\|week2"` → **cero**. El fichero nunca existió en ninguna rama.
4. Por PR: `gh pr list --state merged` → ningún PR asociado a #11.
5. En `bob/sessions/`: 26 exports, ninguno con puntuaciones de calidad de voz.

**Impacto:** esta issue es la puerta de riesgo **R1** de `docs/MVP.md:512` y la "SPRINT 1 TASK" de `docs/MVP.md:329`. Se cerró como COMPLETED sin haberse ejecutado. Agravante: hoy Watsonx devuelve 403 con las credenciales configuradas, de modo que la validación tampoco *pudo* haberse hecho contra el proyecto actual.

---

### #14 — Vocabulario distintivo TF-IDF · ⚠️ Parcial

**Se pidió:** TF-IDF construido sobre los chunks de **los 3 autores**, extrayendo los términos distintivos de cada uno.

**Se encuentra:** `vocabulary.py:20-88` implementa exactamente `style_features.md` §4.1 (un documento TF-IDF por autor, `stop_words="english"`, `token_pattern=r"(?u)\b[a-zA-Z]{3,}\b"`, `max_features=50000`), con 18 tests. El camino del backend lo usa bien: `backend/app/routes/authors.py:84-95` recolecta los corpus de los demás autores y los pasa como `comparison_lemmas`.

**Hueco:** el camino de siembra no. `scripts/seed_corpus.py:634`:

```python
profile = compute_style_profile(author_slug=author_slug, documents=documents, nlp=nlp)
```

Sin `comparison_lemmas`, `compute_style_profile` construye `corpora = {author_slug: lemmas}` — un corpus de **un solo documento**. Con un único documento, el IDF de `TfidfVectorizer` es constante para todos los términos, así que el ranking resultante es TF normalizado: las palabras **más frecuentes**, no las distintivas. El propio docstring lo reconoce a medias (`seed_corpus.py:620-625`: "distinctive_vocab may therefore be weaker"); en realidad no es "más débil", es **una métrica distinta**.

**Impacto:** el vocabulario que se inyecta en el system prompt (`conditioner.py:82-86`) y el que se muestra en la tabla del panel Style DNA serían palabras comunes en vez de "countenance / physiognomy / presently" — justo el efecto que `style_features.md:305` describe como el que "el público *ve* en la demo".

---

### #16 — Precómputo UMAP 2D (servidor) · 🔌 Implementado pero desconectado

**Se pidió:** `scripts/precompute_umap.py` que cargue los embeddings de pgvector, ajuste UMAP (n_neighbors=15, min_dist=0.1, coseno, 2D) y guarde `(x, y, author_id)` en `umap_coords`, "This powers the 2D scatter in the Style DNA screen".

**Se encuentra:** el script existe y es correcto en sí mismo — parámetros exactos, `random_state=42`, join `chunks → documents`, guarda de mínimo de filas, `TRUNCATE` + `execute_values`.

**Huecos, tres:**

1. **Nadie lee `umap_coords`.** Grep de `umap_coords` en todo el repo (excluyendo `node_modules` y `bob/sessions`): las 9 apariciones están **todas** dentro de `scripts/precompute_umap.py`. Ninguna ruta del backend la consulta, ningún test la toca.
2. **El campo que sí consume el front sigue en cero.** `ai_pipeline/autoria_ai/extractor/style_profile.py:177-178`:
   ```python
   # Placeholder — scripts/precompute_umap.py owns real 2-D coords.
   "embedding_umap_2d": {"centroid": [0.0, 0.0], "spread": 0.0},
   ```
   `StyleDnaPanel.tsx:406-407,432-433` lee `profile.embedding_umap_2d.centroid`. Con perfiles reales, **los tres autores se dibujan en (0,0) con dispersión 0**: un solo punto superpuesto.
3. **La tabla no está en ninguna migración.** El script la crea con `CREATE TABLE IF NOT EXISTS` en tiempo de ejecución (`precompute_umap.py:70-77`), contradiciendo `docs/erd.md:4` ("Source of truth for the schema: `0001_init.sql`").

**Impacto:** es el momento `[01:30]` del guion de demo (`docs/MVP.md:85-86`: "vanilla lands in a generic cluster, AutorIA inside the Dickens cluster"). Hoy solo "funciona" cuando el front está sirviendo fixtures inventados (ver #41), es decir, nunca con datos reales.

---

### #18 — Endpoint de recompute manual · ⚠️ Parcial

**Se pidió:** disparar "the full pipeline (lexical → syntactic → stylistic → vocabulary → embeddings → **UMAP**)" como `BackgroundTask` y devolver 202.

**Se encuentra:** ya no es el stub de ceros que describía `api_contract.yaml:136-138`. `backend/app/routes/authors.py:105-138` carga los documentos, recolecta corpus de comparación, llama a `compute_style_profile` real y hace INSERT con el hash canónico. El 202 y `estimated_seconds = max(30, n_tokens // 2000)` son conformes al contrato. Tests verdes.

**Hueco:** el último eslabón del pipeline enumerado en la issue —UMAP— no se ejecuta; el perfil insertado lleva el `[0.0, 0.0]` fijo. Mismo fallo que #16, misma orden de trabajo (WO-07).

*(Observación menor, sin orden de trabajo: `_build_style_profile` hace `spacy.load("en_core_web_lg")` en cada invocación (`authors.py:96`), en vez de reutilizar el singleton que ya mantiene `generator.py:57-74`. Es coste, no incorrección.)*

---

### #22 — Integración Watsonx · ⚠️ Parcial

**Se pidió:** cliente con IAM auth, backoff exponencial 1/2/4 s, timeout duro de 8 s, `generate(prompt, system_prompt, model_id, params) -> str`, y "**Write an integration test hitting real Watsonx**".

**Se encuentra:** todo implementado y verificado en unitarios. `watsonx_client.py:23-25` fija `HARD_TIMEOUT_SECONDS = 8.0` y `_RETRY_DELAYS_SECONDS = (1.0, 2.0, 4.0)`; `test_generate_exhausts_retries` y `test_generate_hard_timeout` comprueban ambos. El test de integración existe y está bien vallado (`@pytest.mark.integration` + `skipif(not _watsonx_creds_present())`, `test_watsonx_client.py:153-168`).

**Hueco:** con las credenciales presentes en el `.env` local, el test **se ejecuta y falla**:

```
Status code: 403, body: {"errors":[{"code":"no_associated_service_instance_error",
"message":"project_id 614cdac6-f924-43e9-a325-c00773883b4c is not associated with a WML instance"}]}
... 4 intentos ... app.services.watsonx_client.WatsonxError: Watsonx generate failed after 4 attempts
```

Esto no es un defecto de código: es el proyecto Watsonx que no tiene instancia WML asociada. Pero sí es un hecho verificado, no una hipótesis: **hoy no se puede generar texto**.

*(Observación de diseño, sin orden de trabajo: 4 intentos × 8 s + 7 s de esperas = hasta 39 s en el peor caso, contra el SLA "< 8s P95" de `docs/MVP.md:220`. Solo aplica en la ruta de fallo, y `lib/api.ts:118` aborta a los 10 s por el lado del cliente, así que el usuario ve un timeout, no una espera de 39 s.)*

---

### #23 — Composición del system prompt condicionado · ⚠️ Parcial

**Se pidió:** system prompt con nombre/época del autor, métricas clave y los 5 pasajes RAG, que "**Must fit within 2000 tokens**".

**Se encuentra:** `conditioner.py:39-98` compone la plantilla de `docs/MVP.md:200-206` con traducción de `subordination_ratio` a lenguaje natural y tope de 15 términos de vocabulario. Real y con 17 tests.

**Hueco:** la única salvaguarda es un corte por número de elementos (`conditioner.py:89`: `safe_chunks = rag_chunks[:_MAX_CHUNKS]`). **En ningún punto se cuenta un token.** Los chunks que llegan son los de `chunks.text`, producidos con ventana de 500 tokens (`authors.py:51`, `seed_corpus.py:130`): 5 × 500 ≈ 2 500 tokens solo de pasajes, más la plantilla. Eso rebasa tanto los 2 000 tokens del AC como el "lean system prompt (< ~1200 tok)" de `architecture.md:315`. Ningún test lo comprueba: en `test_conditioner.py` no hay ninguna aserción sobre longitud (las únicas apariciones de `2000`/`token` son valores de perfil de ejemplo).

**Impacto:** presupuesto de latencia. El prompt condicionado puede duplicar el tamaño previsto, y la rama AutorIA es la que compite contra el SLA de 8 s.

---

### #25 — `POST /api/generate` · ⚠️ Parcial

**Se pidió:** dos llamadas Watsonx concurrentes vía `asyncio.gather`, `fit_score` para ambas, firma del Passport, y la respuesta con las tres claves.

**Se encuentra:** la orquestación es real y correcta. `generator.py:200-204` hace el `asyncio.gather` con `return_exceptions=True` y degradación asimétrica (si falla vanilla se degrada esa columna; si falla AutorIA se propaga porque sin ella no hay Passport). La ruta persiste en `passports` sin abortar la respuesta si el INSERT falla. 37 tests verdes.

**Hueco: el RAG nunca se ejecuta.** La cadena, paso a paso:

1. `backend/app/routes/generate.py:167-174` invoca `orchestrate(...)` **sin** el kwarg `database_url`.
2. `generator.py:168-173` llama a `retrieve_fn(..., database_url=None)`.
3. `db.py:83` — `url = database_url or os.environ["DATABASE_URL"]`.
4. El backend **no carga `.env` en ningún punto**: `backend/app/config.py:54-68` usa `os.getenv` directo y no hay `python-dotenv` en `backend/pyproject.toml` ni en `backend/requirements.txt` (grep de `dotenv` en `backend/`, `ai_pipeline/`, `scripts/`: el único acierto es un helper privado dentro de `backend/tests/test_watsonx_client.py:23`).
5. `KeyError` → capturado por el `except Exception` de `generator.py:174-179` → `logger.warning("RAG retrieval failed…")` → `chunks = []`.

Resultado: `system_prompt` sin pasajes de ejemplo, `rag_sources: []` en el Passport, y la "R" de RAG ausente del producto — silenciosamente, con un warning en el log.

Nota adicional: `settings.database_url` se lee en `config.py:62` y **no se usa en ningún sitio**, lo que confirma que el cableado se dejó a medias.

---

### #28 — UI side-by-side con métricas comparativas · ⚠️ Parcial

**Se pidió:** dos columnas; izquierda vanilla con texto + fit_score; derecha AutorIA con texto + fit_score + **vocabulario distintivo resaltado**; debajo, tabla comparativa; botón Generate Passport.

**Se encuentra:** todo salvo el resaltado. `AuthorColumn.tsx`, `SideBySideOutput.tsx`, `FitScoreBar.tsx`, `ComparativeMetricsTable.tsx` y el botón existen y funcionan; la tabla comparativa se mide en cliente por la limitación de contrato documentada en `decision_log.md` (2026-07-21).

**Hueco:** `frontend/src/components/GenerateStudio.tsx:49`:

```tsx
const [distinctiveTerms] = useState<readonly string[]>([]);
```

Es un `useState` sin setter, inicializado a array vacío y jamás modificado. Se propaga a `SideBySideOutput.tsx:47` → `AuthorColumn.tsx:117-125`, donde `(props.distinctiveTerms?.length ?? 0) > 0` es siempre falso. `DistinctiveVocabHighlight` está construido, testeado y cableado — y siempre recibe `[]`. El comentario adyacente lo admite: "Not fetched here; could be passed in from a parent".

**Impacto:** elimina el dispositivo nº 4 de los cinco del "5-second contrast playbook" (`design-system.md:251-253`), y es el efecto que el guion de demo anuncia en `docs/MVP.md:82-83` ("distinctive vocab: 'countenance', 'physiognomy', 'presently' (right column only)").

---

### #29 — Pantalla `/verify` · ⚠️ Parcial

**Se pidió:** `/verify` con token por subida (`.jws`/`.json`) o pegado, llamada a `POST /api/passports/verify`, badge ✅/❌, tabla del payload decodificado y toggle de JSON crudo.

**Se encuentra:** los seis criterios están cumplidos y bien hechos — `verify/page.tsx` tiene pestañas paste/upload, extracción de `jws_token` de un JSON o token desnudo, estado discriminado de 5 ramas, tabla completa con hashes copiables, y el toggle de JSON. Los mensajes de error se traducen por código desde `en.ts`.

**Hueco (desviación del documento rector de frontend):** el banner de error de red usa colores crudos de la paleta Tailwind en vez de tokens (`verify/page.tsx:505-506`: `border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400`), cuando existe el token `--warning`/`--warning-tint` precisamente para eso y `design-system.md` §1 lo prohíbe explícitamente ("No hardcoded hex/oklch in components — tokens only"). Además ningún banner lleva icono (§6: "Icons always accompany, never replace, a label"; iconos canónicos `BadgeCheck` para verificado, `ShieldAlert` para inválido) y no se usa `.animate-stamp-in`, que §5 y §7 reservan justo para el `VerifiedBanner`.

**Impacto:** bajo funcionalmente, no nulo visualmente — es la pantalla que cierra la demo (`docs/MVP.md:87`).

---

### #41 — Pantalla "Style DNA" · ⚠️ Parcial

**Se pidió:** radar de 6 ejes normalizados a [0,1], scatter de coordenadas UMAP coloreado por autor, y tabla de los 10 términos distintivos.

**Se encuentra:** los tres, bien construidos. `StyleRadarChart.tsx` con los dominios razonados de `design-system.md:274`, `StyleScatter2D.tsx` con centroide + anillo de dispersión, tabla top-10 ordenada por score, chips de corpus, estados loading/empty/error/ready y guarda de timeout de 10 s.

**Hueco: los datos que muestra pueden ser inventados sin que nada lo indique.** `StyleDnaPanel.tsx:374-391`:

```ts
async function fetchProfileWithFallback(authorId: string): Promise<StyleProfile> {
  try { return await getStyleProfile(authorId); }
  catch (err) {
    const fixture = FIXTURE_STYLE_PROFILES[authorId];
    if (fixture) { console.info(`... using fixture for "${authorId}" (demo-safe fallback)`); return fixture; }
    throw err;
  }
}
```

Tres problemas encadenados:

1. **Contradice la decisión registrada.** `design-system.md:276` dice: "On network failure only (**not a real 404**), `StyleDnaPanel` falls back to … typed fixtures". El código cae también en 404. El cambio (PR #76) no tiene entrada correctora en `docs/decision_log.md`.
2. **La cabecera del propio fichero de fixtures ya es falsa.** `fixtures/style-profiles.ts:8-9`: "They are NOT used when the live API returns a real 404 … They are ONLY substituted on network failure".
3. **Los valores no son plausibles, son escogidos para que el gráfico quede bonito.** `fixtures/style-profiles.ts:16-17`: "Centroids are spaced apart in UMAP space so the scatter plot is readable". Y no respetan los rangos del documento rector: Austen queda con `mattr_500: 0.72` (rango de `style_features.md:413`: 0.62-0.68) y `hapax_ratio: 0.18` (rango: 0.38-0.44).

Combinado con el 404 permanente que produce `make seed` (#7) y con `lib/authors.ts:9-34` (que ante fallo de la API pinta las tres tarjetas con `has_style_profile: true` incondicional), el resultado es una pantalla que **parece completa con cero datos reales detrás**, y cuyo único aviso es un `console.info`.

**Impacto:** choca de frente con la regla de honestidad que el propio equipo se impuso (`design-system.md:258`: "both columns use the same model and the real scores. The contrast is earned by design, never faked"). Ante un jurado, la separación de clusters del scatter es hoy un artefacto de fixtures.

---

### #42 — Botón "Download Passport" · ⚠️ Parcial

**Se pidió, dos cosas:** "(1) trigger browser download of `passport-[timestamp].jws`, and (2) **render decoded Passport JSON in a collapsible syntax-highlighted panel on screen**".

**Se encuentra (1):** `frontend/src/lib/passport.ts:25-39` serializa el sobre completo (`jws_token` + `json_payload`) con indentación 2 y lo descarga. La decisión de incluir el JWS está bien razonada (sin firma no sería verificable). Cubierto por `passport.test.ts`. El nombre es `passport-<author_id>.json` en vez de `passport-<timestamp>.jws` — desviación menor y mejor justificada que el AC.

**Hueco (2):** no existe panel en pantalla. `GenerateStudio.tsx:135-151` solo renderiza el botón. No hay componente `PassportCard.tsx` en `frontend/src/components/` (listado completo verificado), pese a que `design-system.md:212` lo inventaría como componente de Sprint 2 con estado "ready": "`PassportCard` | 2 | studio, verify | ready | Mono JSON block + `Download` action".

**Impacto:** el beat `[01:40]` del guion (`docs/MVP.md:87`: "Click 'Generate Passport': JSON appears") no ocurre — el JSON no aparece, se descarga a disco.

---

## Órdenes de trabajo

---

### WO-01 — Corregir el nombre de la variable de entorno de la URL base de la API en el frontend

- **Origen:** issue #2 · veredicto ⚠️ · módulo `infra`/`frontend`
- **Síntoma:** en el frontend desplegado en Vercel, toda llamada a la API va a `http://localhost:8000`; el usuario ve la lista de autores de respaldo, el panel Style DNA con fixtures y un error en cualquier generación.
- **Evidencia:** `frontend/src/lib/api.ts:30` — `const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";`. Búsqueda de `NEXT_PUBLIC_API_URL` en todo el repo (excluyendo `node_modules` y `bob/`): **un solo acierto, esa misma línea**. Búsqueda de `NEXT_PUBLIC_API_BASE_URL`: `.env.example:33`, `docs/DEPLOYMENT.md:30`, `:62`, `:89`.
- **Causa raíz:** el código se escribió con un nombre de variable distinto del que fija `.env.example` y `DEPLOYMENT.md`. Como hay un valor por defecto (`?? "http://localhost:8000"`), el fallo es silencioso: no hay error de build ni de runtime, solo peticiones al host equivocado.
- **Ficheros a tocar:** `frontend/src/lib/api.ts`. (Opcionalmente `frontend/.env.local.example` si se decide crear uno; no existe hoy.)
- **Definición de hecho:**
  - `grep -rn "NEXT_PUBLIC_API_URL" frontend/src` no devuelve nada.
  - `grep -rn "NEXT_PUBLIC_API_BASE_URL" frontend/src/lib/api.ts` devuelve la línea de `API_BASE`.
  - `cd frontend && npx tsc --noEmit && npx eslint . && npm run test` siguen en exit 0.
  - `cd frontend && NEXT_PUBLIC_API_BASE_URL=https://example.invalid npm run build` compila, y una inspección del bundle (`grep -r "example.invalid" .next/` ) muestra el valor inyectado.
- **Contexto obligatorio para el ejecutor:** `docs/DEPLOYMENT.md` (§"Vercel — frontend", paso 3: es el documento que fija qué variable inyecta la plataforma) y `.env.example` (la plantilla que los tres desarrolladores copian). No hace falta leer nada más.
- **Bloqueada por:** nada.
- **Conflicto de ficheros:** ninguno.
- **Tamaño:** XS.
- **Riesgo de regresión:** nulo si se conserva el valor por defecto `http://localhost:8000`; quien tuviera exportada `NEXT_PUBLIC_API_URL` en su entorno local dejaría de verla surtir efecto — mencionarlo en el canal del equipo.

---

### WO-02 — Instalar las dependencias de `ai_pipeline` en la imagen de Railway

- **Origen:** issue #2 · veredicto ⚠️ · módulo `infra`
- **Síntoma:** en el backend desplegado, `POST /api/generate` devuelve 500 (`ImportError`) en lugar de generar; `/health` sigue en 200, así que el despliegue parece sano.
- **Evidencia:** `railway.toml` → `[build] buildCommand = "pip install -r backend/requirements.txt"`. `backend/requirements.txt:4-12` declara únicamente `fastapi`, `uvicorn[standard]`, `pydantic`, `supabase`, `tiktoken`, `python-multipart`, `ibm-watsonx-ai`, `python-jose[cryptography]`, `jsonschema[format]`. `ai_pipeline/autoria_ai/generator.py:150-151` ejecuta `from autoria_ai.db import retrieve_top_k` fuera de todo `try`, y `ai_pipeline/autoria_ai/db.py:34-45` importa `numpy`, `pgvector.sqlalchemy`, `sqlalchemy` y `autoria_ai.embedder` (que a su vez importa `sentence_transformers`). Ninguno de esos paquetes está en el fichero que Railway instala.
- **Causa raíz:** `backend/requirements.txt` se creó como espejo de `backend/pyproject.toml`, pero el runtime del backend depende también de `ai_pipeline/pyproject.toml` desde que `/api/generate` delega en el orquestador. `docs/DEPLOYMENT.md:9-14` ya avisa de que Railway debe construir desde la raíz para que `ai_pipeline/` esté en la imagen — pero estar en la imagen no basta si sus dependencias no se instalan.
- **Ficheros a tocar:** `railway.toml`, `backend/requirements.txt` (y/o un nuevo `requirements-deploy.txt` en la raíz; `requirements.txt` de la raíz ya es un `-r backend/requirements.txt`). Decidir dónde vive la lista es parte de la orden.
- **Definición de hecho:**
  - En un contenedor/venv limpio, `pip install -r <lo que instale railway.toml>` seguido de `python -c "import sys; sys.path.insert(0,'ai_pipeline'); from autoria_ai.generator import orchestrate; from autoria_ai.db import retrieve_top_k; print('ok')"` imprime `ok`.
  - `python -m spacy validate` (o equivalente) confirma que `en_core_web_lg` está disponible, o bien `warmup_models()` registra su ausencia sin abortar y se documenta explícitamente que la generación necesita el modelo.
  - Tras el despliegue: `curl -X POST https://<railway>/api/generate -H 'Content-Type: application/json' -d '{"author_id":"dickens","prompt":"test"}'` devuelve 200, 404 (perfil ausente) o 503 (Watsonx) — **pero nunca 500 con `ImportError`**.
  - `curl https://<railway>/health` sigue devolviendo 200.
- **Contexto obligatorio para el ejecutor:** `docs/DEPLOYMENT.md` (§"Railway — backend": explica por qué Root Directory va vacío y qué produce el plan Nixpacks), `ai_pipeline/pyproject.toml` (`[project].dependencies` — la lista canónica que falta), `railway.toml` (la cabecera documenta la restricción del monorepo), y `docs/architecture.md` §2 (por qué el pipeline es una librería en proceso y no un servicio, que es lo que fuerza esta co-instalación).
- **Bloqueada por:** nada.
- **Conflicto de ficheros:** comparte `backend/requirements.txt` con **WO-06**. No pueden ir en paralelo.
- **Tamaño:** S.
- **Riesgo de regresión:** el tiempo y el tamaño del build de Railway crecen mucho (torch + spaCy + modelo `en_core_web_lg` ≈ varios GB). Puede rebasar los límites del plan hobby o el `healthcheckTimeout = 100` del arranque en frío. Si ocurre, es un hallazgo nuevo que hay que reportar, no resolver por cuenta propia.

---

### WO-03 — Añadir un job de pytest (backend + pipeline) al workflow de CI

- **Origen:** issue #4 · veredicto ⚠️ · módulo `infra`
- **Síntoma:** un PR que rompa cualquier test de Python se fusiona en verde; nadie se entera hasta que alguien ejecuta pytest a mano.
- **Evidencia:** `.github/workflows/ci.yml` completo: dos jobs (`lint-python`: `ruff check .`, `black --check .`; `lint-frontend`: `npm ci`, `npm run lint`, `npx tsc --noEmit`, `npm run test`). Cero apariciones de `pytest` en el fichero. El cuerpo de la issue #4 exige literalmente "Tests: `pytest backend/tests/` and `npm test` in `frontend/`".
- **Causa raíz:** el job nunca se escribió. Probablemente porque instalar `ai_pipeline` en CI arrastra spaCy + sentence-transformers y se pospuso; pero `backend/tests` solo necesita las dependencias de `backend/pyproject.toml` y corre en ~90 s.
- **Ficheros a tocar:** `.github/workflows/ci.yml`. (Si hace falta cachear el modelo de spaCy, también un paso de caché dentro del mismo fichero.)
- **Definición de hecho:**
  - `.github/workflows/ci.yml` contiene un job que ejecuta `pytest backend/tests` y otro (o el mismo) que ejecuta `pytest ai_pipeline/tests`.
  - Los tests marcados `integration` quedan excluidos en CI (`pytest -m "not integration"`), de modo que la ausencia de credenciales Watsonx **no** pone CI en rojo — el marcador ya existe en `backend/pyproject.toml` (`markers = ["integration: hits real external services..."]`).
  - Se añade `npx prettier --check .` al job de frontend (segunda mitad del AC de #4), o se documenta en el propio workflow por qué se omite.
  - Verificación: abrir un PR de prueba con un `assert False` en un test y comprobar que el check falla; revertirlo.
  - Fijar en el job las mismas versiones que ya usa `lint-python` y **alinear `requirements-dev.txt`** (hoy `ruff==0.6.9`, `black==24.8.0` frente a `ruff==0.15.20`, `black==26.5.1` en CI) o dejar constancia de por qué divergen.
- **Contexto obligatorio para el ejecutor:** `.github/workflows/ci.yml` (el estado actual), `backend/pyproject.toml` y `ai_pipeline/pyproject.toml` (extras `[dev]` y `[tool.pytest.ini_options]`, incluido `asyncio_mode = "auto"` del pipeline), `CONTRIBUTING.md` §8.1 y §11 (la Definition of Done por issue que este workflow debe hacer cumplir), y `requirements-dev.txt` (las versiones desalineadas).
- **Bloqueada por:** **WO-04.** Si se añade pytest antes de arreglar el error de colección, CI queda en rojo permanente desde el primer PR.
- **Conflicto de ficheros:** ninguno.
- **Tamaño:** S.
- **Riesgo de regresión:** los tiempos de CI suben; si se incluye `ai_pipeline/tests` habrá que descargar `en_core_web_lg` (`test_smoke.py:19` hace `spacy.load("en_core_web_lg")` a nivel de módulo), lo que sin caché añade varios minutos por ejecución.

---

### WO-04 — Reparar el error de colección de `backend/tests` provocado por la fuga de `sys.modules` de `test_generate.py`

- **Origen:** issue #4 · veredicto ⚠️ · módulo `backend`
- **Síntoma:** `pytest backend/tests` aborta antes de ejecutar un solo test: `Interrupted: 1 error during collection`. La suite completa del backend no se puede ejecutar hoy.
- **Evidencia:** salida literal del comando:
  ```
  ERROR collecting tests/test_watsonx_client.py
  backend\tests\test_watsonx_client.py:12: in <module>
      from app.services.watsonx_client import (
  E   ImportError: cannot import name '_RETRY_DELAYS_SECONDS' from 'app.services.watsonx_client' (unknown location)
  =========================== short test summary info ===========================
  ERROR backend\tests\test_watsonx_client.py
  !!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
  ```
  Contraste que aísla la causa: `pytest backend/tests --ignore=tests/test_generate.py` → `1 failed, 60 passed`; `pytest backend/tests/test_generate.py` → `37 passed`; `pytest backend/tests/test_watsonx_client.py` a solas → `6 tests collected`.
- **Causa raíz:** `backend/tests/test_generate.py:67-79` instala un módulo falso en `sys.modules` **en tiempo de importación del módulo de test**:
  ```python
  _WX_KEY = "app.services.watsonx_client"
  _WX_PRIOR = sys.modules.get(_WX_KEY)
  if _WX_PRIOR is None:
      _wx_fake = types.ModuleType(_WX_KEY)
      _wx_fake.WatsonxError = _WatsonxError
      _wx_fake.generate = MagicMock()
      sys.modules[_WX_KEY] = _wx_fake
  ```
  y solo lo retira en un fixture `@pytest.fixture(autouse=True, scope="module")` (`:82-89`), cuyo teardown corre **después de ejecutar** los tests de ese módulo. Pytest colecciona todos los módulos antes de ejecutar ninguno, y `test_generate.py` se colecciona antes que `test_watsonx_client.py` por orden alfabético: cuando este último se importa, el falso sigue puesto y no tiene `_RETRY_DELAYS_SECONDS`. El `(unknown location)` del mensaje es la firma de un `ModuleType` sintético sin `__file__`.
- **Ficheros a tocar:** `backend/tests/test_generate.py`. Posiblemente `backend/conftest.py` si se prefiere centralizar el doble.
- **Definición de hecho:**
  - `pytest backend/tests -q` colecciona y ejecuta la suite completa sin errores de colección.
  - `pytest backend/tests -q -m "not integration"` termina en `0 failed`.
  - `pytest backend/tests/test_generate.py -q` sigue dando `37 passed` (no se pierde cobertura).
  - `pytest backend/tests/test_watsonx_client.py -q -m "not integration"` pasa tanto en solitario como dentro de la suite completa.
  - El orden no importa: `pytest backend/tests -p no:randomly` y `pytest backend/tests/test_watsonx_client.py backend/tests/test_generate.py` dan el mismo resultado.
- **Contexto obligatorio para el ejecutor:** `backend/tests/test_generate.py` (docstring de `:1-15` explica *por qué* se inyecta el falso: `app.services.watsonx_client` importa `ibm_watsonx_ai` a nivel de módulo y ese paquete puede faltar en un venv solo-backend), `backend/app/services/watsonx_client.py:16-25` (los símbolos reales que el falso debe imitar) y `backend/app/routes/generate.py:161-166` (el import diferido dentro de la función, que es lo que el falso pretende satisfacer). No hace falta leer el resto del backend.
- **Bloqueada por:** nada.
- **Conflicto de ficheros:** ninguno.
- **Tamaño:** S.
- **Riesgo de regresión:** si el doble se elimina sin sustituto, `test_generate.py` deja de poder ejecutarse en entornos sin `ibm-watsonx-ai` instalado. El contrato a preservar: los 37 tests de `test_generate.py` siguen pasando **sin** `ibm_watsonx_ai` presente, y `test_watsonx_client.py` importa siempre el módulo real.

---

### WO-05 — Hacer que `make seed` deje la base lista para la demo (embeddings + StyleProfiles)

- **Origen:** issue #7 · veredicto ⚠️ · módulo `ml`/`infra`
- **Síntoma:** quien sigue el README paso a paso (`make seed` → `make dev`) obtiene un sistema donde la pantalla Style DNA no tiene datos reales (404 → fixtures) y toda generación falla con 404 "StyleProfile not yet computed".
- **Evidencia:** `Makefile:61-63` ejecuta `python scripts/seed_corpus.py` sin flags. `scripts/seed_corpus.py:26-38` documenta que las etapas 4 (embeddings) y 5 (perfiles) son opt-in vía `--with-embeddings` / `--with-profiles`: "Embeddings and profiles are opt-in (not run by default) because both are slow". `README.md:171-172` presenta `make seed` como "Seed the database with the 3 preloaded authors", sin mencionar que faltan dos etapas.
- **Causa raíz:** decisión deliberada de mantener el seed rápido, no propagada ni al `Makefile` ni al README. El resultado es que el camino documentado y el camino que produce un sistema funcional son distintos, y solo el primero está escrito.
- **Ficheros a tocar:** `Makefile`, `README.md`. (No tocar `scripts/seed_corpus.py`: el script ya soporta ambos modos.)
- **Definición de hecho:**
  - Existe un objetivo de `make` que ejecuta las 5 etapas — sea `make seed` con las flags, sea un `make seed-full` nuevo referenciado desde el README como el paso de arranque.
  - `make help` lista el objetivo con una descripción que distingue claramente el seed rápido del completo.
  - Con `DATABASE_URL` apuntando a la base local (`make db-up`), tras ejecutar el objetivo:
    - `psql "$DATABASE_URL" -c "select count(*) from style_profiles"` devuelve `3`.
    - `psql "$DATABASE_URL" -c "select count(*) from chunks where embedding is null"` devuelve `0`.
    - `curl -s localhost:8000/api/authors/dickens/style-profile | jq -e '.lexical.mattr_500 > 0'` devuelve éxito.
    - `curl -s localhost:8000/api/authors | jq -e '[.[] | select(.has_style_profile)] | length == 3'` devuelve éxito.
  - El README refleja el comando real y advierte del tiempo/descarga de modelos que implica.
- **Contexto obligatorio para el ejecutor:** `scripts/seed_corpus.py:12-71` (el docstring enumera las 5 etapas y sus flags — es la referencia exacta), `Makefile:51-68` (los objetivos `db-up`/`seed`/`seed-dry` y el patrón `need_file`), `README.md` §"Getting Started (Local Setup)" (el flujo que hay que mantener coherente) y `CONTRIBUTING.md` §1 (el mismo flujo en PowerShell, que también debe quedar coherente).
- **Bloqueada por:** nada.
- **Conflicto de ficheros:** ninguno.
- **Tamaño:** S.
- **Riesgo de regresión:** `make seed` pasa de segundos a minutos y descarga `all-mpnet-base-v2` (~420 MB) más `en_core_web_lg` (~560 MB). Si se cambia el objetivo `seed` existente en vez de añadir uno nuevo, cualquier automatización que lo invoque se vuelve mucho más lenta. Preferible: `seed` rápido se mantiene, `seed-full` nuevo, y el README apunta al segundo.

---

### WO-06 — Cablear `DATABASE_URL` hasta el RAG y cargar `.env` en el backend

- **Origen:** issue #25 · veredicto ⚠️ · módulo `backend`
- **Síntoma:** toda generación se hace **sin pasajes RAG**: el system prompt sale con `(no example passages provided)` y el Passport se emite con `rag_sources: []`. En los logs aparece `RAG retrieval failed for author '<slug>'; continuing with empty chunks.` — y la petición devuelve 200, así que nada lo delata en la UI.
- **Evidencia:** cadena completa:
  - `backend/app/routes/generate.py:167-174` — `await orchestrate(prompt=..., style_profile=..., author_id=..., author_uuid=..., model_id=..., verifier_url=...)`: **no** pasa `database_url`.
  - `ai_pipeline/autoria_ai/generator.py:168-173` — `chunks = await retrieve_fn(prompt_embedding, k=5, author_id=author_uuid, database_url=database_url)` con `database_url=None`.
  - `ai_pipeline/autoria_ai/db.py:83` — `url = database_url or os.environ["DATABASE_URL"]`.
  - `backend/app/config.py:54-68` — `load_settings()` usa `os.getenv` directo; no hay carga de `.env` en ningún módulo del runtime (grep de `dotenv` en `backend/`, `ai_pipeline/`, `scripts/`: único acierto, el helper privado `_load_dotenv_file` de `backend/tests/test_watsonx_client.py:23`, que solo sirve a los tests).
  - `ai_pipeline/autoria_ai/generator.py:174-179` — el `except Exception` que convierte el `KeyError` en un warning y sigue.
  - `backend/app/config.py:62` define `database_url` en `Settings` y **ninguna otra línea del repo lo consume**.
- **Causa raíz:** dos eslabones sueltos que se tapan entre sí. El backend nunca lee `.env` (pese a que `README.md:159-160`, `CONTRIBUTING.md:33-35` y `docs/DEPLOYMENT.md:95-99` instruyen a crearlo), y aunque lo leyera, la ruta no propaga el valor al orquestador. El `except Exception` de `generator.py` es correcto como degradación pero convierte un fallo de configuración en un silencio.
- **Ficheros a tocar:** `backend/app/config.py`, `backend/app/routes/generate.py`, `backend/pyproject.toml`, `backend/requirements.txt`. (No tocar `ai_pipeline/autoria_ai/db.py`: su contrato — `database_url` explícito o env — ya es correcto.)
- **Definición de hecho:**
  - Con `.env` presente y `DATABASE_URL` relleno, arrancar `cd backend && uvicorn app.main:app` y `curl localhost:8000/internal/env-check` devuelve `"all_present": true`. Hoy devuelve `false` salvo que las variables estén exportadas en la shell.
  - `POST /api/generate` contra una base sembrada con embeddings (ver WO-05) devuelve un `passport.json_payload.rag_sources` con **5 elementos**:
    `curl -s -X POST localhost:8000/api/generate -H 'Content-Type: application/json' -d '{"author_id":"dickens","prompt":"a foggy London evening"}' | jq '.passport.json_payload.rag_sources | length'` → `5`.
  - Un test nuevo comprueba que la ruta propaga la DSN al orquestador (p. ej. patcheando `orchestrate` y afirmando el kwarg), y `pytest backend/tests -m "not integration"` termina en 0 fallos.
  - Si `DATABASE_URL` falta, el arranque lo registra explícitamente **una vez** en vez de que cada generación emita un warning genérico de "RAG retrieval failed".
- **Contexto obligatorio para el ejecutor:** `docs/architecture.md` §4.2 (el diagrama de secuencia que sitúa `BE->>DB: RAG top-5 chunks` como paso obligatorio, no opcional), `docs/MVP.md` §4.3 pasos 2-3 (el RAG top-5 es parte del alcance cerrado), `ai_pipeline/autoria_ai/db.py:241-324` (la firma de `retrieve_top_k` y por qué necesita el `author_id` UUID), `.env.example` (nombres canónicos de variables) y `docs/DEPLOYMENT.md` §"Local parity".
- **Bloqueada por:** **WO-02** (comparten `backend/requirements.txt`). Para validar de punta a punta conviene además tener **WO-05** hecho, pero no es un bloqueo formal.
- **Conflicto de ficheros:** `backend/requirements.txt` con **WO-02**. No pueden ir en paralelo.
- **Tamaño:** S.
- **Riesgo de regresión:** si se añade carga de `.env` sin `override=False`, un `.env` obsoleto puede pisar variables inyectadas por la plataforma en producción — Railway/Vercel deben seguir mandando. Y al pasar a haber chunks reales, el system prompt crece: puede destapar el desbordamiento de presupuesto de tokens de **WO-09** (que hasta ahora quedaba oculto precisamente porque `chunks` siempre venía vacío).

---

### WO-07 — Sustituir el `embedding_umap_2d` de ceros por las coordenadas UMAP reales y persistir `umap_coords` en una migración

- **Origen:** issues #16 y #18 · veredictos 🔌 y ⚠️ · módulo `ml`
- **Síntoma:** el scatter 2D del panel Style DNA dibuja a los tres autores en el mismo punto (0,0) con radio de dispersión 0 en cuanto se sirven perfiles reales. La separación de clusters que se ve hoy proviene únicamente de fixtures inventados.
- **Evidencia:**
  - `ai_pipeline/autoria_ai/extractor/style_profile.py:177-178` — `# Placeholder — scripts/precompute_umap.py owns real 2-D coords.` / `"embedding_umap_2d": {"centroid": [0.0, 0.0], "spread": 0.0},`
  - `ai_pipeline/tests/test_style_profile_compute.py:62` afirma ese cero como comportamiento esperado: `assert profile["embedding_umap_2d"] == {"centroid": [0.0, 0.0], "spread": 0.0}`.
  - `scripts/precompute_umap.py:263-271` escribe en `public.umap_coords`; grep de `umap_coords` en todo el repo (fuera de `bob/sessions/`): las 9 apariciones están todas en ese mismo fichero. Nadie la lee.
  - `precompute_umap.py:70-77` crea la tabla con `CREATE TABLE IF NOT EXISTS` en runtime; no aparece en `infra/supabase/migrations/*.sql` ni en `docs/erd.md` §2.
  - Consumidor real: `frontend/src/components/StyleDnaPanel.tsx:406-407` y `:432-433` leen `profile.embedding_umap_2d.centroid` / `.spread`.
- **Causa raíz:** el precómputo se diseñó como una segunda pasada sobre pgvector (correcto: UMAP necesita todos los embeddings de todos los autores a la vez, cosa que `compute_style_profile` — que corre por autor — no puede hacer), pero **nunca se escribió el paso de vuelta** que proyecta el centroide de cada autor y lo escribe en `style_profiles.json_data.embedding_umap_2d`.
- **Ficheros a tocar:** `scripts/precompute_umap.py`, `ai_pipeline/autoria_ai/extractor/style_profile.py`, `ai_pipeline/tests/test_style_profile_compute.py`, `infra/supabase/migrations/0004_umap_coords.sql` (nuevo), `docs/erd.md`. Posiblemente `backend/app/routes/authors.py` si el recompute debe disparar la reproyección.
- **Definición de hecho:**
  - Existe `infra/supabase/migrations/0004_umap_coords.sql` con la DDL de `umap_coords` (idempotente, en el estilo de 0002/0003), y `precompute_umap.py` ya no crea la tabla en runtime.
  - `docs/erd.md` documenta la nueva tabla en §2/§3/§5.
  - Tras `python scripts/precompute_umap.py` sobre una base sembrada con embeddings:
    `curl -s localhost:8000/api/authors/dickens/style-profile | jq '.embedding_umap_2d'` devuelve un centroide **distinto de `[0,0]`** y `spread > 0`.
  - Los tres autores dan centroides distintos entre sí:
    `for a in austen dickens poe; do curl -s localhost:8000/api/authors/$a/style-profile | jq -c '.embedding_umap_2d.centroid'; done` imprime tres pares diferentes.
  - Un test nuevo cubre la proyección (con UMAP mockeado o con un fixture de embeddings sintéticos): `pytest ai_pipeline/tests -k umap` pasa. El assert de ceros de `test_style_profile_compute.py:62` se actualiza o se traslada al caso "sin proyección todavía".
  - `pytest ai_pipeline/tests` sigue en `214+ passed`.
- **Contexto obligatorio para el ejecutor:** `docs/style_features.md` §5.2 (define exactamente cómo se calcula: UMAP se ajusta *una vez* sobre todos los chunks de los tres autores y luego se proyecta el centroide de cada uno; `spread = float(chunk_embeddings.std())`), `docs/api_contract.yaml` §`EmbeddingUmap2d` (la forma `{centroid: [x,y], spread}` está LOCKED — no cambiarla), `docs/erd.md` §5-§6 (convenciones de migración e índices), y `docs/MVP.md:85-86` (para qué sirve: el beat `[01:30]` de la demo).
- **Bloqueada por:** nada. *(Para validar hace falta una base con embeddings — ver WO-05 — pero la implementación no depende de ella.)*
- **Conflicto de ficheros:** ninguno con las WO de la misma ola. Comparte `scripts/seed_corpus.py`? No — no lo toca. Comparte `backend/app/routes/authors.py` solo consigo misma.
- **Tamaño:** M.
- **Riesgo de regresión:** `style_features.md:459` ya avisa de que UMAP no es determinista si cambian los datos de entrada, aun con `random_state=42`; los centroides se moverán entre ejecuciones y los perfiles se invalidarán en cascada (`style_profiles.hash` cambia → `author_voice.style_profile_hash` de los Passports antiguos deja de coincidir con el perfil vigente). Eso es esperado (`erd.md:141`: los recomputes *añaden* fila), pero conviene comprobar que la verificación de Passports antiguos sigue devolviendo `valid: true` — lo hace, porque el verificador comprueba la firma, no la vigencia del perfil.

---

### WO-08 — Pasar los corpus de comparación en el cálculo de StyleProfile del script de siembra

- **Origen:** issue #14 · veredicto ⚠️ · módulo `ml`
- **Síntoma:** el `distinctive_vocab` de los autores sembrados contiene las palabras más frecuentes del autor (artículos filtrados aparte: nombres propios, verbos comunes) en vez de sus términos característicos. La tabla del panel Style DNA y los términos inyectados en el system prompt pierden todo su valor discriminante.
- **Evidencia:** `scripts/seed_corpus.py:634` — `profile = compute_style_profile(author_slug=author_slug, documents=documents, nlp=nlp)`, sin `comparison_lemmas`. En consecuencia `ai_pipeline/autoria_ai/extractor/style_profile.py:136-137` construye `corpora = {author_slug: author_lemmas}`: un solo documento. `vocabulary.py:68` llama a `TfidfVectorizer.fit_transform` sobre esa lista de longitud 1, donde el IDF es idéntico para todos los términos y el ranking colapsa a frecuencia. Contraste: el camino del backend sí lo hace bien (`backend/app/routes/authors.py:84-95` construye `comparison` con los `raw_text` de los demás autores).
- **Causa raíz:** reconocida en el propio docstring (`scripts/seed_corpus.py:620-625`): "computing it well requires lemmatizing every other author's corpus first, which this script does not currently do". El coste percibido era una segunda pasada de spaCy sobre todos los corpus.
- **Ficheros a tocar:** `scripts/seed_corpus.py`. Posiblemente `ai_pipeline/autoria_ai/extractor/style_profile.py` si se decide exponer un helper para reutilizar los lemas ya calculados entre autores.
- **Definición de hecho:**
  - Tras el seed con perfiles, para Dickens:
    `curl -s localhost:8000/api/authors/dickens/style-profile | jq -r '.distinctive_vocab[:10][].term'` contiene al menos un término del conjunto que `docs/style_features.md:305` nombra como referencia (`countenance`, `physiognomy`, `presently`) — o, si no, el ejecutor documenta qué salió y por qué es defendible.
  - Los tres autores no comparten más de ~3 de sus 10 primeros términos entre sí (comprobable con `jq` + `comm`); hoy compartirían muchos más.
  - `compute_distinctive_vocab` recibe un diccionario de **3 claves** en la ruta de siembra: cubierto por un test que patchea la función y afirma `len(corpora) == 3`.
  - `pytest ai_pipeline/tests/test_seed_corpus.py -q` sigue en verde (31 tests).
- **Contexto obligatorio para el ejecutor:** `docs/style_features.md` §4.1 (define TF-IDF con "each author's full corpus is one 'document' and the collection is all three authors combined" — es exactamente lo que falta), `ai_pipeline/autoria_ai/extractor/vocabulary.py:20-55` (la firma `corpora_lemmas: dict[str, str]` que hay que alimentar), `backend/app/routes/authors.py:73-102` (la implementación de referencia que ya lo hace bien — copiar su forma, no su fuente de datos) y `ai_pipeline/autoria_ai/extractor/style_profile.py:68-80,135-141` (cómo se producen los lemas y el tope `_MAX_LEMMA_CHARS`).
- **Bloqueada por:** nada.
- **Conflicto de ficheros:** ninguno con las WO de su ola (**WO-05** toca `Makefile`/`README.md`, no `scripts/seed_corpus.py`).
- **Tamaño:** S.
- **Riesgo de regresión:** el seed con `--with-profiles` se vuelve más lento y consume más memoria (hay que tener lemas de los tres corpus a la vez; `_MAX_LEMMA_CHARS = 800_000` por autor acota el pico). Con 2 M de tokens totales conviene medir antes y después.

---

### WO-09 — Imponer el presupuesto de tokens del system prompt condicionado

- **Origen:** issue #23 · veredicto ⚠️ · módulo `ml`
- **Síntoma:** el prompt condicionado que se envía a Watsonx puede superar los 2 000 tokens exigidos (y el objetivo de ~1 200 de la arquitectura), inflando la latencia de la rama AutorIA justo contra el SLA de 8 s.
- **Evidencia:** `ai_pipeline/autoria_ai/conditioner.py:89-90` — `safe_chunks = rag_chunks[:_MAX_CHUNKS]` / `chunks_text = " | ".join(safe_chunks)`. Es el único límite, y es por número de elementos. Los chunks provienen de `chunks.text`, generados con ventana de 500 tokens (`backend/app/routes/authors.py:51` `_CHUNK_SIZE = 500`; `scripts/seed_corpus.py:130` `CHUNK_SIZE = 500`): 5 × 500 ≈ 2 500 tokens antes de sumar plantilla y vocabulario. El docstring del módulo (`conditioner.py:9-13`) afirma que "The returned string is kept under ~1200 tokens" y que "The safeguard is applied by truncating `rag_chunks` to at most 5 items" — la salvaguarda no garantiza la afirmación. Ningún test lo comprueba: en `ai_pipeline/tests/test_conditioner.py` no hay una sola aserción sobre longitud del resultado (las apariciones de `token` son campos de perfil de ejemplo).
  *Nota:* este desbordamiento está latente hoy porque el RAG siempre devuelve 0 chunks (**WO-06**); se manifestará en cuanto ese cableado se arregle.
- **Causa raíz:** se implementó un proxy (contar elementos) en lugar de la restricción real (contar tokens), y no se añadió el test que habría revelado la diferencia.
- **Ficheros a tocar:** `ai_pipeline/autoria_ai/conditioner.py`, `ai_pipeline/tests/test_conditioner.py`.
- **Definición de hecho:**
  - `build_system_prompt` devuelve siempre una cadena cuyo recuento con `tiktoken.get_encoding("cl100k_base")` es ≤ el presupuesto elegido, con los pasajes recortados (no descartados en bloque) cuando haga falta.
  - Test nuevo con 5 chunks de 500 tokens cada uno que afirma el límite:
    `pytest ai_pipeline/tests/test_conditioner.py -k budget` pasa.
  - Test de que con 0 chunks el prompt sigue siendo válido y contiene el marcador de "sin pasajes" (comportamiento actual, no debe romperse).
  - El docstring del módulo se corrige para describir la salvaguarda real.
  - `pytest ai_pipeline/tests -q` sigue en `214+ passed`.
- **Contexto obligatorio para el ejecutor:** `docs/MVP.md` §4.3 (la plantilla literal del prompt y el SLA "< 8s (P95)"), `docs/architecture.md:315` (la fila "Latencia" fija "lean system prompt (< ~1200 tok)" — el número que manda si hay conflicto con los 2 000 del texto de la issue: elegir el más restrictivo y dejarlo constante en una sola constante del módulo), y `ai_pipeline/autoria_ai/generator.py:194-204` (cómo se consume el prompt y por qué su tamaño pesa en la latencia).
- **Bloqueada por:** nada.
- **Conflicto de ficheros:** ninguno.
- **Tamaño:** S.
- **Riesgo de regresión:** recortar pasajes por tokens puede cortar frases a media palabra y degradar la calidad del condicionamiento. Recortar por límite de frase dentro del presupuesto es preferible a cortar en seco. Un recorte demasiado agresivo bajaría el `fit_score` de la rama AutorIA — el efecto contrario al buscado.

---

### WO-10 — Restablecer el acceso a Watsonx: asociar el proyecto a una instancia WML

- **Origen:** issue #22 · veredicto ⚠️ · módulo `backend`/infra
- **Síntoma:** cualquier llamada real a Watsonx devuelve 403 tras 4 intentos. En la aplicación, `POST /api/generate` responde 503 "Generation timed out or LLM provider is unavailable". **No se puede generar ni una sola palabra hoy.**
- **Evidencia:** salida literal de `pytest backend/tests --ignore=tests/test_generate.py`:
  ```
  Failure during chat. (POST https://eu-de.ml.cloud.ibm.com/ml/v1/text/chat?version=2026-07-08)
  Status code: 403, body: {"errors":[{"code":"no_associated_service_instance_error",
    "message":"project_id 614cdac6-f924-43e9-a325-c00773883b4c is not associated with a WML instance",
    "more_info":"https://cloud.ibm.com/apidocs/watsonx-ai#text-chat"}],...}
  WARNING  app.services.watsonx_client:watsonx_client.py:143 Watsonx error on attempt 4/4: ApiRequestFailure
  ...
  FAILED tests/test_watsonx_client.py::test_generate_live_watsonx - app.services.watsonx_client.WatsonxError: Watsonx generate failed after 4 attempts
  ```
- **Causa raíz:** configuración de cuenta IBM Cloud, no de código. El `WATSONX_PROJECT_ID` configurado no tiene una instancia de Watson Machine Learning asociada. Secundariamente, el `WATSONX_URL` efectivo es `eu-de` mientras `.env.example:22` sugiere `us-south`: conviene verificar que región del proyecto y región de la instancia coinciden. **Hipótesis a comprobar primero:** entrar en el proyecto en watsonx.ai → pestaña *Manage* → *Services & integrations* y confirmar si hay una instancia WML asociada; si no la hay, asociarla; si la hay, comprobar que su región coincide con `WATSONX_URL`.
- **Ficheros a tocar:** ninguno del código de la aplicación. Como mucho `.env` (no versionado), las variables de Railway, y una nota en `docs/DEPLOYMENT.md` documentando el requisito de asociar la instancia WML. **Si el diagnóstico revela que hace falta cambiar de modelo o de región, eso es un hallazgo nuevo: reportarlo, no decidirlo.**
- **Definición de hecho:**
  - `pytest backend/tests/test_watsonx_client.py::test_generate_live_watsonx -q` pasa (hoy falla).
  - `python -c "import sys; sys.path.insert(0,'backend'); from app.services.watsonx_client import generate; print(generate('Reply with one word: pong', None, 'meta-llama/llama-3-3-70b-instruct', {'max_tokens':8,'temperature':0}))"` imprime texto.
  - Contra el backend desplegado: `curl -X POST https://<railway>/api/generate -H 'Content-Type: application/json' -d '{"author_id":"dickens","prompt":"a foggy London evening in the 1840s"}'` devuelve **200** con `vanilla.text` y `autoria.text` no vacíos.
  - Se mide y se anota la latencia observada de ese 200 (input para el SLA de `docs/MVP.md:495`, "<8s P95").
  - `docs/DEPLOYMENT.md` menciona el requisito de la instancia WML asociada en la sección de variables.
- **Contexto obligatorio para el ejecutor:** `backend/app/services/watsonx_client.py:33-40,61-87` (cómo se construyen las credenciales y por qué se usa `validate=False`, que es lo que hace que el fallo aparezca en la llamada y no antes), `.env.example` §"IBM Watsonx" (los tres nombres de variable), `docs/DEPLOYMENT.md` §"Required environment variables", y `docs/MVP.md` §2 (los model IDs están LOCKED: `meta-llama/llama-3-3-70b-instruct` como creativo, `ibm/granite-3-8b-instruct` como auxiliar — no cambiarlos por iniciativa propia).
- **Bloqueada por:** nada.
- **Conflicto de ficheros:** ninguno (solo `docs/DEPLOYMENT.md`, que nadie más toca en su ola).
- **Tamaño:** S (si es solo asociar la instancia); puede escalar si obliga a recrear el proyecto.
- **Riesgo de regresión:** cambiar región o proyecto invalida las credenciales que ya estén cargadas en Railway y en los `.env` de los tres desarrolladores; hay que actualizarlas de forma coordinada. Ninguna de esas variables está versionada, así que el riesgo es de coordinación, no de código.

---

### WO-11 — REQUIERE DECISIÓN — Resolver la sustitución silenciosa de StyleProfiles por fixtures inventados

> **Esta orden no debe despacharse hasta que una persona elija entre las opciones de abajo.** Toca un compromiso explícito entre fiabilidad de la demo y la regla de honestidad que el propio equipo se impuso, y ya hay una decisión registrada que el código contradice.

- **Origen:** issue #41 · veredicto ⚠️ · módulo `frontend`
- **Síntoma:** cuando el backend no tiene StyleProfile para un autor precargado (404, el estado normal tras `make seed`), la pantalla Style DNA muestra métricas, radar, scatter y vocabulario **inventados a mano**, presentados exactamente igual que los reales. El único indicio es un `console.info` que nadie mira.
- **Evidencia:**
  - `frontend/src/components/StyleDnaPanel.tsx:374-391` — el `catch` devuelve `FIXTURE_STYLE_PROFILES[authorId]` ante *cualquier* error, y su propio docstring lo dice: "we fall back on ANY failure — network, 5xx, **OR a 404 from an unseeded DB**".
  - `docs/design-system.md:276` (decisión de 2026-07-13) dice lo contrario: "On network failure only (**not a real 404**)". El cambio llegó en el PR #76 (`ef69410 fix(front): fall back to fixture StyleProfile on 404 for preloaded authors`) sin entrada correctora en `docs/decision_log.md`, que es donde `docs/MVP.md:4` exige registrarlas.
  - `frontend/src/lib/fixtures/style-profiles.ts:8-9` — la cabecera del fichero afirma una garantía que ya no se cumple: "They are NOT used when the live API returns a real 404 … ONLY substituted on network failure".
  - `frontend/src/lib/fixtures/style-profiles.ts:16-17` — los valores no son mediciones: "Centroids are spaced apart in UMAP space so the scatter plot is readable".
  - Contraste con los rangos del documento rector: fixture Austen `mattr_500: 0.72` y `hapax_ratio: 0.18` frente a los rangos 0.62-0.68 y 0.38-0.44 de `docs/style_features.md:413,415`.
  - Efecto amplificador: `frontend/src/lib/authors.ts:9-34` pinta las tres tarjetas con `has_style_profile: true` incondicional cuando `GET /api/authors` falla.
- **Causa raíz:** una elección deliberada de fiabilidad de demo tomada cuando el seed real no existía (el comentario del código todavía dice "that seed script is missing", cosa ya falsa desde el commit `d802923`). El problema no es tener fixtures: es que sean **indistinguibles** de datos reales y que contradigan una decisión registrada.

**Opciones (elegir una):**

| # | Opción | Coste | Consecuencia |
|---|---|---|---|
| A | Restaurar la decisión registrada: fixtures **solo** en fallo de red/5xx; el 404 vuelve al estado vacío neutro. | XS | Coherente con `design-system.md:276` sin más cambios. Riesgo: si el día de la demo la base no está sembrada, la pantalla Style DNA sale vacía. Mitigación: WO-05. |
| B | Mantener el fallback en 404 pero **marcarlo visiblemente** en la UI (chip "sample data" / banner). | S | Preserva la fiabilidad de demo sin engañar; requiere copia nueva en `en.ts`, un token/variante visual y actualizar `design-system.md` §7. |
| C | Mantener el comportamiento actual y **corregir la decisión** en `docs/decision_log.md` + la cabecera de `fixtures/style-profiles.ts`, asumiendo el riesgo por escrito. | XS | Lo más barato; deja la pantalla capaz de presentar datos inventados como reales ante un jurado. Choca con `design-system.md:258` ("never faked"). |

En cualquiera de las tres: **los valores de los fixtures deben alinearse con los rangos de `docs/style_features.md` §7** (hoy no lo están) para que, si se muestran, al menos sean plausibles.

- **Ficheros a tocar:** `frontend/src/components/StyleDnaPanel.tsx`, `frontend/src/lib/fixtures/style-profiles.ts`, `docs/decision_log.md`. En la opción B, además `frontend/src/lib/i18n/en.ts` y `docs/design-system.md`.
- **Definición de hecho (común a las tres opciones):**
  - Existe una entrada nueva en `docs/decision_log.md` con fecha, decisión y razón, que reconcilia explícitamente el código con `docs/design-system.md:276`.
  - La cabecera de `frontend/src/lib/fixtures/style-profiles.ts` describe el comportamiento real (hoy miente).
  - Un test unitario cubre la elección: con un `NotFoundError`, `fetchProfileWithFallback` hace lo que la decisión diga (lanzar, o devolver el fixture marcado). `cd frontend && npm run test` en verde.
  - Los valores de fixture caen dentro de los rangos de `docs/style_features.md:413-422`; comprobable con un test de rangos.
  - `npx tsc --noEmit && npx eslint .` en exit 0.
  - (Opción B) La pantalla muestra el distintivo: verificable arrancando el front con el backend apagado y comprobando que el texto de aviso aparece.
- **Contexto obligatorio para el ejecutor:** `docs/design-system.md` §8 completo — sobre todo §8.6 ("Honesty rule: both columns use the same model and the real scores. The contrast is earned by design, never faked") y la fila `:276` del decision log interno —, `docs/decision_log.md` (formato append-only, una fila por decisión), `docs/style_features.md` §7 (los rangos esperados por autor) y `docs/MVP.md:4` (la política de cambio: 2/3 votos + entrada en el decision log).
- **Bloqueada por:** la decisión humana. Técnicamente por nada.
- **Conflicto de ficheros:** ninguno con el resto de WO.
- **Tamaño:** XS (A o C) / S (B).
- **Riesgo de regresión:** la opción A puede dejar la pantalla Style DNA vacía en la grabación de la demo si la base no está sembrada — despacharla solo junto con **WO-05** ya verificado.

---

### WO-12 — Alimentar el vocabulario distintivo en la columna AutorIA del side-by-side

- **Origen:** issue #28 · veredicto ⚠️ · módulo `frontend`
- **Síntoma:** en la comparación lado a lado, ningún término aparece resaltado en la columna AutorIA. El dispositivo visual que debía hacer obvia la diferencia sin leer no se activa nunca, ni siquiera cuando la generación es perfecta.
- **Evidencia:** `frontend/src/components/GenerateStudio.tsx:49`:
  ```tsx
  const [distinctiveTerms] = useState<readonly string[]>([]);
  ```
  Declarado sin setter y nunca reasignado. Se pasa a `SideBySideOutput.tsx:47` → `AuthorColumn.tsx:117-125`, donde `(props.distinctiveTerms?.length ?? 0) > 0` es siempre falso, así que ni el `<mark>` ni la leyenda se renderizan. El comentario en `GenerateStudio.tsx:43-48` lo reconoce: "Not fetched here; could be passed in from a parent that already has the StyleProfile loaded".
- **Causa raíz:** el componente `DistinctiveVocabHighlight` se construyó y se cableó, pero el dato nunca se conectó a su fuente. El `StyleProfile` con `distinctive_vocab` ya se descarga en la misma página: `StyleDnaPanel` lo obtiene (`StyleDnaPanel.tsx:84`) y lo usa para su tabla top-10 (`:236-238`). Falta izarlo al padre común (`frontend/src/app/author/[id]/page.tsx`) o volver a pedirlo desde `GenerateStudio`.
- **Ficheros a tocar:** `frontend/src/components/GenerateStudio.tsx`. Probablemente también `frontend/src/app/author/[id]/page.tsx` y `frontend/src/components/StyleDnaPanel.tsx` si se opta por izar el estado. **Si se toca `StyleDnaPanel.tsx`, coordinar con WO-11.**
- **Definición de hecho:**
  - Con una generación exitosa para `dickens`, la columna AutorIA renderiza al menos un `<mark>` cuando el texto generado contiene alguno de los términos de `StyleProfile.distinctive_vocab`; la columna vanilla no recibe términos (el contraste es el punto).
  - La leyenda de una línea que `AuthorColumn.tsx:125` condiciona a `distinctiveTerms.length > 0` aparece.
  - Test unitario de la función de selección de términos (siguiendo la convención "pure-function unit tests only" de `decision_log.md` 2026-07-21): `cd frontend && npm run test` en verde.
  - `npx tsc --noEmit && npx eslint .` en exit 0.
  - Grep de comprobación: `grep -n "useState<readonly string\[\]>(\[\])" frontend/src/components/GenerateStudio.tsx` no devuelve nada.
  - Si `distinctive_vocab` viene vacío (perfil sin calcular), la columna se degrada sin romperse — no debe lanzar.
- **Contexto obligatorio para el ejecutor:** `docs/design-system.md` §8 punto 4 ("Highlighted signature vocabulary … only in the AutorIA column, with a one-line legend. The vanilla side has nothing to highlight — its blankness is the point") y §7 (el inventario de componentes y la regla de props tipadas desde `lib/types.ts`), `docs/MVP.md:82-83` (el beat de demo que esto materializa), `frontend/src/components/AuthorColumn.tsx:110-130` (el contrato de props que ya existe — **no cambiarlo**, solo alimentarlo) y `docs/api_contract.yaml` §`DistinctiveTerm` (la forma `{term, score}`).
- **Bloqueada por:** nada. *(Para que los términos sean realmente distintivos y no meras palabras frecuentes hace falta **WO-08**; el resaltado funciona igual sin ella, con peor calidad de datos.)*
- **Conflicto de ficheros:** comparte `GenerateStudio.tsx` con **WO-13**; comparte potencialmente `StyleDnaPanel.tsx` con **WO-11**. No pueden ir en paralelo con ninguna de las dos.
- **Tamaño:** S.
- **Riesgo de regresión:** izar el estado del `StyleProfile` al componente servidor de la página puede duplicar la petición `GET /api/authors/{id}/style-profile` (una en el padre, otra en `StyleDnaPanel`), o forzar a convertir `StyleDnaPanel` en controlado — lo que tocaría sus cinco estados (loading/empty/error/ready/collapsed). Preferible pasar el perfil hacia abajo desde un único punto de carga.

---

### WO-13 — Mostrar el Passport decodificado en pantalla (componente `PassportCard`)

- **Origen:** issue #42 · veredicto ⚠️ · módulo `frontend`
- **Síntoma:** al pulsar "Download Passport" el fichero se descarga a disco y **no aparece nada en pantalla**. En la demo, el momento "Generate Passport → el JSON aparece" no ocurre.
- **Evidencia:** `frontend/src/components/GenerateStudio.tsx:135-151` renderiza únicamente el `<Button>`; su `onClick` llama a `downloadPassport` (`frontend/src/lib/passport.ts:25-39`), que crea un `Blob` y dispara un `<a download>`. No existe `frontend/src/components/PassportCard.tsx` (listado completo de `frontend/src/components/` verificado: 20 ficheros, ninguno con ese nombre). `docs/design-system.md:212` lo inventaría como componente de Sprint 2 en estado "ready": "`PassportCard` | 2 | studio, verify | ready | Mono JSON block + `Download` action". El cuerpo de la issue #42 pide explícitamente "(2) render decoded Passport JSON in a collapsible syntax-highlighted panel on screen".
- **Causa raíz:** el AC se implementó a medias; la decisión de `decision_log.md` (2026-07-21) que acotó el botón de #28 a "affordance only" remitía la parte visible a "#42/#44", y en #42 solo se hizo la descarga.
- **Ficheros a tocar:** `frontend/src/components/PassportCard.tsx` (nuevo), `frontend/src/components/GenerateStudio.tsx`, `frontend/src/lib/i18n/en.ts`.
- **Definición de hecho:**
  - Tras una generación exitosa con `passport !== null`, la pantalla studio muestra un panel colapsable con el `json_payload` formateado en `font-mono`, y el botón de descarga sigue funcionando.
  - El panel usa los tokens y clases del sistema (`font-mono`, `rounded-lg`, `border-border`, `bg-muted/50`) — no colores crudos de Tailwind.
  - Toda cadena visible pasa por `frontend/src/lib/i18n/en.ts` (regla de `CONTRIBUTING.md` §8.6 y `design-system.md` §7.5).
  - `frontend/src/app/verify/page.tsx:226-239` ya tiene un bloque equivalente de "raw JSON toggle": si se factoriza, ambas pantallas deben seguir funcionando y `npm run test` seguir en verde. Si no se factoriza, dejar constancia de la duplicación deliberada.
  - `cd frontend && npm run test && npx tsc --noEmit && npx eslint .` todo en exit 0.
- **Contexto obligatorio para el ejecutor:** `docs/design-system.md` §7 (la fila de `PassportCard` y las 7 reglas para añadir un componente: ubicación, props desde `lib/types.ts`, solo tokens, tres estados mínimos, strings en `en.ts`, uniones discriminadas, suelo de accesibilidad) y §3 (la fila "Forensic": `font-mono` para hashes, JWS y JSON), `docs/api_contract.yaml` §`PassportEnvelope`/`PassportPayload` (la forma exacta a renderizar), `frontend/src/app/verify/page.tsx:96-242` (implementación de referencia de la tabla del payload — reutilizarla si tiene sentido) y `docs/MVP.md:87` (el beat de demo).
- **Bloqueada por:** **WO-12** (comparten `GenerateStudio.tsx`).
- **Conflicto de ficheros:** `GenerateStudio.tsx` con **WO-12**. `en.ts` con nadie más en su ola.
- **Tamaño:** S.
- **Riesgo de regresión:** el `json_payload` completo es largo; si el panel se renderiza expandido por defecto empuja el resto de la pantalla fuera del viewport y rompe el encuadre de la demo. Debe nacer colapsado.

---

### WO-14 — Ejecutar y registrar la evaluación de baseline de voice-matching de Llama-3.3-70B

- **Origen:** issue #11 · veredicto ❌ · módulo `bob`
- **Síntoma:** no existe ninguna evidencia de que el modelo elegido sea capaz de imitar una voz autoral. La puerta de riesgo R1 del MVP se dio por superada sin datos.
- **Evidencia de la ausencia:** `bob/sessions/week1/baseline_eval.md` no existe. Búsquedas realizadas: `find . -iname "*baseline*"` (solo un acierto dentro de `.venv`, ajeno); grep insensible de `baseline|voice-match|5 prompts|llama-3-1-405b|6/10` sobre `bob/**/*.md` (dos aciertos metodológicos, `bob/playbook.md:146` y `bob/custom-modes/generation-conductor.md:95`, ningún resultado); `git log --all --diff-filter=A --name-only --pretty=format: | grep -i "baseline\|week1\|week2"` → **cero** (el fichero nunca existió en ninguna rama); `gh pr list --state merged` → ningún PR referido a #11. Los 26 exports de `bob/sessions/` no contienen puntuaciones de calidad de voz.
- **Causa raíz:** la tarea se cerró sin ejecutarse. No hay causa técnica.
- **Ficheros a tocar:** `bob/sessions/Sprint_1/baseline_eval.md` (nuevo — usar la convención de carpetas real del repo, `Sprint_1/`, no el `week1/` del texto de la issue, que ya no se usa). Si el resultado dispara la escalada, además una entrada en `docs/decision_log.md`.
- **Definición de hecho:**
  - El documento existe y contiene: los **5 prompts fijos** (textuales), el autor objetivo de cada uno, la salida **sin condicionar** de `meta-llama/llama-3-3-70b-instruct`, una puntuación 1-10 de parecido de voz por prompt con quién la puso, y la media.
  - El veredicto de la puerta está escrito explícitamente: media ≥ 6/10 → seguir con Llama 3.3 70B; media < 6/10 → escalar según `docs/MVP.md:512` (R1: condicionamiento más fuerte / más pasajes RAG, `llama-3-1-405b`, `granite-3-8b`, y como último recurso Mistral Large vía Watsonx), y en ese caso una fila nueva en `docs/decision_log.md`.
  - Las salidas son reproducibles: el documento anota `model_id`, `temperature`, `max_tokens` y fecha.
  - Comprobación: `test -f bob/sessions/Sprint_1/baseline_eval.md && grep -c "^## Prompt" bob/sessions/Sprint_1/baseline_eval.md` devuelve `5`.
- **Contexto obligatorio para el ejecutor:** `docs/MVP.md` §2 (los model IDs LOCKED y el porqué de usar el mismo modelo en ambos lados), `docs/MVP.md:329` (el enunciado de la SPRINT 1 TASK: "validate voice-matching quality with 5 real prompts … if Llama < 6/10 human eval, escalate"), `docs/MVP.md:512` (la fila R1 con el plan B exacto), `docs/MVP.md:78-80` (el prompt de la demo, buen candidato a ser uno de los cinco) y `bob/playbook.md` (formato de export de sesiones que el equipo ya usa).
- **Bloqueada por:** **WO-10**. Sin acceso funcional a Watsonx no se puede generar nada que evaluar.
- **Conflicto de ficheros:** ninguno.
- **Tamaño:** S.
- **Riesgo de regresión:** ninguno sobre el código. Riesgo de proyecto real: si la media sale < 6/10, se abre una escalada de modelo a estas alturas del calendario. Ese resultado hay que **reportarlo, no maquillarlo** — es exactamente para lo que existía la puerta.

---

### WO-15 — Llevar el estilo de `/verify` a los tokens e iconos del sistema de diseño

- **Origen:** issue #29 · veredicto ⚠️ · módulo `frontend`
- **Síntoma:** el banner de error de red de `/verify` usa un ámbar que no pertenece a la paleta del producto y desentona en modo oscuro; ninguno de los tres banners lleva icono, y el sello "verificado" no tiene la animación que el sistema le reserva.
- **Evidencia:** `frontend/src/app/verify/page.tsx:505-506` — `className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3"` y `className="font-heading text-lg font-semibold text-amber-600 dark:text-amber-400"`. Contra `docs/design-system.md` §1 ("**Don't** … No hardcoded hex/oklch in components — tokens only"), teniendo `--warning`, `--warning-tint` y `--warning-foreground` definidos en §2.2 justo para esto. Además §6 exige iconos acompañando etiqueta (`BadgeCheck` verificado, `ShieldAlert` inválido, `Clock` timeout) y `verify/page.tsx` no importa ninguno de `lucide-react`; y §5/§7 asignan `.animate-stamp-in` al `VerifiedBanner`, que no se usa (`verify/page.tsx:453-461`).
- **Causa raíz:** la pantalla se construyó contra la funcionalidad del contrato y no se pasó por la lista de §7 ("Rules for adding a component") antes de cerrar.
- **Ficheros a tocar:** `frontend/src/app/verify/page.tsx`. Solo si falta algún token, `frontend/src/app/globals.css` **y** una fila nueva en `docs/design-system.md` §2 en el mismo cambio (regla §7.3).
- **Definición de hecho:**
  - `grep -nE "amber-|slate-|zinc-|#[0-9a-fA-F]{3,6}" frontend/src/app/verify/page.tsx` no devuelve nada.
  - El banner de éxito usa `--success`/`--success-tint` con `BadgeCheck`; el de inválido usa `--destructive` con `ShieldAlert`; el de red usa `--warning-tint` + `--warning-foreground` con `Clock` o `TriangleAlert`.
  - El banner de verificado aplica `.animate-stamp-in`, y `prefers-reduced-motion: reduce` la desactiva (el bloque ya existe en `globals.css`).
  - `cd frontend && npx tsc --noEmit && npx eslint . && npm run test` todo en exit 0.
  - Comprobación visual en ambos temas: la pantalla `/verify` con un token válido, uno manipulado y el backend apagado, en claro y en oscuro.
- **Contexto obligatorio para el ejecutor:** `docs/design-system.md` §2.2 (tokens de estado y la advertencia de contraste: "White text on `--warning` — never; use `--warning-foreground` on `--warning-tint`"), §5 (tokens de movimiento y `.animate-stamp-in`), §6 (los iconos canónicos de lucide-react y la regla de que acompañan, no sustituyen, a la etiqueta) y §7 filas `VerifiedBanner`/`PassportErrorList`. `docs/passport_schema.md` §8.2 da la copia por tipo de error (ya implementada en `en.ts` — no reescribirla).
- **Bloqueada por:** nada.
- **Conflicto de ficheros:** ninguno.
- **Tamaño:** XS.
- **Riesgo de regresión:** tocar `globals.css` afecta a todas las pantallas; si los tokens `--warning*` ya existen (lo hacen, §2.2), no debería hacer falta editarlo. Verificar el contraste AA en ambos temas antes de dar por hecho.

---

## Plan de despacho

Las olas están ordenadas por **impacto sobre el Definition of Done** (`docs/MVP.md:490-504`), no por facilidad. Se ha verificado explícitamente que dos WO de la misma ola no comparten **ningún** fichero.

### Ola 1 — desbloquear el Definition of Done (paralelizable, sin ficheros compartidos)

| WO | Qué desbloquea del DoD | Ficheros |
|---|---|---|
| **WO-10** | "Side-by-side generation works end-to-end" — hoy imposible (403) | `docs/DEPLOYMENT.md` |
| **WO-02** | Generación en el backend desplegado (hoy `ImportError`) | `railway.toml`, `backend/requirements.txt` |
| **WO-01** | Que el frontend desplegado hable con el backend | `frontend/src/lib/api.ts` |
| **WO-07** | "3 preloaded authors … **visualizable** StyleProfile" + el beat `[01:30]` de la demo | `scripts/precompute_umap.py`, `ai_pipeline/autoria_ai/extractor/style_profile.py`, `ai_pipeline/tests/test_style_profile_compute.py`, `infra/supabase/migrations/0004_umap_coords.sql`, `docs/erd.md`, `backend/app/routes/authors.py` |
| **WO-04** | Que "los tests del backend pasan" deje de ser falso | `backend/tests/test_generate.py` |

Comprobación de disjunción: `docs/DEPLOYMENT.md` · `railway.toml`+`backend/requirements.txt` · `frontend/src/lib/api.ts` · `scripts/`+`ai_pipeline/`+`infra/`+`docs/erd.md`+`backend/app/routes/authors.py` · `backend/tests/test_generate.py`. **Sin intersección.**

### Ola 2 — datos reales de punta a punta (depende de la ola 1)

| WO | Bloqueo | Ficheros |
|---|---|---|
| **WO-06** | bloqueada por **WO-02** (`backend/requirements.txt`) | `backend/app/config.py`, `backend/app/routes/generate.py`, `backend/pyproject.toml`, `backend/requirements.txt` |
| **WO-03** | bloqueada por **WO-04** (si no, CI nace en rojo) | `.github/workflows/ci.yml` |
| **WO-05** | — | `Makefile`, `README.md` |
| **WO-08** | — | `scripts/seed_corpus.py` |
| **WO-12** | — | `frontend/src/components/GenerateStudio.tsx` (+ `app/author/[id]/page.tsx`) |

Comprobación de disjunción: `backend/app/*`+`backend/pyproject.toml`+`backend/requirements.txt` · `.github/` · `Makefile`+`README.md` · `scripts/seed_corpus.py` · `frontend/src/components/GenerateStudio.tsx`. **Sin intersección.** (WO-05 se ha acotado deliberadamente a `Makefile`/`README.md` para no chocar con WO-08 en `scripts/seed_corpus.py`.)

### Ola 3 — completar ACs pendientes (depende de la ola 2)

| WO | Bloqueo | Ficheros |
|---|---|---|
| **WO-13** | bloqueada por **WO-12** (`GenerateStudio.tsx`) | `frontend/src/components/PassportCard.tsx`, `frontend/src/components/GenerateStudio.tsx`, `frontend/src/lib/i18n/en.ts` |
| **WO-14** | bloqueada por **WO-10** | `bob/sessions/Sprint_1/baseline_eval.md` |
| **WO-09** | — (se recomienda tras **WO-06**, que es cuando el desbordamiento se manifiesta) | `ai_pipeline/autoria_ai/conditioner.py`, `ai_pipeline/tests/test_conditioner.py` |
| **WO-15** | — | `frontend/src/app/verify/page.tsx` |

Comprobación de disjunción: `frontend/src/components/*`+`en.ts` · `bob/sessions/` · `ai_pipeline/` · `frontend/src/app/verify/page.tsx`. **Sin intersección.**

### Requieren decisión humana antes de despachar

- **WO-11** — sustitución silenciosa de StyleProfiles por fixtures. Tres opciones con costes en la ficha. Si se elige A, despachar **después** de WO-05 verificado (si no, la pantalla Style DNA queda vacía en la demo). Si se elige B, entra en la ola 3 y **entra en conflicto con WO-12** por `StyleDnaPanel.tsx` en caso de que WO-12 opte por izar el estado — resolver el orden en cuanto haya decisión.

---

## Resumen ejecutivo

**¿Se cumple el Definition of Done? No.** De los 8 criterios auditables desde el repo (3 quedan fuera de alcance: vídeo, curso SkillsBuild y envío), **3 se cumplen y 5 no**.

Se cumplen: el **Authorship Passport se emite, se firma en ES256 y verifica** — comprobado ejecutando el roundtrip completo, con rechazo correcto de token manipulado (`invalid_signature`) y de `alg:none` (`unsupported_algorithm`), y JWKS sirviendo `kid`/`alg` correctos con su `Cache-Control`; los **4 Custom Modes** están documentados; y hay **26 exports BobShell**, más del doble del mínimo de 12. El código del pipeline es de buena calidad: extractores fieles a `style_features.md`, `fit_score` con los pesos exactos del documento, 214 tests de pipeline y 43 de frontend en verde, ruff y black limpios.

No se cumplen: **(1)** la generación side-by-side no funciona de punta a punta — Watsonx devuelve 403 porque el proyecto no tiene instancia WML asociada, y en Railway ni siquiera llegaría a la llamada porque el build no instala las dependencias de `ai_pipeline`; **(2)** los 3 autores no tienen StyleProfile visualizable en el camino documentado — `make seed` no calcula ni embeddings ni perfiles, y el `embedding_umap_2d` que consume la pantalla es un `[0,0]` fijo mientras el UMAP real se escribe en una tabla que nadie lee; **(3)** la aplicación desplegada está rota de raíz por un nombre de variable de entorno equivocado en `frontend/src/lib/api.ts:30`, que manda todas las llamadas del navegador a `localhost:8000`; **(4)** la puerta de validación de voz de Sprint 1 (issue #11) se cerró sin ejecutarse: su entregable nunca existió en el historial de git; **(5)** el README remite a un `bob/usage-report.md` que sigue siendo un esqueleto de TODOs con enlaces a capturas inexistentes.

**Dos hallazgos transversales merecen atención propia.** El primero: `pytest backend/tests` **no llega a coleccionar** — una fuga de `sys.modules` en `test_generate.py` rompe la importación de `test_watsonx_client.py` —, y como CI no ejecuta ningún job de pytest pese a que la issue #4 lo exigía literalmente, nadie lo ha visto. Toda afirmación de "los tests pasan" para el backend es hoy una declaración sin prueba. El segundo: la pantalla Style DNA sustituye silenciosamente los perfiles por **fixtures inventados a mano** ante cualquier error, incluido el 404 permanente que produce el seed actual, contradiciendo tanto la decisión registrada en `design-system.md:276` como la regla de honestidad que el propio equipo se impuso en §8.6. El resultado combinado es una aplicación que **parece funcionar con cero datos reales detrás** — que es precisamente el riesgo que esta auditoría existía para detectar.

Las 15 órdenes de trabajo están ordenadas para atacar primero eso: la ola 1 devuelve la capacidad de generar y desplegar, la ola 2 lleva datos reales de punta a punta, y la ola 3 cierra los criterios de aceptación sueltos. Una sola orden (**WO-11**) requiere una decisión humana antes de despacharse.
