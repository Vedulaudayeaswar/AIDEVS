"""Centralized Groq AI service.

* One platform-owned GROQ_API_KEY (never per-user, never sent to the browser).
* Task-based model routing, configurable via env without touching agents:
    AI_MODEL_<TASK>=model-a,model-b   (comma separated fallback chain)
* Timeouts, exponential backoff with Retry-After support, fallback to the next
  model on rate limits / decommissioned models.
* Structured JSON output with validation + one repair attempt.
* Per-user daily request/token quotas and usage accounting.

Model defaults were chosen from Groq's documentation on 2026-11-09:
`llama-3.3-70b-versatile` / `llama-3.1-8b-instant` were decommissioned on
2026-08-16 and Groq recommends `openai/gpt-oss-120b` / `openai/gpt-oss-20b`.
"""
import json
import logging
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from config import Config
from db import session_scope
from models import UsageRecord

log = logging.getLogger("aidevs.ai")

class AIError(Exception):
    """Base error. `user_message` is safe to show to end users."""
    status = 502

    def __init__(self, user_message, detail=""):
        super().__init__(detail or user_message)
        self.user_message = user_message


class AINotConfigured(AIError):
    status = 503


class AIQuotaExceeded(AIError):
    status = 429


class AIRateLimited(AIError):
    status = 429

    def __init__(self, user_message, detail="", retry_after=None):
        super().__init__(user_message, detail)
        self.retry_after = retry_after


class AICapacityExhausted(AIRateLimited):
    """Platform-wide free AI budget used up: new AI tasks are paused."""


class AIInvalidOutput(AIError):
    status = 502


@dataclass
class AIResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    data: object = None


def models_for(task, client=None):
    """Model fallback chain for a task (see services/model_registry.py)."""
    from services.model_registry import chain_for
    return chain_for(task, client)


def _status_code(exc):
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None)


def _retry_after(exc):
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    try:
        value = headers.get("retry-after")
        return min(float(value), 30.0) if value else None
    except (TypeError, ValueError):
        return None


def extract_json(text):
    """Parse a JSON object from model output (tolerates code fences / chatter)."""
    if text is None:
        raise ValueError("empty response")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


class AIClient:
    def __init__(self, api_key=None, transport=None):
        self._api_key = api_key if api_key is not None else Config.GROQ_API_KEY
        self._transport = transport  # injectable for tests: fn(model, messages, **kw) -> (text, pt, ct)
        self._client = None
        self._lock = threading.Lock()

    @property
    def configured(self):
        return bool(self._transport or self._api_key)

    def raw_client(self):
        """The underlying Groq SDK client (None in tests / when unconfigured)."""
        if self._transport or not self._api_key:
            return None
        return self._groq()

    def _groq(self):
        with self._lock:
            if self._client is None:
                from groq import Groq
                self._client = Groq(
                    api_key=self._api_key,
                    timeout=Config.AI_TIMEOUT_SECONDS,
                    max_retries=0,  # retries handled here (model fallback aware)
                )
            return self._client

    # ------------------------------------------------------------------ quota
    def check_quota(self, user_id):
        if not user_id:
            return
        since = datetime.now(timezone.utc) - timedelta(days=1)
        with session_scope() as s:
            count, tokens = s.execute(
                select(
                    func.count(UsageRecord.id),
                    func.coalesce(func.sum(UsageRecord.prompt_tokens + UsageRecord.completion_tokens), 0),
                ).where(UsageRecord.user_id == user_id, UsageRecord.created_at >= since)
            ).one()
        from services import limits
        if count >= limits.get("ai_daily_requests"):
            raise AIQuotaExceeded("Daily AI request limit reached. Please try again tomorrow.")
        if tokens >= limits.get("ai_daily_tokens"):
            raise AIQuotaExceeded("Daily AI token budget reached. Please try again tomorrow.")

    def _record(self, user_id, project_id, task, model, pt, ct, status, started):
        try:
            with session_scope() as s:
                s.add(UsageRecord(
                    user_id=user_id, project_id=project_id, task=task, model=model,
                    prompt_tokens=pt or 0, completion_tokens=ct or 0, status=status,
                    latency_ms=int((time.monotonic() - started) * 1000),
                ))
        except Exception:  # usage accounting must never break the request
            log.exception("failed to record AI usage")

    # ------------------------------------------------------------------ calls
    def _call_model(self, model, messages, max_tokens, temperature, json_mode):
        """Returns (text, prompt_tokens, completion_tokens, headers)."""
        if self._transport:
            out = self._transport(model, messages, max_tokens=max_tokens, temperature=temperature, json_mode=json_mode)
            return (*out, {}) if len(out) == 3 else out
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if model.startswith("openai/gpt-oss"):
            kwargs["reasoning_effort"] = os.getenv("AI_REASONING_EFFORT", "low")
        elif model.startswith("qwen/"):
            kwargs["reasoning_format"] = "hidden"  # keep chain-of-thought out of the JSON answer
        raw = self._groq().chat.completions.with_raw_response.create(**kwargs)
        response = raw.parse()
        usage = getattr(response, "usage", None)
        text = response.choices[0].message.content or ""
        return (text, getattr(usage, "prompt_tokens", 0) or 0, getattr(usage, "completion_tokens", 0) or 0,
                dict(raw.headers))

    def complete(self, task, system, user, *, user_id=None, project_id=None,
                 max_tokens=4000, temperature=0.6, json_mode=False):
        from services import ai_capacity
        from services.model_registry import params
        if not self.configured:
            raise AINotConfigured(
                "AI is not configured on this server. The administrator must set GROQ_API_KEY.")
        self.check_quota(user_id)
        status = ai_capacity.capacity_status()
        if status["reason"] == "daily_budget":
            raise AICapacityExhausted("Today's shared free AI capacity has been used up. New AI tasks are paused; "
                                      "please try again later (the budget refreshes over the next 24 hours).",
                                      retry_after=status["retryAfterSeconds"])

        max_tokens = min(max_tokens, params(task)["max_tokens"])
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        prompt_text = system + user
        chain = models_for(task, None if self._transport else self.raw_client())
        blocked, failures, last_error, last_code = set(), {}, None, None
        for _round in range(len(chain) * max(1, Config.AI_MAX_RETRIES)):
            candidates = [m for m in chain if m not in blocked]
            if not candidates:
                break
            model, call_tokens, wait = ai_capacity.choose(candidates, prompt_text, max_tokens)
            if model is None:
                raise AIError("This request is too large for the AI models' per-minute limit. "
                              "Try a shorter instruction or a smaller selection.")
            if wait > ai_capacity.max_wait():
                when = f"{int(wait) + 1} seconds" if wait < 120 else f"{int(wait // 60) + 1} minutes"
                raise AIRateLimited(f"The shared free AI capacity is used up for now. Please try again in about {when} "
                                    "- your project was not changed.", retry_after=int(wait) + 1)
            if wait > 0:
                time.sleep(wait)
            ai_capacity.reserve(model, prompt_text, call_tokens)
            started = time.monotonic()
            try:
                text, pt, ct, headers = self._call_model(model, messages, call_tokens, temperature, json_mode)
                ai_capacity.update_from_headers(model, headers)
                self._record(user_id, project_id, task, model, pt, ct, "ok", started)
                return AIResult(text=text, model=model, prompt_tokens=pt, completion_tokens=ct)
            except Exception as exc:  # classify provider errors
                code = _status_code(exc)
                response = getattr(exc, "response", None)
                ai_capacity.update_from_headers(model, dict(getattr(response, "headers", {}) or {}))
                # Rejected generations still consume the provider's quota: account for them.
                body = getattr(exc, "body", None)
                err = body.get("error", body) if isinstance(body, dict) else {}
                failed = err.get("failed_generation", "") if isinstance(err, dict) else ""
                spent_in = ai_capacity.estimate_tokens(prompt_text) if failed else 0
                spent_out = ai_capacity.estimate_tokens(failed) if failed else 0
                self._record(user_id, project_id, task, model, spent_in, spent_out, f"error:{code or 'net'}", started)
                last_error, last_code = exc, code
                log.warning("AI call failed task=%s model=%s code=%s err=%s", task, model, code, str(exc)[:300])
                if code in (401, 403):
                    raise AINotConfigured("The platform's AI key was rejected by Groq.", str(exc)) from exc
                if code == 429 and ai_capacity.learn_from_error(model, str(exc)):
                    continue  # request can never fit this model's window: re-plan (smaller or another model)
                if code == 429 and ai_capacity.learn_daily_exhaustion(model, str(exc)):
                    continue  # daily quota of this model used up: long cooldown, try another model
                if code == 429:
                    ai_capacity.cooldown(model, _retry_after(exc) or 60)
                    continue  # try another model's bucket (or wait for this one)
                if code == 400 and "json_validate_failed" in str(exc):
                    failures[model] = failures.get(model, 0) + 1  # model produced invalid JSON: may succeed again
                elif code in (400, 404, 413, 422):
                    blocked.add(model)  # unknown/decommissioned model or request rejected: next model
                    continue
                else:
                    failures[model] = failures.get(model, 0) + 1  # timeout / network / 5xx
                    time.sleep(min(8.0, (2 ** failures[model]) + random.random()))
                if failures.get(model, 0) >= Config.AI_MAX_RETRIES:
                    blocked.add(model)
        if last_code == 429:
            raise AIRateLimited("The shared free AI capacity is busy. Please retry in a minute - your project "
                                "was not changed.", str(last_error), retry_after=60)
        raise AIError("The AI service failed to respond. Please try again.", str(last_error))

    def complete_json(self, task, system, user, *, validator=None, **kwargs):
        """Return parsed+validated JSON. One repair round-trip on invalid output."""
        kwargs.setdefault("temperature", 0.4)
        result = self.complete(task, system, user, json_mode=True, **kwargs)
        problem = None
        for attempt in range(2):
            try:
                data = extract_json(result.text)
                if validator:
                    data = validator(data)
                result.data = data
                return result
            except Exception as exc:  # JSON or schema validation error
                problem = str(exc)[:800]
                if attempt == 1:
                    break
                repair_user = (
                    f"{user}\n\nYour previous answer was invalid: {problem}\n"
                    "Return ONLY a corrected JSON object that satisfies every requirement."
                )
                result = self.complete(task, system, repair_user, json_mode=True, **kwargs)
        raise AIInvalidOutput("The AI returned an invalid result. Nothing was changed; please retry.",
                              problem or "")


_client = None


def get_ai_client():
    global _client
    if _client is None:
        _client = AIClient()
    return _client


def set_ai_client(client):
    """Used by tests to inject a fake transport."""
    global _client
    _client = client
