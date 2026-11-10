"""Zero-cost deployment behaviour: free-tier AI capacity, daily quotas, Neon/DB failures, restarts."""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy.exc import OperationalError

import db as database
from api.common import reset_rate_limits
from app import create_app
from config import TestConfig
from db import session_scope
from models import AgentRun, Project
from services import ai_capacity, jobs
from services import ai_client as ai
from tests.conftest import auth, register
from tests.test_projects import load_page


# ------------------------------------------------------- Groq free-tier capacity
def test_groq_reset_header_durations():
    assert ai_capacity.parse_duration("682ms") == pytest.approx(0.682)
    assert ai_capacity.parse_duration("7.66s") == pytest.approx(7.66)
    assert ai_capacity.parse_duration("2m59.56s") == pytest.approx(179.56)
    assert ai_capacity.parse_duration("1h2m3s") == pytest.approx(3723)
    assert ai_capacity.parse_duration("12") == 12.0


def test_requests_are_sized_to_fit_the_per_minute_token_window(fake_ai):
    ai_capacity.update_from_headers("m", {"x-ratelimit-limit-tokens": "8000", "x-ratelimit-remaining-tokens": "8000",
                                          "x-ratelimit-reset-tokens": "1s"})
    prompt = "x" * 7000  # ~2000 tokens
    max_tokens, wait = ai_capacity.plan_call("m", prompt, 9000)
    assert max_tokens + ai_capacity.estimate_tokens(prompt) <= 8000 and wait == 0
    assert ai_capacity.plan_call("m", "x" * 30000, 4000) == (None, None)  # can never fit: skip model


def test_scheduler_picks_the_model_with_free_budget_and_honours_429(app, monkeypatch, fake_ai):
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    ai_capacity.update_from_headers("openai/gpt-oss-120b", {"x-ratelimit-remaining-tokens": "100",
                                                            "x-ratelimit-reset-tokens": "20s"})
    model, _tokens, wait = ai_capacity.choose(["openai/gpt-oss-120b", "openai/gpt-oss-20b"], "hello", 2000)
    assert model == "openai/gpt-oss-20b" and wait == 0  # exhausted window -> other model's bucket

    calls = []

    def transport(model, messages, **kw):
        calls.append(model)
        if len(calls) == 1:
            err = Exception("rate limited")
            err.status_code = 429
            err.response = type("R", (), {"headers": {"retry-after": "45"}})()
            raise err
        return "ok", 5, 5
    client = ai.AIClient(api_key="", transport=transport)
    assert client.complete("chat", "s", "u").text == "ok"
    assert calls[0] != calls[1]  # moved to another model after the 429


def test_all_models_saturated_returns_clear_retry_after(app, fake_ai):
    for model in ai.models_for("chat"):
        ai_capacity.cooldown(model, 600)
    client = ai.AIClient(api_key="", transport=lambda *a, **k: ("never", 1, 1))
    with pytest.raises(ai.AIRateLimited) as info:
        client.complete("chat", "s", "u")
    assert info.value.retry_after > 500 and "try again in about" in info.value.user_message.lower()


def test_new_ai_tasks_pause_when_shared_capacity_is_exhausted(client, headers, fake_ai, monkeypatch):
    project = client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
    for model in ai.models_for("code_modification"):
        ai_capacity.cooldown(model, 300)
    resp = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "add a blog"}, headers=headers)
    assert resp.status_code == 503 and "paused" in resp.get_json()["error"]
    usage = client.get("/api/usage", headers=headers).get_json()
    assert usage["aiCapacity"]["available"] is False and usage["today"]["modify"] == 0  # nothing consumed
    ai_capacity.reset()
    client.post("/api/projects/plan", json={"prompt": "A bakery website with menu"}, headers=headers)  # uses tokens
    monkeypatch.setenv("AI_GLOBAL_DAILY_TOKENS", "1")  # platform-wide daily budget now used up
    plan = client.post("/api/projects/plan", json={"prompt": "A bakery website with menu"}, headers=headers)
    assert plan.status_code == 429 and plan.get_json()["code"] == "ai_capacity"  # direct AI calls refuse too
    resp = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "add a blog"}, headers=headers)
    assert resp.status_code == 503 and client.get("/api/public-status").get_json()["ai"]["available"] is False


def test_groq_timeout_and_unavailable_model_fall_back(app, monkeypatch, fake_ai):
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    seq = []

    def transport(model, messages, **kw):
        seq.append(model)
        if model == "openai/gpt-oss-120b":
            err = Exception("model_decommissioned")
            err.status_code = 404
            raise err
        if len(seq) == 2:
            raise TimeoutError("read timeout")
        return "fine", 3, 3
    result = ai.AIClient(api_key="", transport=transport).complete("frontend", "s", "u")
    assert result.text == "fine" and seq[0] == "openai/gpt-oss-120b" and "openai/gpt-oss-120b" not in seq[1:]


# --------------------------------------------------------------- daily quotas
def test_daily_generation_quota_cannot_be_bypassed_with_parallel_requests(tmp_path, fake_ai, monkeypatch):
    monkeypatch.setenv("AI_GENERATIONS_PER_DAY", "2")
    url = "sqlite:///" + os.path.join(tmp_path, "quota.db").replace("\\", "/")

    class FileConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = url

    jobs.SYNC_MODE = True
    reset_rate_limits()
    app = create_app(FileConfig)
    headers = auth(register(app.test_client()))
    spec = app.test_client().post("/api/projects/plan", json={"prompt": "sneaker store"}, headers=headers).get_json()["spec"]

    def create(_i):
        return app.test_client().post("/api/projects", json={"spec": spec}, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(create, range(6)))
    assert codes.count(201) == 2, codes
    assert all(c in (409, 429) for c in codes if c != 201), codes
    listed = app.test_client().get("/api/projects", headers=headers).get_json()
    assert listed["total"] == 2  # rejected requests left no empty projects behind
    database.SessionLocal.remove()
    database.engine.dispose()


def test_failed_ai_work_is_refunded_and_quota_message_is_clear(client, headers, fake_ai, monkeypatch):
    monkeypatch.setenv("AI_MODIFICATIONS_PER_DAY", "1")
    project = client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
    fake_ai.overrides["feature"] = "not json at all"  # AI returns garbage twice -> job fails
    resp = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "add a blog"}, headers=headers)
    assert resp.get_json()["run"]["status"] == "failed"
    assert client.get("/api/usage", headers=headers).get_json()["today"]["modify"] == 0  # refunded
    fake_ai.overrides.pop("feature")
    ok = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "add a blog"}, headers=headers)
    assert ok.status_code == 202 and ok.get_json()["run"]["status"] == "succeeded"
    blocked = client.post(f"/api/projects/{project['id']}/assistant", json={"message": "again"}, headers=headers)
    assert blocked.status_code == 429 and "1 AI modifications for today" in blocked.get_json()["error"]


def test_free_plan_default_limits():
    from services import limits
    d = limits.defaults()
    env_overridden = {"MAX_PROJECTS_PER_USER", "AI_GENERATIONS_PER_DAY", "AI_MODIFICATIONS_PER_DAY", "EXPORTS_PER_DAY"}
    saved = {k: os.environ.pop(k) for k in env_overridden if k in os.environ}
    try:
        d = limits.defaults()
        assert (d["max_projects_per_user"], d["ai_generations_per_day"], d["ai_modifications_per_day"],
                d["exports_per_day"], d["max_storage_mb_per_user"]) == (3, 3, 15, 10, 50)
    finally:
        os.environ.update(saved)


# ------------------------------------------------- database / Neon behaviour
def test_neon_urls_get_ssl_and_pool_settings():
    from db import normalize_url
    url = normalize_url("postgres://u:p@ep-x-123.eu-central-1.aws.neon.tech/neondb?channel_binding=require")
    assert url.startswith("postgresql://") and "sslmode=require" in url and "channel_binding" not in url
    assert "sslmode=verify-full" in normalize_url("postgresql://u:p@ep-x.neon.tech/db?sslmode=verify-full")


def test_database_outage_returns_503_not_500(client, headers, monkeypatch):
    import api.projects as projects_api

    def broken(*_a, **_k):
        raise OperationalError("SELECT 1", {}, Exception("server closed the connection unexpectedly"))
    monkeypatch.setattr(projects_api, "get_owned_project", broken)
    resp = client.get("/api/projects/abc", headers=headers)
    assert resp.status_code == 503 and resp.get_json()["code"] == "db_unavailable"
    assert resp.headers["Retry-After"] == "5"


def test_startup_waits_for_a_sleeping_database(monkeypatch):
    attempts = {"n": 0}

    class FakeConn:
        def __enter__(self):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise OperationalError("connect", {}, Exception("compute is waking up"))
            return self

        def __exit__(self, *a):
            return False

        def execute(self, *_a):
            return None

    monkeypatch.setattr(database, "engine", type("E", (), {"connect": lambda self: FakeConn()})())
    monkeypatch.setattr(database.time, "sleep", lambda s: None)
    assert database.wait_for_db(attempts=5) is True and attempts["n"] == 3


# ------------------------------------------------- restarts and fair scheduling
def test_generation_resumes_after_a_restart_mid_run(client, headers, fake_ai):
    """Simulates Render restarting while a generation runs: the lease expires and the next
    worker re-runs the (idempotent) generation from the durable queue."""
    spec = client.post("/api/projects/plan", json={"prompt": "sneaker store"}, headers=headers).get_json()["spec"]
    jobs.SYNC_MODE = False
    try:
        body = client.post("/api/projects", json={"spec": spec}, headers=headers).get_json()
    finally:
        jobs.SYNC_MODE = True
    run_id, project_id = body["run"]["id"], body["project"]["id"]
    assert jobs._claim(run_id) == run_id  # worker starts ... then the instance is restarted
    with session_scope() as s:
        s.get(AgentRun, run_id).lease_expires_at = jobs.now() - timedelta(seconds=1)
    jobs.release_stale_locks()  # what the new process does at boot (lock still held by a live run: kept)
    assert jobs.process_one() is True
    with session_scope() as s:
        assert s.get(AgentRun, run_id).status == "succeeded"
        project = s.get(Project, project_id)
        assert project.status == "ready" and project.active_run_id is None
    assert load_page(client, headers, project_id)["tree"]["children"]


def test_fair_scheduling_prefers_users_without_running_jobs(client, fake_ai):
    alice = auth(register(client, "Alice", "Smith", "alice@example.com"))
    bob = auth(register(client, "Bob", "Jones", "bob@example.com"))
    uid = lambda h: client.get("/api/auth/me", headers=h).get_json()["user"]["id"]  # noqa: E731

    @jobs.register("fair-noop")
    def _noop(ctx):
        return {}
    ids = {}
    import db
    jobs.SYNC_MODE = False
    try:
        for name, h in (("a1", alice), ("a2", alice), ("b1", bob)):
            p = client.post("/api/projects", json={"blank": True}, headers=h).get_json()["project"]
            ids[name] = jobs.submit(db.get_session(), p["id"], uid(h), "checks", "fair-noop").id
            time.sleep(0.01)
    finally:
        jobs.SYNC_MODE = True
    assert jobs._claim() == ids["a1"]  # oldest first ...
    assert jobs._claim() == ids["b1"]  # ... then Bob (idle) before Alice's second job
    assert jobs._claim() == ids["a2"]


def test_cancel_during_generation_keeps_project_consistent(client, headers, fake_ai):
    spec = client.post("/api/projects/plan", json={"prompt": "sneaker store"}, headers=headers).get_json()["spec"]
    gate = threading.Event()
    original = fake_ai.__call__

    def slow(model, messages, **kw):
        if "UI/UX Architect" in messages[0]["content"]:
            gate.wait(5)
        return original(model, messages, **kw)
    from services.ai_client import AIClient, set_ai_client
    set_ai_client(AIClient(api_key="", transport=slow))
    jobs.SYNC_MODE = False
    try:
        body = client.post("/api/projects", json={"spec": spec}, headers=headers).get_json()
    finally:
        jobs.SYNC_MODE = True
    run_id, project_id = body["run"]["id"], body["project"]["id"]
    worker = threading.Thread(target=jobs.process_one)
    worker.start()
    for _ in range(100):
        with session_scope() as s:
            if s.get(AgentRun, run_id).status == "running":
                break
        time.sleep(0.02)
    assert client.post(f"/api/runs/{run_id}/cancel", headers=headers).get_json()["status"] == "cancelling"
    gate.set()
    worker.join(10)
    with session_scope() as s:
        run, project = s.get(AgentRun, run_id), s.get(Project, project_id)
        assert run.status == "cancelled" and project.active_run_id is None
    usage = client.get("/api/usage", headers=headers).get_json()
    assert usage["today"]["generate"] == 0  # cancelled work is refunded
    assert client.get(f"/api/projects/{project_id}", headers=headers).status_code == 200


def test_model_output_cap_is_learned_from_request_too_large(app, monkeypatch, fake_ai):
    """Real Groq behaviour (2026-11-10): qwen free tier rejects requests with
    'Request too large ... (OTPM): Limit 1000'. The client must route around it, not wait."""
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    calls = []

    def transport(model, messages, max_tokens=None, **kw):
        calls.append((model, max_tokens))
        if model == "qwen/qwen3.8-27b" and max_tokens > 1000:
            err = Exception("Error code: 429 - Request too large for model `qwen/qwen3.8-27b` in organization `org` "
                            "service tier `on_demand` on output tokens per minute (OTPM): Limit 1000, Requested 3631.")
            err.status_code = 429
            raise err
        return "small answer", 5, 5
    monkeypatch.setenv("AI_MODEL_CHAT", "qwen/qwen3.8-27b")
    client = ai.AIClient(api_key="", transport=transport)
    assert client.complete("chat", "s", "u", max_tokens=1500).text == "small answer"
    assert calls[0] == ("qwen/qwen3.8-27b", 1500) and calls[1] == ("qwen/qwen3.8-27b", 1000)  # resized, no cooldown
    assert ai_capacity.snapshot()["qwen/qwen3.8-27b"]["otpm"] == 1000
    assert ai_capacity.plan_call("qwen/qwen3.8-27b", "x" * 100, 5000) == (None, None)  # big pages skip it
    assert ai_capacity.plan_call("qwen/qwen3.8-27b", "x" * 100, 1200)[0] == 1000  # short replies may use it


def test_production_refuses_sqlite(monkeypatch):
    from config import Config

    class Prod(Config):
        IS_PRODUCTION = True
        JWT_SECRET_KEY = "x" * 40
        SQLALCHEMY_DATABASE_URI = "sqlite:///lost-on-restart.db"
    monkeypatch.delenv("ALLOW_SQLITE_IN_PRODUCTION", raising=False)
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        Prod.validate()


def test_daily_quota_exhaustion_fails_fast_and_refunds(client, headers, fake_ai):
    """Real Groq behaviour (2026-11-10): after a heavy day every model answers
    '429 ... tokens per day (TPD): Limit 200000, Used 198941'. Generation must stop with a clear
    message (no template filler pages), refund the user's quota and pause new AI tasks."""
    def tpd_exhausted(user):
        err = Exception("Error code: 429 - Rate limit reached for model `x` on tokens per day (TPD): "
                        "Limit 200000, Used 198941, Requested 5480. Please try again in 37m.")
        err.status_code = 429
        return err
    spec = client.post("/api/projects/plan", json={"prompt": "sneaker store"}, headers=headers).get_json()["spec"]
    fake_ai.overrides["page"] = tpd_exhausted
    resp = client.post("/api/projects", json={"spec": spec}, headers=headers)
    run = resp.get_json()["run"]
    assert run["status"] == "failed" and "capacity" in run["error"].lower(), run
    assert client.get("/api/usage", headers=headers).get_json()["today"]["generate"] == 0  # refunded
    snapshot = ai_capacity.snapshot()
    assert all(v["cooldownSeconds"] > 600 for v in snapshot.values())  # every model cooled down for long
    blocked = client.post("/api/projects", json={"spec": spec}, headers=headers)
    assert blocked.status_code == 503 and "paused" in blocked.get_json()["error"]


def test_generation_pauses_part_way_and_continue_builds_only_empty_pages(client, headers, fake_ai):
    """Real scenario (2026-11-10): the free AI quota ran out after 2 of 6 pages."""
    import json as _json
    from tests.conftest import page_response
    calls = {"n": 0}

    def flaky_pages(user):
        calls["n"] += 1
        if calls["n"] >= 2:  # capacity runs out while designing the second page
            err = Exception("429 Rate limit reached on tokens per day (TPD): Limit 200000, Used 199999, Requested 5000")
            err.status_code = 429
            return err
        return page_response(user.split("(route ")[1].split(")")[0])
    spec = client.post("/api/projects/plan", json={"prompt": "sneaker store"}, headers=headers).get_json()["spec"]
    fake_ai.overrides["page"] = flaky_pages
    body = client.post("/api/projects", json={"spec": spec}, headers=headers).get_json()
    run, pid = body["run"], body["project"]["id"]
    assert run["status"] == "failed" and "1 of 3 pages are built" in run["error"] and "Continue generation" in run["error"]
    project = client.get(f"/api/projects/{pid}", headers=headers).get_json()["project"]
    assert project["status"] == "partial"
    assert [p["sectionCount"] > 0 for p in project["pages"]] == [True, False, False]
    home_before = load_page(client, headers, pid, "/")["tree"]

    ai_capacity.reset()
    fake_ai.overrides.pop("page")
    resumed = client.post(f"/api/projects/{pid}/generate", json={"resume": True}, headers=headers).get_json()["run"]
    assert resumed["status"] == "succeeded", resumed
    assert any("2 to go" in s["message"] for s in resumed["steps"])
    project = client.get(f"/api/projects/{pid}", headers=headers).get_json()["project"]
    assert project["status"] == "ready" and all(p["sectionCount"] > 0 for p in project["pages"])
    page_calls = [c for c in fake_ai.calls if c["kind"] == "page"]
    assert all("(route /)" not in c["user"] for c in page_calls[-2:])  # finished page not regenerated
    assert _json.dumps(load_page(client, headers, pid, "/")["tree"]) == _json.dumps(home_before)


def test_ai_made_duplicate_navbar_and_footer_are_dropped():
    from agents.studio.architect import make_validator
    data = {"nodes": [
        {"id": "n", "parent": None, "type": "section", "name": "Navigation", "tag": "nav"},
        {"id": "l", "parent": "n", "type": "link", "name": "Logo", "props": {"text": "X", "href": "/"}},
        {"id": "h", "parent": None, "type": "section", "name": "Hero"},
        {"id": "t", "parent": "h", "type": "heading", "props": {"text": "Hi"}},
        {"id": "f", "parent": None, "type": "section", "name": "Footer", "tag": "footer"}]}
    tree = make_validator({})(data)["tree"]
    assert [c["name"] for c in tree["children"]] == ["Hero"]
    assert tree["children"][0]["children"][0]["tag"] == "h1"  # heading normalised to the page's h1
