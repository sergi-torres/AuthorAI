# Deployment — Vercel (frontend) + Railway (backend)

AutorIA is a monorepo deployed as **two services from one GitHub repo**
(`github.com/sergi-torres/autorIA`):

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
4. Deploy. Confirm the Nixpacks plan shows
   `start │ cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Note the public URL (e.g. `https://autoria-api.up.railway.app`).


---

## Vercel — frontend

1. **Add New → Project** → import `autorIA`.
2. **Root Directory** = `frontend` (framework auto-detected as Next.js).
3. **Environment Variables** → add `SUPABASE_URL`, `SUPABASE_KEY` (anon), and
   `NEXT_PUBLIC_API_BASE_URL` = the Railway backend URL from the step above.
4. Deploy, then note the Vercel URL and add it to Railway's
   `AUTORIA_CORS_ORIGINS` so the browser can call the API.

---

## Verifying env vars are injected

The backend exposes a secrets-safe check (booleans only, never values):

```bash
curl https://<railway-backend-url>/internal/env-check
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
