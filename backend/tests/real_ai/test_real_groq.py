"""REAL Groq acceptance tests (no fakes). Skipped unless explicitly enabled:

    GROQ_API_KEY=... RUN_REAL_AI=1 python -m pytest tests/real_ai -v -s
    # also build every exported React app (slow, needs npm):  RUN_REAL_AI_BUILD=1

They validate the generated *outputs*: specification, component trees, API
contracts (checks must reach zero errors after the repair loop), and the
exported backend's own pytest suite. Each test uses ~5-15 real requests.
Test G (rate limits, invalid output, timeouts, unavailable models) is covered
deterministically in tests/test_services.py and tests/test_jobs.py by simulating
provider errors; it does not need the live API.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("GROQ_API_KEY") and os.getenv("RUN_REAL_AI") == "1"),
    reason="Real Groq validation disabled (set GROQ_API_KEY and RUN_REAL_AI=1)")


@pytest.fixture(scope="module")
def real_app():
    from app import create_app
    from config import TestConfig
    from services import jobs
    from services.ai_client import AIClient, set_ai_client
    set_ai_client(AIClient(api_key=os.environ["GROQ_API_KEY"]))  # the real platform client
    jobs.SYNC_MODE = True
    app = create_app(TestConfig)
    yield app
    set_ai_client(None)


@pytest.fixture(scope="module")
def client(real_app):
    return real_app.test_client()


@pytest.fixture(scope="module")
def headers(client):
    from tests.conftest import auth, register
    return auth(register(client, "Real", "Tester", "real-ai@example.com"))


def generate(client, headers, prompt):
    plan = client.post("/api/projects/plan", json={"prompt": prompt}, headers=headers)
    assert plan.status_code == 200, plan.get_json()
    spec = plan.get_json()["spec"]
    created = client.post("/api/projects", json={"spec": spec, "prompt": prompt}, headers=headers).get_json()
    run = created["run"]
    assert run["status"] == "succeeded", run
    project = client.get(f"/api/projects/{created['project']['id']}?trees=1", headers=headers).get_json()["project"]
    print(f"\n[{spec['name']}] pages={[p['route'] for p in project['pages']]} "
          f"entities={[e['name'] for e in project['entities']]} result={json.dumps(run['result'])[:400]}")
    return spec, project, run


def assert_valid_project(client, headers, project, run, min_pages=2):
    from services.schema import walk
    assert len(project["pages"]) >= min_pages
    for page in project["pages"]:
        own = [c for c in page["tree"]["children"] if not c.get("shared")]
        assert own, f"page {page['route']} has no sections"
        assert sum(1 for n, _ in walk(page["tree"]) if n.get("tag") == "h1") >= 1, page["route"]
    report = client.post(f"/api/projects/{project['id']}/checks", headers=headers).get_json()["report"]
    errors = [i for i in report["issues"] if i["severity"] == "error"]
    assert not errors, errors
    assert run["result"].get("fallbackPages", 0) <= len(project["pages"]) // 2, "most pages fell back to templates"


def assert_export_runs(client, headers, project, tmp_path_factory):
    data = client.get(f"/api/projects/{project['id']}/export", headers=headers).data
    out = tmp_path_factory.mktemp("export")
    zipfile.ZipFile(io.BytesIO(data)).extractall(out)
    root = next(p for p in out.iterdir() if p.is_dir())
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:asyncio", "-p", "no:cacheprovider"],
                            cwd=root / "backend", capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stdout[-3000:]
    if os.getenv("RUN_REAL_AI_BUILD") == "1" and shutil.which("npm"):
        npm = shutil.which("npm")
        assert subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=root / "frontend",
                              capture_output=True, timeout=900).returncode == 0
        build = subprocess.run([npm, "run", "build"], cwd=root / "frontend", capture_output=True, text=True,
                               timeout=600)
        assert build.returncode == 0, build.stdout[-2000:] + build.stderr[-2000:]
    return root


STATE = {}


def test_A_portfolio(client, headers, tmp_path_factory):
    spec, project, run = generate(client, headers, "A responsive portfolio for a freelance product designer with "
                                  "case studies, an about page and a contact form.")
    assert_valid_project(client, headers, project, run, min_pages=2)
    assert any(e["name"] == "contact_message" for e in project["entities"])
    assert_export_runs(client, headers, project, tmp_path_factory)


def test_B_saas_project_management(client, headers, tmp_path_factory):
    spec, project, run = generate(client, headers, "A project management SaaS where users sign up, log in, see a "
                                  "dashboard and create, update and delete their own tasks and projects.")
    assert_valid_project(client, headers, project, run)
    per_user = [e for e in project["entities"] if e["permissions"]["read"] in ("owner", "auth")]
    assert per_user, f"expected user-scoped data models, got {project['entities']}"
    assert all(e["permissions"]["delete"] != "public" for e in project["entities"])
    assert_export_runs(client, headers, project, tmp_path_factory)


def test_C_ecommerce(client, headers, tmp_path_factory):
    spec, project, run = generate(client, headers, "A sneaker store with a product catalog, product details, a "
                                  "shopping cart, a wishlist, user accounts and admin product management.")
    assert_valid_project(client, headers, project, run)
    names = {e["name"] for e in project["entities"]}
    assert any("product" in n for n in names), names
    product = next(e for e in project["entities"] if "product" in e["name"])
    assert product["permissions"]["create"] == "admin" and product["permissions"]["read"] == "public"
    STATE["shop"] = project
    assert_export_runs(client, headers, project, tmp_path_factory)


def _feature(client, headers, project_id, message):
    resp = client.post(f"/api/projects/{project_id}/assistant", json={"message": message}, headers=headers)
    assert resp.status_code == 202, resp.get_json()
    run = client.get(f"/api/runs/{resp.get_json()['run']['id']}", headers=headers).get_json()["run"]
    assert run["status"] == "succeeded", run
    return run, client.get(f"/api/projects/{project_id}?trees=1", headers=headers).get_json()["project"]


def test_D_add_wishlist_to_existing_project(client, headers):
    project = STATE.get("shop") or generate(client, headers, "A small online bookstore with a catalog.")[1]
    own = lambda tree: [c for c in tree["children"] if not c.get("shared")]  # noqa: E731 (navbar may gain a link)
    before = {p["route"]: own(p["tree"]) for p in project["pages"]}
    run, after = _feature(client, headers, project["id"], "Add a wishlist so signed-in users can save products.")
    wish = [e for e in after["entities"] if "wish" in e["name"]]
    assert wish and wish[0]["permissions"]["read"] in ("owner", "auth"), after["entities"]
    unchanged = [r for r, t in before.items() if any(p["route"] == r and own(p["tree"]) == t for p in after["pages"])]
    assert unchanged, "every existing page was rewritten for a small feature"
    report = client.post(f"/api/projects/{after['id']}/checks", headers=headers).get_json()["report"]
    assert report["summary"]["error"] == 0, report["issues"]


def test_E_visual_modification_of_hero(client, headers):
    project = STATE.get("shop") or generate(client, headers, "A coffee shop landing page.")[1]
    home = project["pages"][0]
    hero = next(c for c in home["tree"]["children"] if not c.get("shared"))
    others = {p["route"]: [c for c in p["tree"]["children"] if not c.get("shared")] for p in project["pages"][1:]}
    resp = client.post(f"/api/projects/{project['id']}/assistant", headers=headers, json={
        "message": "Redesign this section: bolder headline, split layout with an image on the right.",
        "selection": {"pageId": home["id"], "nodeId": hero["id"], "node": hero}})
    body = resp.get_json()
    assert resp.status_code == 200 and body["mode"] == "edit", body
    assert body["node"]["id"] == hero["id"] and body["node"]["type"] == hero["type"]
    assert body["node"] != hero
    after = client.get(f"/api/projects/{project['id']}?trees=1", headers=headers).get_json()["project"]
    assert {p["route"]: [c for c in p["tree"]["children"] if not c.get("shared")]
            for p in after["pages"][1:]} == others  # edit is applied client-side only


def test_F_notification_system(client, headers):
    project = STATE.get("shop") or generate(client, headers, "A community events site with user accounts.")[1]
    run, after = _feature(client, headers, project["id"],
                          "Add a notification system: notifications stored in the database, each user only sees "
                          "and can mark read their own notifications.")
    notes = [e for e in after["entities"] if "notif" in e["name"]]
    assert notes, after["entities"]
    perms = notes[0]["permissions"]
    assert perms["read"] == "owner" and perms["update"] in ("owner", "admin") and perms["delete"] != "public"
    assert any(f["type"] == "boolean" for f in notes[0]["fields"]) or any("read" in f["name"] for f in notes[0]["fields"])
