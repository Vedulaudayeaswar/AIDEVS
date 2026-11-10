"""Structured logging with request correlation and secret redaction.

LOG_FORMAT=json (default in production) emits one JSON object per line with
request_id / user_id / project_id / run_id when available. A redaction filter
removes API keys, bearer/JWT tokens and password-like fields from every record,
so secrets cannot reach logs even through exception messages.
"""
import json
import logging
import os
import re
import time
import uuid

from flask import g, has_request_context, request

REDACTIONS = [
    (re.compile(r"gsk_[A-Za-z0-9]{8,}"), "gsk_[REDACTED]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), "Bearer [REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "[JWT REDACTED]"),
    (re.compile(r'(?i)("?(?:password|refreshToken|refresh_token|accessToken|access_token|api_key|secret)"?\s*[:=]\s*)'
                r'("[^"]*"|[^\s,}]+)'), r"\1[REDACTED]"),
]
CONTEXT_FIELDS = ("request_id", "user_id", "project_id", "run_id", "kind", "stage", "progress", "duration_ms",
                  "status", "method", "path", "error", "model", "task", "tokens", "worker_id", "trace")


def redact(text):
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact(str(record.msg))
        if record.args:
            record.args = tuple(redact(str(a)) if isinstance(a, str) else a for a in
                                (record.args if isinstance(record.args, tuple) else (record.args,)))
        for field in ("error", "trace"):
            if isinstance(getattr(record, field, None), str):
                setattr(record, field, redact(getattr(record, field)))
        if has_request_context():
            record.request_id = getattr(g, "request_id", None)
            user = getattr(g, "log_user_id", None)
            if user and not getattr(record, "user_id", None):
                record.user_id = user
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "level": record.levelname,
                "logger": record.name, "msg": record.getMessage()}
        for field in CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value not in (None, ""):
                data[field] = value
        if record.exc_info:
            data["exc"] = redact(self.formatException(record.exc_info))[-4000:]
        return json.dumps(data, default=str)


def configure(production):
    fmt = os.getenv("LOG_FORMAT", "json" if production else "text")
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    handler.setFormatter(JsonFormatter() if fmt == "json" else logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def install_request_logging(app):
    log = logging.getLogger("aidevs.http")

    @app.before_request
    def _start():
        incoming = request.headers.get("X-Request-ID", "")
        g.request_id = incoming if re.fullmatch(r"[A-Za-z0-9\-]{8,64}", incoming or "") else uuid.uuid4().hex
        g.request_started = time.monotonic()

    @app.after_request
    def _finish(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        try:
            from flask_jwt_extended import get_jwt_identity
            user_id = get_jwt_identity()
        except Exception:  # no JWT on this request
            user_id = None
        duration = int((time.monotonic() - getattr(g, "request_started", time.monotonic())) * 1000)
        if request.path != "/api/health/live":
            log.info("request", extra={"method": request.method, "path": request.path, "status": response.status_code,
                                       "duration_ms": duration, "user_id": user_id})
        return response
