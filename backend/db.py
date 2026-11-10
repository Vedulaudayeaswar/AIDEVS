"""Database engine / session management (SQLAlchemy 2.x, no Flask-SQLAlchemy)."""
import logging
import os
import time
from contextlib import contextmanager
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


engine = None
SessionFactory = sessionmaker(autoflush=False, expire_on_commit=False)
# Request-scoped session (one per thread/greenlet, removed at request teardown).
SessionLocal = scoped_session(SessionFactory)


log = logging.getLogger("aidevs.db")


def normalize_url(url):
    """Accept the connection strings providers hand out (Render, Neon, Heroku style).

    * postgres:// -> postgresql://
    * Neon (and DB_SSLMODE) -> sslmode=require unless the URL already sets it
    * drops `channel_binding`, which older libpq builds reject
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if not url.startswith("postgresql"):
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    wanted = os.getenv("DB_SSLMODE") or ("require" if (parts.hostname or "").endswith((".neon.tech", ".neon.build"))
                                         else None)
    if wanted and "sslmode" not in query:
        query["sslmode"] = wanted
    query.pop("channel_binding", None)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def init_engine(url):
    """Create the engine for `url` and bind the session factory to it."""
    global engine
    url = normalize_url(url)
    kwargs = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        else:
            path = url.replace("sqlite:///", "", 1)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not url.startswith("sqlite"):
        # Small pool for free-tier PostgreSQL (Neon free / pooled endpoints): a single web
        # process needs few connections. Recycle before Neon's 5-minute scale-to-zero drops
        # idle sessions; pre-ping replaces connections broken by a suspend/resume.
        kwargs.update(pool_size=int(os.getenv("DB_POOL_SIZE", "3")), max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "2")),
                      pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "240")), pool_timeout=30,
                      connect_args={"connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "15")),
                                    "keepalives": 1, "keepalives_idle": 30, "keepalives_interval": 10,
                                    "keepalives_count": 3, "application_name": "aidevs"})
    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=30000")
            if url not in ("sqlite://", "sqlite:///:memory:"):
                cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    SessionLocal.remove()
    SessionFactory.configure(bind=engine)
    return engine


def wait_for_db(attempts=None, delay=2.0):
    """Block until the database accepts connections (serverless PostgreSQL may need a few
    seconds to wake from scale-to-zero). Exponential backoff, bounded."""
    from sqlalchemy import text
    attempts = attempts or int(os.getenv("DB_WAIT_ATTEMPTS", "8"))
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            if attempt > 1:
                log.info("database reachable after %d attempts", attempt)
            return True
        except Exception as exc:  # OperationalError while the compute wakes up
            if attempt == attempts:
                log.error("database unreachable after %d attempts: %s", attempts, exc.__class__.__name__)
                raise
            sleep = min(15.0, delay * (2 ** (attempt - 1)))
            log.warning("database not ready (%s); retrying in %.0fs", exc.__class__.__name__, sleep)
            time.sleep(sleep)
    return False


def get_session():
    return SessionLocal()


@contextmanager
def session_scope():
    """Independent transactional session (background jobs, usage accounting).

    Never shares state with the request-scoped session, so committing here can
    not close or flush a request that is still in progress."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
