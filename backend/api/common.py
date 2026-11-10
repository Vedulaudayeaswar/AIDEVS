"""Shared helpers for API blueprints: errors, validation, ownership, rate limits, audit."""
from functools import wraps

from flask import jsonify, request
from flask_jwt_extended import current_user

from db import get_session
from models import AuditLog, Project


class ApiError(Exception):
    def __init__(self, message, status=400, **extra):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def client_ip():
    """Client address. X-Forwarded-For is only honoured for the number of trusted
    proxy hops configured via TRUST_PROXY_HOPS (applied by ProxyFix in app.py);
    the left-most XFF entry is attacker-controlled and is never used directly."""
    return (request.remote_addr or "")[:64]


def audit(session, user_id, action, target="", **meta):
    session.add(AuditLog(user_id=user_id, action=action, target=str(target)[:120], ip=client_ip(), meta=meta))


def get_owned_project(project_id, session=None):
    """Return the project if it belongs to the current user, else 404.

    404 (not 403) avoids revealing whether another user's project exists."""
    session = session or get_session()
    project = session.get(Project, project_id) if isinstance(project_id, str) and len(project_id) <= 32 else None
    if project is None or project.owner_id != current_user.id:
        raise ApiError("Project not found", 404)
    return project


# ------------------------------------------------------------- rate limiting
def rate_limit(name, limit, window, per_user=False):
    """Per-IP or per-user limit. Backend: memory (default) or Redis (REDIS_URL)."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import current_app

            from services.ratelimit import check
            if current_app.config.get("TESTING") and not current_app.config.get("RATE_LIMIT_IN_TESTS"):
                return fn(*args, **kwargs)
            ident = current_user.id if per_user else client_ip()
            ok, retry = check(f"{name}:{ident}", limit, window)
            if not ok:
                response = jsonify(success=False, error="Too many requests. Please slow down and try again shortly.",
                                   code="rate_limited", retryAfter=retry)
                response.headers["Retry-After"] = str(retry)
                return response, 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def reset_rate_limits():
    from services.ratelimit import get_limiter
    get_limiter().reset()
