"""Acceptance TEST 1: registration, login, logout, refresh/restore, persistence."""
import os

from sqlalchemy import select

import db as database
from api.common import reset_rate_limits
from app import create_app
from config import TestConfig
from models import User
from tests.conftest import PASSWORD, auth, register


def test_register_returns_session_and_me_works(client):
    tokens = register(client)
    assert tokens["accessToken"] and tokens["refreshToken"]
    me = client.get("/api/auth/me", headers=auth(tokens))
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "ada@example.com"
    assert me.get_json()["user"]["username"] == "ada.lovelace"


def test_password_is_hashed_with_bcrypt(client, app):
    register(client)
    user = database.get_session().scalar(select(User))
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$2")


def test_duplicate_email_rejected(client):
    register(client)
    resp = client.post("/api/auth/register", json={"firstName": "Ada", "lastName": "Byron",
                                                   "email": "ADA@example.com", "password": PASSWORD})
    assert resp.status_code == 409
    assert "already exists" in resp.get_json()["error"]


def test_same_name_gets_unique_username(client):
    register(client, email="a1@example.com")
    second = register(client, email="a2@example.com")
    assert second["user"]["username"] == "ada.lovelace2"


def test_weak_password_and_bad_email_rejected(client):
    resp = client.post("/api/auth/register", json={"firstName": "Bob", "lastName": "Stone",
                                                   "email": "bob@example.com", "password": "short"})
    assert resp.status_code == 400
    assert "password" in resp.get_json()["fields"]
    resp = client.post("/api/auth/register", json={"firstName": "Bob", "lastName": "Stone",
                                                   "email": "not-an-email", "password": PASSWORD})
    assert resp.status_code == 400


def test_login_with_email_or_username_and_wrong_password(client):
    register(client)
    assert client.post("/api/auth/login", json={"identifier": "ada@example.com",
                                                "password": PASSWORD}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "ada.lovelace",
                                                "password": PASSWORD}).status_code == 200
    bad = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": "Wrong#1234"})
    assert bad.status_code == 401
    unknown = client.post("/api/auth/login", json={"identifier": "ghost@example.com", "password": PASSWORD})
    assert unknown.status_code == 401
    assert bad.get_json()["error"] == unknown.get_json()["error"]  # no user enumeration


def test_protected_route_requires_token(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_rotates_and_detects_reuse(client):
    tokens = register(client)
    first = client.post("/api/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert first.status_code == 200
    rotated = first.get_json()
    assert rotated["refreshToken"] != tokens["refreshToken"]
    assert client.get("/api/auth/me", headers=auth(rotated)).status_code == 200
    # Re-using the old token = theft signal: whole family is revoked.
    reuse = client.post("/api/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert reuse.status_code == 401
    assert client.post("/api/auth/refresh", json={"refreshToken": rotated["refreshToken"]}).status_code == 401


def test_logout_revokes_access_and_refresh(client):
    tokens = register(client)
    out = client.post("/api/auth/logout", json={"refreshToken": tokens["refreshToken"]}, headers=auth(tokens))
    assert out.status_code == 200
    me = client.get("/api/auth/me", headers=auth(tokens))
    assert me.status_code == 401 and me.get_json()["code"] == "token_revoked"
    assert client.post("/api/auth/refresh", json={"refreshToken": tokens["refreshToken"]}).status_code == 401
    again = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": PASSWORD})
    assert again.status_code == 200


def test_users_persist_across_server_restart(tmp_path, fake_ai):
    """The original bug: accounts vanished on restart (in-memory ChromaDB)."""
    url = "sqlite:///" + os.path.join(tmp_path, "persist.db").replace("\\", "/")

    class FileConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = url

    first = create_app(FileConfig)
    tokens = register(first.test_client())
    database.SessionLocal.remove()
    database.engine.dispose()

    second = create_app(FileConfig)  # brand new process-equivalent
    client = second.test_client()
    login = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": PASSWORD})
    assert login.status_code == 200
    # Session restore after "reopening the browser": refresh token still valid.
    assert client.post("/api/auth/refresh", json={"refreshToken": tokens["refreshToken"]}).status_code == 200
    database.SessionLocal.remove()
    database.engine.dispose()


def test_login_rate_limited(app, client):
    app.config["RATE_LIMIT_IN_TESTS"] = True
    reset_rate_limits()
    codes = [client.post("/api/auth/login", json={"identifier": "x@example.com", "password": "nope"}).status_code
             for _ in range(12)]
    assert codes[:10] == [401] * 10
    assert codes[-1] == 429
