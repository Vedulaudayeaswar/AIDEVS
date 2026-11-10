"""Backup -> delete -> restore round trip using the real manage.py commands (file-backed SQLite)."""
import json
import os

import db as database
from app import create_app
from config import TestConfig
from tests.conftest import auth, register


def test_backup_and_restore_round_trip(tmp_path, fake_ai, monkeypatch, capsys):
    url = "sqlite:///" + os.path.join(tmp_path, "backup.db").replace("\\", "/")

    class FileConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = url

    client = create_app(FileConfig).test_client()
    headers = auth(register(client))
    project = client.post("/api/projects", json={"blank": True, "name": "Precious"}, headers=headers).get_json()["project"]
    before = client.get(f"/api/projects/{project['id']}?trees=1", headers=headers).get_json()["project"]

    import manage
    monkeypatch.setattr(manage.Config, "SQLALCHEMY_DATABASE_URI", url)
    backup_file = os.path.join(tmp_path, "backup.json")
    manage.backup(backup_file)
    assert json.load(open(backup_file, encoding="utf-8"))["projects"][0]["name"] == "Precious"

    assert client.delete(f"/api/projects/{project['id']}", headers=headers).status_code == 200  # disaster
    restored, skipped = manage.restore(backup_file)
    assert restored == 1 and skipped == []
    after = client.get(f"/api/projects/{project['id']}?trees=1", headers=headers).get_json()["project"]
    assert [p["route"] for p in after["pages"]] == [p["route"] for p in before["pages"]]
    assert after["pages"][0]["tree"] == before["pages"][0]["tree"]
    assert {e["name"] for e in after["entities"]} == {e["name"] for e in before["entities"]}
    assert manage.restore(backup_file) == (0, [f"{project['id']} (already exists)"])  # idempotent, never overwrites
    database.SessionLocal.remove()
    database.engine.dispose()
