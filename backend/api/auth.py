"""Authentication API.

Session model
* Access token: short-lived JWT (default 15 min), kept in memory by the SPA.
* Refresh token: opaque random string (default 30 days). Only its SHA-256
  hash is stored. It rotates on every refresh; presenting an already-rotated
  token revokes the whole token family (theft detection).
* Logout revokes the refresh token and blocklists the current access token.

Why the refresh token is returned in the body instead of an HttpOnly cookie:
the frontend and API are deployed as two different `*.onrender.com` sites
(onrender.com is on the Public Suffix List), so a cookie would be a
third-party cookie that Safari/Chrome increasingly block, which is exactly the
"logged out after refresh" bug users hit. With the preview iframe now fully
sandboxed (opaque origin, CSP, no generated scripts) the main XSS vector that
could read localStorage is closed. If the app is ever served from the same
site as the API, switch to the cookie transport in `issue_session`.
"""
import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (create_access_token, current_user, get_jwt, jwt_required,
                                verify_jwt_in_request)
from sqlalchemy import or_, select

from api.common import audit, json_body, rate_limit
from db import get_session
from models import RefreshToken, RevokedAccessToken, User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
log = logging.getLogger("aidevs.auth")

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,24}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z '\-]{0,79}$")
SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")


def password_checks(password):
    password = password or ""
    return {
        "min_length": len(password) >= 8,
        "has_letter": bool(re.search(r"[A-Za-z]", password)),
        "has_number": bool(re.search(r"\d", password)),
        "has_special": bool(SPECIAL_RE.search(password)),
        "max_length": len(password) <= 128,
    }


def password_errors(password):
    messages = {
        "min_length": "Password must be at least 8 characters",
        "has_letter": "Password must contain a letter",
        "has_number": "Password must contain a number",
        "has_special": "Password must contain a special character",
        "max_length": "Password must be at most 128 characters",
    }
    return [messages[k] for k, ok in password_checks(password).items() if not ok]


def is_admin_email(email):
    admins = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
    return email.lower() in admins


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc)


def _aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def issue_session(session, user, family_id=None):
    access = create_access_token(identity=user.id, additional_claims={"username": user.username})
    raw = secrets.token_urlsafe(48)
    session.add(RefreshToken(
        user_id=user.id, token_hash=_hash_token(raw), family_id=family_id or secrets.token_hex(16),
        expires_at=_now() + timedelta(days=current_app.config["REFRESH_TOKEN_DAYS"]),
        user_agent=(request.headers.get("User-Agent") or "")[:255],
    ))
    return {
        "user": user.to_public(),
        "accessToken": access,
        "refreshToken": raw,
        "expiresIn": current_app.config["ACCESS_TOKEN_MINUTES"] * 60,
        # Backwards compatibility with the v1 client
        "token": access, "username": user.username, "success": True,
    }


def _unique_username(session, first, last):
    base = re.sub(r"[^a-z.]", "", f"{first.lower()}.{last.lower()}")[:60] or "user"
    candidate, n = base, 1
    while session.scalar(select(User.id).where(User.username == candidate)):
        n += 1
        candidate = f"{base}{n}"
    return candidate


@bp.post("/register")
@rate_limit("auth-register", limit=10, window=60)
def register():
    from services import limits
    if not limits.get("registration_open"):
        return jsonify(success=False, error="New registrations are temporarily closed."), 403
    data = json_body()
    first = str(data.get("firstName", "")).strip()
    middle = str(data.get("middleName", "")).strip()
    last = str(data.get("lastName", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    errors = {}
    if not NAME_RE.match(first) or len(first) < 2:
        errors["firstName"] = "First name must be at least 2 letters"
    if not NAME_RE.match(last) or len(last) < 2:
        errors["lastName"] = "Last name must be at least 2 letters"
    if middle and not NAME_RE.match(middle):
        errors["middleName"] = "Middle name can only contain letters"
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address"
    pw_errors = password_errors(password)
    if pw_errors:
        errors["password"] = pw_errors[0]
    if errors:
        return jsonify(success=False, error=next(iter(errors.values())), fields=errors), 400

    session = get_session()
    if session.scalar(select(User.id).where(User.email == email)):
        return jsonify(success=False, error="An account with this email already exists. Please log in.",
                       fields={"email": "already registered"}), 409

    user = User(
        email=email, username=_unique_username(session, first, last), first_name=first,
        middle_name=middle, last_name=last,
        password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode(),
        last_login_at=_now(), role="admin" if is_admin_email(email) else "user",
    )
    session.add(user)
    session.flush()
    payload = issue_session(session, user)
    audit(session, user.id, "auth.register", user.id)
    session.commit()
    return jsonify(payload), 201


@bp.post("/login")
@rate_limit("auth-login", limit=10, window=60)
def login():
    data = json_body()
    identifier = str(data.get("identifier") or data.get("email") or data.get("username") or "").strip().lower()
    password = str(data.get("password", ""))
    if not identifier or not password:
        return jsonify(success=False, error="Email/username and password are required"), 400
    session = get_session()
    user = session.scalar(select(User).where(or_(User.email == identifier, User.username == identifier)))
    # Constant-ish time: always run one bcrypt check.
    hashed = user.password_hash.encode() if user else bcrypt.hashpw(b"x", bcrypt.gensalt(rounds=4))
    ok = bcrypt.checkpw(password.encode(), hashed) and user is not None and user.is_active
    if not ok:
        audit(session, user.id if user else None, "auth.login_failed", identifier[:120])
        session.commit()
        return jsonify(success=False, error="Invalid email/username or password"), 401
    user.last_login_at = _now()
    if user.role != "admin" and is_admin_email(user.email):
        user.role = "admin"
    payload = issue_session(session, user)
    audit(session, user.id, "auth.login", user.id)
    session.commit()
    payload.update(firstName=user.first_name, lastName=user.last_name, message="Login successful!")
    return jsonify(payload)


@bp.post("/refresh")
@rate_limit("auth-refresh", limit=60, window=60)
def refresh():
    raw = str(json_body().get("refreshToken", ""))
    if not raw:
        return jsonify(success=False, error="Refresh token required"), 401
    session = get_session()
    token = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw)))
    if token is None:
        return jsonify(success=False, error="Session expired. Please log in again."), 401
    if token.revoked_at is not None:
        # Re-use of a rotated token: assume theft, revoke the entire family.
        for t in session.scalars(select(RefreshToken).where(RefreshToken.family_id == token.family_id,
                                                            RefreshToken.revoked_at.is_(None))):
            t.revoked_at = _now()
        audit(session, token.user_id, "auth.refresh_reuse_detected", token.family_id)
        session.commit()
        return jsonify(success=False, error="Session expired. Please log in again."), 401
    if _aware(token.expires_at) <= _now():
        return jsonify(success=False, error="Session expired. Please log in again."), 401
    user = session.get(User, token.user_id)
    if user is None or not user.is_active:
        return jsonify(success=False, error="Account unavailable"), 401
    token.revoked_at = _now()
    payload = issue_session(session, user, family_id=token.family_id)
    session.commit()
    return jsonify(payload)


@bp.post("/logout")
def logout():
    session = get_session()
    raw = str(json_body().get("refreshToken", ""))
    if raw:
        token = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw)))
        if token and token.revoked_at is None:
            token.revoked_at = _now()
    try:
        verify_jwt_in_request(optional=True)
        claims = get_jwt()
        if claims.get("jti"):
            session.merge(RevokedAccessToken(
                jti=claims["jti"], expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc)))
            audit(session, claims.get("sub"), "auth.logout", "")
    except Exception as exc:  # expired/invalid access token: refresh token is still revoked above
        log.info("logout without a valid access token: %s", exc.__class__.__name__)
    session.commit()
    return jsonify(success=True)


@bp.get("/me")
@jwt_required()
def me():
    return jsonify(success=True, user=current_user.to_public())


@bp.post("/validate-password")
def validate_password():
    password = str(json_body().get("password", ""))
    errors = password_errors(password)
    return jsonify(valid=not errors, errors=errors, checks=password_checks(password))


def _verify_password(user, password):
    return bool(password) and bcrypt.checkpw(str(password).encode(), user.password_hash.encode())


@bp.post("/change-password")
@jwt_required()
@rate_limit("auth-change-password", limit=5, window=300, per_user=True)
def change_password():
    data = json_body()
    session = get_session()
    user = session.get(User, current_user.id)
    if not _verify_password(user, data.get("currentPassword")):
        return jsonify(success=False, error="Current password is incorrect"), 400
    new = str(data.get("newPassword", ""))
    errors = password_errors(new)
    if errors:
        return jsonify(success=False, error=errors[0], fields={"newPassword": errors[0]}), 400
    user.password_hash = bcrypt.hashpw(new.encode(), bcrypt.gensalt(rounds=12)).decode()
    # Sign out every other device: revoke all refresh tokens, then issue a fresh session here.
    for token in session.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id,
                                                           RefreshToken.revoked_at.is_(None))):
        token.revoked_at = _now()
    payload = issue_session(session, user)
    audit(session, user.id, "auth.password_changed", user.id)
    session.commit()
    return jsonify(payload)


@bp.get("/export")
@jwt_required()
@rate_limit("auth-export", limit=5, window=3600, per_user=True)
def export_account_data():
    """Everything we store about the user, as JSON (data portability)."""
    from models import ChatMessage, MemoryItem, Project, UsageRecord
    from services.versions import capture
    session = get_session()
    user = session.get(User, current_user.id)
    projects = session.scalars(select(Project).where(Project.owner_id == user.id)).all()
    data = {
        "exportedAt": _now().isoformat(),
        "account": user.to_public(),
        "projects": [{"id": p.id, "createdAt": p.created_at.isoformat(), "prompt": p.prompt, **capture(p),
                      "messages": [{"role": m.role, "content": m.content, "at": m.created_at.isoformat()}
                                   for m in session.scalars(select(ChatMessage).where(ChatMessage.project_id == p.id))],
                      "memory": [{"kind": m.kind, "content": m.content}
                                 for m in session.scalars(select(MemoryItem).where(MemoryItem.project_id == p.id))]}
                     for p in projects],
        "aiUsage": [{"task": u.task, "model": u.model, "tokens": u.prompt_tokens + u.completion_tokens,
                     "at": u.created_at.isoformat()}
                    for u in session.scalars(select(UsageRecord).where(UsageRecord.user_id == user.id))],
    }
    audit(session, user.id, "auth.data_export", user.id)
    session.commit()
    response = jsonify(data)
    response.headers["Content-Disposition"] = 'attachment; filename="aidevs-account-data.json"'
    return response


@bp.delete("/account")
@jwt_required()
@rate_limit("auth-delete", limit=5, window=3600, per_user=True)
def delete_account():
    """Permanently delete the account and all projects, assets, versions and messages."""
    data = json_body()
    session = get_session()
    user = session.get(User, current_user.id)
    if not _verify_password(user, data.get("password")):
        return jsonify(success=False, error="Password is incorrect"), 400
    if str(data.get("confirm", "")).strip().upper() != "DELETE":
        return jsonify(success=False, error='Type DELETE to confirm'), 400
    from models import AgentRun, AuditLog, UsageRecord
    user_id = user.id
    for run in session.scalars(select(AgentRun).where(AgentRun.user_id == user_id,
                                                      AgentRun.status.in_(["queued", "running"]))):
        run.cancel_requested = True
    session.flush()
    session.delete(user)  # cascades: projects -> pages, entities, assets, versions, messages, runs, tokens
    session.execute(UsageRecord.__table__.update().where(UsageRecord.user_id == user_id).values(user_id=None))
    session.add(AuditLog(user_id=None, action="auth.account_deleted", target=user_id[:8] + "…"))
    session.execute(AuditLog.__table__.update().where(AuditLog.user_id == user_id).values(user_id=None))
    session.commit()
    return jsonify(success=True)
