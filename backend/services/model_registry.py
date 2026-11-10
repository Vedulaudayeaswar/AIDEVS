"""Central model registry: which Groq model serves which pipeline task.

Defaults verified against Groq's documentation on 2026-11-09: the Llama 3.x
models used by AIDevs 1.x were decommissioned on 2026-08-16 and Groq recommends
the GPT-OSS family. Every chain is filtered against the models the configured
key can actually access (GET /openai/v1/models, cached for an hour), so a
retired or unavailable model is skipped instead of failing at request time.

Override per task without code changes:  AI_MODEL_<TASK>=model-a,model-b
e.g. AI_MODEL_FRONTEND=openai/gpt-oss-120b,openai/gpt-oss-20b
"""
import logging
import os
import threading
import time

log = logging.getLogger("aidevs.models")

# Each model has its own free-tier bucket (8K tokens/min, 1K requests/day measured on 2026-11-10),
# so a three-model chain triples burst capacity. Budgets below keep prompt + completion < 8K TPM.
BIG = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
SMALL = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]

# task -> settings. Tasks marked deterministic do not call a model at all.
TASKS = {
    "requirements": {"chain": BIG, "max_tokens": 4500, "temperature": 0.4,
                     "purpose": "Idea (+reference site) -> application specification"},
    "ui_planning": {"chain": BIG, "max_tokens": 4500, "temperature": 0.4,
                    "purpose": "Page hierarchy & section planning (part of the specification step)"},
    "frontend": {"chain": BIG, "max_tokens": 5500, "temperature": 0.5,
                 "purpose": "Page component trees (UI/UX Architect + Frontend agent)"},
    "code_modification": {"chain": BIG, "max_tokens": 5500, "temperature": 0.4,
                          "purpose": "Project-wide feature changes (models, pages, navigation)"},
    "visual_edit": {"chain": BIG, "max_tokens": 4000, "temperature": 0.5,
                    "purpose": "Edits to a selected element"},
    "error_analysis": {"chain": BIG, "max_tokens": 3500, "temperature": 0.2,
                       "purpose": "Targeted repair of failed validation checks"},
    "chat": {"chain": SMALL, "max_tokens": 1500, "temperature": 0.7,
             "purpose": "Classic builder conversation"},
    "backend": {"chain": [], "deterministic": True,
                "purpose": "Compiled from data models (services/export_backend.py); no LLM code"},
    "testing": {"chain": [], "deterministic": True,
                "purpose": "Deterministic checks (services/checks.py) + generated pytest suites"},
}
# Older task names used by earlier code / env vars.
ALIASES = {"plan": "requirements", "page": "frontend", "feature": "code_modification", "edit": "visual_edit",
           "repair": "error_analysis", "legacy": "chat"}
_REVERSE = {}
for _old, _new in ALIASES.items():
    _REVERSE.setdefault(_new, []).append(_old)

_available = {"at": 0.0, "models": None, "error": None}
_lock = threading.Lock()
TTL = 3600


def canonical(task):
    return ALIASES.get(task, task)


def configured_chain(task):
    task = canonical(task)
    for name in [task] + _REVERSE.get(task, []):
        env = os.getenv(f"AI_MODEL_{name.upper()}")
        if env:
            return [m.strip() for m in env.split(",") if m.strip()]
    legacy_default = os.getenv("GROQ_MODEL")
    chain = list(TASKS.get(task, TASKS["requirements"])["chain"])
    if legacy_default and legacy_default not in chain:
        chain.insert(0, legacy_default)
    return chain


def available_models(client=None, force=False):
    """Model ids the key can access, or None when unknown (no key / API error)."""
    with _lock:
        if not force and _available["models"] is not None and time.monotonic() - _available["at"] < TTL:
            return _available["models"]
    if client is None:
        return None
    try:
        listing = client.models.list()
        ids = {m.id for m in getattr(listing, "data", []) if getattr(m, "active", True) is not False}
        with _lock:
            _available.update(at=time.monotonic(), models=ids, error=None)
        log.info("groq models available: %d", len(ids))
        return ids
    except Exception as exc:
        with _lock:
            _available.update(at=time.monotonic(), error=str(exc)[:300])
        log.warning("could not list Groq models: %s", exc.__class__.__name__)
        return None


def chain_for(task, client=None):
    chain = configured_chain(task)
    available = available_models(client)
    if available is None:
        return chain
    usable = [m for m in chain if m in available]
    if not usable:
        log.error("no configured model for task %s is available to this key; trying configured chain", task)
        return chain
    return usable


def params(task):
    spec = TASKS.get(canonical(task), TASKS["requirements"])
    return {"max_tokens": spec.get("max_tokens", 6000), "temperature": spec.get("temperature", 0.5)}


def describe(check_availability=False):
    client = None
    if check_availability:
        from services.ai_client import get_ai_client
        client = get_ai_client().raw_client()
    available = available_models(client, force=check_availability) if client else None
    return {
        "availabilityChecked": available is not None,
        "availabilityError": _available["error"],
        "tasks": [{"task": name, "purpose": t["purpose"], "deterministic": bool(t.get("deterministic")),
                   "configured": configured_chain(name) if not t.get("deterministic") else [],
                   "usable": ([m for m in configured_chain(name) if available is None or m in available]
                              if not t.get("deterministic") else []),
                   "maxTokens": t.get("max_tokens"), "temperature": t.get("temperature")}
                  for name, t in TASKS.items()],
    }
