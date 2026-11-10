# Changelog

## 2.2.0 — 2026-11-10 (zero-cost deployment)

### Infrastructure
- Zero-cost target: Render free web service + Render static site + **Neon** PostgreSQL free + Groq free.
  `render.yaml` now creates only free resources (no Render Postgres, workers, disks or Redis).
- Neon support: URL normalization (`sslmode=require`), connect timeouts, TCP keepalives, small pool with
  recycle before scale-to-zero, wait-for-database at startup, `503 db_unavailable` + `Retry-After` on outages.
- Production refuses to start on SQLite (Render's disk is ephemeral).

### AI (Groq free tier)
- Free-tier capacity manager: learns limits from Groq rate-limit headers, sizes requests to the 8K tokens/min
  window, schedules across three model buckets (adds `qwen/qwen3.8-27b`), honours `retry-after`, learns per-model
  output caps, waits a bounded time (25 s web / 90 s jobs), platform-wide daily budget that pauses new AI tasks.
- AI agents now emit a **flat node list** instead of deeply nested JSON: real Groq validity went from 0/3 to 4/4
  and output size dropped ~3x. Headings are normalised to exactly one `h1` per page.
- Failed provider generations are counted in usage accounting (they consume real quota).

### Fair use
- Per-user daily quotas (3 projects, 3 generations, 15 AI modifications, 10 exports, 50 MB uploads, 1 concurrent
  AI task) enforced atomically under a per-user lock; failed/cancelled AI work is refunded; platform storage cap.
- Fair job scheduling (users without running jobs go first).

### UX
- Cold-start banner, automatic retries for safe requests, server wake-up before login/registration, local drafts
  of unsaved Studio edits with automatic restore, autosave retry while the server wakes, AI capacity notices and
  remaining daily allowances on the dashboard and Account page.

### Fixed
- Generated backend tests embedded JSON literals (`false`/`null`) in Python (found by the real Groq run).

## 2.1.0 — 2026-11-10 (production hardening)

### Security
- Rate limits could be bypassed by spoofing `X-Forwarded-For`; client IPs now come from `ProxyFix` with an explicit
  `TRUST_PROXY_HOPS`.
- An untracked, un-ignored `react-version/.env` containing an API key could have been committed by `git add .`;
  `.gitignore` now ignores every `.env` file in the tree (examples excepted). The old nested copy was archived
  outside the repository.
- Upgraded dependencies with 53 known CVEs (Flask, flask-cors, python-dotenv, urllib3, certifi, Pillow, pytest) and
  React Router (open-redirect/XSS advisories); exported apps now use the same fixed versions (Vite 6, React Router 7).
- Secret-redacting JSON logs with request IDs; admin API hidden (404) from non-admins.

### Reliability
- Durable database-backed job queue (leases, retries with backoff, timeouts, cancellation, crash recovery,
  separate worker process option); atomic per-project AI lock.
- Atomic page saves (conditional UPDATE), collision-safe version numbering, SQLite WAL/busy timeout,
  bounded PostgreSQL pool. Migration 0002 upgrades existing data in place (tested on PostgreSQL).
- Canvas no longer goes blank when the web-font CDN is slow or unreachable (fonts load asynchronously);
  exported sites load fonts non-blocking too.
- N+1 query removed from the project list.

### Added
- Central model registry with per-task chains and live availability filtering; bounded validate-and-repair loop.
- Admin-configurable fair-use limits (AI, concurrent jobs, projects, pages, storage, exports, job duration,
  registration switch); `/api/usage` and Account page meters.
- Account: change password (signs out other devices), data export, account deletion.
- Admin console (`/admin`): health, queue, failed runs, AI usage by model, rate-limit hits, limits, users.
- `/api/health/live`, `/api/health/ready`; `manage.py worker | make-admin | restore`; project-list pagination.
- CI (GitHub Actions), Dependabot, gitleaks, pre-commit; LICENSE, SECURITY, CONTRIBUTING, CODE_OF_CONDUCT,
  issue/PR templates; legal drafts; troubleshooting and production-readiness docs; real-Groq acceptance tests.

### Removed
- Pre-React static site (`index.html`, `index.js`, `style.css`), duplicate root images, unused `runtime.txt` files,
  stray `%temp%/` download cache. The nested `react-version/` clone was moved to `../AIDevs-archive/`.

## 2.0.0 — 2026-11-09

### Fixed
- Users and sessions were lost on every restart (ChromaDB `Client()` is in-memory): users and projects now live in
  PostgreSQL/SQLite via SQLAlchemy with Alembic migrations.
- Sessions survive page refreshes and browser restarts (rotating refresh tokens, silent refresh on 401).
- Logout now revokes server-side; reuse of stolen refresh tokens revokes the session family.
- AI generation broken by Groq's decommissioning of `llama-3.3-70b-versatile` (2026-08-16).
- Per-user Groq keys were required and one was forwarded into an LLM prompt; replaced by one platform key.
- Preview XSS: generated HTML ran with `allow-same-origin` and could read tokens; now an opaque-origin sandbox with CSP.
- Open CORS, hard-coded JWT secret fallback, unrestricted errors leaking stack details.
- `render.yaml` referenced a non-existent `Dockerfile.chromadb`.

### Added
- Projects with ownership, pages, data models, assets, chat history, project memory, agent runs, versions
  (snapshot / compare / restore), audit and usage logs.
- One-prompt application planning with reviewable spec; optional reference-URL analysis (SSRF-safe crawler).
- Multi-page generation into a validated component schema; deterministic fallback section library.
- Visual Studio: canvas selection, resize, drag-to-move, inline text editing, layers (rename, reorder, group,
  duplicate, delete), contextual inspector, responsive overrides per device, undo/redo, autosave with conflict
  detection, design tokens, asset manager, data-model editor with API view, versions, code view with element
  source mapping, console, checks and agent activity panels, preview mode with working forms.
- AI assistant: selected-element edits and project-wide feature changes applied atomically.
- Testing agent with real deterministic checks; backend compile check.
- Export: React + Vite frontend, Flask + SQLAlchemy backend with auth/permissions/CRUD/migrations/seed/tests,
  API docs, Docker, docker-compose, render.yaml, sourcemap.
- Admin CLI (`backend/manage.py`), 54 backend tests, frontend unit tests.

### Changed
- `/chatbot` classic builder kept for compatibility, now authenticated by user id and the central AI client.
- ChromaDB is optional (`ENABLE_CHROMADB=1`); heavy ML dependencies removed from the default install.

### Removed
- `utils/auth_manager.py`, ChromaDB user scripts, encryption-key generators and outdated deployment guides
  (superseded by `docs/`).
