"""Administrator-only operations API.

Admins are users whose email is listed in ADMIN_EMAILS (promoted at login) or
promoted with `python manage.py make-admin`. Every route re-checks the role on
the server and answers 404 to everyone else so the API is not discoverable.
"""
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, jsonify
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func, select, update

from api.common import ApiError, audit, json_body
from db import get_session
from models import AgentRun, PlatformSetting, Project, RefreshToken, UsageRecord, User
from services import jobs, limits, ratelimit

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if current_user is None or current_user.role != "admin":
            raise ApiError("Not found", 404)
        return fn(*args, **kwargs)
    return wrapper


@bp.get("/overview")
@admin_required
def overview():
    s = get_session()
    since = datetime.now(timezone.utc) - timedelta(days=1)
    usage = s.execute(select(UsageRecord.model, UsageRecord.status, func.count(UsageRecord.id),
                             func.coalesce(func.sum(UsageRecord.prompt_tokens + UsageRecord.completion_tokens), 0))
                      .where(UsageRecord.created_at >= since).group_by(UsageRecord.model, UsageRecord.status)).all()
    failed = s.scalars(select(AgentRun).where(AgentRun.status == "failed", AgentRun.created_at >= since)
                       .order_by(AgentRun.created_at.desc()).limit(25)).all()
    runs_24h = s.execute(select(AgentRun.kind, AgentRun.status, func.count(AgentRun.id))
                         .where(AgentRun.created_at >= since).group_by(AgentRun.kind, AgentRun.status)).all()
    return jsonify(
        users=s.scalar(select(func.count(User.id))),
        newUsers24h=s.scalar(select(func.count(User.id)).where(User.created_at >= since)),
        projects=s.scalar(select(func.count(Project.id))),
        queue=jobs.queue_stats(s),
        workerHeartbeat=jobs.heartbeat().isoformat() if jobs.heartbeat() else None,
        runs24h=[{"kind": k, "status": st, "count": c} for k, st, c in runs_24h],
        aiUsage24h=[{"model": m, "status": st, "requests": c, "tokens": int(t)} for m, st, c, t in usage],
        rateLimited=ratelimit.blocked_counts(),
        rateLimitBackend=ratelimit.get_limiter().name,
        failedRuns=[{"id": r.id, "kind": r.kind, "projectId": r.project_id, "userId": r.user_id,
                     "error": r.error[:300], "attempts": r.attempts,
                     "at": r.created_at.isoformat()} for r in failed],
    )


@bp.get("/users")
@admin_required
def users():
    s = get_session()
    since = datetime.now(timezone.utc) - timedelta(days=1)
    usage = dict(s.execute(select(UsageRecord.user_id, func.count(UsageRecord.id))
                           .where(UsageRecord.created_at >= since).group_by(UsageRecord.user_id)).all())
    projects = dict(s.execute(select(Project.owner_id, func.count(Project.id)).group_by(Project.owner_id)).all())
    rows = s.scalars(select(User).order_by(User.created_at.desc()).limit(500)).all()
    return jsonify(users=[{**u.to_public(), "isActive": u.is_active, "projects": projects.get(u.id, 0),
                           "aiRequests24h": usage.get(u.id, 0),
                           "lastLoginAt": u.last_login_at.isoformat() if u.last_login_at else None} for u in rows])


@bp.patch("/users/<user_id>")
@admin_required
def update_user(user_id):
    s = get_session()
    user = s.get(User, user_id)
    if user is None:
        raise ApiError("User not found", 404)
    data = json_body()
    if "isActive" in data:
        if user.id == current_user.id:
            raise ApiError("You cannot disable your own account", 400)
        user.is_active = bool(data["isActive"])
        if not user.is_active:  # end all sessions immediately
            s.execute(update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
                      .values(revoked_at=datetime.now(timezone.utc)))
    audit(s, current_user.id, "admin.user_update", user.id, isActive=user.is_active)
    s.commit()
    return jsonify(user={**user.to_public(), "isActive": user.is_active})


@bp.get("/settings")
@admin_required
def get_settings():
    return jsonify(settings=[{"key": k, "value": limits.get(k), "default": limits.defaults()[k],
                              "description": v[3], "type": v[0].__name__} for k, v in limits.LIMITS.items()])


@bp.put("/settings")
@admin_required
def put_settings():
    s = get_session()
    data = json_body()
    try:
        changes = {k: limits.coerce(k, v) for k, v in data.items()}
    except (ValueError, TypeError) as exc:
        raise ApiError(str(exc), 400) from exc
    for key, value in changes.items():
        row = s.get(PlatformSetting, key)
        if row is None:
            s.add(PlatformSetting(key=key, value={"v": value}, updated_by=current_user.id))
        else:
            row.value, row.updated_by = {"v": value}, current_user.id
    audit(s, current_user.id, "admin.settings", ",".join(changes), **{k: v for k, v in changes.items()})
    s.commit()
    limits.invalidate()
    return get_settings()


@bp.get("/models")
@admin_required
def models():
    from services.model_registry import describe
    return jsonify(describe(check_availability=True))
