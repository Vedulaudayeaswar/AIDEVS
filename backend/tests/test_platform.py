"""SaaS hardening: limits, admin, account lifecycle, security controls, repair loop, rate-limit backends."""
import copy
import io
import json
import logging

import pytest

from services import limits, ratelimit
from services.logging_setup import redact
from services.schema import walk
from tests.conftest import PASSWORD, auth, register
from tests.test_projects import by_name, create_generated_project, load_page, save


# ------------------------------------------------------------------ limits
def test_project_limit_is_enforced_with_clear_message(client, headers, monkeypatch):
    monkeypatch.setenv("MAX_PROJECTS_PER_USER", "2")
    for _ in range(2):
        assert client.post("/api/projects", json={"blank": True}, headers=headers).status_code == 201
    resp = client.post("/api/projects", json={"blank": True}, headers=headers)
    assert resp.status_code == 429 and "limit of 2 projects" in resp.get_json()["error"]


def test_storage_and_export_limits(client, headers, monkeypatch):
    from PIL import Image
    monkeypatch.setenv("MAX_STORAGE_MB_PER_USER", "0")
    project = client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
    buf = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buf, "PNG")
    up = client.post(f"/api/projects/{project['id']}/assets", headers=headers,
                     data={"file": (io.BytesIO(buf.getvalue()), "a.png")}, content_type="multipart/form-data")
    assert up.status_code == 413 and "storage limit" in up.get_json()["error"]
    monkeypatch.setenv("EXPORTS_PER_DAY", "1")
    assert client.get(f"/api/projects/{project['id']}/export", headers=headers).status_code == 200
    second = client.get(f"/api/projects/{project['id']}/export", headers=headers)
    assert second.status_code == 429 and "exports for today" in second.get_json()["error"]


def test_usage_endpoint_reports_limits(client, headers):
    body = client.get("/api/usage", headers=headers).get_json()
    for key in ("requestLimit", "tokenLimit", "jobLimit", "projectLimit", "storageLimitBytes", "activeJobs"):
        assert key in body


def test_registration_can_be_closed(client, monkeypatch):
    monkeypatch.setenv("REGISTRATION_OPEN", "0")
    resp = client.post("/api/auth/register", json={"firstName": "New", "lastName": "User",
                                                   "email": "new@example.com", "password": PASSWORD})
    assert resp.status_code == 403


# ------------------------------------------------------------------- admin
@pytest.fixture
def admin(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
    return auth(register(client, "Boss", "Admin", "boss@example.com"))


def test_admin_api_hidden_from_regular_users(client, headers):
    for path in ("/api/admin/overview", "/api/admin/users", "/api/admin/settings", "/api/admin/models"):
        assert client.get(path, headers=headers).status_code == 404
    assert client.get("/api/admin/overview").status_code == 401


def test_admin_overview_settings_and_user_disable(client, admin, headers):
    overview = client.get("/api/admin/overview", headers=admin).get_json()
    assert overview["users"] == 2 and "queue" in overview and "rateLimitBackend" in overview
    resp = client.put("/api/admin/settings", json={"max_projects_per_user": 1}, headers=admin)
    assert resp.status_code == 200
    assert next(s for s in resp.get_json()["settings"] if s["key"] == "max_projects_per_user")["value"] == 1
    assert client.post("/api/projects", json={"blank": True}, headers=headers).status_code == 201
    assert client.post("/api/projects", json={"blank": True}, headers=headers).status_code == 429
    assert client.put("/api/admin/settings", json={"nope": 1}, headers=admin).status_code == 400
    assert client.put("/api/admin/settings", json={"registration_open": "yes"}, headers=admin).status_code == 400

    users = client.get("/api/admin/users", headers=admin).get_json()["users"]
    victim = next(u for u in users if u["email"] == "ada@example.com")
    assert client.patch(f"/api/admin/users/{victim['id']}", json={"isActive": False}, headers=admin).status_code == 200
    assert client.get("/api/projects", headers=headers).status_code == 401  # access token no longer accepted
    login = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": PASSWORD})
    assert login.status_code == 401
    limits.invalidate()


def test_admin_models_registry(client, admin):
    body = client.get("/api/admin/models", headers=admin).get_json()
    tasks = {t["task"]: t for t in body["tasks"]}
    assert {"requirements", "frontend", "code_modification", "visual_edit", "error_analysis", "backend",
            "testing"} <= set(tasks)
    assert tasks["backend"]["deterministic"] and tasks["frontend"]["configured"][0] == "openai/gpt-oss-120b"


# ----------------------------------------------------------------- account
def test_change_password_revokes_other_sessions(client):
    first = register(client)
    other_device = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": PASSWORD}).get_json()
    bad = client.post("/api/auth/change-password", json={"currentPassword": "wrong", "newPassword": "New#Pass2027"},
                      headers=auth(first))
    assert bad.status_code == 400
    ok = client.post("/api/auth/change-password", json={"currentPassword": PASSWORD, "newPassword": "New#Pass2027"},
                     headers=auth(first))
    assert ok.status_code == 200 and ok.get_json()["refreshToken"]
    assert client.post("/api/auth/refresh", json={"refreshToken": other_device["refreshToken"]}).status_code == 401
    assert client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"identifier": "ada@example.com",
                                                "password": "New#Pass2027"}).status_code == 200


def test_data_export_and_account_deletion_only_affect_that_user(client):
    ada = auth(register(client))
    bob = auth(register(client, "Bob", "Jones", "bob@example.com"))
    ada_project = client.post("/api/projects", json={"blank": True, "name": "Ada site"}, headers=ada).get_json()["project"]
    bob_project = client.post("/api/projects", json={"blank": True, "name": "Bob site"}, headers=bob).get_json()["project"]
    export = client.get("/api/auth/export", headers=ada)
    data = json.loads(export.data)
    assert data["account"]["email"] == "ada@example.com"
    assert [p["name"] for p in data["projects"]] == ["Ada site"] and "password_hash" not in export.data.decode()
    assert client.delete("/api/auth/account", json={"password": PASSWORD, "confirm": "nope"},
                         headers=ada).status_code == 400
    assert client.delete("/api/auth/account", json={"password": "bad", "confirm": "DELETE"},
                         headers=ada).status_code == 400
    assert client.delete("/api/auth/account", json={"password": PASSWORD, "confirm": "DELETE"},
                         headers=ada).status_code == 200
    assert client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": PASSWORD}).status_code == 401
    assert client.get(f"/api/projects/{bob_project['id']}", headers=bob).status_code == 200
    assert client.get(f"/api/projects/{ada_project['id']}", headers=bob).status_code == 404
    again = register(client, "Ada", "Lovelace", "ada@example.com")  # email is free again
    assert client.get("/api/projects", headers=auth(again)).get_json()["projects"] == []


# --------------------------------------------------------------- security
def test_spoofed_forwarded_for_cannot_bypass_login_rate_limit(app, client):
    app.config["RATE_LIMIT_IN_TESTS"] = True
    from api.common import reset_rate_limits
    reset_rate_limits()
    codes = [client.post("/api/auth/login", json={"identifier": "x@example.com", "password": "nope"},
                         headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code for i in range(12)]
    assert codes[-1] == 429, codes


def test_security_headers_request_id_and_cors(client):
    resp = client.get("/api/health/live", headers={"X-Request-ID": "abcdef123456"})
    assert resp.headers["X-Request-ID"] == "abcdef123456"
    assert resp.headers["X-Content-Type-Options"] == "nosniff" and resp.headers["X-Frame-Options"] == "DENY"
    evil = client.options("/api/projects", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "Access-Control-Allow-Origin" not in evil.headers
    good = client.options("/api/projects", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert good.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_health_endpoints(client):
    assert client.get("/api/health/live").status_code == 200
    ready = client.get("/api/health/ready")
    assert ready.status_code == 200 and ready.get_json()["database"] is True
    assert client.get("/api/health").get_json()["database"] is True


def test_secrets_are_redacted_from_logs(caplog):
    text = ('key gsk_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 Authorization: Bearer abc.def.ghi '
            '{"password": "hunter2", "refreshToken": "zzz"} token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijkl')
    out = redact(text)
    for secret in ("gsk_ABCDEFGHIJ", "hunter2", "abc.def.ghi", '"zzz"', "eyJhbGciOiJIUzI1NiJ9"):
        assert secret not in out, out


def test_asset_ids_and_paths_cannot_traverse(client):
    for bad in ("../../etc/passwd", "..%2F..%2Fapp.py", "0" * 31, "Z" * 32):
        assert client.get(f"/api/assets/{bad}").status_code == 404


def test_platform_secret_never_returned(client, headers, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_supersecretvalue1234567890")
    project_id, _ = create_generated_project(client, headers)
    for path in ("/api/health", "/api/usage", f"/api/projects/{project_id}", f"/api/projects/{project_id}/export/files"):
        assert "gsk_supersecret" not in client.get(path, headers=headers).get_data(as_text=True)


# ------------------------------------------------------------------ repair
def test_repair_fixes_missing_required_field_deterministically(client, headers, fake_ai):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id, "/contact")
    tree = copy.deepcopy(page["tree"])
    form = next(n for n, _ in walk(tree) if n["type"] == "form")
    form["children"] = [c for c in form["children"] if c["props"].get("name") != "email"]
    by_name(tree, "Shop CTA") if any(n.get("name") == "Shop CTA" for n, _ in walk(tree)) else None
    save(client, headers, project_id, page, tree)
    run = client.post(f"/api/projects/{project_id}/repair", headers=headers).get_json()["run"]
    assert run["status"] == "succeeded", run
    assert run["result"]["errorsBefore"] >= 1 and run["result"]["errorsAfter"] == 0
    assert run["result"]["aiAttempts"] == 0  # no model call needed
    fixed = load_page(client, headers, project_id, "/contact")["tree"]
    form = next(n for n, _ in walk(fixed) if n["type"] == "form")
    names = [c["props"].get("name") for c in form["children"]]
    assert "email" in names and names.index("email") < len(names) - 1  # inserted before the submit button
    labels = [v["label"] for v in client.get(f"/api/projects/{project_id}/versions", headers=headers).get_json()["versions"]]
    assert "Before automatic repair" in labels


def test_ai_repair_kept_only_when_it_reduces_errors(client, headers, fake_ai):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id, "/")
    tree = copy.deepcopy(page["tree"])
    grid = by_name(tree, "Products")
    grid["props"]["entity"] = "ghost_model"  # unfixable deterministically
    save(client, headers, project_id, page, tree)
    # 1) the model returns something that does not help -> rolled back
    fake_ai.overrides["edit"] = lambda user: {"node": json.loads(user.split("SELECTED ELEMENT:\n")[1].split("\n\nINSTRUCTION")[0]),
                                              "summary": "noop"}
    run = client.post(f"/api/projects/{project_id}/repair", headers=headers).get_json()["run"]
    assert run["result"]["errorsAfter"] == run["result"]["errorsBefore"]
    print("ROLLED BACK:", run["result"]["rolledBack"])
    # Either the proposal was rejected by validation, or it was applied, re-checked and rolled back.
    assert run["result"]["rolledBack"] and all(
        ("did not reduce" in r) or ("invalid result" in r) for r in run["result"]["rolledBack"])

    # 2) the model returns a correct fix -> kept
    def good_fix(user):
        node = json.loads(user.split("SELECTED ELEMENT:\n")[1].split("\n\nINSTRUCTION")[0])
        for n, _ in walk(node):
            if n["type"] == "collection":
                n["props"]["entity"] = "product"
        return {"node": node, "summary": "Bound the grid to Products"}
    fake_ai.overrides["edit"] = good_fix
    run = client.post(f"/api/projects/{project_id}/repair", headers=headers).get_json()["run"]
    assert run["result"]["errorsAfter"] < run["result"]["errorsBefore"]
    assert by_name(load_page(client, headers, project_id, "/")["tree"], "Products")["props"]["entity"] == "product"


# ---------------------------------------------------------- rate limiting
class FakeRedis:
    def __init__(self, fail=False):
        self.data, self.fail = {}, fail

    def pipeline(self):
        parent = self

        class Pipe:
            def __init__(self):
                self.ops = []

            def incr(self, key):
                self.ops.append(("incr", key))

            def expire(self, key, ttl):
                self.ops.append(("expire", key))

            def execute(self):
                if parent.fail:
                    raise ConnectionError("redis down")
                out = []
                for op, key in self.ops:
                    if op == "incr":
                        parent.data[key] = parent.data.get(key, 0) + 1
                        out.append(parent.data[key])
                    else:
                        out.append(True)
                return out
        return Pipe()


def test_redis_rate_limiter_shared_counter_and_fail_open(caplog):
    limiter = ratelimit.RedisLimiter(FakeRedis())
    results = [limiter.hit("login:1.2.3.4", 3, 60)[0] for _ in range(5)]
    assert results == [True, True, True, False, False]
    broken = ratelimit.RedisLimiter(FakeRedis(fail=True))
    with caplog.at_level(logging.WARNING):
        assert broken.hit("login:x", 1, 60)[0] is True
    assert "allowing request" in caplog.text


def test_ai_repair_that_does_not_help_is_rolled_back(client, headers, fake_ai):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id, "/")
    tree = copy.deepcopy(page["tree"])
    cta = by_name(tree, "Shop CTA")
    cta["props"]["text"] = ""  # accessibility error: button without text (no deterministic fix)
    save(client, headers, project_id, page, tree)
    hero_before = by_name(load_page(client, headers, project_id, "/")["tree"], "Hero Section")

    def unhelpful(user):
        node = json.loads(user.split("SELECTED ELEMENT:\n")[1].split("\n\nINSTRUCTION")[0])
        for n, _ in walk(node):
            if n["type"] == "heading":
                n["props"]["text"] = "Changed but still broken"
        return {"node": node, "summary": "tweaked heading"}
    fake_ai.overrides["edit"] = unhelpful
    run = client.post(f"/api/projects/{project_id}/repair", headers=headers).get_json()["run"]
    assert run["result"]["aiAttempts"] >= 1
    assert all("did not reduce" in r for r in run["result"]["rolledBack"]), run["result"]
    hero_after = by_name(load_page(client, headers, project_id, "/")["tree"], "Hero Section")
    assert hero_after == hero_before  # the unhelpful edit was reverted exactly


def test_web_fonts_never_block_rendering(client, headers):
    """Regression: a slow/unreachable font CDN blanked the canvas (render-blocking <link>)."""
    project = client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
    html = client.post(f"/api/projects/{project['id']}/preview", json={"pageId": project["pages"][0]["id"]},
                       headers=headers).get_json()["html"]
    assert '<link rel="stylesheet"' not in html  # fonts are injected from script instead
    assert "fonts.googleapis.com" in html.split("</body>")[0].rsplit("<script", 1)[1]
    files = {}
    import io
    import zipfile
    zf = zipfile.ZipFile(io.BytesIO(client.get(f"/api/projects/{project['id']}/export", headers=headers).data))
    for name in zf.namelist():
        if name.endswith("frontend/index.html"):
            files["index"] = zf.read(name).decode()
    assert 'media="print" onload="this.media=\'all\'"' in files["index"]
