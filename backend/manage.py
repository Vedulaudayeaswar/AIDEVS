"""AIDevs admin CLI.

  python manage.py migrate                 # apply database migrations (also runs on app start)
  python manage.py makemigration "message" # autogenerate a migration after editing models.py
  python manage.py users                   # list accounts
  python manage.py usage                   # AI usage per user (last 24h)
  python manage.py prune-tokens            # delete expired refresh/revoked tokens
  python manage.py backup out.json         # JSON backup of all projects (portable across SQLite/Postgres)
  python manage.py gen-secret              # print a strong JWT_SECRET_KEY
  python manage.py worker [concurrency]    # dedicated job worker (set RUN_WORKER_IN_PROCESS=0 on web)
  python manage.py make-admin EMAIL        # grant the admin role
  python manage.py restore backup.json     # restore projects from `backup` (skips ids that exist)
"""
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

from config import Config  # noqa: E402


def _session():
    import db
    import models  # noqa: F401
    db.init_engine(Config.SQLALCHEMY_DATABASE_URI)
    return db.SessionFactory()


def migrate():
    from app import run_migrations
    run_migrations(Config.SQLALCHEMY_DATABASE_URI)
    print("Database is up to date.")


def makemigration(message):
    from alembic import command
    from alembic.config import Config as AlembicConfig
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = AlembicConfig(os.path.join(here, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "migrations"))
    cfg.set_main_option("sqlalchemy.url", Config.SQLALCHEMY_DATABASE_URI.replace("%", "%%"))
    command.revision(cfg, message=message, autogenerate=True)


def users():
    from sqlalchemy import func, select
    from models import Project, User
    s = _session()
    rows = s.execute(select(User, func.count(Project.id)).outerjoin(Project).group_by(User.id)
                     .order_by(User.created_at)).all()
    for user, count in rows:
        print(f"{user.created_at:%Y-%m-%d}  {user.email:<36} {user.username:<24} projects={count}")
    print(f"{len(rows)} user(s)")


def usage():
    from sqlalchemy import func, select
    from models import UsageRecord, User
    s = _session()
    since = datetime.now(timezone.utc) - timedelta(days=1)
    rows = s.execute(select(User.email, func.count(UsageRecord.id),
                            func.sum(UsageRecord.prompt_tokens + UsageRecord.completion_tokens))
                     .join(UsageRecord, UsageRecord.user_id == User.id)
                     .where(UsageRecord.created_at >= since).group_by(User.email)).all()
    for email, count, tokens in rows:
        print(f"{email:<36} requests={count:<5} tokens={tokens or 0}")


def prune_tokens():
    from sqlalchemy import delete
    from models import RefreshToken, RevokedAccessToken
    s = _session()
    now = datetime.now(timezone.utc)
    a = s.execute(delete(RefreshToken).where(RefreshToken.expires_at < now)).rowcount
    b = s.execute(delete(RevokedAccessToken).where(RevokedAccessToken.expires_at < now)).rowcount
    s.commit()
    print(f"Deleted {a} expired refresh tokens and {b} expired revocations.")


def backup(path):
    from sqlalchemy import select
    from models import Project
    from services.versions import capture
    s = _session()
    data = [{"id": p.id, "owner_id": p.owner_id, **capture(p)} for p in s.scalars(select(Project))]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"exported_at": datetime.now(timezone.utc).isoformat(), "projects": data}, fh)
    print(f"Wrote {len(data)} project(s) to {path}")


def worker(concurrency):
    import db
    import models  # noqa: F401
    import agents.studio.orchestrator  # noqa: F401  (registers job handlers)
    from services.logging_setup import configure
    from services.jobs import release_stale_locks, worker_loop
    configure(Config.IS_PRODUCTION)
    db.init_engine(Config.SQLALCHEMY_DATABASE_URI)
    release_stale_locks()
    worker_loop(concurrency=concurrency)


def make_admin(email):
    from sqlalchemy import select
    from models import User
    s = _session()
    user = s.scalar(select(User).where(User.email == email.lower()))
    if not user:
        sys.exit(f"No user with email {email}")
    user.role = "admin"
    s.commit()
    print(f"{email} is now an admin.")


def restore(path):
    """Restore projects from a JSON backup. Existing project ids are left untouched;
    projects whose owner no longer exists are skipped (reported)."""
    from models import Entity, Page, Project, User
    s = _session()
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    restored, skipped = 0, []
    for p in data.get("projects", []):
        if s.get(Project, p["id"]):
            skipped.append(f"{p['id']} (already exists)")
            continue
        if not s.get(User, p["owner_id"]):
            skipped.append(f"{p['id']} (owner missing)")
            continue
        project = Project(id=p["id"], owner_id=p["owner_id"], name=p["name"], description=p.get("description", ""),
                          spec=p.get("spec") or {}, tokens=p.get("tokens") or {}, layout=p.get("layout") or {},
                          status="ready")
        s.add(project)
        for pg in p.get("pages", []):
            s.add(Page(project_id=project.id, name=pg["name"], route=pg["route"], position=pg.get("position", 0),
                       tree=pg["tree"], seo=pg.get("seo") or {}))
        for e in p.get("entities", []):
            s.add(Entity(project_id=project.id, name=e["name"], label=e["label"], fields=e["fields"],
                         permissions=e["permissions"], sample_data=e.get("sample_data") or [],
                         position=e.get("position", 0)))
        restored += 1
    s.commit()
    print(f"Restored {restored} project(s).")
    for item in skipped:
        print(f"Skipped {item}")
    return restored, skipped


if __name__ == "__main__":
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    commands = {"migrate": migrate, "users": users, "usage": usage, "prune-tokens": prune_tokens,
                "gen-secret": lambda: print(secrets.token_urlsafe(48)),
                "makemigration": lambda: makemigration(args[0] if args else "schema change"),
                "backup": lambda: backup(args[0] if args else "aidevs-backup.json"),
                "restore": lambda: restore(args[0]),
                "worker": lambda: worker(int(args[0]) if args else Config.AI_MAX_CONCURRENT_JOBS),
                "make-admin": lambda: make_admin(args[0])}
    if cmd not in commands:
        print(__doc__)
        sys.exit(1)
    commands[cmd]()
