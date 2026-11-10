# AIDevs 2.0 — Repository Audit & Implementation Plan

_Audit date: 2026-11-09. Canonical app = repository root (`backend/`, `src/`, `render.yaml`), which is what Render builds._

## 1. What actually exists (v1)

| Area | Reality in code |
|---|---|
| Frontend | CRA React 18 app: marketing home page (`HomePage` + sections), `RegisterPage`, `LoginModal`, `/chatbot` split view (`ChatPanel` + `PreviewPanel`). |
| Backend | Single Flask `app.py`, endpoints `/api/auth/*`, `/api/chat`, `/api/preview`, `/api/download`, `/api/status`, `/api/reset`, `/api/health`. |
| Auth | bcrypt hashes + JWT (24h) stored in `localStorage`. Users stored as **metadata in a ChromaDB collection**. |
| Storage | `chromadb.Client(Settings(persist_directory=...))` — in ChromaDB ≥0.4 this is an **in-memory client**. Nothing persists. |
| Projects | None. One in-memory `orchestrator.sessions[username_session]` dict per user. |
| AI | Each request builds a new `Groq` client with the **user's own key** (required at registration). Model hard-coded to `llama-3.3-70b-versatile` (**decommissioned by Groq on 2026-08-16**). |
| Agents | `LeadAgent` keyword state machine (header → hero → features → footer), `FrontendAgent` (HTML strings + ecommerce fallback template), `BackendAgent` (LLM writes Flask code as text), `TestAgent` (LLM "imagines" test results; nothing executed). |
| Preview | `iframe` with `sandbox="allow-scripts allow-same-origin"` + `document.write` of AI HTML. |
| Export | Zip of `index.html` + LLM-written `app.py`. |
| Deploy | `render.yaml`: Python web service, static site, and a `pserv` pointing at a non-existent `backend/Dockerfile.chromadb`. |

## 2. Bugs & vulnerabilities found

1. **Users are forgotten on every restart** (in-memory Chroma client; Render disk is ephemeral anyway).
2. Login session not restored reliably; no refresh tokens, no logout invalidation.
3. Hard-coded JWT secret fallback (`aidevs-secret-key-change-in-production`).
4. `CORS(app)` allows every origin.
5. **Preview XSS**: AI-generated scripts run in the app origin and can read the JWT from `localStorage`.
6. User Groq API key forwarded into a prompt (`backend_agent.generate_api(context=user_api_key)`), and key prefixes logged.
7. Decommissioned Groq model → generation currently fails.
8. No project ownership, persistence, history or versions.
9. Fake testing (LLM-written "test results").
10. `ENCRYPTION_KEY` required only to store user API keys.
11. `requirements.txt` pulls `sentence-transformers` (+ torch) / langchain / langgraph that are unused or optional.
12. Three duplicated copies of the app (`react-version/`, `react-version/react-version/`) — left untouched; recommend deleting after review.

## 3. Architecture decisions for 2.0

* **Relational DB as source of truth** — SQLAlchemy 2 + Alembic migrations. SQLite locally, PostgreSQL in production (`DATABASE_URL`).
* **Controlled component schema** — every page is a validated node tree (`id`, `type`, `name`, `props`, `styles{base,tablet,mobile}`, `children`). Visual edits are structured operations on that tree. Preview HTML/CSS and the exported React + Flask project are *compiled deterministically* from it. This gives a stable mapping _visual element → node id → component file → CSS class_ without regex-editing arbitrary source.
* **Generated backends are compiled from an entity schema**, not free-written by the LLM. The AI designs entities/permissions; the compiler emits SQLAlchemy models, validated CRUD REST APIs, auth, migrations SQL and pytest tests.
* **One central Groq client** with task-based model routing, timeouts, retry/backoff, rate-limit handling, model fallback chain, JSON validation and per-user quotas/usage accounting.
* **Sandboxed canvas** — `srcdoc` iframe with `sandbox="allow-scripts"` only (opaque origin), strict CSP with a nonce for the editor bridge script, sanitized content (no user scripts / event handlers), validated `postMessage` protocol.
* **Project memory** — structured tables (spec, tokens, pages, entities, messages, memory items, agent runs, versions). Context for each AI call is assembled from these, not from vector search. ChromaDB becomes optional.

## 4. Phases

1. Audit (this document).
2. Core reliability: DB + migrations, auth rewrite (refresh rotation, logout revocation, rate limiting), central AI client, ownership.
3. Project intelligence: spec, memory, versions/snapshots, agent runs.
4. Generation: requirements agent → UI architect agent → backend compiler → checks agent; URL research agent with SSRF-safe crawler.
5. Visual studio: canvas, selection, resize, drag-reorder, layers, inspector, responsive overrides, undo/redo, autosave.
6. Dev environment: console/checks/activity panels, preview data store wired to forms/collections.
7. Advanced: assets, design tokens, versions/restore, export (React + Flask + tests + Docker + Render).
8. Validation: backend pytest suite, export round-trip test, frontend build.
