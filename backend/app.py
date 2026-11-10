"""AIDevs 2.0 backend (Flask application factory).

Run locally:   python app.py
Production:    gunicorn -k gevent -w 1 --timeout 180 "app:create_app()"   (see render.yaml)
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, request  # noqa: E402
from flask_cors import CORS  # noqa: E402
from flask_jwt_extended import JWTManager  # noqa: E402
from sqlalchemy import select  # noqa: E402

import db as database  # noqa: E402
from config import Config  # noqa: E402

VERSION = "2.0.0"


def run_migrations(url):
    from alembic import command
    from alembic.config import Config as AlembicConfig

    here = os.path.dirname(os.path.abspath(__file__))
    cfg = AlembicConfig(os.path.join(here, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


def create_app(config_object=None):
    config_object = config_object or Config
    config_object.validate()
    from services.logging_setup import configure, install_request_logging
    configure(config_object.IS_PRODUCTION)

    app = Flask(__name__)
    app.config.from_object(config_object)
    hops = int(os.getenv("TRUST_PROXY_HOPS", "1" if config_object.IS_PRODUCTION else "0"))
    if hops > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops)
    app.json.sort_keys = False

    database.init_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    import models  # noqa: F401  (register tables)
    if not app.config.get("TESTING"):
        database.wait_for_db()  # free serverless Postgres may be waking from scale-to-zero
    if app.config.get("AUTO_MIGRATE"):
        run_migrations(database.normalize_url(app.config["SQLALCHEMY_DATABASE_URI"]))
    elif app.config.get("TESTING"):
        database.Base.metadata.create_all(database.engine)

    CORS(app, origins=app.config["CORS_ORIGINS"], methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"], supports_credentials=False, max_age=600)

    jwt = JWTManager(app)

    @jwt.user_lookup_loader
    def _load_user(_header, payload):
        from models import User
        user = database.get_session().get(User, payload["sub"])
        return user if user and user.is_active else None

    @jwt.token_in_blocklist_loader
    def _revoked(_header, payload):
        from models import RevokedAccessToken
        return database.get_session().get(RevokedAccessToken, payload["jti"]) is not None

    @jwt.user_lookup_error_loader
    def _user_missing(_header, _payload):
        return jsonify(success=False, error="Account not found. Please log in again."), 401

    @jwt.expired_token_loader
    def _expired(_header, _payload):
        return jsonify(success=False, error="Session expired", code="token_expired"), 401

    @jwt.invalid_token_loader
    def _invalid(reason):
        return jsonify(success=False, error="Invalid session token", code="token_invalid"), 401

    @jwt.unauthorized_loader
    def _missing(reason):
        return jsonify(success=False, error="Authentication required", code="auth_required"), 401

    @jwt.revoked_token_loader
    def _revoked_resp(_header, _payload):
        return jsonify(success=False, error="Session ended. Please log in again.", code="token_revoked"), 401

    install_request_logging(app)
    from api.admin import bp as admin_bp
    from api.assets import bp as assets_bp
    from api.auth import bp as auth_bp
    from api.common import ApiError
    from api.legacy import bp as legacy_bp
    from api.projects import bp as projects_bp
    from services.ai_client import AIError
    for blueprint in (auth_bp, projects_bp, assets_bp, legacy_bp, admin_bp):
        app.register_blueprint(blueprint)

    @app.errorhandler(ApiError)
    def _api_error(exc):
        database.get_session().rollback()
        return jsonify(success=False, error=exc.message, **exc.extra), exc.status

    from services.jobs import JobConflict
    from services.limits import LimitExceeded

    @app.errorhandler(LimitExceeded)
    def _limit(exc):
        database.get_session().rollback()
        return jsonify(success=False, error=exc.message, code="limit_exceeded"), exc.status

    @app.errorhandler(JobConflict)
    def _conflict(exc):
        database.get_session().rollback()
        return jsonify(success=False, error=str(exc), code="job_conflict"), 409

    from sqlalchemy.exc import DBAPIError, OperationalError
    from sqlalchemy.exc import TimeoutError as PoolTimeout

    @app.errorhandler(OperationalError)
    @app.errorhandler(PoolTimeout)
    def _db_unavailable(exc):
        """Database waking up / briefly unreachable: tell the client to retry, never 500."""
        try:
            database.get_session().rollback()
        except Exception as rollback_exc:
            logging.getLogger("aidevs.db").warning("rollback after DB error failed: %s", rollback_exc)
        logging.getLogger("aidevs.db").warning("database unavailable: %s", exc.__class__.__name__)
        response = jsonify(success=False, code="db_unavailable",
                           error="The database is waking up or briefly unavailable. Please retry in a few seconds.")
        response.headers["Retry-After"] = "5"
        return response, 503

    @app.errorhandler(DBAPIError)
    def _db_error(exc):
        if getattr(exc, "connection_invalidated", False):
            return _db_unavailable(exc)
        database.get_session().rollback()
        logging.getLogger("aidevs").exception("Database error on %s %s", request.method, request.path)
        return jsonify(success=False, error="Internal server error"), 500

    @app.errorhandler(AIError)
    def _ai_error(exc):
        database.get_session().rollback()
        logging.getLogger("aidevs.ai").warning("AI error surfaced to client: %s", exc)
        retry = getattr(exc, "retry_after", None)
        code = "ai_capacity" if exc.__class__.__name__ in ("AIRateLimited", "AICapacityExhausted") else "ai_error"
        response = jsonify(success=False, error=exc.user_message, code=code, retryAfter=retry)
        if retry:
            response.headers["Retry-After"] = str(int(retry))
        return response, exc.status

    @app.errorhandler(404)
    def _not_found(_e):
        return jsonify(success=False, error="Not found"), 404

    @app.errorhandler(405)
    def _method(_e):
        return jsonify(success=False, error="Method not allowed"), 405

    @app.errorhandler(413)
    def _too_large(_e):
        return jsonify(success=False, error="Request too large"), 413

    @app.errorhandler(Exception)
    def _unhandled(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            return jsonify(success=False, error=exc.description), exc.code
        database.get_session().rollback()
        logging.getLogger("aidevs").exception("Unhandled error on %s %s", request.method, request.path)
        return jsonify(success=False, error="Internal server error"), 500

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if app.config.get("IS_PRODUCTION"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.teardown_appcontext
    def _remove_session(_exc):
        database.SessionLocal.remove()

    def _db_ok():
        try:
            database.get_session().execute(select(1))
            return True
        except Exception as exc:
            logging.getLogger("aidevs.health").error("database check failed: %s", exc.__class__.__name__)
            database.get_session().rollback()
            return False

    def _migration_state():
        try:
            from alembic.runtime.migration import MigrationContext
            from alembic.script import ScriptDirectory
            from alembic.config import Config as AlembicConfig
            here = os.path.dirname(os.path.abspath(__file__))
            cfg = AlembicConfig(os.path.join(here, "alembic.ini"))
            cfg.set_main_option("script_location", os.path.join(here, "migrations"))
            head = ScriptDirectory.from_config(cfg).get_current_head()
            with database.engine.connect() as conn:
                current = MigrationContext.configure(conn).get_current_revision()
            return {"current": current, "head": head, "upToDate": current == head}
        except Exception as exc:
            return {"error": exc.__class__.__name__, "upToDate": app.config.get("TESTING", False)}

    @app.get("/api/health/live")
    def live():
        """Liveness: the process is up and serving (no dependencies checked)."""
        return jsonify(status="alive", version=VERSION)

    @app.get("/api/health/ready")
    def ready():
        """Readiness: database reachable, schema migrated, worker alive (if in-process)."""
        from services import jobs
        from services.ai_client import get_ai_client
        db_ok = _db_ok()
        if app.config.get("TESTING") and not app.config.get("AUTO_MIGRATE"):
            migrations = {"upToDate": True, "note": "test schema created without Alembic"}
        else:
            migrations = _migration_state() if db_ok else {"upToDate": False}
        beat = jobs.heartbeat()
        in_process = os.getenv("RUN_WORKER_IN_PROCESS", "1") == "1" and not app.config.get("TESTING")
        worker_ok = (not in_process) or (beat is not None and (jobs.now() - beat).total_seconds() < 30)
        ok = db_ok and migrations.get("upToDate", False) and worker_ok
        body = {"status": "ready" if ok else "not_ready", "database": db_ok, "migrations": migrations,
                "worker": {"inProcess": in_process, "lastHeartbeat": beat.isoformat() if beat else None,
                           "ok": worker_ok},
                "aiConfigured": get_ai_client().configured}
        return jsonify(body), (200 if ok else 503)

    @app.get("/api/health")
    def health():
        """Backwards-compatible summary (used by Render's health check)."""
        from services.ai_client import get_ai_client
        db_ok = _db_ok()
        return jsonify(status="healthy" if db_ok else "degraded", service="AIDevs Backend", version=VERSION,
                       database=db_ok, ai_configured=get_ai_client().configured), (200 if db_ok else 503)

    if not app.config.get("TESTING"):
        # Jobs are durable: queued/expired work is picked up again by a worker.
        from services.jobs import ensure_worker, release_stale_locks
        release_stale_locks()
        ensure_worker()
    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")),
                    debug=not Config.IS_PRODUCTION, use_reloader=False, threaded=True)
