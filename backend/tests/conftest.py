import json
import os
import sys

# Tests drive job execution explicitly; never auto-start the in-process worker.
os.environ["RUN_WORKER_IN_PROCESS"] = "0"
os.environ.setdefault("JOB_POLL_SECONDS", "0.05")
# Generous limits for the general suite; dedicated tests lower them explicitly.
for _name, _value in {"MAX_PROJECTS_PER_USER": "100", "AI_GENERATIONS_PER_DAY": "100",
                      "AI_MODIFICATIONS_PER_DAY": "200", "EXPORTS_PER_DAY": "100", "MAX_CONCURRENT_JOBS_PER_USER": "5",
                      "AI_DAILY_REQUESTS_PER_USER": "1000", "AI_DAILY_TOKENS_PER_USER": "10000000"}.items():
    os.environ.setdefault(_name, _value)

import pytest  # noqa: E402  (env defaults must be set before app imports)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
import db as database  # noqa: E402
from api.common import reset_rate_limits  # noqa: E402
from services import jobs  # noqa: E402
from services.ai_client import AIClient, set_ai_client  # noqa: E402

PASSWORD = "Sneakers#2026"

SPEC = {
    "name": "Stride Lab",
    "summary": "Premium sneaker store with curated drops.",
    "site_type": "ecommerce", "audience": "Sneaker collectors 18-35",
    "brand": {"voice": "Bold and confident", "tagline": "Built to move"},
    "tokens": {"colors": {"primary": "#111827", "secondary": "#f97316", "accent": "#facc15",
                          "background": "#ffffff", "surface": "#f3f4f6", "text": "#111827",
                          "muted": "#4b5563", "onPrimary": "#ffffff"},
               "fonts": {"heading": "Space Grotesk", "body": "Inter"}, "radius": "14px"},
    "pages": [
        {"name": "Home", "route": "/", "purpose": "Showcase brand and featured drops",
         "sections": [{"kind": "hero", "brief": "Bold hero"}, {"kind": "collection_grid", "entity": "product"}]},
        {"name": "Shop", "route": "/shop", "purpose": "Browse all products",
         "sections": [{"kind": "collection_grid", "entity": "product"}]},
        {"name": "Contact", "route": "/contact", "purpose": "Support form",
         "sections": [{"kind": "contact_form"}]},
    ],
    "entities": [{"name": "product", "label": "Products",
                  "fields": [{"name": "title", "type": "string", "required": True},
                             {"name": "price", "type": "number", "required": True},
                             {"name": "image", "type": "image"}, {"name": "description", "type": "text"}],
                  "permissions": {"read": "public", "create": "admin", "update": "admin", "delete": "admin"},
                  "sample_data": [{"title": "Aero Runner", "price": 180,
                                   "image": "https://picsum.photos/seed/shoe/800/600"}]}],
    "features": ["Product catalog", "Contact form"],
    "seo": {"title": "Stride Lab", "description": "Premium sneakers"},
}


def page_response(route):
    hero = {"type": "section", "name": "Hero Section", "props": {"anchor": "hero"},
            "styles": {"base": {"padding": "120px 24px", "background": "var(--color-surface)"},
                       "mobile": {"padding": "64px 16px"}},
            "children": [
                {"type": "heading", "tag": "h1", "name": "Hero Heading", "props": {"text": f"Hero for {route}"},
                 "styles": {"base": {"fontSize": "64px"}, "mobile": {"fontSize": "36px"}}},
                {"type": "button", "name": "Shop CTA", "props": {"text": "Shop now", "href": "/shop"}},
            ]}
    grid = {"type": "section", "name": "Product Grid", "props": {"anchor": "products"}, "children": [
        {"type": "collection", "name": "Products", "props": {"entity": "product", "limit": 6},
         "styles": {"base": {"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)"},
                    "mobile": {"gridTemplateColumns": "1fr"}},
         "children": [{"type": "container", "name": "Card", "children": [
             {"type": "image", "name": "Photo", "props": {"src": "{{image}}", "alt": "{{title}}"}},
             {"type": "heading", "tag": "h3", "name": "Title", "props": {"text": "{{title}}"}},
             {"type": "text", "name": "Price", "props": {"text": "${{price}}"}}]}]}]}
    form = {"type": "section", "name": "Contact", "props": {"anchor": "contact"}, "children": [
        {"type": "heading", "tag": "h1", "name": "Contact heading", "props": {"text": "Talk to us"}},
        {"type": "form", "name": "Contact Form", "props": {"entity": "contact_message"}, "children": [
            {"type": "input", "name": "Name", "props": {"label": "Name", "name": "name", "required": True}},
            {"type": "input", "name": "Email", "props": {"label": "Email", "name": "email", "inputType": "email",
                                                          "required": True}},
            {"type": "textarea", "name": "Message", "props": {"label": "Message", "name": "message",
                                                               "required": True}},
            {"type": "button", "name": "Send", "props": {"text": "Send"}}]}]}
    sections = {"/": [hero, grid], "/shop": [hero, grid], "/contact": [form]}.get(route, [hero])
    return {"sections": sections, "seo": {"title": f"Page {route}", "description": "desc"}}


class FakeAI:
    """Deterministic stand-in for Groq. Records every call."""

    def __init__(self):
        self.calls = []
        self.overrides = {}

    def __call__(self, model, messages, **kwargs):
        system, user = messages[0]["content"], messages[1]["content"]
        kind = ("plan" if "Requirement Analysis Agent" in system else
                "page" if "UI/UX Architect" in system else
                "feature" if "Orchestrator working with" in system else
                "edit" if "Visual Editing Agent" in system else "chat")
        self.calls.append({"kind": kind, "model": model, "user": user})
        if kind in self.overrides:
            value = self.overrides[kind]
            value = value(user) if callable(value) else value
            if isinstance(value, Exception):
                raise value
            return (value if isinstance(value, str) else json.dumps(value)), 100, 200
        if kind == "plan":
            return json.dumps(SPEC), 500, 800
        if kind == "page":
            route = user.split("(route ")[1].split(")")[0]
            return json.dumps(page_response(route)), 900, 1500
        if kind == "feature":
            return json.dumps({"reply": "Nothing to change.", "entities": [], "pages": [], "nav": []}), 100, 50
        return "Hello from the classic builder", 10, 10


@pytest.fixture
def fake_ai():
    from services import ai_capacity
    ai_capacity.reset()
    fake = FakeAI()
    set_ai_client(AIClient(api_key="", transport=fake))
    yield fake
    set_ai_client(None)


@pytest.fixture
def app(fake_ai):
    jobs.SYNC_MODE = True
    reset_rate_limits()
    application = create_app(TestConfig)
    yield application
    # Close every session first: PostgreSQL blocks DROP TABLE behind idle transactions.
    from sqlalchemy.orm import close_all_sessions
    database.SessionLocal.remove()
    close_all_sessions()
    database.Base.metadata.drop_all(database.engine)


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, first="Ada", last="Lovelace", email=None, password=PASSWORD):
    email = email or f"{first.lower()}@example.com"
    resp = client.post("/api/auth/register", json={"firstName": first, "lastName": last, "email": email,
                                                   "password": password})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def auth(tokens):
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


@pytest.fixture
def user(client):
    return register(client)


@pytest.fixture
def headers(user):
    return auth(user)


@pytest.fixture(scope="session", autouse=True)
def _clean_postgres_schema():
    """When running against PostgreSQL (CI), start from an empty schema."""
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        engine.dispose()
    yield
