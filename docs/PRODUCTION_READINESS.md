# AIDevs 2.2 — Production Readiness Report (zero-cost deployment)

_Date: 2026-11-10 · Branch: `fix/groq-api-key-forwarding`_

Legend: **PASS** validated · **PARTIAL** implemented, not fully validated · **BLOCKED** needs unavailable
credentials/infrastructure · **FAIL** not working

**Classification: READY FOR A FREE PUBLIC BETA, with the limitations below.** Real Groq generation is validated.
The Render/Neon deployment itself has not been executed from this machine (no Render/Neon accounts were available
to the agent), so the deployment items remain PARTIAL until you deploy.

## 1. Zero-cost architecture

Render **Static Site** (frontend) + Render **Web Service `plan: free`** (API + in-process durable job worker)
+ **Neon PostgreSQL Free** (external) + **Groq Free** (one platform key) + GitHub/Actions.
`render.yaml` was verified to define only these two free Render services: no Render Postgres, workers, disks or
Redis. Production refuses to start on SQLite.

## 2. Real Groq validation (live API, this account, 2026-11-10)

Account limits read from Groq response headers: per model **1,000 requests/day, 8,000 tokens/minute**; daily token
limit **200,000/model** (observed in 429 responses); qwen3.8-27b output cap **1,000 tokens/minute**.

| Test | Result | Notes |
|---|---|---|
| A — multi-page portfolio | **PASS** (runs 1 and 3) | 4 pages, 0 template fallbacks, 0 check errors, exported backend tests pass |
| B — SaaS project management | **PASS** (runs 2 and 3) | user-scoped models, auth, export tests pass |
| C — e-commerce (cart, wishlist, admin) | **PARTIAL** | Run 1 exposed an export bug (fixed); run 2 a missing-`h1` quality issue (fixed by normalisation); run 3 was stopped by Groq's **daily** token limit after three full test runs. Not yet re-run. |
| D — add wishlist to existing app | **PASS** (run 1) | run 2 failure was a test-harness bug (compared trees incl. the shared navbar); fixed |
| E — redesign selected hero | **PASS** (runs 1 and 2) | only the selected node changes |
| F — notification system | **PASS** (run 1) | run 2 aborted when the platform daily AI budget was reached (capacity guard working) |
| G — failure handling | **PASS** | simulated 429/Retry-After, per-minute and daily-limit 429s, "request too large" caps, timeouts, decommissioned models, invalid JSON |

**Key fix from real testing:** gpt-oss produced malformed deeply-nested JSON (43 `json_validate_failed` in one run).
Switching agents to a flat node list raised valid page outputs from 0/3 to 4/4 in direct probes and cut JSON failures
from 43 to 1 in the next full run, while using ~3x fewer tokens.

To re-run (uses free quota; run when the daily window has refreshed):
`cd backend && RUN_REAL_AI=1 python -m pytest tests/real_ai -v -s`

## 3. Failure behaviour (Phase 9)

| Scenario | Status | Evidence |
|---|---|---|
| Neon temporarily unavailable | **PASS** | live PostgreSQL paused → `503 db_unavailable`, `Retry-After: 5`; recovers with data intact |
| Database connection interruption | **PASS** | server terminated all sessions → next request 200 (pool pre-ping) |
| Database wake-up at boot | **PASS** | `wait_for_db` retries with backoff (unit test) |
| Groq 429 / timeout / unavailable model | **PASS** | `test_free_tier.py`, `test_services.py` |
| Groq daily limit reached | **PASS** | fails fast, refunds quota, pauses new AI tasks (real message format) |
| Render restart during generation | **PASS** | expired lease re-claimed, generation completes, lock released |
| Worker restart during task | **PASS** | lease recovery + max attempts (`test_jobs.py`) |
| User cancels a task | **PASS** | queued and running cancel; quota refunded; project consistent |
| Two users generate simultaneously | **PASS** | 5 concurrent users, no cross-talk (`test_concurrency.py`) |
| User reaches quota / parallel bypass | **PASS** | 6 parallel generations with limit 2 → exactly 2 succeed, no orphan projects |
| Cold start in the browser | **PASS** | backend down at submit → banner → registration completes automatically (16 s) |

## 4. Test totals (final)

- Backend: **111 passed** on SQLite and **111 passed** on PostgreSQL 16 (6 real-AI tests run separately).
- Frontend: lint clean, 4 unit tests, production build OK. Browser (Chromium): **22/22** Studio/auth/account/legal
  checks + **4/4** cold-start checks.
- Earlier validated and unchanged: exported app runs independently (backend + Vite frontend), `pip-audit` /
  `npm audit` clean, gitleaks clean, no secrets in logs or bundle.

## 5. Owner actions before launch

1. Create Neon + Render (Blueprint) + set `GROQ_API_KEY`, `DATABASE_URL`, `ADMIN_EMAILS` (see README).
2. Re-run the real-AI suite once the Groq daily window refreshes to complete test C.
3. Legal drafts in `public/legal/` need review by a qualified lawyer; fill placeholders and contact emails.
4. Rotate any Groq key that was ever stored outside the server environment (e.g. the archived `react-version/.env`).

## 6. Known limitations

- Free capacity is finite: with the measured Groq limits a full multi-page generation uses roughly 20-30k tokens
  (plan + ~4 pages); two usable 200k-token/day models allow roughly 10-20 full generations per day platform-wide,
  plus smaller edits. Fair-use quotas and the
  platform daily budget enforce this; users see clear messages.
- Render free instances sleep after 15 minutes (≈1 minute cold start) and share 750 instance-hours per month.
- Neon free storage is 1 GB; uploads are capped (50 MB/user, 300 MB platform).
- No forgot-password email flow; no server-side execution of generated apps; no real-time collaboration.
- Free-tier terms can change at any time; zero cost is not guaranteed indefinitely.
