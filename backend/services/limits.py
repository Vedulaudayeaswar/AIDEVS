"""Central, admin-configurable resource limits.

Defaults come from environment variables; administrators can override them at
runtime (stored in `platform_settings`). Every limit check produces an
`ApiError` with a clear, user-facing message instead of silently dropping work.
"""
import os
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from db import session_scope


def _env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name, default):
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


# name -> (type, env var, default, description)
# Defaults are tuned for a zero-cost deployment (Groq free tier, Neon free 1 GB, Render free).
LIMITS = {
    "ai_generations_per_day": (int, "AI_GENERATIONS_PER_DAY", 3, "Full AI app generations per user per 24h"),
    "ai_modifications_per_day": (int, "AI_MODIFICATIONS_PER_DAY", 15, "AI edits/feature changes/repairs per user per 24h"),
    "exports_per_day": (int, "EXPORTS_PER_DAY", 10, "Project exports per user per 24h"),
    "max_projects_per_user": (int, "MAX_PROJECTS_PER_USER", 3, "Projects per user"),
    "max_storage_mb_per_user": (int, "MAX_STORAGE_MB_PER_USER", 50, "Uploaded asset storage per user (MB)"),
    "max_total_storage_mb": (int, "MAX_TOTAL_STORAGE_MB", 300, "Uploaded asset storage for the whole platform (MB)"),
    "ai_daily_requests": (int, "AI_DAILY_REQUESTS_PER_USER", 60, "Raw AI model calls per user per 24h"),
    "ai_daily_tokens": (int, "AI_DAILY_TOKENS_PER_USER", 150_000, "AI tokens per user per 24h"),
    "max_concurrent_jobs_per_user": (int, "MAX_CONCURRENT_JOBS_PER_USER", 1, "Queued+running AI jobs per user"),
    "max_pages_per_project": (int, "MAX_PAGES_PER_PROJECT", 12, "Pages per project"),
    "max_asset_mb": (int, "MAX_ASSET_MB", 3, "Largest single upload (MB)"),
    "job_timeout_seconds": (int, "JOB_TIMEOUT_SECONDS", 900, "Maximum duration of one AI job"),
    "registration_open": (bool, "REGISTRATION_OPEN", True, "Allow new sign-ups"),
}
ACTIONS = {"generate": ("ai_generations_per_day", "full AI generations"),
           "modify": ("ai_modifications_per_day", "AI modifications"),
           "export": ("exports_per_day", "exports")}

_cache = {"at": 0.0, "values": {}}
_lock = threading.Lock()
CACHE_SECONDS = 15


class LimitExceeded(Exception):
    def __init__(self, message, status=429):
        super().__init__(message)
        self.message = message
        self.status = status


def defaults():
    out = {}
    for name, (kind, env, default, _desc) in LIMITS.items():
        out[name] = _env_bool(env, default) if kind is bool else _env_int(env, default)
    return out


def _overrides():
    from models import PlatformSetting
    with _lock:
        if time.monotonic() - _cache["at"] < CACHE_SECONDS:
            return _cache["values"]
    try:
        with session_scope() as s:
            rows = {r.key: r.value.get("v") for r in s.scalars(select(PlatformSetting))}
    except Exception:  # table missing during first migration, etc.
        rows = {}
    with _lock:
        _cache.update(at=time.monotonic(), values=rows)
    return rows


def invalidate():
    with _lock:
        _cache["at"] = 0.0


def get(name):
    kind = LIMITS[name][0]
    value = _overrides().get(name, defaults()[name])
    return bool(value) if kind is bool else int(value)


def all_limits():
    return {name: get(name) for name in LIMITS}


def coerce(name, value):
    if name not in LIMITS:
        raise ValueError(f"unknown setting {name}")
    kind = LIMITS[name][0]
    if kind is bool:
        if isinstance(value, bool):
            return value
        raise ValueError(f"{name} must be true or false")
    value = int(value)
    if value < 0 or value > 100_000_000:
        raise ValueError(f"{name} out of range")
    return value


# ------------------------------------------------------------------ checks
def lock_user(session, user_id):
    """Serialize quota checks per user: a no-op UPDATE takes the user's row lock on
    PostgreSQL and the write lock on SQLite until the caller commits, so concurrent
    requests cannot both pass a limit check."""
    from sqlalchemy import update

    from models import User
    session.execute(update(User).where(User.id == user_id).values(role=User.role))


def consume(session, user_id, action):
    """Atomically count and record one unit of a daily quota. Returns a quota id that
    can be refunded if the work fails. Caller must commit."""
    from models import AuditLog
    name, label = ACTIONS[action]
    lock_user(session, user_id)
    since = datetime.now(timezone.utc) - timedelta(days=1)
    rows = session.scalars(select(AuditLog.created_at).where(
        AuditLog.user_id == user_id, AuditLog.action == f"quota.{action}", AuditLog.created_at >= since)
        .order_by(AuditLog.created_at)).all()
    limit = get(name)
    if len(rows) >= limit:
        oldest = rows[0] if rows[0].tzinfo else rows[0].replace(tzinfo=timezone.utc)
        hours = max(1, int(((oldest + timedelta(days=1)) - datetime.now(timezone.utc)).total_seconds() // 3600) + 1)
        raise LimitExceeded(f"You've used all {limit} {label} for today on the free plan. "
                            f"More become available in about {hours} hour(s).")
    record = AuditLog(user_id=user_id, action=f"quota.{action}", target="")
    session.add(record)
    session.flush()
    return record.id


def refund(quota_id):
    """Give a quota unit back (the AI work failed or was cancelled)."""
    if not quota_id:
        return
    from sqlalchemy import delete

    from models import AuditLog
    with session_scope() as s:
        s.execute(delete(AuditLog).where(AuditLog.id == quota_id, AuditLog.action.like("quota.%")))


def usage_today(session, user_id):
    from models import AuditLog
    since = datetime.now(timezone.utc) - timedelta(days=1)
    rows = dict(session.execute(select(AuditLog.action, func.count(AuditLog.id)).where(
        AuditLog.user_id == user_id, AuditLog.action.like("quota.%"), AuditLog.created_at >= since)
        .group_by(AuditLog.action)).all())
    return {action: rows.get(f"quota.{action}", 0) for action in ACTIONS}


def check_project_quota(session, user_id):
    from models import Project
    lock_user(session, user_id)
    count = session.scalar(select(func.count(Project.id)).where(Project.owner_id == user_id))
    limit = get("max_projects_per_user")
    if count >= limit:
        raise LimitExceeded(f"You have reached the free-plan limit of {limit} projects. "
                            "Delete a project to create a new one.")


def check_page_quota(session, project_id):
    from models import Page
    count = session.scalar(select(func.count(Page.id)).where(Page.project_id == project_id))
    limit = get("max_pages_per_project")
    if count >= limit:
        raise LimitExceeded(f"Projects can have at most {limit} pages.")


def check_job_quota(session, user_id):
    from models import AgentRun
    active = session.scalar(select(func.count(AgentRun.id)).where(
        AgentRun.user_id == user_id, AgentRun.status.in_(["queued", "running"])))
    limit = get("max_concurrent_jobs_per_user")
    if active >= limit:
        raise LimitExceeded(f"You already have {active} AI task(s) running. Please wait for one to finish "
                            f"(limit {limit}).")


def check_storage_quota(session, user_id, incoming_bytes):
    from models import Asset, Project
    lock_user(session, user_id)
    total = session.scalar(select(func.coalesce(func.sum(Asset.size), 0)))
    if total + incoming_bytes > get("max_total_storage_mb") * 1024 * 1024:
        raise LimitExceeded("Image storage for the free platform is currently full. Use image URLs instead of "
                            "uploads, or delete unused assets.", status=507)
    used = session.scalar(select(func.coalesce(func.sum(Asset.size), 0)).join(Project, Asset.project_id == Project.id)
                          .where(Project.owner_id == user_id))
    limit = get("max_storage_mb_per_user") * 1024 * 1024
    if used + incoming_bytes > limit:
        raise LimitExceeded(f"Upload storage limit reached ({get('max_storage_mb_per_user')} MB). "
                            "Delete unused assets to free space.", status=413)
    return used


def storage_used(session, user_id):
    from models import Asset, Project
    return int(session.scalar(select(func.coalesce(func.sum(Asset.size), 0))
                              .join(Project, Asset.project_id == Project.id).where(Project.owner_id == user_id)))
