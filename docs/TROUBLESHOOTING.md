# Troubleshooting

Every API response carries an `X-Request-ID` header; search the backend logs for it.

| Symptom | Likely cause | Fix |
|---|---|---|
| "AI is not configured on this server" | `GROQ_API_KEY` missing on the backend | Set it (backend only) and restart. |
| "The platform's AI key was rejected by Groq" | Invalid/revoked key | Create a new key at console.groq.com and update the env var. |
| "The AI service is busy (rate limited)" | Groq account rate limit reached | Wait; lower per-user limits in `/admin`; upgrade the Groq plan. |
| "Daily AI request limit reached" | Per-user quota | Expected; adjust `ai_daily_requests` in `/admin`. |
| AI task stays "Queued" | No worker running | Keep `RUN_WORKER_IN_PROCESS=1`, or run `python manage.py worker`. Check `/api/health/ready` → `worker.ok`. |
| "An AI task is already running for this project" | Per-project lock held by a running job | Wait or press **Cancel**. Locks of crashed jobs are released automatically on restart. |
| Render deploy never becomes live | `/api/health/ready` returns 503 | Open the URL: check `database`, `migrations.upToDate`, `worker.ok`. |
| CORS errors in the browser console | Frontend origin missing from `CORS_ORIGINS` | Add the exact origin (scheme + host) and redeploy. |
| Logged out after every refresh | Storage blocked (private mode) or `JWT_SECRET_KEY` changed | Allow site storage; keep the secret stable across deploys. |
| "This page was changed elsewhere" | Another tab/AI task saved the page | Click **Reload latest**; edits are protected by optimistic concurrency. |
| Too many login attempts → 429 | Rate limit | Wait 60 s. Behind a proxy, set `TRUST_PROXY_HOPS` correctly. |
| Canvas shows default fonts | Font CDN slow/blocked | Expected fallback; pages still render (fonts load asynchronously). |
| `alembic` "Target database is not up to date" | Pending migrations | `python manage.py migrate`. |
| Exported app: "Set JWT_SECRET_KEY" | Missing `.env` in the export | `cp backend/.env.example backend/.env` and set a 32+ character secret. |
| Local SQLite "database is locked" | Very heavy concurrent writes in dev | WAL + busy timeout are enabled; use PostgreSQL for load testing. |
