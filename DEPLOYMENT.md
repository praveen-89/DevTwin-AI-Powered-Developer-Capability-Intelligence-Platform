# Deployment (Zero-Cost)

This describes the free-tier deployment: one Render web service for the
backend (with the analysis worker running in-process), Vercel for the
frontend, and the existing Supabase free project for the database/auth.
No Docker, no Redis, no paid tiers.

## Backend — Render (free web service)

Defined by `render.yaml` at the repo root (a Render Blueprint). Render
reads this automatically when you create a new Blueprint deployment
pointing at this repo.

- **Build**: `cd backend && pip install -r requirements.txt`
- **Start**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Plan**: `free` (explicitly set in `render.yaml` — do not change this to
  a paid plan without deciding to pay for it)

### Why the worker runs in the same process here

Render's free tier has no background-worker instance type — only web
services get a free tier. `RUN_WORKER_IN_PROCESS=true` (set directly in
`render.yaml`, not a secret) makes the FastAPI app launch the existing
`app.workers.runner.worker_loop()` as a background `asyncio` task on
startup (via FastAPI's `lifespan` context in `backend/app/main.py`), and
cancels it cleanly on shutdown. No worker logic was duplicated — the app
just calls the same function `workers/runner.py` already calls.

**Trade-off**: Render's free web services spin down after a period of
inactivity. When that happens, the in-process worker sleeps too — a
queued analysis job sits in `QUEUED` until the next incoming HTTP request
wakes the service back up (which also restarts the worker loop via the
`lifespan` startup). This is acceptable for a zero-cost personal/demo
deployment; it is not a production SLA.

### Upgrading later to a separate worker (no code change)

When you're ready to pay for a dedicated Render background worker:
1. Create a second Render service (type: worker) with start command
   `cd backend && python ../workers/runner.py --poll`.
2. Set `RUN_WORKER_IN_PROCESS=false` (or remove it — `false` is the
   default) on the **web** service.
3. Deploy both. The web service stops running the worker itself; the new
   worker service takes over, exactly as in local development.

No application code changes are required for this — only the two
environment/service changes above.

### Environment variables

Every variable below is declared in `render.yaml` with `sync: false`,
meaning Render will prompt for its real value in the dashboard when you
create the Blueprint — none of them are committed. They mirror
`.env.example` at the repo root; see that file for the format of each
(e.g. `DATABASE_URL` must use the `postgresql+asyncpg://` scheme and the
Supabase **transaction-mode pooler** connection string, not the direct
connection string).

| Variable | Notes |
|---|---|
| `APP_NAME`, `APP_VERSION`, `DEBUG` | `DEBUG=false` in production — disables `/docs`, `/redoc`, `/openapi.json` |
| `DATABASE_URL` | Supabase pooler connection string |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | From the Supabase project dashboard |
| `SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ORIGINS` | Must include your Vercel frontend's URL (comma-separated if more than one, no wildcards) |
| `FRONTEND_URL` | Your Vercel frontend's URL, used for OAuth redirect construction |
| `FRONTEND_DASHBOARD_PATH` | Leave as `/dashboard` unless the frontend route changes |
| `GITHUB_APP_ID`, `GITHUB_APP_SLUG`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_PRIVATE_KEY`, `GITHUB_REDIRECT_URL`, `GITHUB_STATE_ENCRYPTION_KEY`, `GITHUB_STATE_TTL_SECONDS`, `GITHUB_API_BASE_URL` | From your GitHub App settings — `GITHUB_REDIRECT_URL` must point at this Render service's `/github/callback` |

`RUN_WORKER_IN_PROCESS` and `PYTHON_VERSION` are set directly in
`render.yaml` (not secrets) — no action needed for those two.

## Frontend — Vercel (free tier, no repo changes)

Vercel needs no files in this repo. In the Vercel dashboard, when
importing this repository:

1. Set **Root Directory** to `frontend`.
2. Set these three environment variables (all already used by
   `frontend/.env.example`):
   - `NEXT_PUBLIC_API_BASE_URL` — this Render service's URL (e.g.
     `https://devtwin-backend.onrender.com`)
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Vercel auto-detects the Next.js build; no build/start command overrides
are needed.

After both are deployed, update the backend's `CORS_ORIGINS` and
`FRONTEND_URL`, and the GitHub App's callback URL, to match the real
Vercel URL (circular dependency: deploy backend first with a placeholder,
then update it once the Vercel URL is known).

## Database — Supabase (existing free project)

No changes. Use the same Supabase project already configured locally;
just point `DATABASE_URL` / `SUPABASE_URL` / the two Supabase keys above
at it from the Render dashboard.
