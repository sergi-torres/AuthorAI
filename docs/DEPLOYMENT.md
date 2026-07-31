# Deployment — Vercel (frontend) + Railway (backend)

AutorIA is a monorepo deployed as **two services from one GitHub repo**
(`github.com/sergi-torres/autorIA`).

## Production URLs (live)

| What | URL |
| --- | --- |
| **App** | <https://quebasto.com> |
| **Passport verifier** | <https://quebasto.com/verify> |
| **API** | <https://api.quebasto.com> |
| Liveness | <https://api.quebasto.com/health> |
| Public key (JWKS) | <https://api.quebasto.com/.well-known/jwks.json> |
| Secrets present? | <https://api.quebasto.com/internal/env-check> |
| OpenAPI docs | <https://api.quebasto.com/docs> |

Post-deploy smoke check — lists authors, reads a profile, generates side by side,
issues a Passport, verifies it, and confirms a tampered one is rejected:

```bash
python scripts/smoke_demo.py --base-url https://api.quebasto.com
```

> ⚠️ **The domain sits behind Cloudflare**, which rejects some non-browser user agents
> with `403`. `curl` passes; a bare `Python-urllib/3.x` agent does not, so
> `smoke_demo.py` can report `403` on every step against the public domain while the
> API is perfectly healthy. If that happens, run the script against the Railway origin
> URL instead, or confirm by hand with `curl`. A `403` on **every** step is this, not
> an outage — a real outage looks like `502`/`503` or a connection error.

---

| Service       | Platform | Root directory | Deploys           |
| ------------- | -------- | -------------- | ----------------- |
| `frontend/`   | Vercel   | `frontend`     | Next.js app       |
| `backend/` + `ai_pipeline/` | Railway | _(empty / repo root)_ | FastAPI API |
| _Postgres_    | Supabase | —              | DB + pgvector     |

The **root directory** setting is the key to a monorepo deploy: Vercel builds
only `frontend/`. Railway must use the **repo root** so both `backend/` and
`ai_pipeline/` are in the image (passport verify imports `autoria_ai`).

---

## Required environment variables

These three secrets must be injected on **both** platforms:

| Variable          | Used by            | Notes                                                  |
| ----------------- | ------------------ | ------------------------------------------------------ |
| `WATSONX_API_KEY` | backend            | IBM Watsonx generation                                 |
| `SUPABASE_URL`    | backend + frontend | Supabase project URL                                   |
| `SUPABASE_KEY`    | backend + frontend | `service_role` on the backend; `anon` on the frontend  |

Commonly needed alongside them (see `.env.example`): `WATSONX_URL`,
`WATSONX_PROJECT_ID`, `DATABASE_URL`, `AUTORIA_CORS_ORIGINS`,
`NEXT_PUBLIC_API_BASE_URL`.

> Frontend note: only variables prefixed `NEXT_PUBLIC_` are exposed to the
> browser. Never expose the `service_role` key to the frontend.

---

## Railway — backend

1. **New Project → Deploy from GitHub repo** → select `autorIA`.
2. Open the service → **Settings → Root Directory** = **empty** (repo root).
   Do **not** set it to `backend/`. Build logs that say
   `snapshot-target-unpack/backend` or a start plan of
   `uvicorn app.main:app` (without `cd backend`) mean Root Directory is
   still `backend/` — clear it and redeploy.
   Also clear any **Custom Start Command** in Settings so the root
   `railway.toml` wins (`cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
3. **Variables** → add: `WATSONX_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`,
   plus `WATSONX_URL`, `WATSONX_PROJECT_ID`, `DATABASE_URL`, and
   `AUTORIA_CORS_ORIGINS` (include your Vercel URL once you have it).

   **Passport signing keys — required, and easy to miss.** `.gitignore`
   excludes `keys/**` and `*.pem`, so the deployed image contains **no key
   files**: pointing `PASSPORT_*_KEY_PATH` at `keys/…` resolves to nothing in
   Railway. Add instead:

   | Variable | Value |
   | --- | --- |
   | `PASSPORT_PRIVATE_KEY_PEM` | full contents of `keys/passport.priv.pem` |
   | `PASSPORT_PUBLIC_KEY_PEM`  | full contents of `keys/passport.pub.pem` |
   | `PASSPORT_KID`             | must match the `kid` in `keys/jwks.public.json` |
   | `PASSPORT_VERIFIER_URL`    | the public `/verify` URL |

   Multi-line values paste fine; literal `\n` escapes are also accepted. The
   `_PEM` pair takes precedence over `_PATH`, so a stale key baked into an
   image can never outrank the one you set here.

   Without these, `GET /.well-known/jwks.json` answers **500** and
   `POST /api/generate` cannot sign — the Passport is the demo's centrepiece,
   and `/health` will not tell you it is broken.

   **The pair must match.** Public and private key travel under the same
   `kid`, so a mismatched pair produces Passports that fail verification with
   `invalid_signature` and no other symptom. After deploying, compare the `x`
   and `y` served by `/.well-known/jwks.json` against `keys/jwks.public.json`
   in the repo; if they differ, the committed JWKS is stale and offline
   verification against it will reject every valid Passport.
4. Deploy. Confirm the Nixpacks plan shows
   `start │ cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Note the public URL. Ours is served at **`https://api.quebasto.com`** via a custom
   domain in front of the Railway service.


---

## Vercel — frontend

1. **Add New → Project** → import `autorIA`.
2. **Root Directory** = `frontend` (framework auto-detected as Next.js).
3. **Environment Variables** → add `SUPABASE_URL`, `SUPABASE_KEY` (anon), and
   `NEXT_PUBLIC_API_BASE_URL` = the Railway backend URL from the step above
   (ours: `https://api.quebasto.com`).

   The variable name matters: `frontend/src/lib/api.ts` reads
   **`NEXT_PUBLIC_API_BASE_URL`** and falls back to `http://localhost:8000`. A typo
   here fails **silently** — the build succeeds and every browser call goes to
   localhost (this was WO-01 / issue #82).
4. Deploy, then note the public URL and add it to Railway's
   `AUTORIA_CORS_ORIGINS` so the browser can call the API. Ours is
   `https://quebasto.com`.

---

## Verifying env vars are injected

The backend exposes a secrets-safe check (booleans only, never values):

```bash
curl https://api.quebasto.com/internal/env-check
```

```json
{
  "all_present": true,
  "required": ["WATSONX_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"],
  "present": { "WATSONX_API_KEY": true, "SUPABASE_URL": true, "SUPABASE_KEY": true },
  "missing": []
}
```

`all_present: false` with names under `missing` means those variables are not
set on the platform — add them in the dashboard and redeploy.

For the frontend, confirm the browser build received `NEXT_PUBLIC_*` vars via
Vercel's build logs or a client-side reference to `NEXT_PUBLIC_API_BASE_URL`.

---

## Local parity

```bash
cp .env.example .env   # fill in real values
cd backend && uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/internal/env-check
```

This runs the same code against the same Supabase project as Railway would,
which is enough to test application logic. It is **not** running inside the
Railway image itself — dependency resolution, image size, and OS differ
between a dev machine and Railway's Linux container. Those divergences (and
the reproducible way to set up `ai_pipeline` + `backend` locally in the first
place) are documented separately in **[docs/LOCAL_DEV.md](LOCAL_DEV.md)**
(#101), which is explicitly out of scope for this file: this file is about
Vercel/Railway/Supabase, `LOCAL_DEV.md` is about the dev machine.
