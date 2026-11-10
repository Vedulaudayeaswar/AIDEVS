"""Multi-user reliability under real concurrency (file-backed SQLite, parallel threads)."""
import copy
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

import db as database
from api.common import reset_rate_limits
from app import create_app
from config import TestConfig
from services import jobs
from tests.conftest import auth, register


@pytest.fixture
def file_app(tmp_path, fake_ai):
    url = "sqlite:///" + os.path.join(tmp_path, "concurrency.db").replace("\\", "/")

    class FileConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = url

    jobs.SYNC_MODE = True
    reset_rate_limits()
    application = create_app(FileConfig)
    yield application
    database.SessionLocal.remove()
    database.engine.dispose()


def _parallel(fn, n):
    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(fn, range(n)))


def test_concurrent_saves_of_one_page_never_both_win(file_app):
    client = file_app.test_client()
    headers = auth(register(client))
    project = client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
    page_url = f"/api/projects/{project['id']}/pages/{project['pages'][0]['id']}"
    page = client.get(page_url, headers=headers).get_json()["page"]

    def save(i):
        tree = copy.deepcopy(page["tree"])
        tree["children"][1]["name"] = f"Edited by tab {i}"
        return file_app.test_client().put(page_url, json={"tree": tree, "baseRevision": page["revision"]},
                                          headers=headers).status_code

    codes = _parallel(save, 8)
    assert codes.count(200) == 1, codes
    assert codes.count(409) == 7, codes
    final = client.get(page_url, headers=headers).get_json()["page"]
    assert final["revision"] == page["revision"] + 1


def test_concurrent_version_creation_gets_unique_numbers(file_app):
    client = file_app.test_client()
    headers = auth(register(client))
    project = client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
    url = f"/api/projects/{project['id']}/versions"

    codes = _parallel(lambda i: file_app.test_client().post(url, json={"label": f"v{i}"}, headers=headers).status_code, 8)
    assert codes.count(201) == 8, codes
    numbers = [v["number"] for v in client.get(url, headers=headers).get_json()["versions"]]
    assert len(numbers) == len(set(numbers)) == 9  # 8 + "Project created"


def test_many_users_generate_projects_simultaneously_without_crosstalk(file_app):
    users = []
    for i in range(5):
        tokens = register(file_app.test_client(), f"User{chr(65 + i)}", "Tester", f"user{i}@example.com")
        users.append(auth(tokens))

    def generate(i):
        c = file_app.test_client()
        spec = c.post("/api/projects/plan", json={"prompt": f"Shop number {i} for sneakers"},
                      headers=users[i]).get_json()["spec"]
        spec["name"] = f"Shop {i}"
        body = c.post("/api/projects", json={"spec": spec}, headers=users[i]).get_json()
        return body["project"]["id"], body["run"]["status"]

    results = _parallel(generate, 5)
    assert all(status == "succeeded" for _pid, status in results), results
    client = file_app.test_client()
    for i, headers in enumerate(users):
        listed = client.get("/api/projects", headers=headers).get_json()["projects"]
        assert [p["name"] for p in listed] == [f"Shop {i}"]  # each user sees exactly their own project
        assert listed[0]["id"] == results[i][0]
        for j, (other_pid, _s) in enumerate(results):
            if j != i:
                assert client.get(f"/api/projects/{other_pid}", headers=headers).status_code == 404


def test_parallel_assistant_requests_take_one_project_lock(file_app, fake_ai):
    client = file_app.test_client()
    headers = auth(register(client))
    project = client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
    jobs.SYNC_MODE = False  # queue only, so locks stay held while we race
    try:
        codes = _parallel(lambda i: file_app.test_client().post(
            f"/api/projects/{project['id']}/assistant", json={"message": f"change {i}"}, headers=headers).status_code, 6)
    finally:
        jobs.SYNC_MODE = True
    assert codes.count(202) == 1, codes
    assert all(code in (409, 429) for code in codes if code != 202), codes
