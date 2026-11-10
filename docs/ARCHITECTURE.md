# AIDevs 2.0 Architecture

## Overview

```
 Browser (React SPA)                          Flask API (gunicorn + gevent)                 PostgreSQL / SQLite
 ┌───────────────────────────┐   JSON/JWT    ┌───────────────────────────────────┐  SQLAlchemy ┌──────────────┐
 │ Projects dashboard        │ ───────────▶ │ api/auth      sessions, rotation  │ ──────────▶ │ users, tokens │
 │ Studio                    │              │ api/projects  pages, entities,    │             │ projects,     │
 │  ├ Layers / Pages / Data  │              │               versions, assistant │             │ pages, models │
 │  ├ Canvas ─┐ postMessage  │              │ api/assets    validated uploads   │             │ versions, ... │
 │  ├ Inspector│ (validated) │              │ services/jobs background agent runs│            └──────────────┘
 │  └ Assistant│             │              │ agents/studio Requirements,       │   HTTPS     ┌──────────────┐
 └────────────┼──────────────┘              │   Architect, Feature, Visual edit │ ──────────▶ │ Groq (1 key) │
   sandboxed iframe (opaque origin, CSP)    │ services/compiler + exporter      │             └──────────────┘
   └ editor_bridge.js (only script)         └───────────────────────────────────┘
```

## Source of truth: the component schema

Each page is a JSON tree of nodes (`services/schema.py`):

```json
{"id": "n_1a2b3c4d", "type": "heading", "name": "Hero Heading", "tag": "h1",
 "props": {"text": "Run the night"},
 "styles": {"base": {"fontSize": "64px"}, "tablet": {}, "mobile": {"fontSize": "36px"}},
 "children": []}
```

* 15 node types (section, container, heading, text, button, link, image, icon, divider, form, input,
  textarea, select, collection, page). Only containers have children.
* Allow-listed tags, props and ~80 CSS properties; values are checked for injection (`;{}<>`, `url(javascript:)`…).
  Text is always rendered escaped. There is no way to express a script or event handler.
* `styles.base` = desktop/laptop, `tablet` = `@media (max-width:1024px)`, `mobile` = `@media (max-width:640px)`.
  Editing on a device writes only that breakpoint, so desktop edits never destroy mobile layouts.
* `form.entity` / `collection.entity` bind UI to data models; collection templates use `{{field}}` bindings.
* The shared header/footer live in `projects.layout` and are composed into every page (`shared` marker).

**Why a schema instead of editing source files?** Regex/AST edits on arbitrary generated JSX are fragile.
A validated tree makes every edit (canvas, inspector, layers, AI) a small, reversible, structural operation;
undo/redo is a stack of trees; and the compiler deterministically produces identical HTML/CSS for the canvas
and React/CSS for the export. The node id appears as `.n-<id>` in the CSS and in `aidevs.sourcemap.json`.

## Compilers

| Module | Output |
|---|---|
| `services/compiler.py` | Preview document: tokens → CSS variables, per-node class rules + media queries, escaped HTML, CSP with nonce, editor bridge. |
| `services/export_frontend.py` | React 18 + Vite app: one component per section, pages, router, shared header/footer, `DataForm` + `Collection` bound to the API, sitemap/robots. |
| `services/export_backend.py` | Flask + SQLAlchemy app: models, permission-aware CRUD (search/filter/sort/pagination), auth, seed, SQL DDL for SQLite/PostgreSQL, pytest tests, Dockerfile, API docs. |
| `services/exporter.py` | Zip with README, docker-compose, render.yaml, `.env.example` (no platform secrets), project JSON, sourcemap, uploaded assets. |

## Agents (`agents/studio`)

| Agent | Input → validated output |
|---|---|
| Research (`services/crawler.py`) | URL → structural/design summary (SSRF-safe, robots.txt, pinned IP). |
| Requirement Analysis (`requirements.py`) | idea (+reference) → AppSpec (pages, sections, entities, tokens, SEO). |
| UI/UX Architect + Frontend (`architect.py`) | spec page → component tree; rejects unknown entities/fields; deterministic section-library fallback. |
| Backend + Database | compiled from entities (`export_backend.py`) — the LLM designs data, code is generated deterministically. |
| Feature / Orchestrator (`editing.py`, `orchestrator.py`) | request + project memory → plan of entity/page/nav/token changes, applied atomically after a snapshot. |
| Visual Editing (`editing.py`) | selected subtree + instruction → replacement subtree (ids preserved), applied client-side as one undo step. |
| Testing (`services/checks.py`) | project → contract / link / a11y / SEO / responsive / security / compile issues. |
| Security | enforced structurally: sanitizer, permission checks in checks, owner-scoped APIs, sandboxed preview. |

Agents never write the database directly from model text: every output passes a validator; on invalid output the
client asks the model once to repair, then fails without changes. Mutating runs are serialized per project
(`ensure_idle`), recorded in `agent_runs` with step logs, and recover cleanly after restarts.

## AI service (`services/ai_client.py`)

* Single `GROQ_API_KEY`; never sent to browsers or stored per user.
* Task routing: `plan`, `page`, `feature`, `edit`, `chat`, `legacy` → fallback chains configurable with
  `AI_MODEL_<TASK>`. Defaults: `openai/gpt-oss-120b` → `openai/gpt-oss-20b` (Llama 3.x models used by v1 were
  decommissioned by Groq on 2026-08-16).
* Timeouts, exponential backoff for 5xx/network errors, Retry-After handling, model fallback on 429/404/400,
  JSON mode + validation + one repair attempt, per-user daily request/token quotas, `usage_records` accounting.

## Data model (`models.py`, Alembic `migrations/`)

`users`, `refresh_tokens`, `revoked_access_tokens`, `projects`, `pages`, `entities`, `assets`, `chat_messages`,
`memory_items`, `agent_runs`, `project_versions`, `preview_records`, `usage_records`, `audit_logs`.

## Security model

* **Auth**: bcrypt(12); 15-minute access JWT (memory only); 30-day rotating refresh token (SHA-256 hashed in DB);
  reuse of a rotated token revokes the whole family; logout revokes refresh + blocklists the access token;
  login/register rate limited; identical errors for unknown user / wrong password.
  Refresh tokens travel in the body (not cookies) because the SPA and API are different `onrender.com` sites
  (third-party cookies are blocked by modern browsers). Serving both from one site would allow HttpOnly cookies.
* **Isolation**: every project route resolves through `get_owned_project` → 404 for other users' data.
* **Preview**: `sandbox="allow-scripts"` (no same-origin) + `srcdoc`, CSP `connect-src 'none'; form-action 'none'`,
  nonce'd bridge as the only script; messages are checked for `event.source` and schema on both sides.
* **Crawler**: http/https on 80/443 only, all resolved IPs must be public, connection pinned to the vetted IP,
  per-hop redirect validation, size/time limits.
* **Uploads**: Pillow-verified PNG/JPEG/GIF/WebP only (no SVG), size limits, `nosniff`, served by unguessable id.
* **Headers/CORS**: explicit origin allow-list, `X-Frame-Options: DENY`, `nosniff`, HSTS in production.

## Jobs, limits and operations

* **Durable job queue** (`services/jobs.py`): AI work is stored in `agent_runs` (payload, attempts, lease,
  timeout, cancel flag). Workers claim jobs with a compare-and-swap `UPDATE` (safe across processes on
  PostgreSQL and SQLite), extend a lease on every progress step, and retry transient provider failures with
  backoff. Expired leases (crashed/redeployed worker) are re-queued up to `max_attempts`. Users can cancel.
  A per-project lock (`projects.active_run_id`, claimed atomically) guarantees only one AI job mutates a project.
* **Fair-use limits** (`services/limits.py`): AI requests/tokens per day, concurrent jobs, projects, pages,
  upload storage, exports per hour, job duration, registration switch. Env defaults; admins override at runtime
  (`platform_settings`). Each limit returns a clear 429/413 message.
* **Rate limiting** (`services/ratelimit.py`): in-memory per process, or Redis (`REDIS_URL`) shared across
  instances. Client IPs come from `ProxyFix` with an explicit hop count, so `X-Forwarded-For` cannot be spoofed.
* **Bounded repair loop** (`services/repair.py`): after generation/feature work, failed checks are fixed
  deterministically (missing form fields, broken links, unknown bindings, alt text), then by at most
  `REPAIR_MAX_ATTEMPTS` targeted AI edits of the affected section. A change is kept only if the error count drops;
  otherwise the exact previous trees are restored. Snapshots are taken first.
* **Model registry** (`services/model_registry.py`): tasks `requirements`, `ui_planning`, `frontend`,
  `code_modification`, `visual_edit`, `error_analysis`, `chat` each have a model chain, token budget and
  temperature; chains are filtered by the models the key can access (`models.list`, cached 1 h). `backend` and
  `testing` are deterministic (no model).
* **Observability:** JSON logs with request/user/project/run ids and secret redaction (`services/logging_setup.py`),
  `X-Request-ID` on every response, `/api/health/live`, `/api/health/ready` (DB, migrations, worker heartbeat),
  admin console (`/admin`, `api/admin.py`) for queue, failed runs, AI usage by model, rate-limit hits, limits and users.
* **Accounts:** password change (revokes other sessions), JSON data export, permanent account deletion
  (cascades projects; anonymises usage/audit rows).

## Preview isolation vs. server-side execution

| | What runs | Isolation |
|---|---|---|
| **Studio canvas (browser)** | Platform-compiled HTML/CSS + two platform scripts (editor bridge, font loader) | `sandbox="allow-scripts"` opaque-origin iframe via `srcdoc`; CSP `default-src 'none'`, `script-src 'nonce-…'`, `connect-src 'none'`, `form-action 'none'`; content is schema-sanitized so user/AI content can never add scripts or handlers. The canvas cannot read the studio's storage, tokens or DOM. |
| **Preview forms** | Platform API (`/api/projects/<id>/data/<entity>`) called by the *studio*, not by the iframe | Owner-authenticated, validated against the entity schema, capped at 500 records per project. |
| **Server** | Never executes generated application code. The Testing agent only `compile()`s generated Python for syntax. | No subprocesses, no `exec`/`eval` of generated code. |
| **Exported app** | Runs only on the user's own infrastructure. | Not executed by the platform. |

Running generated apps server-side (live backends, Playwright tests of generated sites) would require isolated
containers with CPU/memory/network/time limits; this is **not implemented** and is listed as future work.

## Known limitations / next steps

* Real Groq acceptance tests exist (`backend/tests/real_ai`) but have not been run without a key.
* No email delivery: password *reset* (forgot password) is not implemented; signed-in users can change passwords.
* Generated-app execution sandbox (containers) not implemented; see table above.
* Collaboration (multi-user editing), Git push, marketplace and one-click deploy are not implemented;
  the export includes Docker/Render configs. Page saves use optimistic concurrency (409 on conflicts).
