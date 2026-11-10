# Deploying AIDevs for ₹0 (Render free + Neon free + Groq free)

## Target architecture

| Component | Service | Plan | Notes |
|---|---|---|---|
| Frontend | Render **Static Site** `aidevs-frontend` | free | Global CDN, SPA rewrite, security headers |
| API + job worker | Render **Web Service** `aidevs-backend` | `plan: free` | 512 MB / 0.1 CPU, sleeps after 15 min idle, ~1 min cold start |
| Database | **Neon PostgreSQL** (external) | Free | 1 GB storage, 100 CU-h/month, scale-to-zero after 5 min |
| AI | **Groq API**, one platform key | Free | Per model (measured 2026-11-10): 1,000 req/day, 8,000 tokens/min |
| Source/CI | GitHub + GitHub Actions | Free | Public repos have free Actions minutes |

`render.yaml` creates **only** the two free Render services above. It defines no Render Postgres (which would
expire after 30 days on the free plan), no background worker, no persistent disk and no Redis/Key Value.
AI jobs run in a PostgreSQL-backed queue inside the web service; uploads are stored in the database.

## Step by step

1. **Neon:** sign up → *Create project* (Free) → choose a region near Render's `oregon` (e.g. AWS us-west-2) →
   *Connect* → copy the **pooled** connection string. It looks like
   `postgresql://user:pass@ep-xxx-pooler.us-west-2.aws.neon.tech/neondb?sslmode=require`.
   (`sslmode=require` is added automatically for `*.neon.tech` hosts if missing.)
2. **Groq:** console.groq.com → *API Keys* → create a key. Never commit it.
3. **Render:** *New → Blueprint* → select the GitHub repository → Render shows the two free services from
   `render.yaml` → enter the secrets for `aidevs-backend`:
   - `GROQ_API_KEY` — the Groq key (variable name must be uppercase)
   - `DATABASE_URL` — the Neon connection string
   - `ADMIN_EMAILS` — your email address
4. Deploy. On boot the API waits for Neon to wake, runs Alembic migrations (additive, never deleting data),
   starts the job worker and only then reports ready on `/api/health/ready`.
5. Open `https://aidevs-frontend.onrender.com`, register with your admin email, open `/admin` →
   **Check model availability**. Run one generation to confirm everything end to end.
6. If you rename services or add custom domains: set `CORS_ORIGINS` on the backend and `REACT_APP_API_URL`
   on the frontend (the frontend rebuilds).

## How the free tiers are handled

- **Cold starts:** the frontend shows “Starting the AIDevs server…”, retries reads automatically, wakes the server
  before login/registration, and keeps unsaved Studio edits in the browser until they are saved.
- **Neon scale-to-zero:** startup retries with backoff (`DB_WAIT_ATTEMPTS`), pool `pre_ping` and `pool_recycle=240s`
  replace dropped connections, and a database outage returns `503 db_unavailable` + `Retry-After` instead of 500.
  Pool size is small (`DB_POOL_SIZE=3`, overflow 2) to stay well under connection limits.
- **Groq free limits:** each request is sized to the model's per-minute token window, the scheduler uses the
  model with free budget (three model buckets), honours `retry-after`, learns per-model output caps, and pauses
  new AI tasks with a clear message when the platform budget (`AI_GLOBAL_DAILY_TOKENS`) is used up.
- **Restarts / spin-down during a job:** jobs live in PostgreSQL with leases; when the instance comes back, the
  expired lease is re-claimed and the job re-runs (generation is idempotent). Locks of finished jobs are released at boot.
- **Fair use:** per-user daily quotas (3 projects, 3 generations, 15 AI modifications, 10 exports, 50 MB uploads,
  1 concurrent AI task) are enforced atomically and editable in `/admin`.

## Staging and production

Optional: a second Neon project (or branch) and a second Render Blueprint tracking a `staging` branch, each with
its own Groq key so staging cannot consume production quota. Protect `main` with required CI checks.

## Backups and recovery

- **Neon** keeps restorable history for a limited window on the Free plan (see your project's *History retention*
  setting) and lets you restore or branch from a past point in time.
- **Logical backups (recommended weekly):**
  ```bash
  pg_dump "$DATABASE_URL" --format=custom --file=aidevs-$(date +%F).dump
  pg_restore --clean --if-exists --no-owner --dbname="$NEW_DATABASE_URL" aidevs-2026-11-10.dump
  ```
- **Project-level JSON:** `python manage.py backup projects.json` / `python manage.py restore projects.json`
  (restores missing projects, never overwrites existing ones).
- **Per project:** Versions panel in the Studio (automatic snapshots before every AI change, restore, repair).

## Rollback

- **Code:** Render → service → *Deploys* → *Rollback* (frontend and backend independently), or revert the commit.
- **Schema:** roll back code first, then `python -m alembic downgrade -1` from a Render shell if needed.
- **Data:** restore a `pg_dump` into a new Neon branch/database and switch `DATABASE_URL`.

## Limits you will hit first, and what to do

| Symptom | Cause | Free remedy |
|---|---|---|
| Slow first request | Render free spin-down | Expected; keep-alive pings are possible but consume the 750 h/month |
| “AI tasks are paused” | Groq free windows/budget used | Wait; lower per-user limits in `/admin` |
| Inserts fail, storage errors | Neon 1 GB cap | Delete old projects/assets; lower `MAX_TOTAL_STORAGE_MB` |
| Service suspended late in month | 750 free instance hours used | Single always-on service uses ~720-744 h; avoid extra free web services in the same workspace |
