"""Durable, database-backed job queue for long-running AI work.

Why not Celery/RQ: they require Redis/RabbitMQ even for local development. The
platform already has a transactional database, so jobs live in `agent_runs`:

* submit()  - inserts a queued job (payload = registered job name + args),
              atomically claims the project's mutation lock, enforces per-user
              concurrency limits.
* workers   - claim jobs with a compare-and-swap UPDATE (safe across processes
              and machines on PostgreSQL and SQLite), hold a lease that every
              progress step extends, and release the project lock at the end.
* recovery  - a job whose lease expired (worker crashed / redeployed) is
              re-queued until max_attempts, then failed with a clear reason.
* retries   - transient AI failures (rate limits, provider errors) are retried
              with backoff; validation/quota failures are not.
* cancel    - queued jobs cancel immediately; running jobs stop at their next
              progress step. A stale worker that lost its lease stops the same way.

Workers run inside the web process by default (RUN_WORKER_IN_PROCESS=1, good for
one instance) or as a separate process: `python manage.py worker`.
"""
import logging
import os
import socket
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update

from db import session_scope
from models import AgentRun, Project

log = logging.getLogger("aidevs.jobs")
SYNC_MODE = False  # tests execute jobs inline (same code path)
POLL_SECONDS = float(os.getenv("JOB_POLL_SECONDS", "1.0"))
LEASE_SECONDS = int(os.getenv("JOB_LEASE_SECONDS", "120"))
MUTATING_KINDS = ("generate", "feature")
TERMINAL = ("succeeded", "failed", "cancelled")
REGISTRY = {}

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
_last_heartbeat = {"at": None}


def now():
    return datetime.now(timezone.utc)


def aware(dt):
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def register(name):
    def decorator(fn):
        REGISTRY[name] = fn
        return fn
    return decorator


class JobCancelled(Exception):
    pass


class JobConflict(Exception):
    """Another AI job already holds this project's mutation lock."""


class RunContext:
    def __init__(self, run_id, worker_id):
        self.run_id = run_id
        self.worker_id = worker_id

    def step(self, message, progress=None, level="info"):
        """Record progress, extend the lease, and stop if cancelled or superseded."""
        with session_scope() as s:
            run = s.get(AgentRun, self.run_id)
            if run.worker_id != self.worker_id or run.status != "running":
                raise JobCancelled("This job was taken over by another worker.")
            if run.cancel_requested:
                raise JobCancelled("Cancelled by the user.")
            steps = list(run.steps or [])
            steps.append({"at": now().isoformat(), "message": message[:500], "level": level})
            run.steps = steps[-200:]
            run.message = message[:500]
            run.lease_expires_at = now() + timedelta(seconds=LEASE_SECONDS)
            if progress is not None:
                run.progress = max(0, min(100, int(progress)))
            started = aware(run.started_at) or now()
            if (now() - started).total_seconds() > run.timeout_seconds:
                raise TimeoutError(f"The job exceeded its time limit of {run.timeout_seconds}s.")
        log.info("job step", extra={"run_id": self.run_id, "progress": progress, "stage": message[:120]})


# ------------------------------------------------------------------ submit
def submit(session, project_id, user_id, kind, job_name, *args, max_attempts=2, quota_id=None):
    """Queue a job. Raises LimitExceeded / JobConflict instead of dropping work.

    `quota_id` (from limits.consume) is refunded automatically if the job fails or is cancelled."""
    from services import ai_capacity, limits
    capacity = ai_capacity.capacity_status()
    if not capacity["available"]:
        raise limits.LimitExceeded("Shared free AI capacity is temporarily used up, so new AI tasks are paused. "
                                   f"Please try again in about {max(1, capacity['retryAfterSeconds'] // 60)} minute(s). "
                                   "Your projects are safe.", status=503)
    limits.check_job_quota(session, user_id)
    run = AgentRun(project_id=project_id, user_id=user_id, kind=kind, status="queued", message="Queued",
                   payload={"job": job_name, "args": list(args), "quota_id": quota_id}, max_attempts=max_attempts,
                   timeout_seconds=limits.get("job_timeout_seconds"))
    session.add(run)
    session.flush()
    if kind in MUTATING_KINDS:
        claimed = session.execute(update(Project).where(Project.id == project_id, Project.active_run_id.is_(None))
                                  .values(active_run_id=run.id)).rowcount
        if claimed != 1:
            session.rollback()
            raise JobConflict("An AI task is already running for this project. Please wait for it to finish.")
    session.commit()
    log.info("job queued", extra={"run_id": run.id, "project_id": project_id, "user_id": user_id, "kind": kind})
    if SYNC_MODE:
        process_one(run_id=run.id)
        session.expire_all()
        session.refresh(run)
    else:
        ensure_worker()
    return run


def cancel(session, run):
    if run.status == "queued":
        claimed = session.execute(update(AgentRun).where(AgentRun.id == run.id, AgentRun.status == "queued")
                                  .values(status="cancelled", message="Cancelled", error="Cancelled by the user.",
                                          finished_at=now())).rowcount
        if claimed:
            _release_project(session, run)
            session.commit()
            _refund(run.payload)
            return "cancelled"
    if run.status == "running":
        run.cancel_requested = True
        session.commit()
        return "cancelling"
    return run.status


def _refund(payload):
    from services import limits
    try:
        limits.refund((payload or {}).get("quota_id"))
    except Exception:
        log.exception("quota refund failed")


def _release_project(session, run):
    session.execute(update(Project).where(Project.id == run.project_id, Project.active_run_id == run.id)
                    .values(active_run_id=None))


# ------------------------------------------------------------------ worker
def _claim(run_id=None):
    """Atomically claim one runnable job. Returns its id or None."""
    with session_scope() as s:
        t = now()
        runnable = or_(
            (AgentRun.status == "queued") & or_(AgentRun.run_after.is_(None), AgentRun.run_after <= t),
            (AgentRun.status == "running") & (AgentRun.lease_expires_at < t),  # crashed worker
        )
        if run_id:
            ordered = s.scalars(select(AgentRun.id).where(AgentRun.id == run_id, runnable)).all()
        else:
            # Fair scheduling: among the oldest runnable jobs, prefer users with the fewest running jobs,
            # so one busy user cannot starve everyone else; FIFO within the same load.
            rows = s.execute(select(AgentRun.id, AgentRun.user_id).where(runnable)
                             .order_by(AgentRun.created_at).limit(25)).all()
            from sqlalchemy import func
            busy = dict(s.execute(select(AgentRun.user_id, func.count(AgentRun.id))
                                  .where(AgentRun.status == "running", AgentRun.lease_expires_at >= t)
                                  .group_by(AgentRun.user_id)).all())
            ordered = [rid for _pos, rid in sorted(
                ((busy.get(uid, 0), pos), rid) for pos, (rid, uid) in enumerate(rows))]
        for candidate in ordered:
            claimed = s.execute(update(AgentRun).where(AgentRun.id == candidate, runnable).values(
                status="running", worker_id=WORKER_ID, attempts=AgentRun.attempts + 1,
                lease_expires_at=t + timedelta(seconds=LEASE_SECONDS), started_at=t,
            )).rowcount
            if claimed == 1:
                return candidate
    return None


def _finish(run_id, status, *, result=None, error="", retry_in=None):
    with session_scope() as s:
        run = s.get(AgentRun, run_id)
        if run.worker_id != WORKER_ID:
            return  # lost the lease; the new owner reports the outcome
        steps = list(run.steps or [])
        if retry_in is not None:
            run.status, run.run_after, run.lease_expires_at = "queued", now() + timedelta(seconds=retry_in), None
            run.message = f"Retrying shortly (attempt {run.attempts}/{run.max_attempts} failed: {error[:200]})"
            steps.append({"at": now().isoformat(), "message": run.message, "level": "warning"})
            run.steps = steps
            return
        run.status, run.finished_at, run.lease_expires_at = status, now(), None
        if status in ("failed", "cancelled"):
            refund_payload = dict(run.payload or {})
        else:
            refund_payload = None
        if status == "succeeded":
            run.progress, run.result, run.message = 100, result or {}, "Completed"
        else:
            run.error, run.message = error, error
            steps.append({"at": now().isoformat(), "message": error, "level": "error"})
            run.steps = steps
        _release_project(s, run)
    if refund_payload:
        _refund(refund_payload)


def _is_retryable(exc):
    from services.ai_client import AIError, AIInvalidOutput, AINotConfigured, AIQuotaExceeded, AIRateLimited
    if isinstance(exc, (AIInvalidOutput, AINotConfigured, AIQuotaExceeded, JobCancelled, TimeoutError)):
        return False
    if isinstance(exc, AIRateLimited) and (exc.retry_after or 0) > 120:
        return False  # capacity exhausted for a long time: fail fast, refund, tell the user when to retry
    return isinstance(exc, AIError)


def process_one(run_id=None):
    """Claim one job (optionally a specific one) and run it to completion."""
    claimed = _claim(run_id)
    if not claimed:
        return False
    _run_claimed(claimed)
    return True


def _run_claimed(claimed):
    with session_scope() as s:
        run = s.get(AgentRun, claimed)
        job_name, args, attempts, max_attempts = run.payload.get("job"), run.payload.get("args", []), \
            run.attempts, run.max_attempts
        kind = run.kind
        if run.cancel_requested:
            job_name = None
    started = time.monotonic()
    fn = REGISTRY.get(job_name)
    if job_name is None:
        _finish(claimed, "cancelled", error="Cancelled by the user.")
        return True
    if fn is None:
        _finish(claimed, "failed", error=f"Unknown job type '{job_name}'.")
        return True
    if attempts > max_attempts:
        _finish(claimed, "failed", error="The job was interrupted too many times (server restarts). Please retry.")
        _on_failure(fn, claimed, args, "interrupted")
        return True
    from services import ai_capacity
    ai_capacity.set_job_mode(True)
    try:
        result = fn(RunContext(claimed, WORKER_ID), *args) or {}
        _finish(claimed, "succeeded", result=result)
        log.info("job succeeded", extra={"run_id": claimed, "kind": kind,
                                         "duration_ms": int((time.monotonic() - started) * 1000)})
    except JobCancelled as exc:
        _finish(claimed, "cancelled", error=str(exc))
        _on_failure(fn, claimed, args, str(exc))
    except Exception as exc:
        message = getattr(exc, "user_message", None) or str(exc)[:500] or exc.__class__.__name__
        if _is_retryable(exc) and attempts < max_attempts:
            log.warning("job retry", extra={"run_id": claimed, "kind": kind, "error": message})
            _finish(claimed, "queued", error=message, retry_in=min(60, 10 * attempts))
            return True
        log.error("job failed", extra={"run_id": claimed, "kind": kind, "error": message,
                                       "trace": traceback.format_exc()[-2000:]})
        _finish(claimed, "failed", error=message)
        _on_failure(fn, claimed, args, message)
    finally:
        ai_capacity.set_job_mode(False)
    return True


def _on_failure(fn, run_id, args, message):
    hook = getattr(fn, "on_failure", None)
    if hook:
        try:
            hook(run_id, args, message)
        except Exception:
            log.exception("failure hook failed", extra={"run_id": run_id})


def heartbeat():
    return _last_heartbeat["at"]


def worker_loop(stop_event=None, concurrency=1):
    """Poll for jobs forever (or until stop_event). Safe to run in many processes."""
    stop_event = stop_event or threading.Event()
    log.info("job worker started", extra={"worker_id": WORKER_ID, "concurrency": concurrency})
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="aidevs-job") as pool:
        active = set()
        while not stop_event.is_set():
            _last_heartbeat["at"] = now()
            active = {f for f in active if not f.done()}
            if len(active) < concurrency:
                try:
                    run_id = _claim()
                except Exception:
                    log.exception("job claim failed")
                    run_id = None
                if run_id:
                    active.add(pool.submit(_run_claimed, run_id))
                    continue
            stop_event.wait(POLL_SECONDS)


_worker_thread = None
_worker_lock = threading.Lock()


def ensure_worker():
    """Start the in-process worker once (unless a dedicated worker is used)."""
    global _worker_thread
    if SYNC_MODE or os.getenv("RUN_WORKER_IN_PROCESS", "1") != "1":
        return
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            from config import Config
            _worker_thread = threading.Thread(target=worker_loop, kwargs={"concurrency": Config.AI_MAX_CONCURRENT_JOBS},
                                              name="aidevs-worker", daemon=True)
            _worker_thread.start()


def queue_stats(session):
    from sqlalchemy import func
    rows = session.execute(select(AgentRun.status, func.count(AgentRun.id)).group_by(AgentRun.status)).all()
    return {status: count for status, count in rows}


def release_stale_locks():
    """Clear project locks whose run is already terminal (e.g. after a crash mid-finish)."""
    with session_scope() as s:
        stale = s.execute(select(Project.id, Project.active_run_id).where(Project.active_run_id.is_not(None))).all()
        for pid, rid in stale:
            run = s.get(AgentRun, rid)
            if run is None or run.status in TERMINAL:
                s.execute(update(Project).where(Project.id == pid, Project.active_run_id == rid)
                          .values(active_run_id=None))
