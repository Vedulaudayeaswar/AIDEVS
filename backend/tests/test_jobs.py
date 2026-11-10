"""Durable job queue: claiming, leases, retries, cancellation, locking, limits."""
import threading
from datetime import timedelta

import pytest

from db import session_scope
from models import AgentRun, Project
from services import jobs
from services.ai_client import AIError, AIInvalidOutput
from tests.conftest import auth, register

CALLS = []


@jobs.register("test-ok")
def _ok(ctx, value):
    ctx.step("working", 50)
    CALLS.append(value)
    return {"value": value}


@jobs.register("test-flaky")
def _flaky(ctx, value):
    CALLS.append(value)
    if CALLS.count(value) == 1:
        raise AIError("provider hiccup")
    return {"value": value}


@jobs.register("test-invalid")
def _invalid(ctx):
    raise AIInvalidOutput("bad output")


@jobs.register("test-wait")
def _wait(ctx, event_id):
    EVENTS[event_id].wait(5)
    ctx.step("after wait", 60)  # raises JobCancelled if cancel was requested
    return {}


EVENTS = {}


@pytest.fixture
def project(client, headers):
    return client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]


def _user_id(client, headers):
    return client.get("/api/auth/me", headers=headers).get_json()["user"]["id"]


def _get(run_id):
    with session_scope() as s:
        return s.get(AgentRun, run_id)


def _queue(app, project_id, user_id, job, *args, kind="checks"):
    """Insert a queued job without executing it (as a web process would)."""
    import db
    jobs.SYNC_MODE = False
    try:
        s = db.get_session()
        run = jobs.submit(s, project_id, user_id, kind, job, *args)
        return run.id
    finally:
        jobs.SYNC_MODE = True


def test_job_runs_and_records_result(app, client, headers, project):
    run_id = _queue(app, project["id"], _user_id(client, headers), "test-ok", 7)
    assert _get(run_id).status == "queued"
    assert jobs.process_one() is True
    run = _get(run_id)
    assert run.status == "succeeded" and run.result == {"value": 7} and run.attempts == 1
    assert run.steps[-1]["message"] == "working"


def test_only_one_worker_can_claim_a_job(app, client, headers, project):
    run_id = _queue(app, project["id"], _user_id(client, headers), "test-ok", 1)
    claims = [jobs._claim(run_id) for _ in range(3)]
    assert claims.count(run_id) == 1 and claims.count(None) == 2


def test_expired_lease_is_recovered_by_another_worker(app, client, headers, project):
    run_id = _queue(app, project["id"], _user_id(client, headers), "test-ok", 2)
    assert jobs._claim(run_id) == run_id  # worker A claims, then "crashes"
    with session_scope() as s:
        s.get(AgentRun, run_id).lease_expires_at = jobs.now() - timedelta(seconds=5)
    assert jobs.process_one() is True  # worker B picks it up
    run = _get(run_id)
    assert run.status == "succeeded" and run.attempts == 2


def test_job_fails_after_max_attempts_of_interruption(app, client, headers, project):
    run_id = _queue(app, project["id"], _user_id(client, headers), "test-ok", 3)
    for _ in range(2):
        jobs._claim(run_id)
        with session_scope() as s:
            s.get(AgentRun, run_id).lease_expires_at = jobs.now() - timedelta(seconds=5)
    jobs.process_one()
    run = _get(run_id)
    assert run.status == "failed" and "interrupted" in run.error


def test_transient_ai_error_is_retried_but_invalid_output_is_not(app, client, headers, project):
    uid = _user_id(client, headers)
    CALLS.clear()
    flaky = _queue(app, project["id"], uid, "test-flaky", "x")
    jobs.process_one()
    run = _get(flaky)
    assert run.status == "queued" and run.run_after is not None and "Retrying" in run.message
    with session_scope() as s:
        s.get(AgentRun, flaky).run_after = jobs.now() - timedelta(seconds=1)
    jobs.process_one()
    assert _get(flaky).status == "succeeded"
    invalid = _queue(app, project["id"], uid, "test-invalid")
    jobs.process_one()
    assert _get(invalid).status == "failed" and _get(invalid).attempts == 1


def test_cancel_queued_and_running_jobs(app, client, headers, project):
    uid = _user_id(client, headers)
    queued = _queue(app, project["id"], uid, "test-ok", 4)
    resp = client.post(f"/api/runs/{queued}/cancel", headers=headers)
    assert resp.get_json()["status"] == "cancelled" and _get(queued).status == "cancelled"

    EVENTS["w"] = threading.Event()
    running = _queue(app, project["id"], uid, "test-wait", "w")
    worker = threading.Thread(target=jobs.process_one)
    worker.start()
    for _ in range(100):
        if _get(running).status == "running":
            break
        threading.Event().wait(0.02)
    assert client.post(f"/api/runs/{running}/cancel", headers=headers).get_json()["status"] == "cancelling"
    EVENTS["w"].set()
    worker.join(5)
    assert _get(running).status == "cancelled"


def test_project_lock_prevents_concurrent_ai_mutations(app, client, headers, project):
    uid = _user_id(client, headers)
    first = _queue(app, project["id"], uid, "test-ok", 5, kind="feature")
    with session_scope() as s:
        assert s.get(Project, project["id"]).active_run_id == first
    resp = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "add a blog"}, headers=headers)
    assert resp.status_code == 409 and resp.get_json()["code"] == "job_conflict"
    restore = client.post(f"/api/projects/{project['id']}/versions/x/restore", headers=headers)
    assert restore.status_code == 409
    jobs.process_one()
    with session_scope() as s:
        assert s.get(Project, project["id"]).active_run_id is None  # released on completion


def test_per_user_concurrent_job_limit(app, client, headers, monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_JOBS_PER_USER", "2")
    uid = _user_id(client, headers)
    projects = [client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
                for _ in range(3)]
    _queue(app, projects[0]["id"], uid, "test-ok", 1)
    _queue(app, projects[1]["id"], uid, "test-ok", 2)
    resp = client.post(f"/api/projects/{projects[2]['id']}/assistant", json={"message": "hi"}, headers=headers)
    assert resp.status_code == 429 and "AI task" in resp.get_json()["error"]
    other = auth(register(client, "Other", "Person", "other@example.com"))
    other_project = client.post("/api/projects", json={"blank": True}, headers=other).get_json()["project"]
    assert client.post(f"/api/projects/{other_project['id']}/assistant", json={"message": "hi"},
                       headers=other).status_code == 202  # limits are per user


def test_cancel_requires_ownership(app, client, headers, project):
    run_id = _queue(app, project["id"], _user_id(client, headers), "test-ok", 9)
    stranger = auth(register(client, "Mallory", "Evil", "mallory@example.com"))
    assert client.post(f"/api/runs/{run_id}/cancel", headers=stranger).status_code == 404
    assert client.get(f"/api/runs/{run_id}", headers=stranger).status_code == 404


def test_background_worker_loop_processes_jobs(app, client, headers, project):
    run_id = _queue(app, project["id"], _user_id(client, headers), "test-ok", 11)
    stop = threading.Event()
    thread = threading.Thread(target=jobs.worker_loop, kwargs={"stop_event": stop}, daemon=True)
    thread.start()
    for _ in range(200):
        if _get(run_id).status == "succeeded":
            break
        threading.Event().wait(0.05)
    stop.set()
    thread.join(5)
    assert _get(run_id).status == "succeeded"
    assert jobs.heartbeat() is not None


def test_worker_restarts_in_forked_process(monkeypatch):
    """gunicorn may build the app in its master and fork: the child must start its own worker."""
    from services import jobs
    started = []

    class FakeThread:
        def __init__(self, target=None, kwargs=None, name=None, daemon=None):
            self.alive = False

        def start(self):
            self.alive = True
            started.append(self)

        def is_alive(self):
            return self.alive

    monkeypatch.setattr(jobs, "SYNC_MODE", False)
    monkeypatch.setenv("RUN_WORKER_IN_PROCESS", "1")
    monkeypatch.setattr(jobs.threading, "Thread", FakeThread)
    monkeypatch.setattr(jobs, "_worker_thread", None)
    monkeypatch.setattr(jobs, "_worker_pid", None)
    monkeypatch.setattr(jobs, "WORKER_ID", jobs.WORKER_ID)  # restored after the test
    monkeypatch.setattr(jobs.os, "getpid", lambda: 100)
    jobs.ensure_worker()
    jobs.ensure_worker()
    assert len(started) == 1
    parent_id = jobs.WORKER_ID
    monkeypatch.setattr(jobs.os, "getpid", lambda: 200)  # forked child: the parent's thread is not here
    jobs.ensure_worker()
    assert len(started) == 2 and jobs.WORKER_ID != parent_id and ":200:" in jobs.WORKER_ID
    assert jobs.heartbeat() is not None


def test_after_fork_resets_connection_pool():
    import db
    from sqlalchemy import text
    with db.engine.connect() as conn:
        conn.execute(text("select 1"))
    db.after_fork()
    with db.engine.connect() as conn:
        assert conn.execute(text("select 1")).scalar() == 1
