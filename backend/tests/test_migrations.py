"""Migrations upgrade an existing database with data in place (no data loss) and are reversible.

Runs against SQLite by default; CI also runs it against PostgreSQL by setting
TEST_DATABASE_URL (see .github/workflows/ci.yml).
"""
import json
import os

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, text

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cfg(url):
    cfg = AlembicConfig(os.path.join(HERE, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(HERE, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


@pytest.fixture
def db_url(tmp_path):
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
        with engine.begin() as conn:  # clean slate in the throwaway CI database
            conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        engine.dispose()
        return url
    return "sqlite:///" + os.path.join(tmp_path, "migrate.db").replace("\\", "/")


def test_upgrade_existing_data_then_downgrade_and_reupgrade(db_url):
    cfg = _cfg(db_url)
    command.upgrade(cfg, "0001")
    engine = create_engine(db_url)
    tree = json.dumps({"id": "p1", "type": "page", "children": []})
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO users (id, email, username, first_name, middle_name, last_name, password_hash,
                             role, is_active, created_at) VALUES ('u1', 'old@example.com', 'old.user', 'Old', '', 'User',
                             '$2b$12$hash', 'user', true, CURRENT_TIMESTAMP)"""))
        conn.execute(text("""INSERT INTO projects (id, owner_id, name, description, status, prompt, reference_url, spec,
                             spec_version, tokens, layout, revision, created_at, updated_at) VALUES ('pr1', 'u1', 'Legacy',
                             '', 'ready', 'p', '', '{}', 1, '{}', '{}', 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""))
        conn.execute(text("""INSERT INTO pages (id, project_id, name, route, position, tree, seo, revision, updated_at)
                             VALUES ('pg1', 'pr1', 'Home', '/', 0, :tree, '{}', 5, CURRENT_TIMESTAMP)"""), {"tree": tree})
        conn.execute(text("""INSERT INTO agent_runs (id, project_id, user_id, kind, status, progress, message, steps,
                             result, error, created_at) VALUES ('r1', 'pr1', 'u1', 'generate', 'succeeded', 100, 'done',
                             '[]', '{}', '', CURRENT_TIMESTAMP)"""))

    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT email FROM users WHERE id='u1'")).scalar() == "old@example.com"
        assert conn.execute(text("SELECT revision FROM projects WHERE id='pr1'")).scalar() == 3
        assert conn.execute(text("SELECT active_run_id FROM projects WHERE id='pr1'")).scalar() is None
        assert conn.execute(text("SELECT revision FROM pages WHERE id='pg1'")).scalar() == 5
        row = conn.execute(text("SELECT attempts, max_attempts, timeout_seconds, cancel_requested, worker_id "
                                "FROM agent_runs WHERE id='r1'")).one()
        assert (row[0], row[1], row[2], bool(row[3]), row[4]) == (0, 2, 900, False, "")
    assert "platform_settings" in inspect(engine).get_table_names()

    command.downgrade(cfg, "0001")  # rollback path keeps pre-existing data
    with engine.connect() as conn:
        assert conn.execute(text("SELECT name FROM projects WHERE id='pr1'")).scalar() == "Legacy"
    assert "platform_settings" not in inspect(engine).get_table_names()
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM pages")).scalar() == 1
    engine.dispose()


def test_models_match_migrations(db_url):
    """Fails if models.py changed without a migration (same check as `alembic check`)."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    import models  # noqa: F401
    from db import Base
    command.upgrade(_cfg(db_url), "head")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == [], diff
