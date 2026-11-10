"""Free-tier-aware Groq capacity manager (shared by every AI call in the process).

Groq's free plan limits each model independently (measured for this account on
2026-11-10: 1,000 requests/day and 8,000 tokens/minute per model) and rejects a
request whose prompt + max_completion_tokens exceeds the per-minute budget.
This module:

* learns each model's limits and remaining budget from Groq's response headers
  (x-ratelimit-limit/remaining/reset-tokens|requests, retry-after);
* sizes `max_completion_tokens` so prompt + completion fits the model's TPM limit;
* picks the model in a task's chain that can serve the request soonest, waiting a
  bounded time for a per-minute window to reset instead of failing;
* puts a model on cooldown after a 429 (honouring retry-after) or when its daily
  request quota is exhausted;
* enforces an optional platform-wide daily token budget (AI_GLOBAL_DAILY_TOKENS) from
  the usage table, so the free quota is never "unlimited" and new AI tasks are paused
  with a clear message instead of failing midway.

State is per process (one free Render instance); the durable source of truth for
usage stays in the database (usage_records).
"""
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone

_lock = threading.Lock()
_models = {}  # model -> state dict
MAX_WAIT_SECONDS = float(os.getenv("AI_MAX_WAIT_SECONDS", "25"))           # interactive requests
JOB_MAX_WAIT_SECONDS = float(os.getenv("AI_JOB_MAX_WAIT_SECONDS", "90"))    # background jobs (async)
_local = threading.local()


def set_job_mode(enabled):
    """Background jobs may wait longer for a per-minute window to reset than a web request."""
    _local.job = bool(enabled)


def max_wait():
    return JOB_MAX_WAIT_SECONDS if getattr(_local, "job", False) else MAX_WAIT_SECONDS
DEFAULT_TPM = int(os.getenv("GROQ_TPM_LIMIT", "8000"))
SAFETY_TOKENS = 300
_DURATION = re.compile(r"(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m(?!s))?(?:(\d+(?:\.\d+)?)s)?(?:(\d+(?:\.\d+)?)ms)?$")


def parse_duration(value):
    """Groq reset headers look like '682ms', '7.66s', '2m59.56s', '1h2m3s'. Returns seconds."""
    if value is None:
        return None
    value = str(value).strip()
    try:
        return float(value)
    except ValueError:
        pass
    m = _DURATION.match(value)
    if not m or not any(m.groups()):
        return None
    h, mins, s, ms = (float(x) if x else 0.0 for x in m.groups())
    return h * 3600 + mins * 60 + s + ms / 1000


def estimate_tokens(text):
    # Conservative (~3.5 chars/token for English + JSON); real counts come back in usage.
    return int(len(text) / 3.5) + 16


def _state(model):
    st = _models.get(model)
    if st is None:
        st = _models[model] = {"tpm": DEFAULT_TPM, "otpm": None, "remaining_tokens": None, "tokens_reset_at": 0.0,
                               "remaining_requests": None, "requests_reset_at": 0.0, "cooldown_until": 0.0}
    return st


def update_from_headers(model, headers):
    if not headers:
        return
    now = time.monotonic()
    get = headers.get
    with _lock:
        st = _state(model)
        try:
            if get("x-ratelimit-limit-tokens"):
                st["tpm"] = int(float(get("x-ratelimit-limit-tokens")))
            if get("x-ratelimit-remaining-tokens") is not None:
                st["remaining_tokens"] = int(float(get("x-ratelimit-remaining-tokens")))
                st["tokens_reset_at"] = now + (parse_duration(get("x-ratelimit-reset-tokens")) or 60)
            if get("x-ratelimit-remaining-requests") is not None:
                st["remaining_requests"] = int(float(get("x-ratelimit-remaining-requests")))
                st["requests_reset_at"] = now + (parse_duration(get("x-ratelimit-reset-requests")) or 86400)
                if st["remaining_requests"] <= 0:
                    st["cooldown_until"] = max(st["cooldown_until"], st["requests_reset_at"])
        except (TypeError, ValueError):
            pass


_TOO_LARGE = re.compile(r"Request too large.*?\((O?TPM)\): Limit (\d+)", re.S)


def learn_from_error(model, message):
    """Groq answers 429 'Request too large ... (OTPM): Limit 1000' when a single request can
    never fit the model's per-minute window. Record that cap (it is not a temporary condition).
    Returns True if a cap was learned."""
    m = _TOO_LARGE.search(message or "")
    if not m:
        return False
    kind, limit = m.group(1), int(m.group(2))
    with _lock:
        st = _state(model)
        if kind == "OTPM":
            st["otpm"] = limit
        else:
            st["tpm"] = limit
    return True


_DAILY = re.compile(r"(?:tokens|requests) per day \((TPD|RPD)\): Limit (\d+), Used (\d+)(?:, Requested (\d+))?", re.S)
DAILY_COOLDOWN_SECONDS = int(os.getenv("AI_DAILY_LIMIT_COOLDOWN_SECONDS", "900"))


def learn_daily_exhaustion(model, message):
    """Groq 429 'Rate limit reached ... tokens per day (TPD): Limit 200000, Used 198941, Requested 5480':
    the model's daily budget cannot fit this request; retrying in seconds is useless. Cool the model
    down for a long period (rolling window frees tokens only gradually). Returns True if detected."""
    m = _DAILY.search(message or "")
    if not m:
        return False
    cooldown(model, DAILY_COOLDOWN_SECONDS)
    return True


def cooldown(model, seconds):
    with _lock:
        st = _state(model)
        st["cooldown_until"] = max(st["cooldown_until"], time.monotonic() + max(1.0, float(seconds)))


def plan_call(model, prompt_text, wanted_tokens):
    """Return (max_completion_tokens, wait_seconds) for this model, or (None, None) if it
    cannot serve this prompt at all (too large for its per-minute window)."""
    now = time.monotonic()
    est_prompt = estimate_tokens(prompt_text)
    with _lock:
        st = _state(model)
        budget = st["tpm"] - est_prompt - SAFETY_TOKENS
        if st["otpm"]:
            budget = min(budget, st["otpm"])  # per-model output-tokens-per-minute cap (e.g. 1,000)
        # A model may serve a request only if it can return at least half of the wanted output
        # (min 600 tokens): big page generations skip low-cap models, short replies can use them.
        if budget < min(wanted_tokens, max(600, wanted_tokens // 2)):
            return None, None
        max_tokens = min(wanted_tokens, budget)
        need = est_prompt + max_tokens
        wait = max(0.0, st["cooldown_until"] - now)
        if st["remaining_tokens"] is not None and st["remaining_tokens"] < need and st["tokens_reset_at"] > now:
            wait = max(wait, st["tokens_reset_at"] - now)
        return max_tokens, wait


def reserve(model, prompt_text, max_tokens):
    """Optimistically subtract the request from the local view of the window."""
    with _lock:
        st = _state(model)
        if st["remaining_tokens"] is not None:
            st["remaining_tokens"] -= estimate_tokens(prompt_text) + max_tokens


def choose(chain, prompt_text, wanted_tokens):
    """Pick the model that can start soonest. Returns (model, max_tokens, wait) or raises
    a capacity error carrying a retry-after hint."""
    options = []
    for index, model in enumerate(chain):
        max_tokens, wait = plan_call(model, prompt_text, wanted_tokens)
        if max_tokens is not None:
            options.append((wait, index, model, max_tokens))
    if not options:
        return None, None, None
    options.sort()
    wait, _i, model, max_tokens = options[0]
    return model, max_tokens, wait


def snapshot():
    now = time.monotonic()
    with _lock:
        return {m: {"tpm": s["tpm"], "otpm": s["otpm"], "remainingTokens": s["remaining_tokens"],
                    "remainingRequestsToday": s["remaining_requests"],
                    "cooldownSeconds": round(max(0.0, s["cooldown_until"] - now), 1)} for m, s in _models.items()}


def reset():
    with _lock:
        _models.clear()


# --------------------------------------------------------------- daily budget
def global_daily_budget():
    try:
        return int(os.getenv("AI_GLOBAL_DAILY_TOKENS", "350000"))
    except ValueError:
        return 350000


def global_tokens_used_24h():
    from sqlalchemy import func, select

    from db import session_scope
    from models import UsageRecord
    since = datetime.now(timezone.utc) - timedelta(days=1)
    with session_scope() as s:
        return int(s.scalar(select(func.coalesce(func.sum(UsageRecord.prompt_tokens + UsageRecord.completion_tokens), 0))
                            .where(UsageRecord.created_at >= since)) or 0)


def capacity_status():
    """Platform-wide AI availability (used to pause new tasks and shown to users)."""
    budget = global_daily_budget()
    used = global_tokens_used_24h()
    now = time.monotonic()
    with _lock:
        all_cooling = bool(_models) and all(s["cooldown_until"] > now for s in _models.values())
        soonest = min((s["cooldown_until"] - now for s in _models.values()), default=0) if all_cooling else 0
    exhausted = budget > 0 and used >= budget
    return {"available": not exhausted and not all_cooling, "dailyTokenBudget": budget, "tokensUsed24h": used,
            "retryAfterSeconds": int(soonest) if all_cooling else (3600 if exhausted else 0),
            "reason": "daily_budget" if exhausted else ("rate_limited" if all_cooling else None)}
