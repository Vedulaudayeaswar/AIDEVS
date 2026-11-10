"""AI client resilience, SSRF protection and full export round-trip (TEST 11 / TEST 4)."""
import io
import os
import subprocess
import sys
import zipfile

import pytest

from services import ai_client as ai
from services.crawler import CrawlError, _ip_allowed, validate_url
from tests.conftest import register
from tests.test_projects import create_generated_project, WISHLIST_PLAN


class ProviderError(Exception):
    def __init__(self, status, retry_after=None):
        super().__init__(f"provider error {status}")
        self.status_code = status
        self.response = type("R", (), {"headers": {"retry-after": retry_after} if retry_after else {},
                                       "status_code": status})()


def make_client(responses):
    calls = []

    def transport(model, messages, **kw):
        calls.append(model)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item, 10, 10
    return ai.AIClient(api_key="", transport=transport), calls


def test_ai_retries_transient_errors(app, monkeypatch):
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    client, calls = make_client([ProviderError(503), ProviderError(500), '{"ok": true}'])
    result = client.complete_json("plan", "sys", "user")
    assert result.data == {"ok": True} and len(calls) == 3


def test_ai_falls_back_to_next_model_on_rate_limit_and_decommission(app, monkeypatch):
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    client, calls = make_client([ProviderError(404), '{"ok": 1}'])
    client.complete_json("plan", "sys", "user")
    assert calls == ai.models_for("plan")[:2]
    client, calls = make_client([ProviderError(429, retry_after="60"), "fine"])
    assert client.complete("plan", "s", "u").text == "fine" and calls[0] != calls[1]


def test_ai_invalid_json_is_repaired_once_then_rejected(app):
    client, calls = make_client(["nope", '{"fixed": true}'])
    assert client.complete_json("plan", "s", "u").data == {"fixed": True}
    client, _ = make_client(["nope", "still nope"])
    with pytest.raises(ai.AIInvalidOutput):
        client.complete_json("plan", "s", "u")


def test_ai_not_configured_and_auth_failure(app):
    with pytest.raises(ai.AINotConfigured):
        ai.AIClient(api_key="").complete("plan", "s", "u")
    client, _ = make_client([ProviderError(401)])
    with pytest.raises(ai.AINotConfigured):
        client.complete("plan", "s", "u")


def test_ai_per_user_quota(app, client, monkeypatch):
    user = register(client)
    monkeypatch.setenv("AI_DAILY_REQUESTS_PER_USER", "2")
    fake, _ = make_client(["a", "b", "c"])
    fake.complete("chat", "s", "u", user_id=user["user"]["id"])
    fake.complete("chat", "s", "u", user_id=user["user"]["id"])
    with pytest.raises(ai.AIQuotaExceeded):
        fake.complete("chat", "s", "u", user_id=user["user"]["id"])


def test_quota_error_maps_to_http_429(app, client, headers, monkeypatch):
    monkeypatch.setenv("AI_DAILY_REQUESTS_PER_USER", "0")
    resp = client.post("/api/projects/plan", json={"prompt": "A bakery website please"}, headers=headers)
    assert resp.status_code == 429 and "limit" in resp.get_json()["error"]


@pytest.mark.parametrize("url", [
    "http://localhost/", "http://127.0.0.1/", "http://[::1]/", "file:///etc/passwd", "gopher://x.com",
    "http://example.com:22/", "http://user:pw@example.com/", "http://intranet.local/", "ftp://example.com",
])
def test_crawler_rejects_dangerous_urls(url):
    with pytest.raises(CrawlError):
        validate_url(url)
        from services.crawler import resolve_public
        resolve_public(validate_url(url)[1], 80)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "172.16.3.4", "192.168.1.1", "169.254.169.254",
                                "100.64.0.1", "0.0.0.0", "::1", "fd00::1", "::ffff:10.0.0.1", "224.0.0.1"])
def test_private_and_metadata_addresses_blocked(ip):
    assert not _ip_allowed(ip)


def test_public_address_allowed():
    assert _ip_allowed("93.184.216.34")


def test_exported_project_installs_and_passes_its_own_tests(client, headers, fake_ai, tmp_path):
    """TEST 11 + TEST 4: download the full app and run its backend test-suite independently."""
    project_id, _ = create_generated_project(client, headers)
    fake_ai.overrides["feature"] = WISHLIST_PLAN
    client.post(f"/api/projects/{project_id}/assistant", json={"message": "Add a wishlist"}, headers=headers)
    resp = client.get(f"/api/projects/{project_id}/export", headers=headers)
    zipfile.ZipFile(io.BytesIO(resp.data)).extractall(tmp_path)
    root = next(p for p in tmp_path.iterdir() if p.is_dir())
    for required in ["README.md", "API.md", "render.yaml", "docker-compose.yml", "backend/app.py",
                     "backend/migrations/0001_initial.postgresql.sql", "backend/.env.example",
                     "frontend/package.json", "frontend/src/App.jsx", "frontend/src/api.js",
                     "aidevs.project.json"]:
        assert (root / required).exists(), required
    env_example = (root / "backend/.env.example").read_text()
    assert "gsk_" not in env_example and "GROQ" not in env_example  # no platform secrets
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:asyncio", "-p", "no:cacheprovider"],
                            cwd=root / "backend", capture_output=True, text=True, timeout=300,
                            env={k: v for k, v in os.environ.items()
                                 if k not in ("JWT_SECRET_KEY", "DATABASE_URL", "GROQ_API_KEY", "CORS_ORIGINS")}
                            | {"PYTHONDONTWRITEBYTECODE": "1"})
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    assert " passed" in result.stdout
